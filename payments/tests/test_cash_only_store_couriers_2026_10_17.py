"""Pilote B2C : espèces à la livraison uniquement si la boutique a sa propre livraison."""
from datetime import time
from decimal import Decimal

from django.test import TestCase, override_settings

from api.models import SystemSettings
from orders.models import Order
from orders.serializers import OrderSerializer
from payments.configuration import DEFAULT_PAYMENT_POLICY, available_payment_options, matching_option
from payments.direct_service import create_arrangement
from stores.models import Store, StoreCategory
from users.models import User


@override_settings(B2C_STORE_COURIER_CASH_ONLY=True)
class CashWithStoreCouriersTests(TestCase):
    def setUp(self):
        self.client = User.objects.create_user(
            phone='+241077987601', user_type='client', password='test-pass')
        self.manager = User.objects.create_user(
            phone='+241077987602', user_type='store_manager', password='test-pass')
        self.store = Store.objects.create(
            name='Boutique test livreurs internes',
            manager=self.manager,
            category=StoreCategory.objects.create(name='Commerces test paiement boutique'),
            address='Libreville', phone='+241077987602',
            opening_time=time(0, 0), closing_time=time(23, 59),
            offers_delivery=False,
        )
        obj = SystemSettings.get_settings()
        obj.payment_policy = DEFAULT_PAYMENT_POLICY
        obj.save(update_fields=['payment_policy'])

    def make_order(self, delivery_requested=True):
        return Order.objects.create(
            client=self.client, store=self.store, delivery_requested=delivery_requested,
            items_total=Decimal('10000'), delivery_fee=Decimal('2000'),
            total_amount=Decimal('12000'), commission_amount=Decimal('800'),
            delivery_address='Libreville', delivery_phone='+241077987601',
            delivery_zone='Centre',
        )

    def test_gaboshop_courier_cannot_collect_cash_at_delivery(self):
        _, options = available_payment_options(self.store)
        self.assertFalse(any(o['method'] == 'cash' for o in options))
        self.assertFalse(any(o['flow'] == 'courier_cash' for o in options))
        order = self.make_order()
        from rest_framework.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            create_arrangement(order, 'courier_cash', 'cash', user=self.client)
        with self.assertRaises(ValidationError):
            create_arrangement(order, 'direct_split', 'cash', user=self.client)

    def test_cash_delivery_is_collected_by_store_own_courier(self):
        self.store.offers_delivery = True
        self.store.save(update_fields=['offers_delivery'])
        _, options = available_payment_options(self.store)
        cash_options = [o for o in options if o['method'] == 'cash']
        self.assertEqual(len(cash_options), 1)
        self.assertEqual(cash_options[0]['flow'], 'store_collects_all')
        self.assertIn('boutique', cash_options[0]['label'])

        order = self.make_order()
        arrangement = create_arrangement(order, 'store_collects_all', 'cash', user=self.client)
        self.assertEqual(arrangement.delivery_method, 'store')
        paid_roles = dict(arrangement.obligations.filter(
            kind__in=['products', 'delivery_collection']
        ).values_list('kind', 'payee'))
        self.assertEqual(paid_roles, {'products': 'store', 'delivery_collection': 'store'})
        self.assertFalse(arrangement.obligations.filter(kind='delivery').exists())
        self.assertFalse(arrangement.obligations.filter(kind='courier_remittance').exists())
        self.assertTrue(OrderSerializer(order).data['delivered_by_store'])
        from payments.direct_service import store_delivers
        self.store.offers_delivery = False
        self.store.save(update_fields=['offers_delivery'])
        order.refresh_from_db()
        self.assertTrue(store_delivers(order), 'La livraison boutique est figée pour la commande')

    def test_pickup_can_still_be_paid_cash_at_store(self):
        _, options = available_payment_options(self.store, delivery_requested=False)
        self.assertTrue(matching_option(options, 'direct_split', 'cash'))
        self.assertFalse(any(o['flow'] == 'courier_cash' for o in options))

    def test_global_cash_disable_is_respected_even_for_store_delivery(self):
        self.store.offers_delivery = True
        self.store.save(update_fields=['offers_delivery'])
        obj = SystemSettings.get_settings()
        obj.payment_policy = {**DEFAULT_PAYMENT_POLICY, 'enabled_methods': ['airtel_money'],
                              'enabled_flows': ['direct_split', 'store_collects_all']}
        obj.save(update_fields=['payment_policy'])
        _, options = available_payment_options(self.store)
        self.assertFalse(any(o['method'] == 'cash' for o in options))
