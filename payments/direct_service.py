from decimal import Decimal
from datetime import timedelta

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .configuration import available_payment_options, get_payment_policy, matching_option
from .direct_models import PaymentArrangement, PaymentObligation, PaymentReceipt, PaymentAdjustment, CommissionSettlement, SettlementAllocation


def is_manual_order(order):
    return hasattr(order, 'payment_arrangement') and order.payment_arrangement.flow != 'platform_online'


STORE_DELIVERY = 'store'
GABOSHOP_DELIVERY = 'gaboshop'


def store_delivers(order):
    """Le commerce livre lui-même cette commande payée en ligne (option « tout au commerce »).

    Les anciennes commandes, faites avant ce choix, suivent le réglage du commerce (« il livre lui-même »)."""
    arrangement = getattr(order, 'payment_arrangement', None)
    # Respecter le choix figé lors de la commande, même si la boutique modifie
    # plus tard le paramètre offers_delivery : ne jamais basculer une commande
    # payée en espèces au livreur de la boutique vers un livreur Gaboshop.
    if arrangement is not None and arrangement.delivery_method == STORE_DELIVERY:
        return True
    if arrangement is not None and arrangement.flow == 'platform_online':
        if arrangement.delivery_method == GABOSHOP_DELIVERY:
            return False
    store = getattr(order, 'store', None)
    return bool(getattr(store, 'offers_delivery', False))


# Ce que Gaboshop se fait devoir après une commande payée en direct (hors de SingPay).
PLATFORM_DEBT_KINDS = ('commission', 'delivery_margin')


def direct_margin_on(arrangement):
    """La part Gaboshop de la livraison est-elle due sur cette commande directe ? Figé à la création."""
    return bool(arrangement.policy_snapshot.get('direct_delivery_margin'))


def courier_earning(order):
    """Ce que touche le livreur pour la course, selon le circuit de paiement de la commande.

    Paiement en ligne : la part réglée dans l'admin. Paiement direct : toute la livraison, sauf si la
    commande a été créée avec « part Gaboshop aussi en direct » (le livreur doit alors cette part à Gaboshop).
    """
    from api.models import SystemSettings
    fee = Decimal(order.delivery_fee or 0)
    arrangement = getattr(order, 'payment_arrangement', None)
    if arrangement is not None and arrangement.flow != 'platform_online' and not direct_margin_on(arrangement):
        return fee
    return SystemSettings.courier_share(fee)


def _refresh_status(obligation):
    paid = obligation.received_amount
    if obligation.status in ('cancelled', 'waived', 'refunded'):
        return obligation.status
    previous = obligation.status
    if paid >= obligation.amount:
        obligation.status = 'paid'
    elif paid > 0:
        obligation.status = 'partially_paid'
    elif obligation.due_at and obligation.due_at < timezone.now():
        obligation.status = 'overdue'
    elif obligation.status != 'not_due':
        obligation.status = 'unpaid'
    # Appelé à chaque affichage : on n'écrit en base que si le statut change.
    if obligation.status != previous:
        obligation.save(update_fields=['status', 'updated_at'])
    return obligation.status


def ensure_credit_limit(store, additional_commission=Decimal('0')):
    policy = get_payment_policy(store)
    # Verrou sur le commerce : deux commandes simultanées ne dépassent pas ensemble le plafond.
    from stores.models import Store
    list(Store.objects.select_for_update().filter(pk=store.pk).values_list('pk', flat=True))
    # Seules les commissions exigibles (commande livrée) comptent : des commandes passées puis jamais
    # livrées (par un concurrent malveillant, par exemple) ne bloquent plus le commerce.
    debts = PaymentObligation.objects.filter(
        arrangement__store=store, kind__in=PLATFORM_DEBT_KINDS, payer='store'
    ).exclude(status__in=['paid', 'cancelled', 'waived', 'not_due']).prefetch_related('receipts', 'adjustments')
    outstanding = sum((debt.remaining_amount for debt in debts), Decimal('0'))
    if outstanding + Decimal(additional_commission) > Decimal(policy['merchant_debt_limit']):
        raise ValidationError('Plafond de commissions dues atteint pour ce commerce.')


@transaction.atomic
def create_arrangement(order, flow, method, delivery_method=None, user=None):
    if hasattr(order, 'payment_arrangement'):
        return order.payment_arrangement
    policy, options = available_payment_options(order.store, order.delivery_requested, b2b=getattr(order, 'is_b2b', False), user=order.client)
    if flow == 'platform_online':
        delivery_method = STORE_DELIVERY if delivery_method == STORE_DELIVERY else GABOSHOP_DELIVERY
    # Pour les commandes livrées et payées en espèces, seule une boutique
    # assurant elle-même les livraisons peut recevoir cet argent.
    if (not order.is_b2b and flow == 'store_collects_all' and method == 'cash'
            and order.delivery_requested and order.store.offers_delivery):
        delivery_method = STORE_DELIVERY
    if not matching_option(options, flow, method, delivery_method if flow == 'platform_online' else ''):
        raise ValidationError('Ce circuit ou moyen de paiement n’est pas autorisé pour ce commerce.')
    if flow != 'platform_online':
        ensure_credit_limit(order.store, order.commission_amount)
    from api.models import SystemSettings
    margin_on = (flow != 'platform_online' and bool(order.delivery_fee) and not order.store.offers_delivery
                 and bool(SystemSettings.current('direct_delivery_margin', False)))
    policy = {**policy, 'direct_delivery_margin': margin_on}
    arrangement = PaymentArrangement.objects.create(
        order=order, store=order.store, created_by=user or order.client, flow=flow, method=method,
        delivery_method=delivery_method or method, policy_snapshot=policy,
        products_amount=order.items_total, delivery_amount=order.delivery_fee,
        commission_rate=order.commission_rate, commission_amount=order.commission_amount,
    )
    due = timezone.now() + timedelta(days=policy['commission_settlement_days'])
    specs = []
    courier_part = SystemSettings.courier_share(order.delivery_fee) if margin_on else order.delivery_fee
    margin = Decimal(order.delivery_fee or 0) - Decimal(courier_part) if margin_on else Decimal('0')
    if flow == 'direct_split':
        specs = [('products', 'client', 'store', order.items_total), ('delivery', 'client', 'courier', order.delivery_fee)]
    elif flow == 'store_collects_all':
        specs = [('products', 'client', 'store', order.items_total),
                 ('delivery_collection', 'client', 'store', order.delivery_fee)]
        # Le livreur est salarié/partenaire de la boutique : aucun reversement
        # à un livreur indépendant Gaboshop ne doit être créé par cette commande.
        if delivery_method != STORE_DELIVERY:
            specs.append(('delivery', 'store', 'courier', courier_part))
    elif flow == 'courier_cash':
        specs = [('products', 'client', 'courier', order.items_total), ('delivery', 'client', 'courier', order.delivery_fee), ('courier_remittance', 'courier', 'store', order.items_total)]
    else:
        # Paiement en ligne : Gaboshop encaisse tout, puis reverse la livraison au livreur, ou au commerce s'il livre.
        delivery_payee = 'store' if delivery_method == STORE_DELIVERY else 'courier'
        # Le client paie la livraison moins la réduction de son forfait ; le livreur (ou le commerce) touche le prix plein.
        collected = order.delivery_fee - order.applied_forfait_discount()
        specs = [('products', 'client', 'platform', order.items_total), ('delivery_collection', 'client', 'platform', collected), ('delivery', 'platform', delivery_payee, order.delivery_fee)]
    for kind, payer, payee, amount in specs:
        if amount:
            PaymentObligation.objects.create(arrangement=arrangement, kind=kind, payer=payer, payee=payee, amount=amount, status='unpaid', requires_delivery_proof=(kind == 'delivery'))
    PaymentObligation.objects.create(
        arrangement=arrangement, kind='commission', payer='store', payee='platform',
        amount=order.commission_amount,
        status='paid' if flow == 'platform_online' else 'not_due',
        due_at=None if flow == 'platform_online' else due,
    )
    if margin:
        # Celui qui encaisse la livraison (le livreur, ou le commerce en « il encaisse tout ») doit la part Gaboshop,
        # exigible à la livraison comme la commission.
        PaymentObligation.objects.create(
            arrangement=arrangement, kind='delivery_margin',
            payer='store' if flow == 'store_collects_all' else 'courier', payee='platform',
            amount=margin, status='not_due', due_at=due,
        )
    if flow != 'platform_online':
        order.status = 'confirmed'
        order.confirmed_at = timezone.now()
        order.save(update_fields=['status', 'confirmed_at'])
        if hasattr(order, 'delivery') and delivery_method != STORE_DELIVERY:
            order.delivery.agent_commission = courier_part
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
        for debt in arrangement.obligations.filter(kind__in=PLATFORM_DEBT_KINDS, status='not_due'):
            debt.status = 'overdue' if debt.due_at and debt.due_at < timezone.now() else 'unpaid'
            debt.save(update_fields=['status', 'updated_at'])
    elif order.status in ('cancelled', 'refunded'):
        arrangement.obligations.filter(kind__in=PLATFORM_DEBT_KINDS, status='not_due').update(status='cancelled')


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
    # Verrou sur l'obligation : deux confirmations simultanées ne dépassent jamais le solde dû.
    receipt.obligation = PaymentObligation.objects.select_for_update().get(pk=receipt.obligation_id)
    if receipt.amount > receipt.obligation.remaining_amount:
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
    from core import guardian
    actor = receipt.actor
    transaction.on_commit(lambda: guardian.check(actor))
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
        # Déjà réservé par un autre règlement encore à confirmer : pas alloué deux fois.
        reserved = SettlementAllocation.objects.filter(obligation=debt, settlement__status='pending_confirmation').exclude(settlement=settlement).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        allocation = min(remaining, max(Decimal('0'), debt.remaining_amount - reserved))
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
    if settlement.status != 'pending_confirmation':
        raise ValidationError('Seul un règlement en attente de confirmation peut être confirmé.')
    if settlement.collected_by_id == user.id:
        raise ValidationError('Le déclarant ne peut pas confirmer son propre règlement cash.')
    allocations = list(settlement.allocations.order_by('id'))
    # Verrou sur les dettes puis nouvelle vérification du solde restant au moment de confirmer.
    locked = {o.pk: o for o in PaymentObligation.objects.select_for_update().filter(pk__in=[a.obligation_id for a in allocations])}
    for allocation in allocations:
        allocation.obligation = locked[allocation.obligation_id]
        if allocation.amount > allocation.obligation.remaining_amount:
            raise ValidationError('Ce règlement dépasse désormais la commission restant due.')
    for allocation in allocations:
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


# ---------------------------------------------------------------------------
# Dettes envers Gaboshop (paiement direct) : commission du commerce, part livraison du livreur.
# ---------------------------------------------------------------------------
DUE_STATUSES = ('unpaid', 'overdue', 'partially_paid')


def platform_debts(party, target):
    """Dettes exigibles (commande livrée) d'un commerce ou d'un livreur envers Gaboshop, les plus anciennes d'abord."""
    qs = PaymentObligation.objects.filter(kind__in=PLATFORM_DEBT_KINDS, payee='platform', payer=party)
    if party == 'store':
        qs = qs.filter(arrangement__store=target)
    elif party == 'courier':
        qs = qs.filter(arrangement__order__delivery__delivery_agent=target)
    else:
        raise ValidationError('Débiteur inconnu.')
    debts = list(qs.select_related('arrangement__order').prefetch_related('receipts', 'adjustments').order_by('due_at', 'id'))
    for debt in debts:
        _refresh_status(debt)
    return [d for d in debts if d.status in DUE_STATUSES and d.remaining_amount > 0]


def debt_summary(debts):
    return {
        'total_due': str(sum((d.remaining_amount for d in debts), Decimal('0'))),
        'overdue': str(sum((d.remaining_amount for d in debts if d.status == 'overdue'), Decimal('0'))),
        'items': [{
            'obligation_id': d.id, 'kind': d.kind, 'order_number': d.arrangement.order.order_number,
            'amount': str(d.amount), 'remaining': str(d.remaining_amount), 'status': d.status, 'due_at': d.due_at,
        } for d in debts],
    }


@transaction.atomic
def collect_platform_debt(party, target, amount, method, reference, admin, idempotency_key):
    """L'admin note l'argent qu'il a reçu d'un commerce ou d'un livreur : réparti sur les plus vieilles dettes.

    Idempotent (même clé = même encaissement) ; un ID de transaction Mobile Money ne sert qu'une fois.
    """
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValidationError({'amount': 'Le montant doit être positif.'})
    idem = (idempotency_key or '').strip()[:60]
    if not idem:
        raise ValidationError('Une clé d’idempotence est obligatoire.')
    existing = list(PaymentReceipt.objects.filter(idempotency_key__startswith=f'collect:{idem}:'))
    if existing:
        return existing
    reference = (reference or '').strip().replace(' ', '').upper()
    if method == 'cash' and not reference:
        reference = f'ESPECES-{timezone.now():%Y%m%d%H%M%S}-{admin.id}'
    if not reference:
        raise ValidationError({'reference': 'Indiquez l’ID de transaction reçu par SMS.'})
    if method != 'cash' and PaymentReceipt.objects.exclude(status='rejected').filter(reference__startswith=reference).exists():
        raise ValidationError({'reference': 'Cet ID de transaction a déjà été utilisé.'})
    debts = platform_debts(party, target)
    locked = {o.pk: o for o in PaymentObligation.objects.select_for_update().filter(pk__in=[d.pk for d in debts])}
    total = sum((d.remaining_amount for d in debts), Decimal('0'))
    if amount > total:
        raise ValidationError({'amount': f'Le montant dépasse la dette ({total:.0f} FCFA).'})
    receipts, remaining = [], amount
    for debt in debts:
        part = min(remaining, debt.remaining_amount)
        if part <= 0:
            break
        receipt = PaymentReceipt.objects.create(
            obligation=locked[debt.pk], actor=admin, amount=part, method=method,
            reference=f'{reference}-{debt.pk}', idempotency_key=f'collect:{idem}:{debt.pk}',
            comment='Encaissé par Gaboshop', status='confirmed', confirmed_by=admin, confirmed_at=timezone.now(),
        )
        _refresh_status(locked[debt.pk])
        receipts.append(receipt)
        remaining -= part
    return receipts
