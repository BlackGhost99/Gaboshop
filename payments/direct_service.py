from decimal import Decimal
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .configuration import available_payment_options, get_payment_policy
from .direct_models import PaymentArrangement, PaymentObligation, PaymentReceipt, PaymentAdjustment, CommissionSettlement, SettlementAllocation


def is_manual_order(order):
    return hasattr(order, 'payment_arrangement') and order.payment_arrangement.flow != 'platform_online'


def _refresh_status(obligation):
    paid = obligation.received_amount
    if obligation.status in ('cancelled', 'waived', 'refunded'):
        return obligation.status
    if paid >= obligation.amount:
        obligation.status = 'paid'
    elif paid > 0:
        obligation.status = 'partially_paid'
    elif obligation.due_at and obligation.due_at < timezone.now():
        obligation.status = 'overdue'
    elif obligation.status != 'not_due':
        obligation.status = 'unpaid'
    obligation.save(update_fields=['status', 'updated_at'])
    return obligation.status


def ensure_credit_limit(store, additional_commission=Decimal('0')):
    policy = get_payment_policy(store)
    debts = PaymentObligation.objects.filter(
        arrangement__store=store, kind='commission'
    ).exclude(status__in=['paid', 'cancelled', 'waived']).prefetch_related('receipts', 'adjustments')
    outstanding = sum((debt.remaining_amount for debt in debts), Decimal('0'))
    if outstanding + Decimal(additional_commission) > Decimal(policy['merchant_debt_limit']):
        raise ValidationError('Plafond de commissions dues atteint pour ce commerce.')


@transaction.atomic
def create_arrangement(order, flow, method, delivery_method=None, user=None):
    if hasattr(order, 'payment_arrangement'):
        return order.payment_arrangement
    policy, options = available_payment_options(order.store, order.delivery_requested)
    if not any(x['flow'] == flow and x['method'] == method for x in options):
        raise ValidationError('Ce circuit ou moyen de paiement n’est pas autorisé pour ce commerce.')
    if flow != 'platform_online':
        ensure_credit_limit(order.store, order.commission_amount)
    arrangement = PaymentArrangement.objects.create(
        order=order, store=order.store, created_by=user or order.client, flow=flow, method=method,
        delivery_method=delivery_method or method, policy_snapshot=policy,
        products_amount=order.items_total, delivery_amount=order.delivery_fee,
        commission_rate=order.commission_rate, commission_amount=order.commission_amount,
    )
    due = timezone.now() + timedelta(days=policy['commission_settlement_days'])
    specs = []
    if flow == 'direct_split':
        specs = [('products', 'client', 'store', order.items_total), ('delivery', 'client', 'courier', order.delivery_fee)]
    elif flow == 'store_collects_all':
        specs = [('products', 'client', 'store', order.items_total), ('delivery_collection', 'client', 'store', order.delivery_fee), ('delivery', 'store', 'courier', order.delivery_fee)]
    elif flow == 'courier_cash':
        specs = [('products', 'client', 'courier', order.items_total), ('delivery', 'client', 'courier', order.delivery_fee), ('courier_remittance', 'courier', 'store', order.items_total)]
    else:
        specs = [('products', 'client', 'platform', order.items_total), ('delivery_collection', 'client', 'platform', order.delivery_fee), ('delivery', 'platform', 'courier', order.delivery_fee)]
    for kind, payer, payee, amount in specs:
        if amount:
            PaymentObligation.objects.create(arrangement=arrangement, kind=kind, payer=payer, payee=payee, amount=amount, status='unpaid', requires_delivery_proof=(kind == 'delivery'))
    PaymentObligation.objects.create(
        arrangement=arrangement, kind='commission', payer='store', payee='platform',
        amount=order.commission_amount,
        status='paid' if flow == 'platform_online' else 'not_due',
        due_at=None if flow == 'platform_online' else due,
    )
    if flow != 'platform_online':
        order.status = 'confirmed'
        order.confirmed_at = timezone.now()
        order.save(update_fields=['status', 'confirmed_at'])
        if hasattr(order, 'delivery'):
            order.delivery.agent_commission = order.delivery_fee
            order.delivery.save(update_fields=['agent_commission'])
    return arrangement


def can_dispatch(order):
    if not hasattr(order, 'payment_arrangement'):
        return True
    arrangement = order.payment_arrangement
    # Mobile Money / virement payé directement au commerce : rien ne part avant la confirmation du paiement.
    # Espèces : payé à la livraison, sauf si la politique exige le paiement avant l'expédition.
    prepaid_method = arrangement.flow != 'platform_online' and arrangement.method != 'cash'
    if not prepaid_method and arrangement.policy_snapshot.get('payment_timing') != 'before_dispatch':
        return True
    required = arrangement.obligations.filter(kind='products').first()
    return not required or _refresh_status(required) == 'paid'


def sync_on_order_status(order):
    if not hasattr(order, 'payment_arrangement'):
        return
    arrangement = order.payment_arrangement
    if order.status == 'delivered':
        commission = arrangement.obligations.filter(kind='commission').first()
        if commission and commission.status == 'not_due':
            commission.status = 'overdue' if commission.due_at and commission.due_at < timezone.now() else 'unpaid'
            commission.save(update_fields=['status', 'updated_at'])
    elif order.status in ('cancelled', 'refunded'):
        arrangement.obligations.filter(kind='commission', status='not_due').update(status='cancelled')


def is_admin_user(user):
    return bool(user and (user.is_superuser or getattr(user, 'user_type', '') == 'admin'))


def role_user_id(obligation, role):
    """Compte qui joue un rôle (client, commerce, livreur) dans la commande de l'obligation."""
    arrangement = obligation.arrangement
    delivery = getattr(arrangement.order, 'delivery', None)
    return {
        'client': arrangement.order.client_id,
        'store': arrangement.store.manager_id,
        'courier': getattr(delivery, 'delivery_agent_id', None),
    }.get(role)


def can_declare(user, obligation):
    # Seuls le payeur et le bénéficiaire déclarent un paiement (jamais un tiers de la commande).
    if is_admin_user(user):
        return True
    return user.id in (role_user_id(obligation, obligation.payer), role_user_id(obligation, obligation.payee))


def can_review(user, obligation):
    # Seul celui qui reçoit l'argent confirme ou refuse ; ce qui est dû à Gaboshop, seul l'admin.
    if is_admin_user(user):
        return True
    if obligation.payee == 'platform':
        return False
    payee_id = role_user_id(obligation, obligation.payee)
    return payee_id is not None and user.id == payee_id


def receipt_payload(receipt):
    return {
        'id': receipt.id, 'receipt_number': receipt.receipt_number, 'amount': str(receipt.amount),
        'method': receipt.method, 'reference': receipt.reference, 'comment': receipt.comment,
        'status': receipt.status, 'rejection_reason': receipt.rejection_reason,
        'declared_by_payee': receipt.actor_id == role_user_id(receipt.obligation, receipt.obligation.payee),
        'created_at': receipt.created_at,
    }


def payment_summary(value, user=None):
    arrangement = value if isinstance(value, PaymentArrangement) else getattr(value, 'payment_arrangement', None)
    if not arrangement:
        return None
    obligations = []
    for obligation in arrangement.obligations.all():
        _refresh_status(obligation)
        item = {'id': obligation.id, 'kind': obligation.kind, 'payer': obligation.payer, 'payee': obligation.payee, 'amount': str(obligation.amount), 'received_amount': str(obligation.received_amount), 'remaining_amount': str(obligation.remaining_amount), 'status': obligation.status, 'due_at': obligation.due_at}
        if user is not None:
            item['can_declare'] = can_declare(user, obligation)
            item['can_review'] = can_review(user, obligation)
            item['i_am_payer'] = user.id == role_user_id(obligation, obligation.payer)
            item['i_am_payee'] = user.id == role_user_id(obligation, obligation.payee)
            item['receipts'] = [receipt_payload(r) for r in obligation.receipts.all()]
        obligations.append(item)
    order = arrangement.order
    live = ((arrangement.store.payment_preferences or {}).get('instructions') or {}).get(arrangement.method, '')
    instructions = live or (arrangement.policy_snapshot.get('instructions') or {}).get(arrangement.method, '')
    summary = {
        'id': arrangement.id, 'flow': arrangement.flow, 'method': arrangement.method,
        'order_id': order.id, 'order_number': order.order_number, 'is_b2b': getattr(order, 'is_b2b', False),
        'store_name': arrangement.store.name, 'store_phone': arrangement.store.phone,
        'instructions': instructions,
        'products_amount': str(arrangement.products_amount), 'delivery_amount': str(arrangement.delivery_amount), 'commission_rate': str(arrangement.commission_rate), 'commission_amount': str(arrangement.commission_amount), 'obligations': obligations,
    }
    if arrangement.flow == 'platform_online':
        summary['online_payment'] = _online_payment_summary(order, user)
    return summary


def _online_payment_summary(order, user):
    """État du paiement en ligne (SingPay) de la commande, pour le client et le commerce."""
    from .models import Payment

    payment = Payment.objects.filter(order=order).first()
    is_client = user is not None and user.id == order.client_id
    return {
        'status': payment.status if payment else 'not_started',
        'method': payment.payment_method if payment else '',
        'amount': str(payment.amount) if payment else str(order.total_amount),
        'phone': payment.client_phone if payment and is_client else '',
        'order_status': order.status,
        'i_am_client': is_client,
    }


@transaction.atomic
def confirm_receipt(receipt, user, payee_acknowledgement=False):
    # payee_acknowledgement : le bénéficiaire déclare lui-même avoir reçu l'argent (contre son intérêt),
    # ce qui vaut confirmation.
    receipt = PaymentReceipt.objects.select_for_update().select_related('obligation').get(pk=receipt.pk)
    if receipt.status == 'confirmed':
        return receipt
    if receipt.status == 'rejected':
        raise ValidationError('Un reçu refusé ne peut pas être confirmé.')
    if receipt.actor_id == user.id and not payee_acknowledgement:
        raise ValidationError('Le déclarant ne peut pas confirmer son propre mouvement.')
    if receipt.obligation.received_amount + receipt.amount > receipt.obligation.amount:
        raise ValidationError('Le montant confirmé dépasserait le solde dû.')
    receipt.status, receipt.confirmed_by, receipt.confirmed_at = 'confirmed', user, timezone.now()
    receipt.save(update_fields=['status', 'confirmed_by', 'confirmed_at'])
    _refresh_status(receipt.obligation)
    return receipt


@transaction.atomic
def reject_receipt(receipt, user, reason):
    receipt = PaymentReceipt.objects.select_for_update().get(pk=receipt.pk)
    if receipt.status != 'pending':
        raise ValidationError('Seul un reçu en attente peut être refusé.')
    if receipt.actor_id == user.id:
        raise ValidationError('Le déclarant ne peut pas statuer sur son propre mouvement.')
    if not (reason or '').strip():
        raise ValidationError('Une justification de refus est obligatoire.')
    receipt.status = 'rejected'
    receipt.rejected_by = user
    receipt.rejected_at = timezone.now()
    receipt.rejection_reason = reason.strip()
    receipt.save(update_fields=['status', 'rejected_by', 'rejected_at', 'rejection_reason'])
    return receipt


def courier_cash_position(user):
    """Confirmed third-party cash held by one courier."""
    qs = PaymentObligation.objects.filter(
        arrangement__flow='courier_cash',
        arrangement__order__delivery__delivery_agent=user,
    )
    collected = Decimal('0')
    remitted = Decimal('0')
    for obligation in qs.prefetch_related('receipts', 'adjustments'):
        if obligation.kind == 'products':
            collected += obligation.received_amount
        elif obligation.kind == 'courier_remittance':
            remitted += obligation.received_amount
    return max(Decimal('0'), collected - remitted)


def courier_cash_exposure(user, exclude_order=None):
    """Cash held plus product collections already committed to this courier."""
    held = courier_cash_position(user)
    assigned = PaymentArrangement.objects.filter(
        flow='courier_cash', order__delivery__delivery_agent=user,
    ).exclude(order__status__in=['cancelled', 'refunded'])
    if exclude_order is not None:
        assigned = assigned.exclude(order=exclude_order)
    reserved = Decimal('0')
    for arrangement in assigned.prefetch_related('obligations__receipts'):
        products = next((x for x in arrangement.obligations.all() if x.kind == 'products'), None)
        if products:
            reserved += max(Decimal('0'), products.amount - products.received_amount)
    return held + reserved


def can_courier_accept_collection(user, order):
    if not hasattr(order, 'payment_arrangement') or order.payment_arrangement.flow != 'courier_cash':
        return True
    limit = Decimal(order.payment_arrangement.policy_snapshot.get('courier_cash_limit', '0'))
    return courier_cash_exposure(user, exclude_order=order) + order.payment_arrangement.products_amount <= limit


@transaction.atomic
def create_settlement(store, amount, method, user, reference='', comment='', proof=None):
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValidationError('Le montant doit être positif.')
    settlement = CommissionSettlement.objects.create(store=store, amount=amount, method=method, reference=reference, comment=comment, proof=proof, collected_by=user)
    remaining = amount
    debts = PaymentObligation.objects.select_for_update().filter(arrangement__store=store, kind='commission').exclude(status__in=['paid', 'cancelled', 'waived']).order_by('due_at', 'id')
    for debt in debts:
        allocation = min(remaining, debt.remaining_amount)
        if allocation > 0:
            SettlementAllocation.objects.create(settlement=settlement, obligation=debt, amount=allocation)
            remaining -= allocation
        if remaining <= 0:
            break
    if remaining:
        raise ValidationError('Le règlement dépasse la dette de commission disponible.')
    return settlement


@transaction.atomic
def confirm_settlement(settlement, user):
    settlement = CommissionSettlement.objects.select_for_update().get(pk=settlement.pk)
    if settlement.status == 'confirmed':
        return settlement
    if settlement.collected_by_id == user.id:
        raise ValidationError('Le déclarant ne peut pas confirmer son propre règlement cash.')
    for allocation in settlement.allocations.select_related('obligation'):
        PaymentReceipt.objects.create(obligation=allocation.obligation, actor=settlement.collected_by, amount=allocation.amount, method=settlement.method, reference=f'{settlement.receipt_number}-{allocation.id}', idempotency_key=f'settlement:{settlement.id}:{allocation.id}', status='confirmed', confirmed_by=user, confirmed_at=timezone.now())
        _refresh_status(allocation.obligation)
    settlement.status, settlement.confirmed_by, settlement.confirmed_at = 'confirmed', user, timezone.now()
    settlement.save(update_fields=['status', 'confirmed_by', 'confirmed_at'])
    return settlement


@transaction.atomic
def record_refund(order, component, amount, user, reference, reason=''):
    """Record an evidenced refund without rewriting the original ledger.

    Product refunds create a proportional credit on Gaboshop's commission.
    Delivery refunds remain independent and never erase earned courier pay.
    """
    if component not in ('products', 'delivery'):
        raise ValidationError('Composant de remboursement invalide.')
    arrangement = PaymentArrangement.objects.select_for_update().get(order=order)
    obligation_kind = 'delivery_collection' if component == 'delivery' and arrangement.obligations.filter(kind='delivery_collection').exists() else component
    obligation = arrangement.obligations.filter(kind=obligation_kind).first()
    if not obligation:
        raise ValidationError('Aucune obligation correspondante.')
    amount = Decimal(str(amount))
    if amount <= 0 or obligation.refunded_amount + amount > obligation.amount:
        raise ValidationError('Montant de remboursement invalide.')
    adjustment = PaymentAdjustment.objects.create(obligation=obligation, actor=user, adjustment_type='refund', status='confirmed', amount=amount, reason=reason, reference=reference, idempotency_key=f'refund:{order.id}:{component}:{reference}')
    refunded = obligation.refunded_amount
    obligation.status = 'refunded' if refunded >= obligation.amount else 'partially_refunded'
    obligation.save(update_fields=['status', 'updated_at'])
    if component == 'products' and arrangement.products_amount:
        commission = arrangement.obligations.get(kind='commission')
        credit = (arrangement.commission_amount * amount / arrangement.products_amount).quantize(Decimal('0.01'))
        PaymentAdjustment.objects.create(obligation=commission, actor=user, adjustment_type='commission_credit', status='confirmed', amount=credit, reason=f'Avoir lié au remboursement {reference}', reference=f'COM-{reference}', idempotency_key=f'commission-refund:{order.id}:{reference}')
        if commission.refunded_amount >= commission.amount:
            commission.status = 'cancelled'
            commission.save(update_fields=['status', 'updated_at'])
    return adjustment
