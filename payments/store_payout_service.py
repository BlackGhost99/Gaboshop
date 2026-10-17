"""Versement de la part du commerce lorsque Gaboshop a encaissé la commande en ligne.

Déclencheur : le commerce confirme la commande (passage au statut ``preparing``).
Le versement du livreur reste déclenché séparément par la confirmation de livraison
(``PaymentService.payout_delivery_agent``), sauf si le commerce gère sa livraison :
la part livraison est alors incluse ici, en un seul versement.

Garanties :
- un seul ``StorePayout`` par commande (contrainte d'unicité) -> pas de double versement ;
- l'état ``processing`` est validé en base *avant* l'appel au fournisseur, donc un incident
  entre l'appel et l'enregistrement du résultat bloque un second versement au lieu de le permettre ;
- montants en ``Decimal``, figés à la création (la commission est celle de la commande) ;
- aucune exception ne remonte à l'appelant : une commande ne doit jamais échouer à cause d'un versement.
"""
import logging
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from orders.models import Order
from .models import Payment, StorePayout
from .configuration import payments_simulated, transfers_enabled
from .references import base_reference, paid_reference
from .utils import call_singpay_transfer

logger = logging.getLogger(__name__)

ONLINE_SUCCESS = ('success', 'completed')
FINAL_STATUSES = ('processing', 'paid', 'skipped')


def collected_by_platform(order):
    """Gaboshop détient l'argent : paiement en ligne réussi, hors circuits manuels et B2B."""
    if order.is_b2b or order.status in ('cancelled', 'refunded'):
        return False
    arrangement = getattr(order, 'payment_arrangement', None)
    if arrangement is not None and arrangement.flow != 'platform_online':
        return False
    return Payment.objects.filter(order=order, status__in=ONLINE_SUCCESS).exists()


def compute_store_share(order):
    """Part du commerce : produits - commission figée, + livraison si le commerce livre lui-même."""
    products = Decimal(order.items_total)
    commission = Decimal(order.commission_amount)
    from .direct_service import store_delivers
    delivery = Decimal(order.delivery_fee) if store_delivers(order) else Decimal('0')
    amount = max(Decimal('0'), products - commission) + delivery
    # FCFA sans centimes : franc entier
    return products, commission, delivery, amount.quantize(Decimal('1'), rounding=ROUND_HALF_UP)


def _provider_amount(amount):
    return int(amount) if amount == amount.to_integral_value() else float(amount)


FROZEN_NOTE = 'Versements gelés par Gaboshop'
# Issue inconnue (délai dépassé, coupure réseau...) : le transfert a pu partir, on ne relance pas à l'aveugle.
VERIFY_NOTE = 'Issue inconnue, à vérifier auprès de SingPay avant toute relance'
PROBLEM_NOTE = 'Problème signalé par le client : versement retenu'


def needs_verification(payout):
    return payout.status == 'failed' and (payout.note or '').startswith(VERIFY_NOTE)


def payout_blocked(order, admin_override=False):
    """Raison de ne pas verser (commande annulée ou litige client), sinon ''."""
    if order.status in ('cancelled', 'refunded'):
        return 'Commande annulée ou remboursée'
    if order.client_problem_reported_at and not admin_override:
        return PROBLEM_NOTE
    return ''


def transfer_error_is_certain(response, exc=None):
    """Vrai si SingPay a clairement refusé (aucun argent parti) ; faux si l'issue est inconnue."""
    if exc is not None or not isinstance(response, dict):
        return False
    error = str(response.get('error') or '')
    if 'request failed' in error.lower():  # délai dépassé, réseau
        return False
    if error.startswith('SingPay HTTP '):
        try:
            return int(error.split()[2]) < 500
        except (IndexError, ValueError):
            return False
    return True


_SUCCESS = {'success', 'successful', 'succeeded', 'completed', 'complete', 'done', 'ok', 'paid', 'terminated', 'terminee', 'terminée'}
_FAILURE = {'failed', 'failure', 'error', 'refused', 'rejected', 'cancelled', 'canceled', 'echec', 'échec', 'expired'}


def _walk(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


def find_transfer(reference, disbursement, amount):
    """Cherche chez SingPay un transfert déjà fait : 'paid', 'absent' ou 'unknown'."""
    from . import utils
    try:
        data = utils.call_singpay_transfers_by_reference(reference)
    except Exception:
        logger.exception('Vérification du transfert %s impossible', reference)
        return 'unknown'
    if not isinstance(data, dict):
        return 'unknown'
    if data.get('error'):
        return 'absent' if str(data.get('error')).startswith('SingPay HTTP 404') else 'unknown'
    try:
        wanted = Decimal(str(amount)).quantize(Decimal('1'))
    except Exception:
        return 'unknown'
    verdict = 'absent'
    for item in _walk(data):
        target = item.get('disbursement') or item.get('disbursementId') or item.get('disbursement_id')
        if isinstance(target, dict):
            target = target.get('id') or target.get('_id')
        if str(target or '').strip() != str(disbursement).strip():
            continue
        try:
            same_amount = Decimal(str(item.get('amount'))).quantize(Decimal('1')) == wanted
        except Exception:
            same_amount = False
        if not same_amount:
            continue
        state = str(item.get('status') or item.get('result') or item.get('state') or '').strip().lower()
        if state in _SUCCESS:
            return 'paid'
        if state not in _FAILURE:
            verdict = 'unknown'  # transfert trouvé mais encore en cours : on attend
    return verdict


def release_store_payment(order_id, admin_override=False, admin_retry=False):
    """Crée (ou relance) le versement du commerce pour une commande. Idempotent.

    ``admin_override`` : l'admin a vérifié le litige signalé par le client.
    ``admin_retry`` : l'admin relance un versement à l'issue inconnue (après vérification SingPay).
    """
    verify = None
    try:
        with transaction.atomic():
            order = Order.objects.select_for_update().select_related('store').get(pk=order_id)
            if not collected_by_platform(order) or payout_blocked(order, admin_override):
                return None
            payout = StorePayout.objects.select_for_update().filter(order=order).first()
            if payout and payout.status in FINAL_STATUSES:
                return payout
            if payout and needs_verification(payout):
                # Jamais renvoyé automatiquement : on regarde d'abord si SingPay a déjà versé.
                verify = (payout.pk, payout.agent_code, payout.amount)
    except Exception:
        logger.exception('Versement commerce : préparation impossible (commande %s)', order_id)
        return None

    if verify is not None:
        payout = _reconcile_store_payout(order_id, verify, admin_retry)
        if payout is not None:
            return payout

    try:
        with transaction.atomic():
            order = Order.objects.select_for_update().select_related('store').get(pk=order_id)
            if not collected_by_platform(order) or payout_blocked(order, admin_override):
                return None
            payout = StorePayout.objects.select_for_update().filter(order=order).first()
            if payout and (payout.status in FINAL_STATUSES or needs_verification(payout)):
                return payout

            products, commission, delivery, amount = compute_store_share(order)
            # SingPay verse vers un décaissement enregistré dans l'espace marchand de Gaboshop
            # (le code agent ou le numéro Mobile Money indiqué par le commerce), jamais vers un simple numéro.
            disbursement_id = (order.store.singpay_disbursement_id or '').strip()
            if not disbursement_id and payments_simulated():
                disbursement_id = 'SIMULATION'  # site de test : versement simulé
            if payout is None:
                payout = StorePayout.objects.create(
                    order=order, store=order.store, amount=amount, products_amount=products,
                    commission_amount=commission, delivery_amount=delivery,
                    includes_delivery=delivery > 0, agent_code=disbursement_id,
                    reference=f'STOREPAY_{order.pk}',
                )
            else:
                payout.agent_code = disbursement_id

            if amount <= 0:
                payout.status, payout.note = 'skipped', 'Montant nul'
                payout.save()
                return payout
            if order.store.payouts_frozen:
                payout.status, payout.note = 'pending', FROZEN_NOTE
                payout.save()
                return payout
            if not disbursement_id:
                changed = payout.status != 'pending' or payout.note != 'Identifiant de décaissement SingPay du commerce manquant'
                payout.status, payout.note = 'pending', 'Identifiant de décaissement SingPay du commerce manquant'
                payout.save()
                if changed:
                    transaction.on_commit(lambda p=payout: _notify_store(p))
                return payout
            if not transfers_enabled():
                changed = payout.status != 'pending' or payout.note != 'Transferts automatiques désactivés : versement manuel'
                payout.status, payout.note = 'pending', 'Transferts automatiques désactivés : versement manuel'
                payout.save()
                if changed:
                    transaction.on_commit(lambda p=payout: _notify_store(p))
                return payout

            payout.status, payout.note = 'processing', ''
            payout.attempts += 1
            payout.save()
            # SingPay retrouve l'encaissement à reverser par sa référence marchande (celle de l'essai réussi).
            paid = Payment.objects.filter(order=order, status__in=ONLINE_SUCCESS).first()
            reference = paid_reference(paid) if paid else base_reference(order.order_number)
            amount_to_send = _provider_amount(payout.amount)
    except Exception:
        logger.exception('Versement commerce : préparation impossible (commande %s)', order_id)
        return None

    # Appel fournisseur hors transaction : l'état "processing" est déjà validé en base.
    exc = None
    try:
        response = call_singpay_transfer(
            reference=reference,
            disbursement=disbursement_id,
            amount=amount_to_send,
            portefeuille=getattr(settings, 'SINGPAY_WALLET_ID', ''),
        )
        error = response.get('error') if isinstance(response, dict) else 'Réponse invalide'
    except Exception as e:  # réseau, configuration...
        response, error, exc = {}, str(e), e

    with transaction.atomic():
        payout = StorePayout.objects.select_for_update().get(pk=payout.pk)
        payout.provider_response = response if isinstance(response, dict) else {}
        if error and transfer_error_is_certain(response, exc):
            payout.status, payout.note = 'failed', str(error)[:255]
            logger.error('Versement commerce %s refusé : %s', payout.reference, error)
        elif error:
            payout.status, payout.note = 'failed', f'{VERIFY_NOTE} ({error})'[:255]
            logger.error('Versement commerce %s : issue inconnue, à vérifier : %s', payout.reference, error)
        else:
            payout.status, payout.note, payout.paid_at = 'paid', '', timezone.now()
        payout.save()
    _notify_store(payout)
    return payout


def _reconcile_store_payout(order_id, verify, admin_retry):
    """Versement à l'issue inconnue : rapproché avec SingPay. Renvoie le versement, ou None pour relancer."""
    payout_id, disbursement_id, amount = verify
    paid = Payment.objects.filter(order_id=order_id, status__in=ONLINE_SUCCESS).first()
    if paid is None:
        return StorePayout.objects.get(pk=payout_id)
    found = find_transfer(paid_reference(paid), disbursement_id, amount)
    with transaction.atomic():
        payout = StorePayout.objects.select_for_update().get(pk=payout_id)
        if not needs_verification(payout):
            return payout
        if found == 'paid':
            payout.status, payout.note, payout.paid_at = 'paid', 'Transfert retrouvé chez SingPay', timezone.now()
            payout.save()
            return payout
        if found == 'absent' and admin_retry:
            # Aucun transfert chez SingPay : l'admin peut relancer.
            payout.note = 'Aucun transfert trouvé chez SingPay : relance par l’admin'
            payout.save(update_fields=['note', 'updated_at'])
            return None
        return payout


def _notify_store(payout):
    try:
        from notifications.service import NotificationService
        NotificationService.notify_store_payout(payout)
    except Exception:
        logger.exception('Notification du versement %s impossible', payout.pk)


def payout_moment_reached(order, moment):
    """Un commerce de confiance est payé dès la préparation ; les autres, une fois la réception confirmée."""
    trusted = bool(getattr(order.store, 'is_trusted', False))
    return moment == ('preparing' if trusted else 'client_confirmed')


def schedule_store_payment(order_id):
    """À appeler depuis un signal : exécute le versement après validation de la transaction courante."""
    transaction.on_commit(lambda: release_store_payment(order_id))


def held_funds(store, limit=10):
    """Argent encaissé en ligne par Gaboshop pour ce commerce et pas encore versé : rassure le commerce."""
    from django.db.models import Q
    orders = (
        Order.objects.filter(store=store, is_b2b=False, payment__status__in=ONLINE_SUCCESS)
        .exclude(status__in=('cancelled', 'refunded'))
        .filter(Q(payment_arrangement__isnull=True) | Q(payment_arrangement__flow='platform_online'))
        .exclude(store_payout__status__in=('paid', 'skipped'))
        .select_related('store', 'store_payout')
        .order_by('-created_at')
    )
    total, count, items = Decimal('0'), 0, []
    for order in orders[:200]:
        payout = getattr(order, 'store_payout', None)
        amount = payout.amount if payout else compute_store_share(order)[3]
        if payout and payout.status == 'processing':
            stage = 'Versement en cours'
        elif payout and payout.note == FROZEN_NOTE:
            stage = 'Retenu par Gaboshop (vérification)'
        elif payout:
            stage = 'Versement en préparation'
        elif store.is_trusted:
            stage = 'Versement possible après préparation, sous réserve de vérification'
        else:
            stage = 'Versement à rapprocher après confirmation de livraison'
        total += amount
        count += 1
        if len(items) < limit:
            items.append({'order_id': order.id, 'order_number': order.order_number, 'created_at': order.created_at, 'amount': float(amount), 'stage': stage})
    return {
        'total': float(total), 'count': count, 'items': items,
        'frozen': bool(store.payouts_frozen), 'trusted': bool(store.is_trusted),
    }
