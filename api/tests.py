from datetime import time, timedelta
from unittest import mock

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from api.models import SystemSettings
from delivery.assignment_flow import _rank_candidates
from delivery.models import Delivery
from notifications.service import NotificationService
from orders.models import Order
from stores.models import Store, StoreCategory
from users.models import LivreurProfile, User


class SettingsApiTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(phone='+24107200001', password='x', user_type='admin')
        self.api = APIClient()

    def test_defaults_are_for_gabon(self):
        data = self.api.get('/api/v1/settings/').json()['data']
        self.assertEqual(data['default_city'], 'Libreville')
        self.assertIn('Port-Gentil', data['enabled_cities'])
        self.assertNotIn('Abidjan', data['enabled_cities'])
        # L'état technique n'est montré qu'aux admins.
        self.assertNotIn('technical_status', data)

    def test_admin_sees_technical_status_and_saves_valid_values(self):
        self.api.force_authenticate(self.admin)
        response = self.api.patch('/api/v1/settings/', {
            'enabled_cities': ['Libreville', 'Oyem'], 'default_city': 'Oyem',
            'max_orders_per_delivery': 2, 'order_hours_enabled': True, 'order_opening_time': '07:30',
        }, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        data = response.json()['data']
        self.assertIn('technical_status', data)
        self.assertEqual(data['enabled_cities'], ['Libreville', 'Oyem'])
        self.assertEqual(data['order_opening_time'], '07:30')
        self.assertEqual(SystemSettings.get_settings().max_orders_per_delivery, 2)

    def test_invalid_values_are_refused_with_explanation(self):
        self.api.force_authenticate(self.admin)
        response = self.api.patch('/api/v1/settings/', {'max_orders_per_delivery': 0, 'default_city': 'Abidjan'}, format='json')
        self.assertEqual(response.status_code, 400)
        details = response.json()['error']['details']
        self.assertIn('max_orders_per_delivery', details)
        self.assertEqual(SystemSettings.get_settings().max_orders_per_delivery, 3)

    def test_non_admin_cannot_change_settings(self):
        client = User.objects.create_user(phone='+24107200002', password='x', user_type='client')
        self.api.force_authenticate(client)
        self.assertEqual(self.api.patch('/api/v1/settings/', {'enable_sms': False}, format='json').status_code, 403)


class SettingsAreAppliedTests(TestCase):
    def setUp(self):
        self.settings = SystemSettings.get_settings()
        self.manager = User.objects.create_user(phone='+24107200010', password='x', user_type='store_manager')
        self.category = StoreCategory.objects.create(name='Cat')

    def make_store(self, **extra):
        return Store.objects.create(name='C', category=self.category, manager=self.manager, phone='+24107200100',
                                    address='Libreville', zone='Centre', **extra)

    def test_new_store_gets_default_hours_from_admin(self):
        self.settings.default_store_opening = time(7, 0)
        self.settings.default_store_closing = time(21, 30)
        self.settings.save()
        store = self.make_store()
        store.refresh_from_db()
        self.assertEqual((store.opening_time, store.closing_time), (time(7, 0), time(21, 30)))

    def test_disabled_channel_is_skipped(self):
        self.settings.enable_whatsapp = False
        self.settings.save()
        self.assertEqual(NotificationService._enabled_channels(['whatsapp', 'sms']), ['sms'])

    def test_busy_courier_is_not_offered_another_delivery(self):
        self.settings.max_orders_per_delivery = 1
        self.settings.save()
        store = self.make_store()
        client = User.objects.create_user(phone='+24107200011', password='x', user_type='client')
        courier = User.objects.create_user(phone='+24107200012', password='x', user_type='delivery_agent', is_available=True)
        LivreurProfile.objects.filter(user=courier).update(disponible=True)
        order = Order.objects.create(client=client, store=store, delivery_address='A', delivery_phone='+24107200011', delivery_zone='Centre')
        self.assertEqual(len(_rank_candidates(order, [], same_city_only=False)), 1)
        busy_order = Order.objects.create(client=client, store=store, delivery_address='B', delivery_phone='+24107200011', delivery_zone='Centre')
        Delivery.objects.filter(order=busy_order).delete()
        Delivery.objects.create(order=busy_order, delivery_agent=courier, status='picked_up')
        self.assertEqual(_rank_candidates(order, [], same_city_only=False), [])

    def test_old_pending_orders_are_cancelled_after_admin_delay(self):
        from orders.tasks import nettoyer_paniers_abandonnes
        self.settings.cart_validity_hours = 2
        self.settings.save()
        client = User.objects.create_user(phone='+24107200013', password='x', user_type='client')
        store = self.make_store()
        old = Order.objects.create(client=client, store=store, delivery_address='A', delivery_phone='+24107200013', delivery_zone='Centre')
        recent = Order.objects.create(client=client, store=store, delivery_address='A', delivery_phone='+24107200013', delivery_zone='Centre')
        Order.objects.filter(pk=old.pk).update(status='pending', created_at=timezone.now() - timedelta(hours=3))
        Order.objects.filter(pk=recent.pk).update(status='pending', created_at=timezone.now() - timedelta(hours=1))
        nettoyer_paniers_abandonnes()
        self.assertEqual(Order.objects.get(pk=old.pk).status, 'cancelled')
        self.assertEqual(Order.objects.get(pk=recent.pk).status, 'pending')

    def test_order_hours_block_orders_outside_the_window(self):
        from orders.serializers import OrderCreateSerializer
        self.settings.order_hours_enabled = True
        self.settings.save()
        from rest_framework.exceptions import ValidationError
        with mock.patch('orders.serializers.within_hours', return_value=False):
            with self.assertRaisesMessage(ValidationError, 'Les commandes sont ouvertes'):
                OrderCreateSerializer().validate({'store': self.make_store(), 'items': []})
