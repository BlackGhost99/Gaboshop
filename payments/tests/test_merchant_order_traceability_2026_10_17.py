"""Tests : le relevé marchand montre l'origine des commissions sans réclamer une commande annulée."""
from decimal import Decimal

from django.test import TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from orders.models import Order, OrderItem
from payments.direct_models import PaymentArrangement, PaymentObligation, PaymentReceipt
from payments.direct_service import create_settlement, platform_debts
from products.models import Product, ProductCategory
from stores.models import Store, StoreCategory
from users.models import User


class MerchantOrderTraceabilityTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            phone='+241077510001', password='test', user_type='store_manager',
        )
        self.client_user = User.objects.create_user(
            phone='+241077510002', password='test', user_type='client',
        )
        self.store = Store.objects.create(
            name='Boutique traçabilité', manager=self.manager,
            category=StoreCategory.objects.create(name='Catégorie traçabilité'),
            phone='+241077510003', address='Libreville', zone='Centre',
        )
        self.product = Product.objects.create(
            store=self.store,
            category=ProductCategory.objects.create(
                name='Article traçabilité',
                store_category=self.store.category,
                commission_rate=Decimal('8'),
            ),
            name='Casque audio', price=Decimal('10000'), stock=20, weight_kg=Decimal('1'),
        )

    def make_debt(self, status, fee):
        order = Order.objects.create(
            client=self.client_user, store=self.store, status=status,
            delivery_address='Akanda', delivery_phone=self.client_user.phone,
            delivery_zone='Centre', items_total=Decimal('10000'),
            delivery_fee=Decimal('2000'), total_amount=Decimal('12000'),
            commission_amount=Decimal(fee),
        )
        OrderItem.objects.create(order=order, product=self.product, quantity=2, unit_price=Decimal('5000'))
        arrangement = PaymentArrangement.objects.create(
            order=order, store=self.store, created_by=self.client_user,
            flow='direct_split', method='cash', delivery_method='cash',
            products_amount=Decimal('10000'), delivery_amount=Decimal('2000'),
            commission_amount=Decimal(fee), commission_rate=Decimal('8'),
        )
        obligation = PaymentObligation.objects.create(
            arrangement=arrangement, kind='commission', payer='store',
            payee='platform', amount=Decimal(fee), status='unpaid',
        )
        return order, obligation

    def test_cancelled_and_pending_are_reviewed_not_charged(self):
        delivered, payable = self.make_debt('delivered', '800')
        cancelled, _ = self.make_debt('cancelled', '300')
        pending, _ = self.make_debt('pending_payment', '450')
        api = APIClient()
        api.force_authenticate(user=self.manager)
        response = api.get('/api/v1/payments/debts/mine/')
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data['data']
        self.assertEqual(Decimal(data['total_due']), Decimal('800'))
        self.assertEqual([row['order_id'] for row in data['items']], [delivered.id])
        self.assertEqual(Decimal(data['review']['total_due']), Decimal('750'))
        self.assertEqual(
            {row['order_id'] for row in data['review']['items']},
            {cancelled.id, pending.id},
        )
        item = data['items'][0]
        self.assertEqual(item['order_status'], 'delivered')
        self.assertEqual(item['items'][0]['name'], 'Casque audio')
        self.assertEqual(item['items'][0]['quantity'], 2)
        self.assertEqual(Decimal(item['order_total']), Decimal('12000'))
        self.assertIsNotNone(item['created_at'])
        self.assertEqual(item['kind'], 'commission')
        self.assertEqual(item['payment_flow'], 'direct_split')
        self.assertEqual(platform_debts('store', self.store), [payable])

    def test_partial_payment_reduces_amount_but_retains_origin(self):
        order, obligation = self.make_debt('delivered', '800')
        PaymentReceipt.objects.create(
            obligation=obligation, actor=self.manager,
            amount=Decimal('200'), method='cash', reference='CASH-HIST-TEST-1',
            idempotency_key='hist-payment-1', status='confirmed',
            confirmed_by=self.manager,
        )
        api = APIClient()
        api.force_authenticate(user=self.manager)
        data = api.get('/api/v1/payments/debts/mine/').data['data']
        self.assertEqual(Decimal(data['total_due']), Decimal('600'))
        self.assertEqual(data['items'][0]['order_id'], order.id)
        self.assertEqual(Decimal(data['items'][0]['paid_to_platform']), Decimal('200'))

    def test_review_only_cannot_be_collected_as_new_commission_payment(self):
        self.make_debt('cancelled', '300')
        self.assertEqual(platform_debts('store', self.store), [])
        with self.assertRaises(ValidationError):
            create_settlement(self.store, Decimal('300'), 'cash', self.manager, reference='NON-DUE')
