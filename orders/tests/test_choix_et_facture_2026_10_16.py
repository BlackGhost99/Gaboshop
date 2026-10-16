"""Pointure/couleur choisies par le client et facture PDF Gaboshop (16 oct. 2026)."""
from datetime import time
from io import BytesIO
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from pypdf import PdfReader
from django.test import TestCase
from rest_framework.test import APIClient

from api.models import SystemSettings
from orders.models import Order
from payments.configuration import DEFAULT_PAYMENT_POLICY
from products.models import Product, ProductCategory
from products.options import split_values
from products.serializers import ProductAttributesField
from stores.models import Store, StoreCategory
from users.models import User


class ChoixEtFactureTests(TestCase):
    def setUp(self):
        cache.clear()
        self.manager = User.objects.create_user(phone='+24177600601', password='Mapeto88x', user_type='store_manager')
        self.client_user = User.objects.create_user(phone='+24177600602', password='Mapeto88x', user_type='client',
                                                    first_name='Awa', last_name='Client')
        cat = StoreCategory.objects.create(name='Mode test facture')
        self.store = Store.objects.create(name='TEST0.2', category=cat, manager=self.manager, phone='+24177600603',
                                          address='Mont Bouet', zone='Centre', commission_rate=Decimal('6'),
                                          is_verified=True, opening_time=time(0, 0), closing_time=time(23, 59),
                                          delivery_fee=Decimal('2000'))
        pcat = ProductCategory.objects.create(store_category=cat, name='Chaussures facture', commission_rate=Decimal('6'))
        self.product = Product.objects.create(store=self.store, name='Timberland', price=70000, stock=5, category=pcat,
                                              weight_kg=Decimal('0.2'), length_m=Decimal('0.35'),
                                              attributes={'sizes': '40, 41, 42, 44', 'color': 'Marron, Noir'})
        settings = SystemSettings.get_settings()
        settings.payment_policy = DEFAULT_PAYMENT_POLICY
        settings.save(update_fields=['payment_policy'])
        self.api = APIClient()
        self.api.force_authenticate(self.client_user)

    def order(self, options=None):
        item = {'product_id': self.product.id, 'quantity': 1}
        if options is not None:
            item['options'] = options
        payload = {'store': self.store.id, 'city': 'Libreville', 'delivery_address': 'Portail bleu',
                   'delivery_phone': '077391199', 'delivery_zone': 'Louis', 'delivery_requested': True,
                   'payment_flow': 'direct_split', 'payment_method': 'cash', 'items': [item]}
        with mock.patch('delivery.tasks.assign_nearest_delivery_agent'):
            return self.api.post('/api/v1/orders/create/', payload, format='json')

    def test_sizes_typed_without_commas_are_cleaned(self):
        self.assertEqual(split_values('40 41 42'), ['40', '41', '42'])
        self.assertEqual(split_values('40;41 / 44'), ['40', '41', '44'])
        self.assertEqual(split_values('Taille unique'), ['Taille unique'])
        self.assertEqual(ProductAttributesField().to_internal_value({'sizes': '40 41 41'})['sizes'], '40, 41')

    def test_choice_required_and_checked(self):
        res = self.order()
        self.assertEqual(res.status_code, 400)
        self.assertIn('pointure', res.content.decode())
        self.assertEqual(self.order({'size': '43', 'color': 'Marron'}).status_code, 400)

    def test_choice_saved_and_invoice(self):
        res = self.order({'size': '42', 'color': 'marron'})
        self.assertIn(res.status_code, (200, 201), res.content)
        order = Order.objects.get(client=self.client_user)
        self.assertEqual(order.items.get().options, {'size': '42', 'color': 'Marron'})

        pdf = self.api.get(f'/api/v1/orders/{order.id}/invoice/')
        self.assertEqual(pdf.status_code, 200, pdf.content[:300])
        self.assertEqual(pdf['Content-Type'], 'application/pdf')
        self.assertTrue(pdf.content.startswith(b'%PDF'))
        # Une commande simple ne doit pas créer une deuxième page quasi vide.
        reader = PdfReader(BytesIO(pdf.content))
        self.assertEqual(len(reader.pages), 1, 'La facture simple doit tenir sur une page A4')
        extracted = reader.pages[0].extract_text()
        self.assertIn('72 000', extracted)
        self.assertIn('Timberland', extracted)

        from orders.invoice import invoice_context
        ctx = invoice_context(order)
        self.assertEqual(ctx['number'], f'FAC-{order.order_number}')
        self.assertEqual(ctx['items'][0]['options'], 'Taille 42 · Marron')
        self.assertFalse(ctx['payment_is_paid'], "Ne pas indiquer payé sans confirmation")
        self.assertNotEqual(ctx['payment_state'], 'Règlement confirmé')

        store_api = APIClient()
        store_api.force_authenticate(self.manager)
        self.assertEqual(store_api.get(f'/api/v1/orders/{order.id}/invoice/').status_code, 200)
        stranger = APIClient()
        stranger.force_authenticate(User.objects.create_user(phone='+24177600604', password='Mapeto88x', user_type='client'))
        self.assertEqual(stranger.get(f'/api/v1/orders/{order.id}/invoice/').status_code, 404)
