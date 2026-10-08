"""Une commande refusée (magasin fermé, montant minimum…) doit donner un message clair, pas une erreur 500."""
from datetime import time
from decimal import Decimal
from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient

from api.models import SystemSettings
from payments.configuration import DEFAULT_PAYMENT_POLICY
from products.models import Product, ProductCategory
from stores.models import Store, StoreCategory
from users.models import User


class OrderCreateErrorTests(TestCase):
    def setUp(self):
        manager = User.objects.create_user(phone='+24107000202', password='x', user_type='store_manager')
        self.client_user = User.objects.create_user(phone='+24107000203', password='x', user_type='client')
        category = StoreCategory.objects.create(name='Test')
        self.store = Store.objects.create(
            name='Commerce', category=category, manager=manager, phone='+24107000210', address='Libreville',
            zone='Centre', commission_rate=Decimal('8'), opening_time=time(0, 0), closing_time=time(23, 59),
        )
        product_category = ProductCategory.objects.create(store_category=category, name='P', commission_rate=Decimal('8'))
        self.product = Product.objects.create(
            store=self.store, category=product_category, name='Article', price=Decimal('50'), stock=20, weight_kg=Decimal('1'),
        )
        settings = SystemSettings.get_settings()
        settings.payment_policy = DEFAULT_PAYMENT_POLICY
        settings.save(update_fields=['payment_policy'])
        self.api = APIClient()
        self.api.force_authenticate(self.client_user)

    def order(self, **changes):
        payload = {
            'store': self.store.id, 'city': 'Libreville', 'delivery_address': 'Akanda', 'delivery_phone': '077391199',
            'delivery_zone': 'Centre', 'delivery_requested': True, 'payment_flow': 'direct_split',
            'payment_method': 'cash', 'items': [{'product_id': self.product.id, 'quantity': 1}], **changes,
        }
        with mock.patch('delivery.tasks.assign_nearest_delivery_agent'):
            return self.api.post('/api/v1/orders/create/', payload, format='json')

    def test_order_is_created(self):
        self.assertEqual(self.order().status_code, 201)

    def test_refusals_are_clear_messages(self):
        response = self.order(payment_flow='platform_online', payment_method='bank_transfer')
        self.assertEqual(response.status_code, 400)
        self.assertIn('payment_method', response.json()['error']['details'])

        Store.objects.filter(pk=self.store.pk).update(min_order_amount=Decimal('1000'))
        response = self.order()
        self.assertEqual(response.status_code, 400)
        self.assertIn('montant minimum', str(response.json()['error']['details']['items']))

        Store.objects.filter(pk=self.store.pk).update(min_order_amount=0, is_active=False)
        response = self.order()
        self.assertEqual(response.status_code, 400)
        self.assertIn('store', response.json()['error']['details'])
