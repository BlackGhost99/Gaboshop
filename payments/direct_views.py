from decimal import Decimal, InvalidOperation

from django.shortcuts import get_object_or_404
from django.db.models import Sum
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from stores.models import Store
from .configuration import available_payment_options, get_payment_policy, validate_store_preferences
from .direct_models import PaymentArrangement, PaymentObligation, PaymentReceipt, CommissionSettlement
from .direct_service import payment_summary, confirm_receipt, reject_receipt, create_settlement, confirm_settlement, courier_cash_position, courier_cash_exposure


def _is_admin(user):
    return user.is_superuser or getattr(user, 'user_type', '') == 'admin'


def _can_access_arrangement(user, arrangement):
    return _is_admin(user) or arrangement.order.client_id == user.id or arrangement.store.manager_id == user.id or getattr(arrangement.order.delivery, 'delivery_agent_id', None) == user.id


def _can_review_obligation(user, obligation):
    if _is_admin(user):
        return True
    arrangement = obligation.arrangement
    delivery = getattr(arrangement.order, 'delivery', None)
    role_ids = {
        'client': arrangement.order.client_id,
        'store': arrangement.store.manager_id,
        'courier': getattr(delivery, 'delivery_agent_id', None),
    }
    return user.id in (role_ids.get(obligation.payer), role_ids.get(obligation.payee))


class PaymentOptionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        store = get_object_or_404(Store, pk=request.query_params.get('store_id'))
        delivery = str(request.query_params.get('delivery_requested', 'true')).lower() != 'false'
        policy, options = available_payment_options(store, delivery)
        return Response({'success': True, 'data': {'policy': policy, 'options': options}})


class StorePaymentPreferencesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _store(self, request):
        store_id = request.query_params.get('store_id') or request.data.get('store_id')
        store = get_object_or_404(Store, pk=store_id) if store_id else get_object_or_404(Store, manager=request.user)
        if not (_is_admin(request.user) or store.manager_id == request.user.id):
            self.permission_denied(request)
        return store

    def get(self, request):
        store = self._store(request)
        return Response({'success': True, 'data': {'store_id': store.id, 'store_name': store.name, 'preferences': store.payment_preferences, 'policy': get_payment_policy(store), 'global_policy': get_payment_policy()}})

    def patch(self, request):
        store = self._store(request)
        store.payment_preferences = validate_store_preferences(request.data.get('preferences', request.data))
        store.save(update_fields=['payment_preferences'])
        return self.get(request)


class ArrangementDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, order_id):
        arrangement = get_object_or_404(PaymentArrangement.objects.select_related('order', 'store'), order_id=order_id)
        if not _can_access_arrangement(request.user, arrangement):
            self.permission_denied(request)
        return Response({'success': True, 'data': payment_summary(arrangement, request.user)})


class ReceiptCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        obligation = get_object_or_404(PaymentObligation.objects.select_related('arrangement__order', 'arrangement__store'), pk=request.data.get('obligation_id'))
        if not _can_access_arrangement(request.user, obligation.arrangement):
            self.permission_denied(request)
        try:
            amount = Decimal(str(request.data.get('amount')))
        except (InvalidOperation, TypeError):
            raise ValidationError({'amount': 'Montant invalide.'})
        if amount <= 0 or amount > obligation.remaining_amount:
            raise ValidationError({'amount': 'Le montant doit être positif et ne pas dépasser le solde.'})
        method = request.data.get('method', '')
        reference = request.data.get('reference', '').strip()
        idem = request.data.get('idempotency_key', '').strip()
        if not reference or not idem:
            raise ValidationError('Une référence et une clé d’idempotence sont obligatoires.')
        receipt, created = PaymentReceipt.objects.get_or_create(idempotency_key=idem, defaults={'obligation': obligation, 'actor': request.user, 'amount': amount, 'method': method, 'reference': reference, 'comment': request.data.get('comment', ''), 'proof': request.FILES.get('proof')})
        return Response({'success': True, 'data': {'id': receipt.id, 'receipt_number': receipt.receipt_number, 'status': receipt.status}, 'created': created}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class ReceiptConfirmView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, receipt_id):
        receipt = get_object_or_404(PaymentReceipt.objects.select_related('obligation__arrangement__order', 'obligation__arrangement__store'), pk=receipt_id)
        if not _can_review_obligation(request.user, receipt.obligation):
            self.permission_denied(request)
        receipt = confirm_receipt(receipt, request.user)
        return Response({'success': True, 'data': {'id': receipt.id, 'status': receipt.status}})


class ReceiptRejectView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, receipt_id):
        receipt = get_object_or_404(PaymentReceipt.objects.select_related('obligation__arrangement__order', 'obligation__arrangement__store'), pk=receipt_id)
        if not _can_review_obligation(request.user, receipt.obligation):
            self.permission_denied(request)
        receipt = reject_receipt(receipt, request.user, request.data.get('reason', ''))
        return Response({'success': True, 'data': {'id': receipt.id, 'status': receipt.status, 'rejection_reason': receipt.rejection_reason}})


class SettlementListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        qs = CommissionSettlement.objects.select_related('store').prefetch_related('allocations')
        if not _is_admin(request.user):
            qs = qs.filter(store__manager=request.user)
        data = [{'id': x.id, 'receipt_number': x.receipt_number, 'store_id': x.store_id, 'amount': str(x.amount), 'method': x.method, 'status': x.status, 'created_at': x.created_at} for x in qs[:200]]
        return Response({'success': True, 'data': data})

    def post(self, request):
        store = get_object_or_404(Store, pk=request.data.get('store_id'))
        if not (_is_admin(request.user) or store.manager_id == request.user.id):
            self.permission_denied(request)
        settlement = create_settlement(store, request.data.get('amount'), request.data.get('method'), request.user, request.data.get('reference', ''), request.data.get('comment', ''), request.FILES.get('proof'))
        return Response({'success': True, 'data': {'id': settlement.id, 'receipt_number': settlement.receipt_number, 'status': settlement.status}}, status=status.HTTP_201_CREATED)


class SettlementConfirmView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, settlement_id):
        if not _is_admin(request.user):
            self.permission_denied(request)
        settlement = confirm_settlement(get_object_or_404(CommissionSettlement, pk=settlement_id), request.user)
        return Response({'success': True, 'data': {'id': settlement.id, 'status': settlement.status}})


class FinancialControlView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if not _is_admin(request.user):
            self.permission_denied(request)
        from users.models import User
        from .configuration import get_payment_policy
        from .direct_service import _refresh_status

        commissions = PaymentObligation.objects.filter(kind='commission').select_related('arrangement__store').prefetch_related('receipts', 'adjustments')
        for debt in commissions:
            _refresh_status(debt)
        stores = []
        for store in Store.objects.filter(payment_arrangements__isnull=False).distinct():
            debts = [x for x in commissions if x.arrangement.store_id == store.id]
            due = sum((x.remaining_amount for x in debts if x.status not in ('cancelled', 'waived', 'paid')), Decimal('0'))
            overdue = sum((x.remaining_amount for x in debts if x.status == 'overdue'), Decimal('0'))
            limit = Decimal(get_payment_policy(store)['merchant_debt_limit'])
            latest = PaymentReceipt.objects.filter(obligation__kind='commission', obligation__arrangement__store=store, status='confirmed').order_by('-confirmed_at').first()
            stores.append({'store_id': store.id, 'store_name': store.name, 'debt': str(due), 'overdue': str(overdue), 'debt_limit': str(limit), 'remaining_before_suspension': str(max(Decimal('0'), limit - due)), 'pending_receipts': PaymentReceipt.objects.filter(obligation__arrangement__store=store, status='pending').count(), 'last_payment_at': latest.confirmed_at if latest else None})
        couriers = []
        for courier in User.objects.filter(user_type='delivery_agent', deliveries__order__payment_arrangement__flow='courier_cash').distinct():
            held = courier_cash_position(courier)
            exposure = courier_cash_exposure(courier)
            related = PaymentArrangement.objects.filter(flow='courier_cash', order__delivery__delivery_agent=courier)
            configured_limits = [Decimal(x.policy_snapshot.get('courier_cash_limit', '0')) for x in related]
            limit = min(configured_limits) if configured_limits else Decimal('0')
            couriers.append({'courier_id': courier.id, 'courier_phone': courier.phone, 'cash_held': str(held), 'cash_committed': str(exposure), 'cash_limit': str(limit), 'remaining_capacity': str(max(Decimal('0'), limit - exposure))})
        return Response({'success': True, 'data': {'stores': stores, 'couriers': couriers, 'pending_cash_receipts': PaymentReceipt.objects.filter(method='cash', status='pending').count(), 'rejected_receipts': PaymentReceipt.objects.filter(status='rejected').count(), 'overdue_obligations': commissions.filter(status='overdue').count(), 'incomplete_settlements': CommissionSettlement.objects.filter(status='pending_confirmation').count()}})
