"""Carte de livraison en direct : position GPS du client, position du livreur, qui peut voir quoi."""
from datetime import time
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from api.models import SystemSettings
from delivery.models import City, Delivery, Neighborhood
from orders.models import Order
from payments.configuration import DEFAULT_PAYMENT_POLICY
from products.models import Product, ProductCategory
from stores.models import Store, StoreCategory
from users.models import User


class CarteLivreurTests(TestCase):
    def setUp(self):
        cache.clear()
        self.louis = Neighborhood.objects.get(city=City.objects.get(name='Libreville'), name='Louis')
        manager = User.objects.create_user(phone='+24177600601', password='Mapeto88x', user_type='store_manager')
        self.client_user = User.objects.create_user(phone='+24177600602', password='Mapeto88x', user_type='client')
        self.courier = User.objects.create_user(phone='+24177600604', password='Mapeto88x', user_type='delivery_agent',
                                                first_name='Jean')
        cat = StoreCategory.objects.create(name='Carte test')
        self.store = Store.objects.create(name='Boutique carte', category=cat, manager=manager, phone='+24177600603',
                                          address='Bord de mer', zone='Centre', commission_rate=Decimal('6'),
                                          delivery_fee=Decimal('2000'), is_verified=True,
                                          latitude=Decimal('0.392000'), longitude=Decimal('9.450000'),
                                          opening_time=time(0, 0), closing_time=time(23, 59))
        s = SystemSettings.get_settings()
        s.payment_policy = DEFAULT_PAYMENT_POLICY
        s.save(update_fields=['payment_policy'])
        pcat = ProductCategory.objects.create(store_category=cat, name='Carte cat', commission_rate=Decimal('6'))
        self.product = Product.objects.create(store=self.store, name='Sac', price=5000, stock=10, category=pcat,
                                              weight_kg=1, length_m=Decimal('0.3'))
        self.api = APIClient()
        self.api.force_authenticate(self.client_user)

    def create_order(self, **extra):
        payload = {
            'store': self.store.id, 'city': 'Libreville', 'delivery_address': 'Portail bleu',
            'delivery_phone': '077391199', 'delivery_zone': 'x', 'neighborhood': self.louis.id,
            'delivery_requested': True, 'payment_flow': 'direct_split', 'payment_method': 'cash',
            'items': [{'product_id': self.product.id, 'quantity': 1}], **extra,
        }
        with mock.patch('delivery.tasks.assign_nearest_delivery_agent'):
            res = self.api.post('/api/v1/orders/create/', payload, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        return Order.objects.order_by('-id').first()

    def start_ride(self, order, status='picked_up'):
        delivery = Delivery.objects.get(order=order)
        delivery.delivery_agent = self.courier
        delivery.status = status
        delivery.save()
        return delivery

    def test_client_gps_becomes_delivery_destination(self):
        order = self.create_order(delivery_latitude='0.412345', delivery_longitude='9.467890')
        self.assertEqual(order.delivery_latitude, Decimal('0.412345'))
        delivery = Delivery.objects.get(order=order)
        self.assertEqual((delivery.delivery_lat, delivery.delivery_lng), (Decimal('0.412345'), Decimal('9.467890')))

    def test_gps_outside_gabon_refused(self):
        payload_extra = {'delivery_latitude': '48.85', 'delivery_longitude': '2.35'}
        with mock.patch('delivery.tasks.assign_nearest_delivery_agent'):
            res = self.api.post('/api/v1/orders/create/', {
                'store': self.store.id, 'delivery_address': 'x', 'delivery_phone': '077391199', 'delivery_zone': 'x',
                'neighborhood': self.louis.id, 'delivery_requested': True, 'payment_flow': 'direct_split',
                'payment_method': 'cash', 'items': [{'product_id': self.product.id, 'quantity': 1}], **payload_extra,
            }, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('hors du Gabon', res.content.decode())

    def test_client_follows_courier_during_ride(self):
        order = self.create_order(delivery_latitude='0.412345', delivery_longitude='9.467890')
        delivery = self.start_ride(order)
        courier_api = APIClient()
        courier_api.force_authenticate(self.courier)
        res = courier_api.post(f'/api/v1/dashboard/delivery/{delivery.id}/position/',
                               {'latitude': 0.400000, 'longitude': 9.455000}, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        data = self.api.get(f'/api/v1/orders/{order.id}/tracking/').json()['data']
        self.assertTrue(data['courier']['live'])
        self.assertEqual(data['courier']['name'], 'Jean')
        self.assertAlmostEqual(data['courier']['position']['lat'], 0.4)
        self.assertEqual(data['destination']['source'], 'gps')
        self.assertIsNotNone(data['eta_minutes'])
        self.assertIn('google.com/maps/dir', data['directions']['google'])
        self.assertNotIn('client', data)  # le client ne reçoit pas son propre numéro en double
        # Le livreur voit le numéro du client.
        self.assertEqual(courier_api.get(f'/api/v1/orders/{order.id}/tracking/').json()['data']['client']['phone'],
                         '077391199')

    def test_courier_hidden_after_delivery_and_strangers_refused(self):
        order = self.create_order()
        delivery = self.start_ride(order, status='delivered')
        courier_api = APIClient()
        courier_api.force_authenticate(self.courier)
        res = courier_api.post(f'/api/v1/dashboard/delivery/{delivery.id}/position/',
                               {'latitude': 0.4, 'longitude': 9.45}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIsNone(self.api.get(f'/api/v1/orders/{order.id}/tracking/').json()['data']['courier'])
        stranger = APIClient()
        stranger.force_authenticate(User.objects.create_user(phone='+24177600609', password='Mapeto88x',
                                                             user_type='client'))
        self.assertEqual(stranger.get(f'/api/v1/orders/{order.id}/tracking/').status_code, 404)
        # Un autre livreur ne peut pas envoyer de position pour cette course.
        self.assertEqual(stranger.post(f'/api/v1/dashboard/delivery/{delivery.id}/position/',
                                       {'latitude': 0.4, 'longitude': 9.45}, format='json').status_code, 404)
