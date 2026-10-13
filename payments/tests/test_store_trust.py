"""Protection contre les faux commerces : validation par l'admin, versement après réception, gel des versements."""
from datetime import time
from decimal import Decimal
from importlib import import_module
from unittest import mock

from django.apps import apps as django_apps
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from api.models import SystemSettings
from orders.models import Order, OrderItem
from payments.models import Payment, StorePayout
from payments.configuration import DEFAULT_PAYMENT_POLICY
from payments.store_payout_service import FROZEN_NOTE, payout_moment_reached, release_store_payment
from products.models import Product, ProductCategory
from stores.models import Store, StoreCategory
from users.models import User

TRANSFER = 'payments.store_payout_service.call_singpay_transfer'


class StoreTrustTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(phone='+24107100002', password='x', user_type='store_manager')
        self.client_user = User.objects.create_user(phone='+24107100003', password='x', user_type='client')
        self.admin = User.objects.create_user(phone='+24107100004', password='x', user_type='admin')
        category = StoreCategory.objects.create(name='Test')
        self.store = Store.objects.create(
            name='Nouveau commerce', category=category, manager=self.manager, phone='+24107100100',
            address='Libreville', zone='Centre', commission_rate=Decimal('8'),
            singpay_disbursement_id='DISB-001', opening_time=time(0, 0), closing_time=time(0, 0),
        )
        product_category = ProductCategory.objects.create(store_category=category, name='Produits', commission_rate=Decimal('8'))
        self.product = Product.objects.create(store=self.store, category=product_category, name='Article', price=Decimal('10000'), stock=20, weight_kg=Decimal('1'))
        settings = SystemSettings.get_settings()
        settings.payment_policy = DEFAULT_PAYMENT_POLICY
        settings.save(update_fields=['payment_policy'])
        patcher = mock.patch('delivery.tasks.assign_nearest_delivery_agent')
        patcher.start()
        self.addCleanup(patcher.stop)

    def make_order(self, status='confirmed'):
        order = Order.objects.create(client=self.client_user, store=self.store, delivery_address='Akanda', delivery_phone='+24107100003', delivery_zone='Centre', delivery_fee=Decimal('2000'))
        OrderItem.objects.create(order=order, product=self.product, quantity=1, unit_price=self.product.price)
        Order.objects.filter(pk=order.pk).update(items_total=Decimal('10000'), commission_rate=Decimal('8'), commission_amount=Decimal('800'), total_amount=Decimal('12000'))
        Payment.objects.create(order=order, payment_method='airtel_money', status='pending', amount=Decimal('12000'))
        Payment.objects.filter(order=order).update(status='success')
        Order.objects.filter(pk=order.pk).update(status=status)
        order.refresh_from_db()
        return order

    # --- un nouveau commerce reste invisible -------------------------------------------
    def test_new_store_is_not_verified(self):
        self.assertFalse(self.store.is_verified)
        self.assertFalse(self.store.is_trusted)

    def test_unverified_store_is_hidden_from_customers(self):
        api = APIClient()
        self.assertEqual(api.get(f'/api/v1/stores/{self.store.id}/').status_code, 404)
        listed = api.get('/api/v1/stores/').json()
        rows = listed.get('results') or listed.get('data') or []
        self.assertNotIn(self.store.id, [row['id'] for row in rows])
        products = api.get('/api/v1/products/').json()
        product_rows = products.get('results') or products.get('data') or []
        if isinstance(product_rows, dict):
            product_rows = product_rows.get('results') or product_rows.get('products') or []
        self.assertNotIn(self.product.id, [row['id'] for row in product_rows])
        self.assertEqual(api.get(f'/api/v1/products/{self.product.id}/').status_code, 404)

    def test_manager_previews_own_unverified_store(self):
        api = APIClient()
        api.force_authenticate(self.manager)
        self.assertEqual(api.get(f'/api/v1/stores/{self.store.id}/').status_code, 200)
        self.assertEqual(api.get(f'/api/v1/products/{self.product.id}/').status_code, 200)
        other = User.objects.create_user(phone='+24107100009', password='x', user_type='store_manager')
        api.force_authenticate(other)
        self.assertEqual(api.get(f'/api/v1/stores/{self.store.id}/').status_code, 404)

    def test_verified_store_is_visible(self):
        Store.objects.filter(pk=self.store.pk).update(is_verified=True)
        self.assertEqual(APIClient().get(f'/api/v1/stores/{self.store.id}/').status_code, 200)

    def test_unverified_store_cannot_receive_orders(self):
        api = APIClient()
        api.force_authenticate(self.client_user)
        response = api.post('/api/v1/orders/create/', {
            'store': self.store.id, 'city': 'Libreville', 'delivery_address': 'Akanda', 'delivery_phone': '077391199',
            'delivery_zone': 'Centre', 'delivery_requested': True, 'payment_flow': 'direct_split',
            'payment_method': 'cash', 'items': [{'product_id': self.product.id, 'quantity': 1}],
        }, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('vérification', str(response.content.decode()))
        self.assertEqual(Order.objects.count(), 0)

    # --- moment du versement -----------------------------------------------------------
    def test_payout_moment_depends_on_trust(self):
        order = self.make_order()
        self.assertFalse(payout_moment_reached(order, 'preparing'))
        self.assertTrue(payout_moment_reached(order, 'client_confirmed'))
        self.store.is_trusted = True
        self.store.save()
        order.refresh_from_db()
        self.assertTrue(payout_moment_reached(order, 'preparing'))
        self.assertFalse(payout_moment_reached(order, 'client_confirmed'))

    @override_settings(SINGPAY_ENABLE_TRANSFER=False)
    def test_untrusted_store_is_not_paid_at_preparing(self):
        order = self.make_order()
        with self.captureOnCommitCallbacks(execute=True):
            order.status = 'preparing'
            order.save()
        self.assertFalse(StorePayout.objects.filter(order=order).exists())

    @override_settings(SINGPAY_ENABLE_TRANSFER=False)
    def test_trusted_store_is_paid_at_preparing(self):
        Store.objects.filter(pk=self.store.pk).update(is_verified=True, is_trusted=True)
        order = self.make_order()
        with self.captureOnCommitCallbacks(execute=True):
            order.status = 'preparing'
            order.save()
        self.assertTrue(StorePayout.objects.filter(order=order).exists())

    # --- gel des versements --------------------------------------------------------------
    @override_settings(SINGPAY_ENABLE_TRANSFER=True)
    def test_frozen_payouts_stay_pending_then_leave_on_unfreeze(self):
        Store.objects.filter(pk=self.store.pk).update(is_verified=True, payouts_frozen=True)
        order = self.make_order(status='delivered')
        with mock.patch(TRANSFER) as transfer:
            payout = release_store_payment(order.id)
            transfer.assert_not_called()
        self.assertEqual((payout.status, payout.note), ('pending', FROZEN_NOTE))

        api = APIClient()
        api.force_authenticate(self.admin)
        with mock.patch(TRANSFER, return_value={'status': 'ok'}) as transfer:
            response = api.post(f'/api/v1/admin/stores/{self.store.id}/trust/', {'payouts_frozen': False}, format='json')
            self.assertEqual(response.status_code, 200)
            transfer.assert_called_once()
        payout.refresh_from_db()
        self.assertNotEqual(payout.note, FROZEN_NOTE)

    # --- bouton admin ------------------------------------------------------------------
    def test_trust_endpoint_is_admin_only(self):
        api = APIClient()
        api.force_authenticate(self.manager)
        response = api.post(f'/api/v1/admin/stores/{self.store.id}/trust/', {'is_verified': True}, format='json')
        self.assertEqual(response.status_code, 403)
        self.store.refresh_from_db()
        self.assertFalse(self.store.is_verified)

    def test_admin_validates_store_and_manager_is_notified(self):
        api = APIClient()
        api.force_authenticate(self.admin)
        with mock.patch('notifications.service.NotificationService.notify_user') as notify:
            response = api.post(f'/api/v1/admin/stores/{self.store.id}/trust/', {'is_verified': True, 'is_trusted': True}, format='json')
        self.assertEqual(response.status_code, 200)
        self.store.refresh_from_db()
        self.assertTrue(self.store.is_verified)
        self.assertTrue(self.store.is_trusted)
        self.assertIsNotNone(self.store.verified_at)
        notify.assert_called_once()

    # --- migration : les commerces existants restent visibles -------------------------
    def test_migration_verifies_existing_stores(self):
        migration = import_module('stores.migrations.0020_store_trust')
        migration.verify_existing_stores(django_apps, None)
        self.store.refresh_from_db()
        self.assertTrue(self.store.is_verified)
        self.assertIsNotNone(self.store.verified_at)

    # --- encart « Votre argent en sécurité » ---------------------------------------------
    def test_held_funds_lists_money_waiting_for_the_store(self):
        from payments.store_payout_service import held_funds
        order = self.make_order(status='delivered')
        funds = held_funds(self.store)
        self.assertEqual(funds['count'], 1)
        self.assertEqual(funds['total'], 9200.0)
        self.assertEqual(funds['items'][0]['order_number'], order.order_number)
        self.assertIn('réception', funds['items'][0]['stage'])
        StorePayout.objects.create(order=order, store=self.store, amount=Decimal('9200'), products_amount=Decimal('10000'),
                                   commission_amount=Decimal('800'), reference='STOREPAY_T', status='paid')
        self.assertEqual(held_funds(self.store)['count'], 0)

    def test_store_dashboard_shows_held_funds(self):
        api = APIClient()
        api.force_authenticate(self.manager)
        self.make_order(status='delivered')
        body = api.get('/api/v1/dashboard/store/').json()
        data = body.get('data', body)
        self.assertEqual(data['held_funds']['count'], 1)
