"""Livraison express et suivi en temps réel : deux outils du forfait Pro, appliqués par le serveur (17 oct. 2026)."""
from datetime import time, timedelta
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from api.models import SystemSettings
from delivery.models import City, Delivery, DeliveryZone, Neighborhood, VehicleType, ZoneVehicleRate
from orders.models import Order
from payments.configuration import DEFAULT_PAYMENT_POLICY
from payments.models import StoreSubscription, SubscriptionPlan
from products.models import Product, ProductCategory
from stores.models import Store, StoreCategory
from users.models import User


class Base(TestCase):
    def setUp(self):
        cache.clear()
        self.free = SubscriptionPlan.objects.get(plan_type='free')
        self.pro = SubscriptionPlan.objects.get(plan_type='pro')
        SubscriptionPlan.objects.filter(pk=self.pro.pk).update(
            can_offer_express_delivery=True, has_advanced_delivery_tracking=True, is_active=True, is_available=True)
        SubscriptionPlan.objects.filter(pk=self.free.pk).update(
            can_offer_express_delivery=False, has_advanced_delivery_tracking=False)
        self.pro.refresh_from_db()
        self.free.refresh_from_db()

        libreville = City.objects.get(name='Libreville')
        self.louis = Neighborhood.objects.get(city=libreville, name='Louis')
        zone = DeliveryZone.objects.create(name='Centre express', city='Libreville')
        moto = VehicleType.objects.filter(name='MOTO').first() or VehicleType.objects.create(
            name='MOTO', max_weight_kg=20, max_length_m=1, max_items=10, max_distance_km=30)
        ZoneVehicleRate.objects.create(zone=zone, vehicle=moto, base_price=Decimal('1500'))
        self.louis.zone = zone
        self.louis.save(update_fields=['zone'])

        self.manager = User.objects.create_user(phone='+24177700501', password='Mapeto88x', user_type='store_manager')
        self.client_user = User.objects.create_user(phone='+24177700502', password='Mapeto88x', user_type='client')
        self.courier = User.objects.create_user(phone='+24177700504', password='Mapeto88x', user_type='delivery_agent',
                                                first_name='Jean')
        cat = StoreCategory.objects.create(name='Mode express')
        self.store = Store.objects.create(
            name='Boutique express', category=cat, manager=self.manager, phone='+24177700503', address='Bord de mer',
            city='Libreville', zone='Centre', commission_rate=Decimal('6'), delivery_fee=Decimal('2000'),
            delivery_fee_express=Decimal('3500'), is_verified=True,
            latitude=Decimal('0.392000'), longitude=Decimal('9.450000'),
            opening_time=time(0, 0), closing_time=time(23, 59))
        pcat = ProductCategory.objects.create(store_category=cat, name='Sacs express', commission_rate=Decimal('6'))
        self.product = Product.objects.create(store=self.store, name='Sac', price=5000, stock=100, category=pcat,
                                              weight_kg=1, length_m=Decimal('0.3'))
        s = SystemSettings.get_settings()
        s.payment_policy = DEFAULT_PAYMENT_POLICY
        s.save(update_fields=['payment_policy'])
        self.api = APIClient()
        self.api.force_authenticate(self.client_user)
        self.manager_api = APIClient()
        self.manager_api.force_authenticate(self.manager)

    def subscribe(self, plan):
        return StoreSubscription.objects.create(
            store=self.store, plan=plan, plan_name=plan.name, monthly_fee=plan.price, status='active',
            end_date=timezone.now().date() + timedelta(days=20))

    def body(self, **extra):
        return {
            'store': self.store.id, 'city': 'Libreville', 'delivery_address': 'Portail bleu',
            'delivery_phone': '077391199', 'delivery_zone': 'x', 'neighborhood': self.louis.id,
            'delivery_requested': True, 'payment_flow': 'direct_split', 'payment_method': 'cash',
            'items': [{'product_id': self.product.id, 'quantity': 1}], **extra,
        }

    def create_order(self, expect=201, **extra):
        cache.clear()
        with mock.patch('delivery.tasks.assign_nearest_delivery_agent'):
            res = self.api.post('/api/v1/orders/create/', self.body(**extra), format='json')
        self.assertEqual(res.status_code, expect, res.content)
        return res


class ExpressTests(Base):
    def quote(self, **extra):
        res = self.api.post('/api/v1/orders/delivery-quote/', self.body(**extra), format='json')
        self.assertEqual(res.status_code, 200, res.content)
        return res.json()['data']

    def test_free_store_does_not_offer_express(self):
        data = self.quote()
        self.assertFalse(data['express_available'])
        self.assertEqual(data['delivery_options'], [])
        self.assertEqual(data['delivery']['type'], 'standard')
        self.assertEqual(Decimal(data['delivery_fee']), Decimal('1500'))

    def test_free_store_refuses_express_order_with_plan_message(self):
        res = self.create_order(expect=400, delivery_type='express')
        text = res.content.decode()
        self.assertIn('Livraison express', text)
        self.assertIn('Pro', text)
        self.assertFalse(Order.objects.exists())

    def test_free_store_quote_with_express_is_blocking_and_stays_standard(self):
        data = self.quote(delivery_type='express')
        self.assertEqual(data['delivery_type'], 'standard')
        self.assertTrue(any('express' in reason for reason in data['blocking']))
        self.assertEqual(Decimal(data['delivery_fee']), Decimal('1500'))

    def test_pro_store_quote_lists_both_prices_and_recalculates(self):
        self.subscribe(self.pro)
        standard = self.quote()
        self.assertTrue(standard['express_available'])
        options = {o['type']: o for o in standard['delivery_options']}
        self.assertEqual(Decimal(options['standard']['fee']), Decimal('1500'))
        # Supplément du commerce : 3 500 - 2 000 = 1 500 F, ajouté au tarif de la zone.
        self.assertEqual(Decimal(options['express']['fee']), Decimal('3000'))
        self.assertTrue(options['standard']['selected'])
        express = self.quote(delivery_type='express')
        self.assertEqual(express['delivery_type'], 'express')
        self.assertTrue(express['delivery']['is_express'])
        self.assertEqual(Decimal(express['delivery_fee']), Decimal('3000'))
        self.assertEqual(Decimal(express['total']), Decimal(standard['total']) + Decimal('1500'))
        self.assertEqual(express['blocking'], [])

    def test_express_order_total_equals_quote(self):
        self.subscribe(self.pro)
        quote = self.quote(delivery_type='express')
        order = Order.objects.get(pk=self.create_order(delivery_type='express').json()['data']['id'])
        self.assertEqual(order.delivery_type, 'express')
        self.assertEqual(order.delivery_fee, Decimal('3000'))
        self.assertEqual(Decimal(quote['total']), order.total_amount)

    def test_standard_order_unchanged_for_pro(self):
        self.subscribe(self.pro)
        order = Order.objects.get(pk=self.create_order().json()['data']['id'])
        self.assertEqual((order.delivery_type, order.delivery_fee), ('standard', Decimal('1500')))

    def test_express_needs_delivery(self):
        self.subscribe(self.pro)
        res = self.create_order(expect=400, delivery_type='express', delivery_requested=False)
        self.assertIn('livraison', res.content.decode())
        data = self.quote(delivery_type='express', delivery_requested=False)
        self.assertFalse(data['express_available'])
        self.assertTrue(data['blocking'])

    def test_legacy_express_fee_below_standard_uses_admin_default_gap(self):
        self.subscribe(self.pro)
        Store.objects.filter(pk=self.store.pk).update(delivery_fee=Decimal('4000'), delivery_fee_express=Decimal('3500'))
        settings = SystemSettings.get_settings()
        settings.default_delivery_fee, settings.default_express_delivery_fee = Decimal('2000'), Decimal('3500')
        settings.save()
        data = self.quote(delivery_type='express')
        # Tarif de zone 1 500 + écart par défaut de l'admin (3 500 - 2 000).
        self.assertEqual(Decimal(data['delivery_fee']), Decimal('3000'))

    def test_public_store_detail_tells_if_express_is_available(self):
        url = f'/api/v1/stores/{self.store.id}/'
        self.assertFalse(self.api.get(url).json()['data']['express_available'])
        self.subscribe(self.pro)
        data = self.api.get(url).json()['data']
        self.assertTrue(data['express_available'])
        self.assertNotIn('express', data)  # frais et réglage réservés au commerçant

    def test_manager_sees_express_setting_and_hint(self):
        url = f'/api/v1/stores/{self.store.id}/'
        info = self.manager_api.get(url).json()['data']['express']
        self.assertFalse(info['enabled'])
        self.assertEqual(info['plan_name'], self.pro.name)
        self.assertIn('Livraison express', info['upgrade_hint'])
        self.subscribe(self.pro)
        info = self.manager_api.get(url).json()['data']['express']
        self.assertTrue(info['enabled'])
        self.assertEqual(Decimal(info['fee']), Decimal('3500'))
        self.assertEqual(Decimal(info['supplement']), Decimal('1500'))

    def test_hint_without_plan_for_sale_is_honest(self):
        SubscriptionPlan.objects.filter(plan_type__in=('pro', 'business')).update(is_available=False)
        info = self.manager_api.get(f'/api/v1/stores/{self.store.id}/').json()['data']['express']
        self.assertEqual(info['plan_name'], '')
        self.assertIn('aucun forfait en vente', info['upgrade_hint'])

    def test_manager_sets_express_fee_only_with_the_tool(self):
        url = f'/api/v1/stores/{self.store.id}/update/'
        res = self.manager_api.patch(url, {'delivery_fee_express': '5000'}, format='json')
        self.assertEqual(res.status_code, 400, res.content)
        self.assertIn('Livraison express', res.content.decode())
        # Renvoyer la valeur inchangée reste permis.
        res = self.manager_api.patch(url, {'delivery_fee_express': '3500'}, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        self.subscribe(self.pro)
        res = self.manager_api.patch(url, {'delivery_fee_express': '5000'}, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        self.store.refresh_from_db()
        self.assertEqual(self.store.delivery_fee_express, Decimal('5000'))
        low = self.manager_api.patch(url, {'delivery_fee_express': '1000'}, format='json')
        self.assertEqual(low.status_code, 400)
        self.assertIn('inférieurs', low.content.decode())

    def test_order_lists_flag_express_for_store_and_courier(self):
        self.subscribe(self.pro)
        order = Order.objects.get(pk=self.create_order(delivery_type='express').json()['data']['id'])
        listed = self.manager_api.get(f'/api/v1/orders/{order.id}/').json()
        data = listed.get('data', listed)
        self.assertTrue(data['is_express'])
        self.assertEqual(data['delivery_type'], 'express')
        delivery = Delivery.objects.get(order=order)
        courier_api = APIClient()
        courier_api.force_authenticate(self.courier)
        delivery.delivery_agent, delivery.status = self.courier, 'assigned'
        delivery.save()
        dash = courier_api.get('/api/v1/dashboard/delivery/').json()
        text = str(dash)
        self.assertIn("'is_express': True", text)


class SuiviTests(Base):
    def ride(self, order, status='picked_up'):
        delivery = Delivery.objects.get(order=order)
        delivery.delivery_agent, delivery.status = self.courier, status
        delivery.courier_lat, delivery.courier_lng = Decimal('0.400000'), Decimal('9.455000')
        delivery.courier_location_at = timezone.now()
        delivery.save()
        return delivery

    def tracking(self, api, order):
        return api.get(f'/api/v1/orders/{order.id}/tracking/').json()['data']

    def test_free_store_gets_status_steps_only(self):
        order = Order.objects.get(pk=self.create_order().json()['data']['id'])
        self.ride(order)
        data = self.tracking(self.api, order)
        self.assertFalse(data['live_tracking'])
        self.assertNotIn('courier', data)
        self.assertNotIn('store', data)
        self.assertNotIn('destination', data)
        self.assertFalse(data['active'])
        self.assertEqual([s['key'] for s in data['steps']][-1], 'delivered')
        current = [s['key'] for s in data['steps'] if s['current']]
        self.assertEqual(current, ['on_the_way'])
        self.assertIn('pas disponible', data['message'])
        # Forfait Pro en vente : la mention commerciale est permise.
        self.assertIn(self.pro.name, data['upgrade_note'])

    def test_manager_of_free_store_gets_steps_too(self):
        order = Order.objects.get(pk=self.create_order().json()['data']['id'])
        data = self.tracking(self.manager_api, order)
        self.assertFalse(data['live_tracking'])
        self.assertNotIn('courier', data)
        self.assertNotIn('client', data)

    def test_no_upgrade_note_when_no_plan_for_sale(self):
        order = Order.objects.get(pk=self.create_order().json()['data']['id'])
        SubscriptionPlan.objects.filter(plan_type__in=('pro', 'business')).update(is_available=False)
        data = self.tracking(self.api, order)
        self.assertEqual(data['upgrade_note'], '')
        self.assertFalse(data['live_tracking'])

    def test_pro_store_keeps_the_live_map(self):
        self.subscribe(self.pro)
        order = Order.objects.get(pk=self.create_order(delivery_latitude='0.412345', delivery_longitude='9.467890').json()['data']['id'])
        self.ride(order)
        data = self.tracking(self.api, order)
        self.assertTrue(data['live_tracking'])
        self.assertTrue(data['courier']['live'])
        self.assertEqual(data['destination']['source'], 'gps')
        self.assertIn('steps', data)
        self.assertEqual(self.tracking(self.manager_api, order)['courier']['name'], 'Jean')

    def test_courier_and_admin_keep_the_map_on_a_free_store(self):
        order = Order.objects.get(pk=self.create_order(delivery_latitude='0.412345', delivery_longitude='9.467890').json()['data']['id'])
        self.ride(order)
        courier_api = APIClient()
        courier_api.force_authenticate(self.courier)
        data = self.tracking(courier_api, order)
        self.assertTrue(data['live_tracking'])
        self.assertIn('directions', data)
        self.assertEqual(data['client']['phone'], '077391199')
        admin = User.objects.create_user(phone='+24177700599', password='Mapeto88x', user_type='admin')
        admin_api = APIClient()
        admin_api.force_authenticate(admin)
        self.assertTrue(self.tracking(admin_api, order)['live_tracking'])

    def test_courier_can_still_send_position_on_a_free_store(self):
        order = Order.objects.get(pk=self.create_order().json()['data']['id'])
        delivery = self.ride(order)
        courier_api = APIClient()
        courier_api.force_authenticate(self.courier)
        res = courier_api.post(f'/api/v1/dashboard/delivery/{delivery.id}/position/',
                               {'latitude': 0.401, 'longitude': 9.456}, format='json')
        self.assertEqual(res.status_code, 200, res.content)

    def test_delivery_history_hidden_without_the_tool_for_client_and_store(self):
        order = Order.objects.get(pk=self.create_order().json()['data']['id'])
        delivery = self.ride(order)
        from delivery.models import DeliveryTracking
        DeliveryTracking.objects.create(delivery=delivery, status='picked_up', latitude=Decimal('0.4'),
                                        longitude=Decimal('9.45'))
        from delivery.serializers import DeliverySerializer
        from rest_framework.test import APIRequestFactory
        for user in (self.client_user, self.manager):
            request = APIRequestFactory().get('/')
            request.user = user
            self.assertEqual(DeliverySerializer(delivery, context={'request': request}).data['tracking_history'], [])
        request = APIRequestFactory().get('/')
        request.user = self.courier
        self.assertEqual(len(DeliverySerializer(delivery, context={'request': request}).data['tracking_history']), 1)
        self.subscribe(self.pro)
        request.user = self.client_user
        self.assertEqual(len(DeliverySerializer(delivery, context={'request': request}).data['tracking_history']), 1)

    def test_pin_proof_unchanged(self):
        order = Order.objects.get(pk=self.create_order().json()['data']['id'])
        delivery = self.ride(order)
        data = self.tracking(self.api, order)
        self.assertNotIn(delivery.delivery_code, str(data))
