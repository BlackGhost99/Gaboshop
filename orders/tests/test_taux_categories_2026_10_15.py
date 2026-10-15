"""Taux de commission par catégorie donnés le 15 oct. 2026 (migration products 0021)."""
import importlib
from decimal import Decimal

from django.apps import apps
from django.test import TestCase

from api.models import SystemSettings
from products.models import ProductCategory
from stores.models import StoreCategory

migration = importlib.import_module('products.migrations.0021_taux_commission_categories_2026_10_15')


class CategoryRateTests(TestCase):
    def test_all_categories_exist_with_their_rate(self):
        migration.apply_rates(apps, None)
        for name, rate, _store_type in migration.RATES:
            category = ProductCategory.objects.get(store__isnull=True, name=name)
            self.assertEqual(category.commission_rate, Decimal(rate), name)
        self.assertEqual(SystemSettings.get_settings().b2b_commission_rate, Decimal('3'))

    def test_existing_category_is_updated_not_duplicated(self):
        ProductCategory.objects.filter(name__in=[n for n, _r, _s in migration.RATES]).delete()
        food = StoreCategory.objects.get_or_create(name='ALIMENTATION & BOISSONS')[0]
        old = ProductCategory.objects.create(store_category=food, name='Alimentaire essentiel', commission_rate=Decimal('8'))
        migration.apply_rates(apps, None)
        old.refresh_from_db()
        self.assertEqual(old.commission_rate, Decimal('2'))
        self.assertEqual(ProductCategory.objects.filter(name__iexact='alimentaire essentiel').count(), 1)
        migration.apply_rates(apps, None)  # deuxième passage : rien de neuf
        self.assertEqual(ProductCategory.objects.filter(store__isnull=True, name='MODE').count(), 1)
