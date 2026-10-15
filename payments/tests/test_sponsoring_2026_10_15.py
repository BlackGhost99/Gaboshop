"""Mise en avant payante (sponsoring) et frais petit panier (15 oct. 2026)."""
from datetime import time, timedelta
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from api.models import SystemSettings
from payments.configuration import DEFAULT_PAYMENT_POLICY
from payments.models import PaymentIntent, SponsoredProduct
from payments.views import process_intent_outcome
from products.models import Product, ProductCategory
from stores.models import Store, StoreCategory
from users.models import User

INIT_OK = {'status': 'pending'}


class SponsoringTests(TestCase):
    def setUp(self):
        cache.clear()  # limite de commandes par heure : partagée entre les tests sinon
        self.manager = User.objects.create_user(phone='+24107400101', password='x', user_type='store_manager')
        other_manager = User.objects.create_user(phone='+24107400102', password='x', user_type='store_manager')
        category = StoreCategory.objects.create(name='Test')
        self.store = Store.objects.create(is_verified=True, name='A', category=category, manager=self.manager,
                                          phone='+24107400110', address='Libreville', zone='Centre')
        self.other_store = Store.objects.create(is_verified=True, name='B', category=category, manager=other_manager,
                                                phone='+24107400111', address='Libreville', zone='Centre')
        pcat = ProductCategory.objects.create(store_category=category, name='P', commission_rate=Decimal('5'))
        self.product = Product.objects.create(store=self.store, category=pcat, name='Mis en avant', price=Decimal('1000'), stock=5)
        self.plain = Product.objects.create(store=self.store, category=pcat, name='Normal', price=Decimal('1000'), stock=5)
        self.foreign = Product.objects.create(store=self.other_store, category=pcat, name='Autre', price=Decimal('1000'), stock=5)
        self.api = APIClient()
        self.api.force_authenticate(self.manager)

    def enable(self, on=True):
        s = SystemSettings.get_settings()
        s.sponsoring_enabled = on
        s.sponsor_product_week_price = Decimal('1500')
        s.sponsor_store_week_price = Decimal('5000')
        s.save()

    def buy(self, **over):
        body = {'target': 'product', 'product_id': self.product.id, 'weeks': 2, 'operator': 'airtel', 'phone_number': '077400101'}
        body.update(over)
        with mock.patch('payments.utils.call_airtel_money_init', return_value=INIT_OK):
            return self.api.post('/api/v1/store/sponsoring/', body, format='json')

    def test_greyed_out_while_disabled(self):
        res = self.api.get('/api/v1/store/sponsoring/')
        self.assertEqual(res.status_code, 200)
        self.assertFalse(res.json()['data']['enabled'])
        self.assertEqual(self.buy().status_code, 403)
        self.assertFalse(SponsoredProduct.objects.exists())

    def test_cannot_sponsor_another_shops_product(self):
        self.enable()
        self.assertEqual(self.buy(product_id=self.foreign.id).status_code, 404)

    def test_paid_then_listed_first_with_label(self):
        self.enable()
        res = self.buy()
        self.assertEqual(res.status_code, 201, res.content)
        intent = PaymentIntent.objects.get(reference=res.json()['data']['reference'])
        self.assertEqual(intent.amount, 3000)  # 2 semaines x 1 500
        sponsorship = SponsoredProduct.objects.get()
        self.assertEqual(sponsorship.status, 'pending_payment')

        listed = self.api.get('/api/v1/products/').json()
        rows = listed['results']['data'] if 'results' in listed else listed['data']
        self.assertFalse(any(r['sponsored'] for r in rows))  # pas encore payé

        process_intent_outcome(intent, 'TX-1', 'success', {})
        process_intent_outcome(intent, 'TX-1', 'success', {})  # deuxième notification : sans effet
        sponsorship.refresh_from_db()
        self.assertEqual(sponsorship.status, 'active')
        self.assertAlmostEqual((sponsorship.end_date - sponsorship.start_date).days, 14)

        listed = self.api.get('/api/v1/products/').json()
        rows = listed['results']['data'] if 'results' in listed else listed['data']
        self.assertEqual(rows[0]['id'], self.product.id)
        self.assertTrue(rows[0]['sponsored'])
        self.assertFalse(next(r for r in rows if r['id'] == self.plain.id)['sponsored'])

    def test_second_purchase_follows_the_first(self):
        self.enable()
        first = PaymentIntent.objects.get(reference=self.buy(weeks=1).json()['data']['reference'])
        second = PaymentIntent.objects.get(reference=self.buy(weeks=1).json()['data']['reference'])
        process_intent_outcome(first, 'TX-A', 'success', {})
        process_intent_outcome(second, 'TX-B', 'success', {})
        a, b = SponsoredProduct.objects.order_by('id')
        self.assertEqual(b.start_date, a.end_date)

    def test_failed_payment_cancels(self):
        self.enable()
        intent = PaymentIntent.objects.get(reference=self.buy().json()['data']['reference'])
        process_intent_outcome(intent, 'TX-F', 'failed', {})
        self.assertEqual(SponsoredProduct.objects.get().status, 'cancelled')

    def test_store_sponsoring_puts_store_first(self):
        self.enable()
        res = self.buy(target='store', weeks=1)
        intent = PaymentIntent.objects.get(reference=res.json()['data']['reference'])
        self.assertEqual(intent.amount, 5000)
        process_intent_outcome(intent, 'TX-S', 'success', {})
        anon = APIClient()
        data = anon.get('/api/v1/stores/').json()
        rows = data['results'] if isinstance(data.get('results'), list) else data.get('data') or data['results']['data']
        self.assertEqual(rows[0]['id'], self.store.id)
        self.assertTrue(rows[0]['sponsored'])

    def test_expired_is_not_shown(self):
        now = timezone.now()
        SponsoredProduct.objects.create(store=self.store, product=self.plain, sponsor_type='featured', price_paid=0,
                                        status='active', start_date=now - timedelta(days=10), end_date=now - timedelta(days=3))
        listed = self.api.get('/api/v1/products/').json()
        rows = listed['results']['data'] if 'results' in listed else listed['data']
        self.assertFalse(any(r['sponsored'] for r in rows))


class SmallOrderFeeTests(TestCase):
    def setUp(self):
        cache.clear()  # limite de commandes par heure : partagée entre les tests sinon
        manager = User.objects.create_user(phone='+24107400201', password='x', user_type='store_manager')
        self.client_user = User.objects.create_user(phone='+24107400202', password='x', user_type='client')
        category = StoreCategory.objects.create(name='Test')
        self.store = Store.objects.create(
            is_verified=True, name='Commerce', category=category, manager=manager, phone='+24107400210', address='Libreville',
            zone='Centre', commission_rate=Decimal('5'), opening_time=time(0, 0), closing_time=time(23, 59),
            delivery_fee=Decimal('1000'),
        )
        pcat = ProductCategory.objects.create(store_category=category, name='P', commission_rate=Decimal('5'))
        self.product = Product.objects.create(store=self.store, category=pcat, name='Pain', price=Decimal('1500'), stock=50, weight_kg=Decimal('1'))
        s = SystemSettings.get_settings()
        s.payment_policy = {**DEFAULT_PAYMENT_POLICY,
                            'enabled_flows': DEFAULT_PAYMENT_POLICY['enabled_flows'] + ['platform_online']}
        s.small_order_fee = Decimal('200')
        s.small_order_threshold = Decimal('5000')
        s.airtel_money_fee = Decimal('0')
        s.save()
        self.api = APIClient()
        self.api.force_authenticate(self.client_user)

    def order(self, quantity, flow, method):
        payload = {
            'store': self.store.id, 'city': 'Libreville', 'delivery_address': 'Rue 1', 'delivery_phone': '077400299',
            'delivery_zone': 'Akanda', 'delivery_requested': True, 'payment_flow': flow, 'payment_method': method,
            'delivery_payment_method': 'gaboshop' if flow == 'platform_online' else '',
            'items': [{'product_id': self.product.id, 'quantity': quantity}],
        }
        online = flow == 'platform_online'
        with mock.patch('delivery.tasks.assign_nearest_delivery_agent'), \
                mock.patch('payments.configuration.platform_online_ready', return_value=online):
            return self.api.post('/api/v1/orders/create/', payload, format='json')

    def created(self, res):
        from orders.models import Order
        self.assertEqual(res.status_code, 201, res.content)
        return Order.objects.order_by('-id').first()

    def test_online_small_basket_pays_fee(self):
        order = self.created(self.order(2, 'platform_online', 'airtel_money'))
        self.assertEqual(order.payment_fees, Decimal('200'))
        self.assertEqual(order.total_amount, Decimal('3000') + Decimal('1000') + Decimal('200'))

    def test_online_big_basket_no_fee(self):
        order = self.created(self.order(4, 'platform_online', 'airtel_money'))  # 6 000 F
        self.assertEqual(order.payment_fees, Decimal('0'))

    def test_cash_never_pays_fee(self):
        s = SystemSettings.get_settings()
        s.payment_policy = DEFAULT_PAYMENT_POLICY
        s.save()
        order = self.created(self.order(2, 'direct_split', 'cash'))
        self.assertEqual(order.payment_fees, Decimal('0'))

    def test_off_by_default(self):
        s = SystemSettings.get_settings()
        s.small_order_fee = Decimal('0')
        s.save()
        order = self.created(self.order(2, 'platform_online', 'airtel_money'))
        self.assertEqual(order.payment_fees, Decimal('0'))

    def test_quote_shows_fee(self):
        res = self.api.post('/api/v1/orders/delivery-quote/', {
            'store': self.store.id, 'city': 'Libreville', 'delivery_zone': 'Akanda',
            'items': [{'product_id': self.product.id, 'quantity': 2}]}, format='json')
        self.assertEqual(res.json()['data']['small_order_fee_online'], '200')
        res = self.api.post('/api/v1/orders/delivery-quote/', {
            'store': self.store.id, 'delivery_requested': False,
            'items': [{'product_id': self.product.id, 'quantity': 2}]}, format='json')
        self.assertEqual(res.json()['data']['delivery_fee'], '0')
