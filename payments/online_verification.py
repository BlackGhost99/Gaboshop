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
from .utils import call_singpay_status

logger = logging.getLogger(__name__)

SUCCESS_WORDS = {'SUCCESS', 'SUCCESSFUL', 'SUCCEEDED', 'COMPLETED', 'APPROVED'}
FAILED_WORDS = {
    'FAILED', 'FAILURE', 'ERROR', 'KO', 'TIMEOUT', 'TIMEOUTERROR', 'CANCELLED', 'CANCELED',
    'REFUSED', 'REJECTED', 'EXPIRED',
}
SUCCESS_CODES = {'00', 'TS'}
FAILED_CODES = {'TF'}
PENDING_STEPS = {'START', 'PARTENAIRE', 'PENDING', 'PROCESSING', 'INITIATED'}
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
    if result in FAILED_WORDS or code in FAILED_CODES or top in FAILED_WORDS:
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


def mark_order_payment_success(payment, reason, user=None, ip_address=None, user_agent=''):
    """Paiement réussi -> commande confirmée. À appeler dans une transaction, paiement verrouillé."""
    payment.status = 'success'
    payment.completed_at = timezone.now()
    payment.save(update_fields=['status', 'completed_at', 'webhook_data', 'updated_at'])

    order = payment.order
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
    if not ids:
        return payment.status
    outcome, amount, reference, raw = _ask_singpay(ids)

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
            mark_order_payment_success(payment, f'Paiement vérifié auprès de SingPay ({source})', user, ip_address)
        elif outcome == 'failed':
            payment.status = 'failed'
            payment.save(update_fields=['status', 'webhook_data', 'updated_at'])
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
    if reference and str(reference).startswith('GABOSHOP_'):
        order_number = str(reference).replace('GABOSHOP_', '', 1).strip()
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
