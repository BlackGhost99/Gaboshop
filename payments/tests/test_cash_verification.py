from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from api.models import SystemSettings
from delivery.models import Delivery
from orders.models import Order, OrderItem
from payments.configuration import DEFAULT_PAYMENT_POLICY
from payments.direct_models import PaymentReceipt
from payments.direct_service import create_arrangement, can_dispatch
from payments.models import CategoryCommission
from products.models import Product, ProductCategory
from stores.models import Store, StoreCategory
from users.models import User


class CashVerificationTests(TestCase):
    """Paiement direct au commerce (sans agrégateur) : le payeur déclare, le bénéficiaire confirme."""

    def setUp(self):
        self.manager = User.objects.create_user(phone='+24106200002', password='x', user_type='store_manager')
        self.client_user = User.objects.create_user(phone='+24106200003', password='x', user_type='client')
        self.other = User.objects.create_user(phone='+24106200005', password='x', user_type='client')
        self.category = StoreCategory.objects.create(name='Test')
        self.store = Store.objects.create(
            name='Commerce', category=self.category, manager=self.manager, phone='+24106000100', address='Libreville', zone='Centre',
            commission_rate=Decimal('8'), payment_preferences={'instructions': {'airtel_money': 'Code marchand Airtel 123456'}},
        )
        pcat = ProductCategory.objects.create(store_category=self.category, name='Produits', commission_rate=Decimal('8'))
        self.product = Product.objects.create(store=self.store, category=pcat, name='Article', price=Decimal('10000'), stock=20, weight_kg=Decimal('1'))
        settings = SystemSettings.get_settings()
        settings.payment_policy = DEFAULT_PAYMENT_POLICY
        settings.save(update_fields=['payment_policy'])
        self.api = APIClient()

    def order(self, method='airtel_money', flow='direct_split'):
        order = Order.objects.create(client=self.client_user, store=self.store, delivery_address='Akanda', delivery_phone='+24106200003', delivery_zone='Centre', delivery_fee=Decimal('0'))
        OrderItem.objects.create(order=order, product=self.product, quantity=1, unit_price=self.product.price)
        order.items_total = Decimal('10000')
        order.commission_rate = Decimal('8')
        order.commission_amount = Decimal('800')
        order.total_amount = Decimal('10000')
        order.save()
        create_arrangement(order, flow, method, user=self.client_user)
        return order

    def products_obligation(self, order):
        return order.payment_arrangement.obligations.get(kind='products')

    def declare(self, user, obligation, reference='MP2410061234', key='k1', amount='10000', method='airtel_money'):
        self.api.force_authenticate(user)
        return self.api.post('/api/v1/payments/receipts/', {'obligation_id': obligation.id, 'amount': amount, 'method': method, 'reference': reference, 'idempotency_key': key}, format='json')

    def test_summary_shows_merchant_code_and_order_number(self):
        order = self.order()
        self.api.force_authenticate(self.client_user)
        data = self.api.get(f'/api/v1/payments/arrangements/order/{order.id}/').json()['data']
        self.assertEqual(data['instructions'], 'Code marchand Airtel 123456')
        self.assertEqual(data['order_number'], order.order_number)
        products = next(o for o in data['obligations'] if o['kind'] == 'products')
        self.assertTrue(products['i_am_payer'] and products['can_declare'])
        self.assertFalse(products['can_review'])

    def test_client_declares_store_confirms_then_order_can_ship(self):
        order = self.order()
        self.assertFalse(can_dispatch(order))
        res = self.declare(self.client_user, self.products_obligation(order))
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()['data']['status'], 'pending')
        self.api.force_authenticate(self.manager)
        pending = self.api.get('/api/v1/payments/receipts/pending/').json()['data']
        self.assertEqual([p['reference'] for p in pending], ['MP2410061234'])
        self.assertEqual(self.api.post(f"/api/v1/payments/receipts/{pending[0]['id']}/confirm/").status_code, 200)
        self.assertTrue(can_dispatch(order))

    def test_client_cannot_confirm_own_payment(self):
        order = self.order()
        receipt_id = self.declare(self.client_user, self.products_obligation(order)).json()['data']['id']
        self.assertEqual(self.api.post(f'/api/v1/payments/receipts/{receipt_id}/confirm/').status_code, 403)

    def test_same_transaction_id_cannot_be_reused(self):
        first, second = self.order(), self.order()
        self.assertEqual(self.declare(self.client_user, self.products_obligation(first), reference='MP 999').status_code, 201)
        res = self.declare(self.client_user, self.products_obligation(second), reference='mp999', key='k2')
        self.assertEqual(res.status_code, 400)

    def test_repeated_false_declarations_block_the_client(self):
        self.api.force_authenticate(self.manager)
        for i in range(3):
            order = self.order()
            rid = self.declare(self.client_user, self.products_obligation(order), reference=f'FAUX{i}', key=f'f{i}').json()['data']['id']
            self.api.force_authenticate(self.manager)
            self.assertEqual(self.api.post(f'/api/v1/payments/receipts/{rid}/reject/', {'reason': 'Rien reçu'}, format='json').status_code, 200)
        res = self.declare(self.client_user, self.products_obligation(self.order()), reference='FAUX9', key='f9')
        self.assertEqual(res.status_code, 403)

    def test_store_records_cash_received_without_second_step(self):
        order = self.order(method='cash')
        res = self.declare(self.manager, self.products_obligation(order), reference='', key='c1', method='cash')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()['data']['status'], 'confirmed')

    def test_outsider_cannot_declare(self):
        order = self.order()
        self.assertEqual(self.declare(self.other, self.products_obligation(order)).status_code, 403)

    def test_store_cannot_mark_its_commission_paid(self):
        order = self.order(method='cash')
        commission = order.payment_arrangement.obligations.get(kind='commission')
        commission.status = 'unpaid'
        commission.save()
        rid = self.declare(self.manager, commission, reference='COM1', key='m1', amount='800', method='cash').json()['data']['id']
        self.assertEqual(PaymentReceipt.objects.get(pk=rid).status, 'pending')
        self.api.force_authenticate(self.client_user)
        self.assertEqual(self.api.post(f'/api/v1/payments/receipts/{rid}/confirm/').status_code, 403)


class SecurityFixesTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.manager = User.objects.create_user(phone='+24106300001', password='x', user_type='store_manager', email='gerant@example.com')
        self.client_user = User.objects.create_user(phone='+24106300002', password='secret123', user_type='client')
        category = StoreCategory.objects.create(name='Mode')
        self.store = Store.objects.create(name='Boutique', category=category, manager=self.manager, phone='+24106000200', address='Libreville', zone='Centre')
        pcat = ProductCategory.objects.create(store_category=category, name='Habits')
        self.product = Product.objects.create(store=self.store, category=pcat, name='Robe', price=Decimal('15000'), stock=3, weight_kg=Decimal('1'))
        self.commission = CategoryCommission.objects.create(store_category=category, base_rate=Decimal('8'))

    def test_unsigned_payment_callbacks_are_refused(self):
        self.assertEqual(self.api.post('/api/v1/payments/webhooks/airtel/', {'transaction_id': 'x', 'status_code': 'TS'}, format='json').status_code, 404)
        res = self.api.post('/api/v1/payments/provider/singpay/notify/', {'reference': 'R', 'status': 'SUCCESS'}, format='json')
        self.assertEqual(res.status_code, 401)

    def test_client_cannot_edit_someone_elses_product(self):
        self.api.force_authenticate(self.client_user)
        res = self.api.patch(f'/api/v1/products-api/{self.product.id}/', {'price': '1'}, format='json')
        self.assertIn(res.status_code, (403, 404))
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, Decimal('15000'))

    def test_store_cannot_change_platform_commission(self):
        self.api.force_authenticate(self.manager)
        res = self.api.patch(f'/api/v1/finance/category-commissions/{self.commission.id}/', {'base_rate': '0'}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_public_store_page_hides_manager_private_contact(self):
        data = self.api.get(f'/api/v1/stores/{self.store.id}/').json()
        payload = data.get('data', data)
        self.assertEqual(payload['phone'], '+24106000200')  # le numéro du magasin reste visible
        self.assertEqual(payload['manager_details']['email'], '')
        self.assertEqual(payload['manager_details']['phone'], '')

    def test_login_is_rate_limited_per_phone(self):
        codes = [self.api.post('/api/v1/auth/login/', {'phone': '+24106300002', 'password': f'bad{i}'}, format='json').status_code for i in range(12)]
        self.assertEqual(codes[-1], 429)

    def test_old_ai_confirm_action_is_gone(self):
        self.api.force_authenticate(self.client_user)
        self.assertEqual(self.api.post('/api/v1/ai/confirm-action/', {}, format='json').status_code, 404)

    def test_delivery_pin_locks_after_five_errors(self):
        courier = User.objects.create_user(phone='+24106300009', password='x', user_type='delivery_agent')
        order = Order.objects.create(client=self.client_user, store=self.store, delivery_address='Akanda', delivery_phone='+24106300002', delivery_zone='Centre', delivery_fee=Decimal('0'))
        delivery, _ = Delivery.objects.get_or_create(order=order)
        delivery.delivery_agent = courier
        delivery.save()
        self.api.force_authenticate(courier)
        url = f'/api/v1/dashboard/delivery/{delivery.id}/verify-pin/'
        for _ in range(5):
            self.api.post(url, {'pin_code': '000000' if delivery.delivery_code != '000000' else '111111'}, format='json')
        res = self.api.post(url, {'pin_code': delivery.delivery_code}, format='json')
        self.assertEqual(res.status_code, 429)
