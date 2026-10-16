"""Devis complet du panier : le total affiché est celui de la commande créée, pour chaque façon de payer."""
from datetime import time, timedelta
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from api.models import SystemSettings
from delivery.models import City, DeliveryZone, Landmark, Neighborhood, VehicleType, ZoneVehicleRate
from orders.models import Order
from payments.configuration import DEFAULT_PAYMENT_POLICY
from payments.models import ClientForfait, Forfait
from products.models import Product, ProductCategory
from stores.models import Store, StoreCategory
from users.models import User


class DevisCompletTests(TestCase):
    def setUp(self):
        cache.clear()
        libreville = City.objects.get(name='Libreville')
        self.louis = Neighborhood.objects.get(city=libreville, name='Louis')
        self.landmark = Landmark.objects.get(neighborhood=self.louis, name='Carrefour Louis')
        zone = DeliveryZone.objects.create(name='Centre devis', city='Libreville')
        moto = VehicleType.objects.filter(name='MOTO').first() or VehicleType.objects.create(
            name='MOTO', max_weight_kg=20, max_length_m=1, max_items=10, max_distance_km=30)
        ZoneVehicleRate.objects.create(zone=zone, vehicle=moto, base_price=Decimal('1500'))
        self.louis.zone = zone
        self.louis.save(update_fields=['zone'])

        manager = User.objects.create_user(phone='+24177600501', password='Mapeto88x', user_type='store_manager')
        self.client_user = User.objects.create_user(phone='+24177600502', password='Mapeto88x', user_type='client')
        cat = StoreCategory.objects.create(name='Mode devis')
        self.store = Store.objects.create(name='Boutique devis', category=cat, manager=manager, phone='+24177600503',
                                          address='Bord de mer', city='Libreville', zone='Centre',
                                          commission_rate=Decimal('6'), delivery_fee=Decimal('3000'),
                                          offers_delivery=True, is_verified=True,
                                          opening_time=time(0, 0), closing_time=time(23, 59))
        pcat = ProductCategory.objects.create(store_category=cat, name='Chaussures devis', commission_rate=Decimal('6'))
        self.product = Product.objects.create(store=self.store, name='Timberland', price=2000, stock=100, category=pcat,
                                              weight_kg=1, length_m=Decimal('0.3'))
        s = SystemSettings.get_settings()
        s.airtel_money_fee = Decimal('2')
        s.moov_money_fee = Decimal('1.5')
        s.small_order_fee = Decimal('200')
        s.small_order_threshold = Decimal('5000')
        s.save()
        forfait = Forfait.objects.create(name='Livraison -20 %', discount_rate=20)
        ClientForfait.objects.create(user=self.client_user, forfait=forfait, status='active',
                                     expiration_date=timezone.now() + timedelta(days=30))
        self.set_policy(online=False)
        self.api = APIClient()
        self.api.force_authenticate(self.client_user)

    def set_policy(self, online):
        s = SystemSettings.get_settings()
        flows = DEFAULT_PAYMENT_POLICY['enabled_flows'] + (['platform_online'] if online else [])
        s.payment_policy = {**DEFAULT_PAYMENT_POLICY, 'enabled_flows': flows,
                            'instructions': {'airtel_money': 'Code marchand 123456'}}
        s.save(update_fields=['payment_policy'])

    def body(self, flow, method, delivery_by='', quantity=2):
        return {
            'store': self.store.id, 'city': 'Libreville', 'delivery_address': 'Portail bleu',
            'delivery_phone': '077391199', 'delivery_zone': 'x', 'neighborhood': self.louis.id,
            'landmark': self.landmark.id, 'delivery_requested': True, 'payment_flow': flow,
            'payment_method': method, 'delivery_by': delivery_by,
            'delivery_payment_method': delivery_by if flow == 'platform_online' else '',
            'items': [{'product_id': self.product.id, 'quantity': quantity}],
        }

    def quote_then_order(self, flow, method, delivery_by='', quantity=2):
        online = flow == 'platform_online'
        self.set_policy(online)
        with mock.patch('payments.configuration.platform_online_ready', return_value=online):
            quote = self.api.post('/api/v1/orders/delivery-quote/', self.body(flow, method, delivery_by, quantity),
                                  format='json')
            self.assertEqual(quote.status_code, 200, quote.content)
            quote = quote.json()['data']
            with mock.patch('delivery.tasks.assign_nearest_delivery_agent'):
                res = self.api.post('/api/v1/orders/create/', self.body(flow, method, delivery_by, quantity),
                                    format='json')
        self.assertEqual(res.status_code, 201, res.content)
        return quote, Order.objects.order_by('-id').first()

    def test_quote_total_equals_order_total_for_every_flow(self):
        cases = [
            ('direct_split', 'cash', ''), ('direct_split', 'airtel_money', ''), ('store_collects_all', 'cash', ''),
            ('courier_cash', 'cash', ''), ('platform_online', 'airtel_money', 'gaboshop'),
            ('platform_online', 'moov_money', 'gaboshop'), ('platform_online', 'airtel_money', 'store'),
        ]
        for flow, method, delivery_by in cases:
            with self.subTest(flow=flow, method=method, delivery_by=delivery_by):
                cache.clear()
                quote, order = self.quote_then_order(flow, method, delivery_by)
                Order.objects.filter(pk=order.pk).update(status='cancelled')  # limite de 5 commandes en cours
                self.assertEqual(quote['blocking'], [])
                self.assertEqual(Decimal(quote['total']), order.total_amount)
                self.assertEqual(Decimal(quote['delivery_fee']), order.delivery_fee)
                self.assertEqual(order.delivery_address, 'Louis, 1er arrondissement, Libreville — près de Carrefour Louis — Portail bleu')
                self.assertEqual(quote['delivery']['address'], order.delivery_address)
                split = sum(Decimal(line['amount']) for line in quote['payment']['split'])
                self.assertEqual(split, order.total_amount)

    def test_online_quote_lists_every_fee(self):
        quote, order = self.quote_then_order('platform_online', 'airtel_money', 'gaboshop')
        labels = [fee['label'] for fee in quote['fees']]
        self.assertIn('Frais Airtel Money', labels)
        self.assertIn('Réduction de votre forfait livraison', labels)
        self.assertTrue(any(label.startswith('Frais petit panier') for label in labels))
        # 4 000 articles + 1 500 livraison + 2 % de 5 500 (110) + 200 petit panier - 20 % de 1 500 (300)
        self.assertEqual(Decimal(quote['total']), Decimal('5510'))
        self.assertEqual(quote['delivery']['vehicle_label'], 'Moto')
        self.assertEqual(quote['payment']['split'][0]['payee'], 'Gaboshop (paiement en ligne)')
        self.assertTrue(any('code de livraison' in note for note in quote['notes']))

    def test_direct_split_pays_store_and_courier_separately(self):
        quote, _ = self.quote_then_order('direct_split', 'cash')
        payees = {line['payee']: Decimal(line['amount']) for line in quote['payment']['split']}
        self.assertEqual(payees, {'Le commerce': Decimal('4000'), 'Le livreur': Decimal('1500')})

    def test_blocking_reasons_shown_before_ordering(self):
        self.store.min_order_amount = Decimal('999999')
        self.store.opening_time, self.store.closing_time = time(3, 0), time(3, 1)
        self.store.save()
        with mock.patch('stores.models.Store.is_open', return_value=False):
            quote = self.api.post('/api/v1/orders/delivery-quote/', self.body('direct_split', 'cash', quantity=150),
                                  format='json').json()['data']
        text = ' '.join(quote['blocking'])
        self.assertIn('Stock insuffisant', text)
        self.assertIn('fermé', text)
        self.assertIn('Minimum de commande', text)

    def test_missing_quarter_explains_instead_of_total(self):
        body = self.body('direct_split', 'cash')
        body.pop('neighborhood')
        body['delivery_zone'] = ''
        quote = self.api.post('/api/v1/orders/delivery-quote/', body, format='json').json()['data']
        self.assertIsNone(quote['total'])
        self.assertIn('quartier', quote['message'])
