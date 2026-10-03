from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from api.models import SystemSettings
from orders.models import Order, OrderItem
from payments.configuration import DEFAULT_PAYMENT_POLICY, available_payment_options, get_payment_policy
from payments.direct_models import PaymentReceipt
from payments.models import PaymentIntent
from payments.direct_service import create_arrangement, confirm_receipt, reject_receipt, create_settlement, confirm_settlement, payment_summary, sync_on_order_status, record_refund, courier_cash_position, courier_cash_exposure, can_courier_accept_collection
from products.models import Product, ProductCategory
from stores.models import Store, StoreCategory
from users.models import User


class ManualPaymentWorkflowTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(phone='+24106000001', password='x', user_type='admin', is_staff=True)
        self.manager = User.objects.create_user(phone='+24106000002', password='x', user_type='store_manager')
        self.client = User.objects.create_user(phone='+24106000003', password='x', user_type='client')
        self.courier = User.objects.create_user(phone='+24106000004', password='x', user_type='delivery_agent')
        category = StoreCategory.objects.create(name='Test')
        self.store = Store.objects.create(name='Commerce test', category=category, manager=self.manager, phone='+24106000100', address='Libreville', zone='Centre', commission_rate=Decimal('8'))
        product_category = ProductCategory.objects.create(store_category=category, name='Produits', commission_rate=Decimal('8'))
        self.product = Product.objects.create(store=self.store, category=product_category, name='Article', price=Decimal('10000'), stock=20, weight_kg=Decimal('1'))
        settings = SystemSettings.get_settings()
        settings.payment_policy = DEFAULT_PAYMENT_POLICY
        settings.save(update_fields=['payment_policy'])

    def make_order(self, number=1):
        order = Order.objects.create(client=self.client, store=self.store, delivery_address='Akanda', delivery_phone='+24106000003', delivery_zone='Centre', delivery_fee=Decimal('2000'))
        OrderItem.objects.create(order=order, product=self.product, quantity=number, unit_price=self.product.price)
        order.items_total = Decimal('10000') * number
        order.delivery_fee = Decimal('2000')
        order.commission_rate = Decimal('8')
        order.commission_amount = order.items_total * Decimal('0.08')
        order.total_amount = order.items_total + order.delivery_fee
        order.save()
        return order

    def test_direct_store_payment_generates_frozen_commission(self):
        order = self.make_order()
        arrangement = create_arrangement(order, 'direct_split', 'cash', user=self.client)
        self.assertEqual(arrangement.commission_amount, Decimal('800'))
        self.assertEqual(arrangement.commission_rate, Decimal('8'))
        self.store.commission_rate = Decimal('20')
        self.store.save()
        arrangement.refresh_from_db()
        self.assertEqual(arrangement.commission_amount, Decimal('800'))

    def test_partial_then_complete_commission_settlement(self):
        arrangement = create_arrangement(self.make_order(), 'courier_cash', 'cash', user=self.client)
        commission = arrangement.obligations.get(kind='commission')
        commission.status = 'unpaid'
        commission.save()
        first = create_settlement(self.store, '500', 'cash', self.manager, reference='CASH-1')
        confirm_settlement(first, self.admin)
        commission.refresh_from_db()
        self.assertEqual(commission.status, 'partially_paid')
        second = create_settlement(self.store, '300', 'cash', self.manager, reference='CASH-2')
        confirm_settlement(second, self.admin)
        commission.refresh_from_db()
        self.assertEqual(commission.status, 'paid')

    def test_cash_declaration_requires_confirmation_and_has_receipt_number(self):
        arrangement = create_arrangement(self.make_order(), 'courier_cash', 'cash', user=self.client)
        obligation = arrangement.obligations.get(kind='products')
        receipt = PaymentReceipt.objects.create(obligation=obligation, actor=self.client, amount=obligation.amount, method='cash', reference='HAND-1', idempotency_key='idem-1')
        self.assertEqual(receipt.status, 'pending')
        self.assertTrue(receipt.receipt_number.startswith('PAY-'))
        confirm_receipt(receipt, self.admin)
        obligation.refresh_from_db()
        self.assertEqual(obligation.status, 'paid')

    def test_confirming_same_receipt_twice_does_not_double_pay(self):
        arrangement = create_arrangement(self.make_order(), 'courier_cash', 'cash', user=self.client)
        obligation = arrangement.obligations.get(kind='products')
        receipt = PaymentReceipt.objects.create(obligation=obligation, actor=self.client, amount=obligation.amount, method='cash', reference='HAND-2', idempotency_key='idem-2')
        confirm_receipt(receipt, self.admin)
        confirm_receipt(receipt, self.admin)
        self.assertEqual(obligation.receipts.filter(status='confirmed').count(), 1)

    def test_courier_direct_payment_is_full_delivery_price(self):
        order = self.make_order()
        create_arrangement(order, 'direct_split', 'cash', user=self.client)
        order.delivery.refresh_from_db()
        self.assertEqual(order.delivery.agent_commission, order.delivery_fee)

    def test_cancelled_order_cancels_not_due_commission(self):
        order = self.make_order()
        arrangement = create_arrangement(order, 'courier_cash', 'cash', user=self.client)
        order.status = 'cancelled'
        order.save()
        sync_on_order_status(order)
        self.assertEqual(arrangement.obligations.get(kind='commission').status, 'cancelled')

    def test_store_cannot_enable_globally_disabled_mode(self):
        settings = SystemSettings.get_settings()
        settings.payment_policy = {**DEFAULT_PAYMENT_POLICY, 'enabled_methods': ['cash']}
        settings.save()
        self.store.payment_preferences = {'enabled_methods': ['airtel_money']}
        self.store.save()
        with self.assertRaises(ValidationError):
            get_payment_policy(self.store)

    def test_disabled_mode_is_not_offered(self):
        settings = SystemSettings.get_settings()
        settings.payment_policy = {**DEFAULT_PAYMENT_POLICY, 'enabled_methods': ['cash']}
        settings.save()
        _, options = available_payment_options(self.store, True)
        self.assertTrue(options)
        self.assertTrue(all(x['method'] == 'cash' for x in options))

    def test_legacy_order_without_arrangement_remains_readable(self):
        self.assertIsNone(payment_summary(self.make_order()))

    def test_all_ledger_amounts_remain_decimal(self):
        arrangement = create_arrangement(self.make_order(), 'courier_cash', 'cash', user=self.client)
        obligation = arrangement.obligations.get(kind='commission')
        self.assertIsInstance(obligation.remaining_amount, Decimal)
        self.assertEqual(obligation.remaining_amount, Decimal('800.00'))

    def test_full_product_refund_cancels_commission(self):
        order = self.make_order()
        arrangement = create_arrangement(order, 'courier_cash', 'cash', user=self.client)
        record_refund(order, 'products', Decimal('10000'), self.admin, 'REF-PROD-1', 'Retour complet')
        self.assertEqual(arrangement.obligations.get(kind='commission').status, 'cancelled')

    def test_delivery_refund_does_not_cancel_courier_payment_or_commission(self):
        order = self.make_order()
        arrangement = create_arrangement(order, 'direct_split', 'cash', user=self.client)
        record_refund(order, 'delivery', Decimal('2000'), self.admin, 'REF-DEL-1', 'Geste commercial')
        self.assertNotEqual(arrangement.obligations.get(kind='commission').status, 'cancelled')
        self.assertEqual(arrangement.obligations.get(kind='delivery').status, 'refunded')

    def test_receipt_declarant_cannot_confirm_or_reject_own_receipt(self):
        arrangement = create_arrangement(self.make_order(), 'courier_cash', 'cash', user=self.client)
        obligation = arrangement.obligations.get(kind='products')
        receipt = PaymentReceipt.objects.create(obligation=obligation, actor=self.client, amount='1000', method='cash', reference='SELF-1', idempotency_key='self-1')
        with self.assertRaises(ValidationError):
            confirm_receipt(receipt, self.client)
        with self.assertRaises(ValidationError):
            reject_receipt(receipt, self.client, 'Conflit')

    def test_rejected_receipt_keeps_reason_and_reviewer(self):
        arrangement = create_arrangement(self.make_order(), 'courier_cash', 'cash', user=self.client)
        receipt = PaymentReceipt.objects.create(obligation=arrangement.obligations.get(kind='products'), actor=self.courier, amount='1000', method='cash', reference='REJECT-1', idempotency_key='reject-1')
        reject_receipt(receipt, self.client, 'Montant non remis')
        receipt.refresh_from_db()
        self.assertEqual(receipt.rejected_by, self.client)
        self.assertEqual(receipt.rejection_reason, 'Montant non remis')
        self.assertIsNotNone(receipt.rejected_at)

    def test_cash_settlement_declarant_cannot_self_confirm(self):
        arrangement = create_arrangement(self.make_order(), 'courier_cash', 'cash', user=self.client)
        commission = arrangement.obligations.get(kind='commission')
        commission.status = 'unpaid'
        commission.save()
        settlement = create_settlement(self.store, '100', 'cash', self.manager, reference='SELF-SETTLEMENT')
        with self.assertRaises(ValidationError):
            confirm_settlement(settlement, self.manager)

    def test_store_collects_all_creates_delivery_debt_from_store(self):
        arrangement = create_arrangement(self.make_order(), 'store_collects_all', 'cash', user=self.client)
        delivery = arrangement.obligations.get(kind='delivery')
        self.assertEqual((delivery.payer, delivery.payee, delivery.amount), ('store', 'courier', Decimal('2000')))

    def test_courier_cash_limit_blocks_another_collection(self):
        settings = SystemSettings.get_settings()
        settings.payment_policy = {**DEFAULT_PAYMENT_POLICY, 'courier_cash_limit': '15000'}
        settings.save()
        first = self.make_order()
        arrangement = create_arrangement(first, 'courier_cash', 'cash', user=self.client)
        first.delivery.delivery_agent = self.courier
        first.delivery.save()
        receipt = PaymentReceipt.objects.create(obligation=arrangement.obligations.get(kind='products'), actor=self.courier, amount='10000', method='cash', reference='COLLECT-1', idempotency_key='collect-1')
        confirm_receipt(receipt, self.client)
        second = self.make_order()
        create_arrangement(second, 'courier_cash', 'cash', user=self.client)
        self.assertEqual(courier_cash_position(self.courier), Decimal('10000'))
        self.assertFalse(can_courier_accept_collection(self.courier, second))

    def test_merchant_debt_limit_blocks_new_debt(self):
        settings = SystemSettings.get_settings()
        settings.payment_policy = {**DEFAULT_PAYMENT_POLICY, 'merchant_debt_limit': '1000'}
        settings.save()
        create_arrangement(self.make_order(), 'courier_cash', 'cash', user=self.client)
        with self.assertRaises(ValidationError):
            create_arrangement(self.make_order(), 'courier_cash', 'cash', user=self.client)

    def test_assigned_uncollected_cash_is_reserved_against_courier_limit(self):
        settings = SystemSettings.get_settings()
        settings.payment_policy = {**DEFAULT_PAYMENT_POLICY, 'courier_cash_limit': '15000'}
        settings.save()
        first = self.make_order()
        create_arrangement(first, 'courier_cash', 'cash', user=self.client)
        first.delivery.delivery_agent = self.courier
        first.delivery.save()
        second = self.make_order()
        create_arrangement(second, 'courier_cash', 'cash', user=self.client)
        self.assertEqual(courier_cash_position(self.courier), Decimal('0'))
        self.assertEqual(courier_cash_exposure(self.courier), Decimal('10000'))
        self.assertFalse(can_courier_accept_collection(self.courier, second))

    def test_end_to_end_courier_cash_partial_commission(self):
        order = self.make_order()
        arrangement = create_arrangement(order, 'courier_cash', 'cash', user=self.client)
        order.delivery.delivery_agent = self.courier
        order.delivery.save()
        for kind, amount, reference in [('products', '10000', 'E2E-P'), ('delivery', '2000', 'E2E-D')]:
            receipt = PaymentReceipt.objects.create(obligation=arrangement.obligations.get(kind=kind), actor=self.courier, amount=amount, method='cash', reference=reference, idempotency_key=reference)
            confirm_receipt(receipt, self.client)
        remittance = PaymentReceipt.objects.create(obligation=arrangement.obligations.get(kind='courier_remittance'), actor=self.courier, amount='10000', method='cash', reference='E2E-R', idempotency_key='E2E-R')
        confirm_receipt(remittance, self.manager)
        order.status = 'delivered'
        order.save()
        settlement = create_settlement(self.store, '500', 'cash', self.manager, reference='E2E-C1')
        confirm_settlement(settlement, self.admin)
        commission = arrangement.obligations.get(kind='commission')
        commission.refresh_from_db()
        self.assertEqual(commission.status, 'partially_paid')
        self.assertEqual(commission.remaining_amount, Decimal('300'))

    def test_admin_financial_control_endpoint_summarizes_store_and_courier(self):
        order = self.make_order()
        create_arrangement(order, 'courier_cash', 'cash', user=self.client)
        order.delivery.delivery_agent = self.courier
        order.delivery.save()
        client = APIClient()
        client.force_authenticate(self.admin)
        response = client.get('/api/v1/payments/financial-control/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['stores'][0]['store_id'], self.store.id)
        self.assertEqual(response.data['data']['couriers'][0]['courier_id'], self.courier.id)

    def test_end_to_end_direct_split(self):
        order = self.make_order()
        arrangement = create_arrangement(order, 'direct_split', 'cash', user=self.client)
        order.delivery.delivery_agent = self.courier
        order.delivery.save()
        product_receipt = PaymentReceipt.objects.create(obligation=arrangement.obligations.get(kind='products'), actor=self.manager, amount='10000', method='cash', reference='SPLIT-P', idempotency_key='SPLIT-P')
        confirm_receipt(product_receipt, self.client)
        delivery_receipt = PaymentReceipt.objects.create(obligation=arrangement.obligations.get(kind='delivery'), actor=self.courier, amount='2000', method='cash', reference='SPLIT-D', idempotency_key='SPLIT-D')
        confirm_receipt(delivery_receipt, self.client)
        self.assertEqual(arrangement.obligations.get(kind='products').status, 'paid')
        self.assertEqual(arrangement.obligations.get(kind='delivery').status, 'paid')

    def test_end_to_end_store_collects_all_with_partial_refund(self):
        order = self.make_order()
        arrangement = create_arrangement(order, 'store_collects_all', 'cash', user=self.client)
        collection = PaymentReceipt.objects.create(obligation=arrangement.obligations.get(kind='products'), actor=self.manager, amount='10000', method='cash', reference='STORE-P', idempotency_key='STORE-P')
        confirm_receipt(collection, self.client)
        delivery_collection = PaymentReceipt.objects.create(obligation=arrangement.obligations.get(kind='delivery_collection'), actor=self.manager, amount='2000', method='cash', reference='STORE-DC', idempotency_key='STORE-DC')
        confirm_receipt(delivery_collection, self.client)
        payout = PaymentReceipt.objects.create(obligation=arrangement.obligations.get(kind='delivery'), actor=self.courier, amount='2000', method='cash', reference='STORE-DP', idempotency_key='STORE-DP')
        confirm_receipt(payout, self.manager)
        record_refund(order, 'products', Decimal('2500'), self.admin, 'STORE-REF', 'Remboursement partiel')
        products = arrangement.obligations.get(kind='products')
        commission = arrangement.obligations.get(kind='commission')
        self.assertEqual(products.status, 'partially_refunded')
        self.assertEqual(commission.remaining_amount, Decimal('600'))
        self.assertEqual(arrangement.obligations.get(kind='delivery').status, 'paid')

    def test_legacy_refund_endpoint_records_new_ledger_adjustment(self):
        order = self.make_order()
        arrangement = create_arrangement(order, 'direct_split', 'cash', user=self.client)
        intent = PaymentIntent.objects.create(order=order, user=self.client, reference='LEGACY-REFUND-1', amount=10000, provider='cinetpay', status='SUCCESS')
        client = APIClient()
        client.force_authenticate(self.admin)
        response = client.post('/api/v1/payments/refund/', {'reference': intent.reference, 'amount': '2500', 'component': 'products', 'reason': 'Retour partiel'}, format='json')
        self.assertEqual(response.status_code, 200)
        products = arrangement.obligations.get(kind='products')
        self.assertEqual(products.adjustments.filter(adjustment_type='refund').count(), 1)
        self.assertEqual(arrangement.obligations.get(kind='commission').remaining_amount, Decimal('600'))
