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


class BusinessRulesTests(TestCase):
    def setUp(self):
        self.settings = SystemSettings.get_settings()

    def test_courier_share_follows_admin_percent(self):
        from decimal import Decimal
        self.assertEqual(SystemSettings.courier_share(Decimal('2000')), Decimal('1600.00'))
        self.settings.courier_share_percent = Decimal('70')
        self.settings.save()
        self.assertEqual(SystemSettings.courier_share(Decimal('2000')), Decimal('1400.00'))

    def test_new_store_gets_default_commission_from_admin(self):
        from decimal import Decimal
        self.settings.commission_global = Decimal('6.5')
        self.settings.save()
        manager = User.objects.create_user(phone='+24107200020', password='x', user_type='store_manager')
        store = Store.objects.create(name='C', category=StoreCategory.objects.create(name='K'), manager=manager,
                                     phone='+24107200120', address='Libreville', zone='Centre')
        store.refresh_from_db()
        self.assertEqual(store.commission_rate, Decimal('6.50'))

    def test_pin_lock_follows_admin_values(self):
        from delivery import pin_guard
        self.settings.pin_max_attempts = 2
        self.settings.pin_lock_minutes = 15
        self.settings.save()
        delivery = mock.Mock(pk=987654)
        pin_guard.reset(delivery)
        pin_guard.record_failure(delivery)
        self.assertFalse(pin_guard.is_locked(delivery))
        pin_guard.record_failure(delivery)
        self.assertTrue(pin_guard.is_locked(delivery))
        self.assertIn('15 minutes', pin_guard.locked_message())
        pin_guard.reset(delivery)

    def test_assignment_timeout_follows_admin_value(self):
        from delivery.assignment_flow import assignment_timeout_minutes
        self.settings.assignment_timeout_minutes = 7
        self.settings.save()
        self.assertEqual(assignment_timeout_minutes(), 7)


class DeliveryAdminTests(TestCase):
    def setUp(self):
        from decimal import Decimal
        from delivery.models import VehicleType
        self.admin = User.objects.create_user(phone='+24107200030', password='x', user_type='admin')
        self.api = APIClient()
        self.api.force_authenticate(self.admin)
        self.moto = VehicleType.objects.create(name='MOTO', max_weight_kg=Decimal('20'), max_items=10, max_distance_km=Decimal('30'))
        self.car = VehicleType.objects.create(name='CAR', max_weight_kg=Decimal('200'), max_items=0, max_distance_km=Decimal('300'))

    def test_zone_with_prices_and_simulated_price(self):
        response = self.api.post('/api/v1/admin/delivery/zones/', {
            'name': 'Akanda', 'city': 'Akanda', 'inter_city_surcharge': 1500,
            'rates': [{'vehicle_id': self.moto.id, 'price': 2500}, {'vehicle_id': self.car.id, 'price': ''}],
        }, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        zone = response.json()['data']
        prices = {r['vehicle_id']: r['price'] for r in zone['rates']}
        self.assertEqual(prices, {self.moto.id: 2500.0, self.car.id: None})

        simulated = self.api.post('/api/v1/admin/delivery/simulate/', {
            'zone_id': zone['id'], 'vehicle_id': self.moto.id, 'store_city': 'Libreville',
        }, format='json').json()['data']
        self.assertEqual(simulated['price'], 4000.0)  # 2500 + 1500 autre ville
        self.assertEqual(simulated['courier_share'], 3200.0)  # 80 %

        # Même nom dans la même ville : refusé avec une explication.
        duplicate = self.api.post('/api/v1/admin/delivery/zones/', {'name': 'Akanda', 'city': 'Akanda'}, format='json')
        self.assertEqual(duplicate.status_code, 409)

    def test_defaults_can_be_applied_to_every_store(self):
        manager = User.objects.create_user(phone='+24107200031', password='x', user_type='store_manager')
        store = Store.objects.create(name='C', category=StoreCategory.objects.create(name='K'), manager=manager,
                                     phone='+24107200131', address='Libreville', zone='Centre')
        response = self.api.patch('/api/v1/admin/delivery/defaults/', {
            'default_delivery_fee': 1500, 'default_express_delivery_fee': 3000, 'apply_to_all_stores': True,
        }, format='json')
        self.assertEqual(response.json()['data']['stores_updated'], 1)
        store.refresh_from_db()
        self.assertEqual((int(store.delivery_fee), int(store.delivery_fee_express)), (1500, 3000))

    def test_monitoring_screens_load(self):
        for url in ('tariffs', 'operations', 'stats', 'incidents'):
            response = self.api.get(f'/api/v1/admin/delivery/{url}/')
            self.assertEqual(response.status_code, 200, (url, response.content))

    def test_only_admins_can_change_tariffs(self):
        client = User.objects.create_user(phone='+24107200032', password='x', user_type='client')
        self.api.force_authenticate(client)
        self.assertEqual(self.api.post('/api/v1/admin/delivery/zones/', {'name': 'X', 'city': 'Y'}, format='json').status_code, 403)


class CompanyAndAiSettingsTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(phone='+24107200040', password='x', user_type='admin')
        self.api = APIClient()
        self.api.force_authenticate(self.admin)

    def test_company_info_is_public_and_validated(self):
        ok = self.api.patch('/api/v1/settings/', {'company_name': 'Gaboshop SARL', 'support_phone': '+241 77 12 34 56'}, format='json')
        self.assertEqual(ok.status_code, 200, ok.content)
        public = APIClient().get('/api/v1/settings/').json()['data']
        self.assertEqual(public['company_name'], 'Gaboshop SARL')
        bad = self.api.patch('/api/v1/settings/', {'support_email': 'pas-un-email', 'support_phone': 'abc'}, format='json')
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(set(bad.json()['error']['details']), {'support_email', 'support_phone'})

    def test_legal_form_comes_from_the_list(self):
        from api.models import SystemSettings
        refused = self.api.patch('/api/v1/settings/', {'company_legal_form': 'Gaboshop SARL bidon'}, format='json')
        self.assertEqual(refused.status_code, 400)
        self.assertIn('company_legal_form', refused.json()['error']['details'])
        ok = self.api.patch('/api/v1/settings/', {'company_trade_name': 'Gaboshop', 'company_legal_form': 'Entreprise individuelle (EI)'}, format='json')
        self.assertEqual(ok.status_code, 200, ok.content)
        self.assertIn('Entreprise individuelle (EI)', ok.json()['data']['legal_forms'])
        # Une ancienne valeur libre ne bloque pas l'enregistrement des autres réglages.
        SystemSettings.objects.update(company_legal_form='Ancienne forme')
        again = self.api.patch('/api/v1/settings/', {'company_legal_form': 'Ancienne forme', 'support_whatsapp': '+241 77 00 00 00'}, format='json')
        self.assertEqual(again.status_code, 200, again.content)
        self.assertNotIn('legal_forms', APIClient().get('/api/v1/settings/').json()['data'])

    def test_ai_provider_must_have_a_key(self):
        with mock.patch('api.v1.ai.providers.AIProvider.configured_providers', return_value=['groq']):
            refused = self.api.patch('/api/v1/settings/', {'ai_provider': 'openai'}, format='json')
            accepted = self.api.patch('/api/v1/settings/', {'ai_provider': 'groq', 'ai_model': 'llama-3.3-70b-versatile'}, format='json')
        self.assertEqual(refused.status_code, 400)
        self.assertEqual(accepted.status_code, 200, accepted.content)

    def test_disabled_ai_uses_builtin_engine_and_instructions_reach_prompt(self):
        from api.v1.ai.assistant import admin_instructions
        from api.v1.ai.providers import AIProvider
        settings = SystemSettings.get_settings()
        settings.ai_enabled = False
        settings.ai_instructions = 'Livraison offerte ce week-end.'
        settings.save()
        self.assertEqual(AIProvider.get_provider_config()['name'], 'local')
        self.assertIn('Livraison offerte ce week-end.', admin_instructions())
