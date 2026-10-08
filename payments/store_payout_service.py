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
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from orders.models import Order
from .models import Payment, StorePayout
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
    delivery = Decimal(order.delivery_fee) if order.store.offers_delivery else Decimal('0')
    amount = max(Decimal('0'), products - commission) + delivery
    return products, commission, delivery, amount.quantize(Decimal('0.01'))


def _provider_amount(amount):
    return int(amount) if amount == amount.to_integral_value() else float(amount)


def release_store_payment(order_id):
    """Crée (ou relance) le versement du commerce pour une commande. Idempotent."""
    try:
        with transaction.atomic():
            order = Order.objects.select_for_update().select_related('store').get(pk=order_id)
            if not collected_by_platform(order):
                return None
            payout = StorePayout.objects.select_for_update().filter(order=order).first()
            if payout and payout.status in FINAL_STATUSES:
                return payout

            products, commission, delivery, amount = compute_store_share(order)
            # SingPay verse vers un décaissement enregistré dans l'espace marchand de Gaboshop
            # (le code agent ou le numéro Mobile Money indiqué par le commerce), jamais vers un simple numéro.
            disbursement_id = (order.store.singpay_disbursement_id or '').strip()
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
            if not disbursement_id:
                payout.status, payout.note = 'pending', 'Identifiant de décaissement SingPay du commerce manquant'
                payout.save()
                return payout
            if not getattr(settings, 'SINGPAY_ENABLE_TRANSFER', False):
                payout.status, payout.note = 'pending', 'Transferts automatiques désactivés : versement manuel'
                payout.save()
                return payout

            payout.status, payout.note = 'processing', ''
            payout.attempts += 1
            payout.save()
            # SingPay retrouve l'encaissement à reverser par sa référence marchande.
            reference, amount_to_send = f'GABOSHOP_{order.order_number}', _provider_amount(payout.amount)
    except Exception:
        logger.exception('Versement commerce : préparation impossible (commande %s)', order_id)
        return None

    # Appel fournisseur hors transaction : l'état "processing" est déjà validé en base.
    try:
        response = call_singpay_transfer(
            reference=reference,
            disbursement=disbursement_id,
            amount=amount_to_send,
            portefeuille=getattr(settings, 'SINGPAY_WALLET_ID', ''),
        )
        error = response.get('error') if isinstance(response, dict) else 'Réponse invalide'
    except Exception as exc:  # réseau, configuration...
        response, error = {}, str(exc)

    with transaction.atomic():
        payout = StorePayout.objects.select_for_update().get(pk=payout.pk)
        payout.provider_response = response if isinstance(response, dict) else {}
        if error:
            payout.status, payout.note = 'failed', str(error)[:255]
            logger.error('Versement commerce %s échoué : %s', payout.reference, error)
        else:
            payout.status, payout.note, payout.paid_at = 'paid', '', timezone.now()
        payout.save()
    return payout


def schedule_store_payment(order_id):
    """À appeler depuis un signal : exécute le versement après validation de la transaction courante."""
    transaction.on_commit(lambda: release_store_payment(order_id))
