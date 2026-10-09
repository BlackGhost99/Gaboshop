"""Confirmation des paiements en ligne SingPay en interrogeant SingPay lui-même.

SingPay ne signe pas ses notifications (callbacks) : n'importe qui pourrait en envoyer une fausse.
Une notification non signée n'est donc qu'un signal « va vérifier » : le serveur interroge l'API
SingPay avec ses propres clés, sur l'identifiant de transaction qu'il a lui-même reçu au lancement
du paiement, et seule cette réponse confirme ou refuse un paiement.
"""
import logging
from decimal import Decimal, InvalidOperation

from django.core.cache import cache
from django.db import transaction as db_transaction
from django.utils import timezone

from core.models import AuditLog
from .models import Payment, PaymentIntent
from .references import PAID_REFERENCE_KEY, order_number_from_reference, payment_references
from .utils import call_singpay_status, call_singpay_transaction_by_reference

logger = logging.getLogger(__name__)

SUCCESS_WORDS = {'SUCCESS', 'SUCCESSFUL', 'SUCCEEDED', 'COMPLETED', 'APPROVED'}
FAILED_WORDS = {
    'FAILED', 'FAILURE', 'ERROR', 'KO', 'TIMEOUT', 'TIMEOUTERROR', 'CANCELLED', 'CANCELED',
    'REFUSED', 'REJECTED', 'EXPIRED', 'PASSWORDERROR', 'BALANCEERROR',
}
SUCCESS_CODES = {'00', 'TS'}
FAILED_CODES = {'TF'}
PENDING_STEPS = {'START', 'PARTENAIRE', 'DISBURSEMENT', 'PENDING', 'PROCESSING', 'INITIATED'}
# Étape SingPay « Refund » : l'argent est rendu au client, le paiement n'a pas abouti.
FAILED_STEPS = {'REFUND'}
FINAL_PAYMENT_STATUSES = ('success', 'refunded')
# Identifiants internes jamais envoyés à SingPay (lancement échoué, mode simulation).
LOCAL_ID_PREFIXES = ('PAY-', 'AIRTEL_', 'MOOV_')
CHECK_INTERVAL_SECONDS = 5


def _upper(value):
    return str(value or '').strip().upper()


def read_singpay_status(response):
    """Lit une réponse de l'API SingPay -> (outcome, amount, reference).

    outcome vaut 'success', 'failed', 'pending' ou 'unknown' (erreur d'appel, réponse illisible).
    Volontairement strict : « status.success = true » signifie seulement que l'appel a abouti,
    pas que le client a payé.
    """
    if not isinstance(response, dict) or response.get('error'):
        return 'unknown', None, None
    body = response.get('paymentResult') or response.get('paiementResult') or response
    if not isinstance(body, dict):
        return 'unknown', None, None
    tx = body.get('transaction') if isinstance(body.get('transaction'), dict) else {}
    status_block = body.get('status') if isinstance(body.get('status'), dict) else {}
    top = _upper(body.get('status')) if isinstance(body.get('status'), str) else ''
    result = _upper(tx.get('result') or body.get('result'))
    step = _upper(tx.get('status'))
    code = _upper(status_block.get('code') or status_block.get('result_code'))
    amount = tx.get('amount', body.get('amount'))
    reference = tx.get('reference') or body.get('reference')

    if result in SUCCESS_WORDS or code in SUCCESS_CODES or top in SUCCESS_WORDS:
        return 'success', amount, reference
    if result in FAILED_WORDS or code in FAILED_CODES or top in FAILED_WORDS or step in FAILED_STEPS:
        return 'failed', amount, reference
    if step in PENDING_STEPS or top in PENDING_STEPS:
        return 'pending', amount, reference
    return 'unknown', amount, reference


def amount_matches(amount, expected):
    """Montant absent : accepté, l'identifiant interrogé vient de notre propre appel à SingPay."""
    if amount in (None, ''):
        return True
    try:
        received = Decimal(str(amount)).quantize(Decimal('0.01'))
        return received == Decimal(str(expected)).quantize(Decimal('0.01'))
    except (InvalidOperation, TypeError, ValueError):
        return False


def _ask_singpay(transaction_ids):
    outcome, amount, reference, raw = 'unknown', None, None, {}
    for tx_id in transaction_ids:
        raw = call_singpay_status(tx_id)
        outcome, amount, reference = read_singpay_status(raw)
        if outcome != 'unknown':
            break
    return outcome, amount, reference, raw if isinstance(raw, dict) else {}


OUTCOME_RANK = {'success': 3, 'pending': 2, 'failed': 1, 'unknown': 0}


def _transactions_in(value, depth=0):
    """Transactions (dictionnaires) contenues dans une réponse de recherche SingPay, quelle que soit sa forme."""
    if depth > 3:
        return []
    if isinstance(value, list):
        return [tx for item in value for tx in _transactions_in(item, depth + 1)]
    if not isinstance(value, dict):
        return []
    if value.get('reference') and (value.get('id') or value.get('_id')):
        return [value]
    found = []
    for key in ('transaction', 'transactions', 'data', 'results', 'items'):
        found += _transactions_in(value.get(key), depth + 1)
    return found


def singpay_ids_for_reference(reference):
    """Identifiants SingPay des transactions portant exactement notre référence (GABOSHOP_<commande>[_<essai>]).

    Sert quand SingPay a répondu par une erreur au lancement mais a quand même créé la transaction.
    La recherche ne décide de rien : chaque identifiant est ensuite vérifié sur l'API de statut.
    """
    raw = call_singpay_transaction_by_reference(reference)
    if not isinstance(raw, (dict, list)) or (isinstance(raw, dict) and raw.get('error')):
        return []
    ids = []
    for tx in _transactions_in(raw):
        tx_id = str(tx.get('id') or tx.get('_id') or '').strip()
        if str(tx.get('reference')) == reference and tx_id and tx_id not in ids:
            ids.append(tx_id)
    return ids


def _best_singpay_answer(transaction_ids):
    """Plusieurs essais pour une même commande : un seul réussi suffit (succès > en cours > échec)."""
    best = ('unknown', None, None, {})
    for tx_id in transaction_ids:
        raw = call_singpay_status(tx_id)
        outcome, amount, reference = read_singpay_status(raw)
        if OUTCOME_RANK[outcome] > OUTCOME_RANK[best[0]]:
            best = (outcome, amount, reference, raw if isinstance(raw, dict) else {})
        if outcome == 'success':
            break
    return best


def check_allowed(key):
    """Au plus une interrogation de SingPay toutes les quelques secondes par paiement."""
    try:
        return cache.add(f'singpay-check:{key}', 1, CHECK_INTERVAL_SECONDS)
    except Exception:  # cache indisponible : on ne bloque pas la vérification
        return True


# --- Paiements de commandes ---------------------------------------------------------------

def order_transaction_ids(payment):
    ids = []
    for value in (payment.transaction_id, payment.operator_reference):
        value = (value or '').strip()
        if not value or value in ids or value.upper() in ('AIRTEL', 'MOOV'):
            continue
        if value.upper().startswith(LOCAL_ID_PREFIXES):
            continue
        ids.append(value)
    return ids


def _notify(method, *args):
    """Notification après validation en base ; un échec d'envoi ne touche jamais au paiement."""
    try:
        from notifications.service import NotificationService
        getattr(NotificationService, method)(*args)
    except Exception:
        logger.exception('Notification %s impossible', method)


def mark_order_payment_success(payment, reason, user=None, ip_address=None, user_agent=''):
    """Paiement réussi -> commande confirmée. À appeler dans une transaction, paiement verrouillé."""
    payment.status = 'success'
    payment.completed_at = timezone.now()
    payment.save(update_fields=['status', 'completed_at', 'webhook_data', 'updated_at'])

    order = payment.order
    db_transaction.on_commit(lambda: _notify('notify_payment_success', order, payment))
    if order.status in ('created', 'pending_payment', 'paid'):
        order.status = 'confirmed'
        order.confirmed_at = timezone.now()
        order.save(update_fields=['status', 'updated_at', 'confirmed_at'])
    else:
        # Commande annulée entre-temps : l'argent est arrivé, un admin doit rembourser.
        logger.error('Paiement %s reçu pour la commande %s au statut %s', payment.pk, order.order_number, order.status)

    AuditLog.log_action(
        action_type='payment_completed',
        user=user or order.client,
        object_type='payment',
        object_id=payment.id,
        old_value='pending',
        new_value='success',
        ip_address=ip_address,
        user_agent=user_agent,
        reason=reason,
    )


def verify_order_payment(payment, source, user=None, ip_address=None):
    """Interroge SingPay pour ce paiement de commande et applique sa réponse.

    Renvoie le statut du paiement après vérification.
    """
    if payment.status in FINAL_PAYMENT_STATUSES:
        return payment.status
    ids = order_transaction_ids(payment)
    outcome, amount, reference, raw = _ask_singpay(ids) if ids else ('unknown', None, None, {})
    if outcome in ('unknown', 'failed'):
        # Lancement en erreur (aucun identifiant) ou essai échoué : SingPay a pu créer une autre
        # transaction pour cette commande, que le client a validée. On la cherche par la référence.
        others = []
        for ref in payment_references(payment):
            others += [i for i in singpay_ids_for_reference(ref) if i not in ids and i not in others]
        if others:
            found = _best_singpay_answer(others)
            if OUTCOME_RANK[found[0]] > OUTCOME_RANK[outcome]:
                outcome, amount, reference, raw = found
    if not ids and outcome == 'unknown':
        return payment.status

    with db_transaction.atomic():
        payment = Payment.objects.select_for_update().select_related('order').get(pk=payment.pk)
        if payment.status in FINAL_PAYMENT_STATUSES:
            return payment.status
        payment.webhook_data = {
            **(payment.webhook_data or {}),
            'singpay_verification': {
                'source': source, 'at': timezone.now().isoformat(), 'outcome': outcome, 'response': raw,
            },
        }
        order = payment.order

        if outcome == 'success':
            reference_ok = not reference or order.order_number in str(reference)
            if not amount_matches(amount, payment.amount) or not reference_ok:
                payment.save(update_fields=['webhook_data', 'updated_at'])
                logger.error('Paiement %s : montant ou référence SingPay incohérents (%s, %s)', payment.pk, amount, reference)
                AuditLog.log_action(
                    action_type='payment_failed', user=order.client, object_type='payment', object_id=payment.id,
                    old_value=payment.status, new_value=payment.status, ip_address=ip_address,
                    reason=f'SingPay : montant {amount} ou référence {reference} incohérents', is_suspicious=True,
                )
                return payment.status
            if reference:
                payment.webhook_data[PAID_REFERENCE_KEY] = str(reference)
            mark_order_payment_success(payment, f'Paiement vérifié auprès de SingPay ({source})', user, ip_address)
        elif outcome == 'failed':
            newly_failed = payment.status != 'failed'
            payment.status = 'failed'
            payment.save(update_fields=['status', 'webhook_data', 'updated_at'])
            if newly_failed:
                db_transaction.on_commit(lambda: _notify('notify_payment_failed', order, payment, raw))
        elif outcome == 'pending':
            payment.status = 'processing'
            payment.save(update_fields=['status', 'webhook_data', 'updated_at'])
        else:
            payment.save(update_fields=['webhook_data', 'updated_at'])
        return payment.status


def find_order_payment(transaction_ids, reference):
    """Retrouve le paiement d'une commande à partir d'une notification (données non fiables)."""
    ids = [str(value).strip() for value in transaction_ids if value]
    if ids:
        payment = Payment.objects.select_related('order').filter(transaction_id__in=ids).first()
        if payment:
            return payment
    order_number = order_number_from_reference(reference)
    if order_number:
        return Payment.objects.select_related('order').filter(order__order_number=order_number).first()
    return None


# --- Paiements d'abonnement (PaymentIntent) -----------------------------------------------

def intent_transaction_ids(intent):
    """Identifiants SingPay enregistrés par notre serveur au lancement du paiement."""
    raw = intent.raw_response if isinstance(intent.raw_response, dict) else {}
    tx = raw.get('transaction') if isinstance(raw.get('transaction'), dict) else {}
    ids = []
    for value in (tx.get('id'), tx.get('_id'), tx.get('airtel_money_id'), raw.get('id'), raw.get('_id')):
        value = str(value or '').strip()
        if value and value not in ids:
            ids.append(value)
    return ids


def verify_intent(intent):
    """Interroge SingPay pour un paiement d'abonnement -> (outcome, provider_tx_id, raw).

    outcome vaut 'mismatch' si SingPay annonce un succès avec un autre montant ou une autre référence.
    """
    ids = intent_transaction_ids(intent)
    if not ids:
        return 'unknown', None, {}
    outcome, amount, reference, raw = _ask_singpay(ids)
    if outcome == 'success':
        reference_ok = not reference or str(reference) == intent.reference
        if not amount_matches(amount, intent.amount) or not reference_ok:
            return 'mismatch', ids[0], raw
    return outcome, ids[0], raw


def find_intent(reference):
    if not reference:
        return None
    return PaymentIntent.objects.filter(reference=str(reference)).first()
