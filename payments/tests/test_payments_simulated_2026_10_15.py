"""Site de test : paiements en ligne simulés de bout en bout (PAYMENTS_SIMULATED), sans argent réel."""
from datetime import time
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from api.models import SystemSettings
from orders.models import Order
from payments.configuration import DEFAULT_PAYMENT_POLICY, available_payment_options, platform_online_ready
from payments import singpay_simulator
from payments.models import Payment, PaymentIntent, SponsoredProduct
from products.models import Product, ProductCategory
from stores.models import Store, StoreCategory
from users.models import User

LATER = singpay_simulator.SIMULATED_DELAY_SECONDS + 1


def later(seconds=LATER):
    """Avance l'horloge du faux SingPay (le client a tapé son code)."""
    real = singpay_simulator.time.time
    return mock.patch('payments.singpay_simulator.time.time', side_effect=lambda: real() + seconds)


@override_settings(PAYMENTS_SIMULATED=True, PAYMENTS_DISABLED=False,
                   SINGPAY_CLIENT_ID='', SINGPAY_CLIENT_SECRET='', SINGPAY_WALLET_ID='')
class SimulatedPaymentTests(TestCase):
    def setUp(self):
        cache.clear()
        self.manager = User.objects.create_user(phone='+24107500101', password='x', user_type='store_manager')
        self.client_user = User.objects.create_user(phone='+24107500102', password='x', user_type='client')
        category = StoreCategory.objects.create(name='Test')
        self.store = Store.objects.create(
            is_verified=True, name='Commerce', category=category, manager=self.manager, phone='+24107500110',
            address='Libreville', zone='Centre', commission_rate=Decimal('5'), opening_time=time(0, 0),
            closing_time=time(23, 59), delivery_fee=Decimal('1000'),
        )
        pcat = ProductCategory.objects.create(store_category=category, name='P', commission_rate=Decimal('5'))
        self.product = Product.objects.create(store=self.store, category=pcat, name='Sac', price=Decimal('5000'),
                                              stock=20, weight_kg=Decimal('1'))
        s = SystemSettings.get_settings()
        s.payment_policy = {**DEFAULT_PAYMENT_POLICY,
                            'enabled_flows': DEFAULT_PAYMENT_POLICY['enabled_flows'] + ['platform_online']}
        s.airtel_money_fee = Decimal('0')
        s.save()
        self.api = APIClient()
        self.api.force_authenticate(self.client_user)
        self.http = mock.patch('payments.utils.requests.request', side_effect=AssertionError('appel réseau'))
        self.http.start()
        self.addCleanup(self.http.stop)
        for target in ('orders.signals.NotificationService.notify_order_status_update',
                       'delivery.tasks.assign_nearest_delivery_agent.delay'):
            patcher = mock.patch(target)
            patcher.start()
            self.addCleanup(patcher.stop)

    def order_and_pay(self, phone='077500102'):
        payload = {
            'store': self.store.id, 'city': 'Libreville', 'delivery_address': 'Rue 1', 'delivery_phone': '077500199',
            'delivery_zone': 'Akanda', 'delivery_requested': True, 'payment_flow': 'platform_online',
            'payment_method': 'airtel_money', 'delivery_payment_method': 'gaboshop',
            'items': [{'product_id': self.product.id, 'quantity': 1}],
        }
        with mock.patch('delivery.tasks.assign_nearest_delivery_agent'):
            res = self.api.post('/api/v1/orders/create/', payload, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        order = Order.objects.order_by('-id').first()
        res = self.api.post(f'/api/v1/orders/{order.id}/payments/init/',
                            {'payment_method': 'airtel_money', 'phone_number': phone}, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        return order

    def verify(self, order):
        cache.clear()
        return self.api.post(f'/api/v1/orders/{order.id}/payments/verify/', {}, format='json')

    def test_online_payment_offered_without_keys_and_flagged(self):
        self.assertTrue(platform_online_ready())
        _policy, options = available_payment_options(self.store)
        self.assertTrue(options and all(o['flow'] == 'platform_online' and o['simulated'] for o in options))

    def test_order_pending_then_paid(self):
        order = self.order_and_pay()
        payment = Payment.objects.get(order=order)
        self.assertTrue(payment.transaction_id.startswith('SIM'))
        self.verify(order)
        payment.refresh_from_db()
        self.assertIn(payment.status, ('pending', 'processing'))
        with later():
            self.verify(order)
        payment.refresh_from_db()
        order.refresh_from_db()
        self.assertEqual(payment.status, 'success')
        self.assertEqual(order.status, 'confirmed')

    def test_number_ending_in_99_is_refused(self):
        order = self.order_and_pay(phone='077500199')
        with later():
            self.verify(order)
        self.assertEqual(Payment.objects.get(order=order).status, 'failed')
        order.refresh_from_db()
        self.assertNotEqual(order.status, 'confirmed')

    def test_sponsoring_paid_when_shop_reopens_the_page(self):
        s = SystemSettings.get_settings()
        s.sponsoring_enabled = True
        s.save()
        shop = APIClient()
        shop.force_authenticate(self.manager)
        res = shop.post('/api/v1/store/sponsoring/', {'target': 'store', 'weeks': 1, 'operator': 'airtel',
                                                       'phone_number': '077500101'}, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(SponsoredProduct.objects.get().status, 'pending_payment')
        cache.clear()
        with later():
            shop.get('/api/v1/store/sponsoring/')
        self.assertEqual(SponsoredProduct.objects.get().status, 'active')
        self.assertEqual(PaymentIntent.objects.get().status, 'SUCCESS')

    def test_simulated_transfer_succeeds(self):
        from payments.utils import call_singpay_transfer
        response = call_singpay_transfer(reference='GABOSHOP_X', disbursement='SIMULATION', amount=4750)
        self.assertFalse(response.get('error'))


@override_settings(PAYMENTS_SIMULATED=True, PAYMENTS_DISABLED=True)
class DisabledWinsTests(TestCase):
    def test_disabled_wins_over_simulated(self):
        self.assertFalse(platform_online_ready())
