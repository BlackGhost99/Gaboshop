"""Adresse par liste (Province › Ville › Arrondissement › Quartier) : le prix vient de la zone du quartier."""
from datetime import time
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from api.models import SystemSettings
from delivery.models import City, DeliveryZone, Landmark, Neighborhood, Province, VehicleType, ZoneVehicleRate
from delivery.zones import resolve_zone
from orders.models import Order
from payments.configuration import DEFAULT_PAYMENT_POLICY
from products.models import Product, ProductCategory
from stores.models import Store, StoreCategory
from users.models import User


class AdressesQuartiersTests(TestCase):
    def setUp(self):
        cache.clear()
        self.libreville = City.objects.get(name='Libreville')
        self.louis = Neighborhood.objects.get(city=self.libreville, name='Louis')
        self.glass = Neighborhood.objects.get(city=self.libreville, name='Quartier Glass')
        self.centre = DeliveryZone.objects.create(name='Centre', city='Libreville')
        moto = VehicleType.objects.filter(name='MOTO').first() or VehicleType.objects.create(
            name='MOTO', max_weight_kg=20, max_length_m=1, max_items=10, max_distance_km=30)
        ZoneVehicleRate.objects.create(zone=self.centre, vehicle=moto, base_price=Decimal('1500'))
        Neighborhood.objects.filter(pk__in=[self.louis.pk, self.glass.pk]).update(zone=self.centre)

        manager = User.objects.create_user(phone='+24177600401', password='Mapeto88x', user_type='store_manager')
        self.client_user = User.objects.create_user(phone='+24177600402', password='Mapeto88x', user_type='client')
        cat = StoreCategory.objects.create(name='Mode test geo')
        self.store = Store.objects.create(name='Boutique geo', category=cat, manager=manager, phone='+24177600403',
                                          address='Libreville', zone='Centre', commission_rate=Decimal('6'),
                                          delivery_fee=Decimal('3000'), is_verified=True,
                                          opening_time=time(0, 0), closing_time=time(23, 59))
        settings = SystemSettings.get_settings()
        settings.payment_policy = DEFAULT_PAYMENT_POLICY
        settings.save(update_fields=['payment_policy'])
        pcat = ProductCategory.objects.create(store_category=cat, name='Bottes geo', commission_rate=Decimal('6'))
        self.product = Product.objects.create(store=self.store, name='Timberland', price=20000, stock=5, category=pcat,
                                              weight_kg=1, length_m=Decimal('0.3'))
        self.api = APIClient()
        self.api.force_authenticate(self.client_user)

    def test_seeded_reference(self):
        self.assertEqual(Province.objects.count(), 9)
        self.assertTrue(self.libreville.is_open)
        self.assertFalse(City.objects.get(name='Akanda').is_open)
        self.assertEqual(self.libreville.arrondissements.count(), 6)
        self.assertEqual(City.objects.get(name='Ntoum').arrondissements.count(), 3)

    def test_public_tree(self):
        res = APIClient().get('/api/v1/geo/')
        self.assertEqual(res.status_code, 200)
        data = res.json()['data']
        self.assertEqual(len(data['provinces']), 9)
        louis = next(n for n in data['neighborhoods'] if n['id'] == self.louis.id)
        self.assertEqual(louis['zone'], 'Centre')
        self.assertIn('Libreville', data['message'])

    def test_quote_uses_neighborhood_zone(self):
        res = self.api.post('/api/v1/orders/delivery-quote/', {
            'store': self.store.id, 'neighborhood': self.glass.id,
            'items': [{'product_id': self.product.id, 'quantity': 1}],
        }, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(Decimal(res.json()['data']['delivery_fee']), Decimal('1500'))
        self.assertEqual(res.json()['data']['zone'], 'Centre')

    def test_closed_city_refused(self):
        okala = Neighborhood.objects.get(city__name='Akanda', name='Okala')
        res = self.api.post('/api/v1/orders/delivery-quote/', {
            'store': self.store.id, 'neighborhood': okala.id,
            'items': [{'product_id': self.product.id, 'quantity': 1}],
        }, format='json')
        self.assertIsNone(res.json()['data']['delivery_fee'])
        self.assertIn('ne livre pas encore à Akanda', res.json()['data']['message'])

    def test_legacy_typed_neighborhood_maps_to_zone(self):
        self.assertEqual(resolve_zone('Libreville', 'louis'), 'Centre')
        with self.assertRaises(ValueError):
            resolve_zone('Libreville', 'Lewis')

    def test_order_with_neighborhood(self):
        payload = {
            'store': self.store.id, 'city': 'Owendo', 'delivery_address': 'Portail bleu', 'delivery_phone': '077391199',
            'delivery_zone': 'texte ignoré', 'neighborhood': self.louis.id, 'delivery_requested': True,
            'landmark': Landmark.objects.get(neighborhood=self.louis, name='Carrefour Louis').id,
            'payment_flow': 'direct_split', 'payment_method': 'cash',
            'items': [{'product_id': self.product.id, 'quantity': 1}],
        }
        with mock.patch('delivery.tasks.assign_nearest_delivery_agent'):
            res = self.api.post('/api/v1/orders/create/', payload, format='json')
        self.assertIn(res.status_code, (200, 201), res.content)
        order = Order.objects.get(client=self.client_user)
        self.assertEqual(order.neighborhood_id, self.louis.id)
        self.assertEqual(order.city, 'Libreville')
        self.assertEqual(order.delivery_zone, 'Centre')
        self.assertEqual(order.delivery_fee, Decimal('1500'))
        self.assertEqual(order.landmark.name, 'Carrefour Louis')
        self.assertEqual(order.delivery_address, 'Louis, 1er arrondissement, Libreville — près de Carrefour Louis — Portail bleu')

    def test_every_seeded_quarter_has_its_arrondissement(self):
        self.assertFalse(Neighborhood.objects.filter(city__name__in=['Libreville', 'Akanda', 'Owendo'],
                                                     arrondissement__isnull=True).exists())
        self.assertEqual(Neighborhood.objects.get(city=self.libreville, name='Nzeng-Ayong').arrondissement.number, 5)
        tree = APIClient().get('/api/v1/geo/').json()['data']
        self.assertTrue(any(l['name'] == 'Marché de Mont-Bouët' for l in tree['landmarks']))

    def test_landmark_from_another_quarter_refused(self):
        rio = Landmark.objects.get(name='Carrefour Rio')
        payload = {
            'store': self.store.id, 'delivery_address': 'Portail', 'delivery_phone': '077391199', 'delivery_zone': 'x',
            'neighborhood': self.louis.id, 'landmark': rio.id, 'delivery_requested': True,
            'payment_flow': 'direct_split', 'payment_method': 'cash',
            'items': [{'product_id': self.product.id, 'quantity': 1}],
        }
        res = self.api.post('/api/v1/orders/create/', payload, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('zone phare', res.content.decode())

    def test_admin_quarter_needs_arrondissement(self):
        admin = User.objects.create_user(phone='+24177600409', password='Mapeto88x', user_type='admin',
                                         is_staff=True, is_superuser=True)
        api = APIClient()
        api.force_authenticate(admin)
        res = api.post('/api/v1/admin/geo/neighborhoods/', {'city_id': self.libreville.id, 'name': 'Bikélé'}, format='json')
        self.assertEqual(res.status_code, 400)
        arr = self.libreville.arrondissements.get(number=6)
        res = api.post('/api/v1/admin/geo/neighborhoods/', {'city_id': self.libreville.id, 'name': 'Bikélé',
                                                            'arrondissement_id': arr.id}, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        res = api.post('/api/v1/admin/geo/landmarks/', {'neighborhood_id': res.json()['data']['id'],
                                                        'name': 'Carrefour Bikélé'}, format='json')
        self.assertEqual(res.status_code, 200, res.content)
