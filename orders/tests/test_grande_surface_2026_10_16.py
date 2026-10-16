"""Une grande surface (hypermarché…) vend de tout : chaque produit garde le taux de sa propre catégorie."""
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from products.models import ProductCategory
from stores.models import Store, StoreCategory
from users.models import User


class GrandeSurfaceTests(TestCase):
    def setUp(self):
        cache.clear()
        self.manager = User.objects.create_user(phone='+24177600501', password='Mapeto88x', user_type='store_manager')
        self.hyper = StoreCategory.objects.create(name='HYPERMARCHÉ test', sells_everything=True)
        mode = StoreCategory.objects.create(name='MODE test hyper')
        self.store = Store.objects.create(name='Hyper', category=self.hyper, manager=self.manager, phone='+24177600502',
                                          address='Libreville', zone='Centre', commission_rate=Decimal('8'))
        self.shoes = ProductCategory.objects.create(store_category=mode, name='CHAUSSURES test', commission_rate=Decimal('6'))
        self.api = APIClient()
        self.api.force_authenticate(self.manager)

    def create(self):
        return self.api.post(f'/api/v1/stores/{self.store.id}/products/create/', {
            'name': 'Timberland', 'price': '45000', 'stock': 5, 'weight_kg': '1', 'length_m': '0.3',
            'category': self.shoes.id,
        }, format='json')

    def test_hypermarket_can_sell_shoes(self):
        res = self.create()
        self.assertEqual(res.status_code, 201, res.content)

    def test_hypermarket_sees_all_categories(self):
        res = self.api.get(f'/api/v1/stores/{self.store.id}/categories/')
        names = [c['name'] for c in res.json()['data']]
        self.assertIn('CHAUSSURES test', names)

    def test_specialised_store_still_limited(self):
        StoreCategory.objects.filter(pk=self.hyper.pk).update(sells_everything=False)
        self.assertEqual(self.create().status_code, 400)

    def test_migration_marks_hypermarkets(self):
        from importlib import import_module
        from django.apps import apps
        StoreCategory.objects.create(name='Super Marché test')
        import_module('stores.migrations.0022_grandes_surfaces_2026_10_16').apply(apps, None)
        self.assertTrue(StoreCategory.objects.get(name='Super Marché test').sells_everything)
