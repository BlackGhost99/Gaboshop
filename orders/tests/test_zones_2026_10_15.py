"""Zones de livraison (15 oct. 2026) : le client choisit sa zone dans une liste, le prix affiché est celui payé."""
from datetime import time
from decimal import Decimal
from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient

from api.models import SystemSettings
from delivery.models import DeliveryZone, VehicleType, ZoneVehicleRate
from delivery.zones import resolve_zone
from orders.models import Order
from payments.configuration import DEFAULT_PAYMENT_POLICY
from products.models import Product, ProductCategory
from stores.models import Store, StoreCategory
from users.models import User


class ZoneTests(TestCase):
    def setUp(self):
        manager = User.objects.create_user(phone='+24107300202', password='x', user_type='store_manager')
        self.client_user = User.objects.create_user(phone='+24107300203', password='x', user_type='client')
        category = StoreCategory.objects.create(name='Test')
        self.store = Store.objects.create(
            is_verified=True, name='Commerce', category=category, manager=manager, phone='+24107300210', address='Libreville',
            zone='Centre', commission_rate=Decimal('8'), opening_time=time(0, 0), closing_time=time(23, 59),
            delivery_fee=Decimal('2000'),
        )
        pcat = ProductCategory.objects.create(store_category=category, name='P', commission_rate=Decimal('8'))
        self.product = Product.objects.create(store=self.store, category=pcat, name='Article', price=Decimal('5000'), stock=20, weight_kg=Decimal('1'))
        settings = SystemSettings.get_settings()
        settings.payment_policy = DEFAULT_PAYMENT_POLICY
        settings.save(update_fields=['payment_policy'])
        self.api = APIClient()
        self.api.force_authenticate(self.client_user)

    def make_zone(self):
        moto = VehicleType.objects.create(name='MOTO', max_weight_kg=Decimal('30'), max_length_m=Decimal('1'), max_items=0, max_distance_km=Decimal('50'))
        zone = DeliveryZone.objects.create(name='Louis', city='Libreville')
        ZoneVehicleRate.objects.create(zone=zone, vehicle=moto, base_price=Decimal('1500'))
        return zone

    def quote(self, zone, city='Libreville'):
        return self.api.post('/api/v1/orders/delivery-quote/', {
            'store': self.store.id, 'city': city, 'delivery_zone': zone,
            'items': [{'product_id': self.product.id, 'quantity': 2}],
        }, format='json')

    def order(self, zone):
        payload = {
            'store': self.store.id, 'city': 'Libreville', 'delivery_address': 'Rue 1', 'delivery_phone': '077391199',
            'delivery_zone': zone, 'delivery_requested': True, 'payment_flow': 'direct_split',
            'payment_method': 'cash', 'items': [{'product_id': self.product.id, 'quantity': 2}],
        }
        with mock.patch('delivery.tasks.assign_nearest_delivery_agent'):
            return self.api.post('/api/v1/orders/create/', payload, format='json')

    def test_free_text_when_city_has_no_zone(self):
        self.assertEqual(resolve_zone('Libreville', ' Akanda '), 'Akanda')
        res = self.quote('Akanda')
        self.assertEqual(res.json()['data']['delivery_fee'], '2000')  # prix du commerce
        self.assertEqual(self.order('Akanda').status_code, 201)

    def test_zone_must_be_chosen_from_list(self):
        self.make_zone()
        self.assertEqual(resolve_zone('libreville', 'louis'), 'Louis')
        with self.assertRaises(ValueError):
            resolve_zone('Libreville', 'Lewis')
        res = self.order('Lewis')
        self.assertEqual(res.status_code, 400)
        self.assertIn('delivery_zone', res.json()['error']['details'])
        self.assertIsNone(self.quote('Lewis').json()['data']['delivery_fee'])

    def test_quoted_price_is_the_price_paid(self):
        self.make_zone()
        quoted = self.quote('louis').json()['data']
        self.assertEqual((quoted['delivery_fee'], quoted['zone'], quoted['zones']), ('1500', 'Louis', ['Louis']))
        res = self.order('louis')
        self.assertEqual(res.status_code, 201, res.content)
        order = Order.objects.latest('id')
        self.assertEqual(order.delivery_zone, 'Louis')
        self.assertEqual(order.delivery_fee, Decimal('1500'))

    def test_quote_requires_login_and_ignores_other_store_products(self):
        self.assertIn(APIClient().post('/api/v1/orders/delivery-quote/', {}, format='json').status_code, (401, 403))
        res = self.api.post('/api/v1/orders/delivery-quote/', {'store': self.store.id, 'items': [{'product_id': 999999}]}, format='json')
        self.assertEqual(res.status_code, 400)
