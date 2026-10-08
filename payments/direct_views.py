from decimal import Decimal, InvalidOperation
from datetime import timedelta

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
from .direct_service import can_declare, can_review, receipt_payload, role_user_id, payment_summary, confirm_receipt, reject_receipt, create_settlement, confirm_settlement, courier_cash_position, courier_cash_exposure


def _is_admin(user):
    return user.is_superuser or getattr(user, 'user_type', '') == 'admin'


def _can_access_arrangement(user, arrangement):
    return _is_admin(user) or arrangement.order.client_id == user.id or arrangement.store.manager_id == user.id or getattr(getattr(arrangement.order, 'delivery', None), 'delivery_agent_id', None) == user.id


def _can_declare_obligation(user, obligation):
    return can_declare(user, obligation)


def _can_review_obligation(user, obligation):
    return can_review(user, obligation)


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
        arrangement = get_object_or_404(
            PaymentArrangement.objects.select_related('order', 'order__delivery', 'store')
            .prefetch_related('obligations__receipts', 'obligations__adjustments'),
            order_id=order_id,
        )
        if not _can_access_arrangement(request.user, arrangement):
            self.permission_denied(request)
        return Response({'success': True, 'data': payment_summary(arrangement, request.user)})


class ReceiptCreateView(APIView):
    """Déclarer un paiement sur une obligation.

    - Le payeur déclare (ex. le client indique l'ID de transaction Mobile Money reçu par SMS) :
      le reçu attend la confirmation du bénéficiaire.
    - Le bénéficiaire qui déclare avoir reçu l'argent (ex. espèces en main) : confirmé tout de suite,
      sauf pour ce qui est dû à Gaboshop (validé par l'admin).
    """
    permission_classes = [permissions.IsAuthenticated]
    MAX_REJECTED = 3
    REJECTED_WINDOW_DAYS = 30

    def post(self, request):
        obligation = get_object_or_404(PaymentObligation.objects.select_related('arrangement__order', 'arrangement__store'), pk=request.data.get('obligation_id'))
        if not _can_declare_obligation(request.user, obligation):
            self.permission_denied(request)
        try:
            amount = Decimal(str(request.data.get('amount')))
        except (InvalidOperation, TypeError):
            raise ValidationError({'amount': 'Montant invalide.'})
        if amount <= 0 or amount > obligation.remaining_amount:
            raise ValidationError({'amount': 'Le montant doit être positif et ne pas dépasser le solde.'})
        method = (request.data.get('method') or obligation.arrangement.method or '').strip()
        reference = (request.data.get('reference') or '').strip()
        idem = (request.data.get('idempotency_key') or '').strip()
        if not idem:
            raise ValidationError('Une clé d’idempotence est obligatoire.')
        existing = PaymentReceipt.objects.filter(idempotency_key=idem).first()
        if existing:
            return Response({'success': True, 'data': receipt_payload(existing), 'created': False}, status=status.HTTP_200_OK)

        user = request.user
        is_payee = user.id == role_user_id(obligation, obligation.payee)
        if method == 'cash' and not reference:
            reference = f'ESPECES-{timezone.now():%Y%m%d%H%M%S}-{user.id}'
        if not reference:
            raise ValidationError({'reference': 'Indiquez l’ID de transaction reçu par SMS.'})
        if method != 'cash':
            # Un même ID de transaction Mobile Money ne sert qu'une fois, sur toute la plateforme.
            normalized = reference.replace(' ', '').upper()
            used = PaymentReceipt.objects.filter(method=method).exclude(status='rejected').values_list('reference', flat=True)
            if any(r.replace(' ', '').upper() == normalized for r in used):
                raise ValidationError({'reference': 'Cet ID de transaction a déjà été utilisé.'})
        if PaymentReceipt.objects.filter(obligation=obligation, reference=reference).exists():
            raise ValidationError({'reference': 'Cet ID a déjà été déclaré pour ce paiement.'})
        if not is_payee and not _is_admin(user):
            since = timezone.now() - timedelta(days=self.REJECTED_WINDOW_DAYS)
            if PaymentReceipt.objects.filter(actor=user, status='rejected', rejected_at__gte=since).count() >= self.MAX_REJECTED:
                return Response({'success': False, 'error': {'code': 403, 'message': 'Trop de paiements déclarés ont été refusés. Contactez le support Gaboshop.'}}, status=status.HTTP_403_FORBIDDEN)
            if obligation.receipts.filter(status='pending').exists():
                raise ValidationError('Un paiement déclaré attend déjà la confirmation du bénéficiaire.')

        receipt = PaymentReceipt.objects.create(
            idempotency_key=idem, obligation=obligation, actor=user, amount=amount, method=method,
            reference=reference, comment=(request.data.get('comment') or '')[:500], proof=request.FILES.get('proof'),
        )
        if is_payee and obligation.payee != 'platform':
            confirm_receipt(receipt, user, payee_acknowledgement=True)
            receipt.refresh_from_db()
        else:
            _notify_payee(obligation, receipt)
        return Response({'success': True, 'data': receipt_payload(receipt), 'created': True}, status=status.HTTP_201_CREATED)


def _notify_payee(obligation, receipt):
    payee_id = role_user_id(obligation, obligation.payee)
    if not payee_id:
        return
    try:
        from notifications.models import Notification
        order = obligation.arrangement.order
        Notification.objects.create(
            user_id=payee_id, title='Paiement à vérifier',
            body=f'{receipt.amount:.0f} FCFA déclarés pour la commande {order.order_number} (réf. {receipt.reference}). Vérifiez votre SMS puis confirmez ou refusez.',
            notif_type='payment', order=order, metadata={'order_id': order.id, 'receipt_id': receipt.id},
        )
    except Exception:
        pass


class PendingReceiptsView(APIView):
    """Paiements déclarés qui attendent ma confirmation (commerce, fournisseur B2B, livreur, admin)."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        qs = PaymentReceipt.objects.filter(status='pending').select_related('obligation__arrangement__order', 'obligation__arrangement__store', 'actor')
        if not _is_admin(user):
            from django.db.models import Q
            qs = qs.filter(
                Q(obligation__payee='store', obligation__arrangement__store__manager=user)
                | Q(obligation__payee='courier', obligation__arrangement__order__delivery__delivery_agent=user)
                | Q(obligation__payee='client', obligation__arrangement__order__client=user)
            )
        data = []
        for receipt in qs.order_by('created_at')[:100]:
            order = receipt.obligation.arrangement.order
            item = receipt_payload(receipt)
            item.update({
                'order_id': order.id, 'order_number': order.order_number, 'is_b2b': getattr(order, 'is_b2b', False),
                'kind': receipt.obligation.kind, 'payer': receipt.obligation.payer,
                'declared_by': (f'{receipt.actor.first_name} {receipt.actor.last_name}'.strip() or receipt.actor.phone),
                'declared_by_phone': receipt.actor.phone,
            })
            data.append(item)
        return Response({'success': True, 'data': data})


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
        try:
            from notifications.models import Notification
            order = receipt.obligation.arrangement.order
            Notification.objects.create(
                user_id=receipt.actor_id, title='Paiement refusé', order=order,
                body=f'Votre paiement de {receipt.amount:.0f} FCFA (réf. {receipt.reference}) pour la commande {order.order_number} a été refusé : {receipt.rejection_reason}',
                notif_type='payment', metadata={'order_id': order.id, 'receipt_id': receipt.id},
            )
        except Exception:
            pass
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
