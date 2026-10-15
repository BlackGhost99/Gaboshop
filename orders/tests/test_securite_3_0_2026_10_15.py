"""Contrôle de sécurité 3.0 (15/10/2026) : commissions, B2B, forfaits, comptes, IA, stock."""
from decimal import Decimal

from django.test import override_settings
from rest_framework.test import APIClient

from orders.models import Order
from orders.tests import test_decisions_2026_10_15 as base
from products.models import Product, ProductCategory
from stores.models import StoreCategory
from users.models import User


@override_settings(SINGPAY_ENABLE_TRANSFER=False)
class Securite30Tests(base.DecisionsTests.__mro__[1]):
    setUp = base.DecisionsTests.setUp

    def test_store_cannot_pick_a_cheaper_category_of_another_store_type(self):
        food = StoreCategory.objects.create(name='Alimentation')
        cheap = ProductCategory.objects.create(store_category=food, name='Riz', commission_rate=Decimal('0'))
        from products.serializers import ProductCreateSerializer
        data = {'name': 'Téléphone', 'price': '50000', 'stock': 3, 'weight_kg': '1', 'length_m': '0.2'}
        bad = ProductCreateSerializer(data=dict(data, category=cheap.id), context={'store': self.store})
        self.assertFalse(bad.is_valid())
        self.assertIn('category', bad.errors)
        good = ProductCreateSerializer(data=dict(data, category=self.product_category.id), context={'store': self.store})
        self.assertTrue(good.is_valid(), good.errors)
        self.api.force_authenticate(self.manager)
        response = self.api.patch(f'/api/v1/products/{self.product.id}/update/', {'category': cheap.id}, format='json')
        self.assertEqual(response.status_code, 400, response.content)
        self.product.refresh_from_db()
        self.assertEqual(self.product.category_id, self.product_category.id)

    def test_store_cannot_put_back_a_product_removed_by_admin(self):
        self.api.force_authenticate(self.admin)
        self.assertEqual(self.api.post(f'/api/v1/admin/products/{self.product.id}/deactivate/').status_code, 200)
        self.api.force_authenticate(self.manager)
        response = self.api.patch(f'/api/v1/products/{self.product.id}/update/', {'is_available': True}, format='json')
        self.assertEqual(response.status_code, 400, response.content)
        self.product.refresh_from_db()
        self.assertFalse(self.product.is_available)

    def test_open_orders_are_capped_per_client(self):
        for _ in range(5):
            Order.objects.create(client=self.client_user, store=self.store, delivery_address='Akanda',
                                 delivery_phone='+24107200002', delivery_zone='Centre', delivery_fee=Decimal('2000'))
        Order.objects.filter(client=self.client_user).update(status='confirmed')
        self.api.force_authenticate(self.client_user)
        response = self.api.post('/api/v1/orders/create/', {
            'store': self.store.id, 'city': 'Libreville', 'delivery_address': 'Akanda', 'delivery_phone': '+24107200002',
            'delivery_zone': 'Centre', 'items': [{'product_id': self.product.id, 'quantity': 1}],
            'payment_flow': 'courier_cash', 'payment_method': 'cash',
        }, format='json')
        self.assertEqual(response.status_code, 429, response.content)
        self.assertEqual(response.json()['error']['code'], 'trop_de_commandes_ouvertes')

    def test_cancelled_orders_do_not_use_the_store_monthly_quota(self):
        from unittest import mock
        from payments.subscription_check import SubscriptionChecker
        for _ in range(3):
            Order.objects.create(client=self.client_user, store=self.store, delivery_address='Akanda',
                                 delivery_phone='+24107200002', delivery_zone='Centre', delivery_fee=Decimal('2000'))
        Order.objects.filter(store=self.store).update(status='cancelled')
        plan = mock.MagicMock(name='Free')
        with mock.patch.object(SubscriptionChecker, 'get_current_plan', return_value=plan), \
                mock.patch.object(SubscriptionChecker, '_get_monthly_order_limit', return_value=2):
            SubscriptionChecker.check_can_create_order(self.store)  # ne lève rien

    def test_undelivered_orders_do_not_count_as_commission_debt(self):
        from payments.direct_service import create_arrangement, ensure_credit_limit
        for _ in range(3):
            order = Order.objects.create(client=self.client_user, store=self.store, delivery_address='Akanda',
                                         delivery_phone='+24107200002', delivery_zone='Centre', delivery_fee=Decimal('2000'))
            Order.objects.filter(pk=order.pk).update(commission_amount=Decimal('60000'))
            order.refresh_from_db()
            create_arrangement(order, 'courier_cash', 'cash')
        ensure_credit_limit(self.store, Decimal('800'))  # ne lève rien : aucune commande livrée

    def test_b2b_order_cannot_use_online_payment(self):
        from b2b.api.serializers import B2BOrderCreateSerializer
        serializer = B2BOrderCreateSerializer(data={
            'wholesaler_id': self.store.id, 'items': [{'product_id': self.product.id, 'quantity': 1}],
            'payment_flow': 'platform_online', 'payment_method': 'airtel_money',
            'delivery_address': 'Akanda', 'delivery_phone': '+24107200002', 'delivery_zone': 'Centre',
        })
        self.assertFalse(serializer.is_valid())
        self.assertIn('payment_flow', str(serializer.errors) + str(serializer.errors.get('non_field_errors', '')))

    def test_same_number_cannot_open_two_accounts(self):
        api = APIClient()
        payload = {'phone': '077123456', 'password': 'Mapeto88x', 'password_confirm': 'Mapeto88x',
                   'user_type': 'client'}
        self.assertEqual(api.post('/api/v1/auth/register/', payload, format='json').status_code, 201)
        again = dict(payload, phone='+241077123456')
        self.assertEqual(api.post('/api/v1/auth/register/', again, format='json').status_code, 400)
        bad = dict(payload, phone='+241abc')
        self.assertEqual(api.post('/api/v1/auth/register/', bad, format='json').status_code, 400)

    def test_public_settings_hide_the_assistant_instructions(self):
        data = APIClient().get('/api/v1/settings/').json()['data']
        self.assertNotIn('ai_instructions', data)
        self.api.force_authenticate(self.admin)
        self.assertIn('ai_instructions', self.api.get('/api/v1/settings/').json()['data'])

    def test_public_ai_status_shows_no_technical_details(self):
        data = APIClient().get('/api/v1/ai/assistant/status/?test=1').json()['data']
        self.assertEqual(set(data), {'provider', 'key_present', 'last_ok'})

    def test_assistant_does_not_show_pro_only_products(self):
        from types import SimpleNamespace
        from api.v1.ai.assistant import Ctx, t_get_product
        Product.objects.filter(pk=self.product.pk).update(market_type='b2b')
        ctx = Ctx(SimpleNamespace(user=SimpleNamespace(is_authenticated=False)), 'visitor', [])
        self.assertIn('error', t_get_product(ctx, self.product.id))
