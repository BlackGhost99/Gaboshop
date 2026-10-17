"""Historique commerçant : recherche serveur au-delà de la première page et isolation des boutiques."""
from decimal import Decimal
from django.test import TestCase
from rest_framework.test import APIClient

from orders.models import Order, OrderItem
from products.models import Product, ProductCategory
from stores.models import Store, StoreCategory
from users.models import User


class MerchantOrdersSearchTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(phone='+241077520001', password='test', user_type='store_manager')
        self.other_owner = User.objects.create_user(phone='+241077520002', password='test', user_type='store_manager')
        self.client_user = User.objects.create_user(phone='+241077520003', password='test', user_type='client')
        self.cat = StoreCategory.objects.create(name='Recherche B2C')
        self.store = Store.objects.create(
            name='Commerce recherche', category=self.cat, manager=self.owner,
            phone='+241077520004', address='Libreville', zone='Centre',
        )
        self.other_store = Store.objects.create(
            name='Autre commerce', category=self.cat, manager=self.other_owner,
            phone='+241077520005', address='Libreville', zone='Centre',
        )
        pc = ProductCategory.objects.create(name='Produits recherche', store_category=self.cat)
        self.old_product = Product.objects.create(
            store=self.store, category=pc, name='Casque Vintage',
            price=Decimal('5000'), stock=80, weight_kg=Decimal('1'),
        )
        self.new_product = Product.objects.create(
            store=self.store, category=pc, name='Produit courant',
            price=Decimal('5000'), stock=80, weight_kg=Decimal('1'),
        )
        self.foreign_product = Product.objects.create(
            store=self.other_store, category=pc, name='Casque Vintage',
            price=Decimal('5000'), stock=80, weight_kg=Decimal('1'),
        )

    def order(self, store, product, status='cancelled'):
        order = Order.objects.create(
            client=self.client_user, store=store, status=status,
            delivery_address='Libreville', delivery_phone=self.client_user.phone,
            delivery_zone='Centre', total_amount=Decimal('5000'), items_total=Decimal('5000'),
        )
        OrderItem.objects.create(order=order, product=product, quantity=1, unit_price=Decimal('5000'))
        return order

    def test_search_finds_an_old_sale_beyond_first_page_without_cross_store_leak(self):
        old = self.order(self.store, self.old_product)
        foreign = self.order(self.other_store, self.foreign_product)
        for _ in range(24):
            self.order(self.store, self.new_product)
        api = APIClient()
        api.force_authenticate(user=self.owner)
        response = api.get('/api/v1/orders/', {'search': 'Casque Vintage'})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['id'], old.id)
        self.assertNotEqual(response.data['results'][0]['id'], foreign.id)

    def test_server_status_filter_excludes_unrelated_orders(self):
        delivered = self.order(self.store, self.new_product, status='delivered')
        self.order(self.store, self.old_product, status='cancelled')
        api = APIClient()
        api.force_authenticate(user=self.owner)
        response = api.get('/api/v1/orders/', {'status': 'delivered'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([x['id'] for x in response.data['results']], [delivered.id])

    def test_bad_date_returns_validation_error(self):
        self.order(self.store, self.old_product)
        api = APIClient()
        api.force_authenticate(user=self.owner)
        response = api.get('/api/v1/orders/', {'date_from': 'not-a-date'})
        self.assertEqual(response.status_code, 400)
