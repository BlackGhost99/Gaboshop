"""Forfaits : l'alimentaire se limite en quantité, le non alimentaire n'est jamais bloqué par catégorie.

Avant, le forfait Free empêchait les commerces de publier des produits non alimentaires
(can_sell_non_food_products / max_products_non_food), alors que c'est la vraie source de commission.
"""
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from api.models import SystemSettings
from payments.models import SubscriptionPlan
from products.models import Product, ProductCategory
from stores.models import Store, StoreCategory
from users.models import User


class PlanFoodLimitTests(TestCase):
    def setUp(self):
        self.plan, _ = SubscriptionPlan.objects.update_or_create(
            plan_type='free',
            defaults={
                'name': 'Free', 'slug': 'free', 'price': Decimal('0'),
                'max_products': 5, 'max_products_food': 2,
                # Anciens réglages qui bloquaient le non alimentaire : ils ne doivent plus rien faire.
                'can_sell_non_food_products': False, 'max_products_non_food': 0,
            },
        )
        settings = SystemSettings.get_settings()
        settings.food_category_keywords = 'ALIMENTATION,BOISSONS'
        settings.save(update_fields=['food_category_keywords'])

        self.manager = User.objects.create_user(phone='+24106000201', password='x', user_type='store_manager')
        self.other = User.objects.create_user(phone='+24106000202', password='x', user_type='store_manager')
        food = StoreCategory.objects.create(name='Alimentation générale')
        fashion = StoreCategory.objects.create(name='Mode')
        self.store = Store.objects.create(
            name='Boutique test', category=food, manager=self.manager, phone='+24106000203',
            address='Libreville', zone='Centre', commission_rate=Decimal('8'),
        )
        self.food_cat = ProductCategory.objects.create(store_category=food, name='Riz', commission_rate=Decimal('2'))
        self.other_cat = ProductCategory.objects.create(store_category=fashion, name='Robes', commission_rate=Decimal('12'))
        self.api = APIClient()
        self.api.force_authenticate(self.manager)

    def create(self, category, name='Article'):
        return self.api.post(
            f'/api/v1/stores/{self.store.id}/products/create/',
            {'name': name, 'price': '5000', 'stock': 3, 'weight_kg': '1', 'length_m': '0.3', 'category': category.id},
            format='json',
        )

    def test_non_food_allowed_on_free_plan(self):
        res = self.create(self.other_cat, 'Robe')
        self.assertEqual(res.status_code, 201, res.content)

    def test_food_limited_by_quantity_but_non_food_still_allowed(self):
        self.assertEqual(self.create(self.food_cat, 'Riz 1').status_code, 201)
        self.assertEqual(self.create(self.food_cat, 'Riz 2').status_code, 201)
        res = self.create(self.food_cat, 'Riz 3')
        self.assertEqual(res.status_code, 403)
        self.assertIn('alimentaires', res.json()['error']['message'])
        self.assertEqual(self.create(self.other_cat, 'Robe').status_code, 201)

    def test_global_cap_still_applies(self):
        for i in range(5):
            Product.objects.create(store=self.store, category=self.other_cat, name=f'P{i}', price=Decimal('1000'))
        self.assertEqual(self.create(self.other_cat).status_code, 403)

    def test_no_food_limit_when_empty(self):
        self.plan.max_products_food = None
        self.plan.save(update_fields=['max_products_food'])
        for i in range(3):
            self.assertEqual(self.create(self.food_cat, f'Riz {i}').status_code, 201)

    def test_keywords_come_from_admin_settings(self):
        settings = SystemSettings.get_settings()
        settings.food_category_keywords = 'BOISSONS'
        settings.save(update_fields=['food_category_keywords'])
        for i in range(3):
            self.assertEqual(self.create(self.food_cat, f'Riz {i}').status_code, 201)

    def test_moving_product_into_food_respects_limit(self):
        for i in range(2):
            Product.objects.create(store=self.store, category=self.food_cat, name=f'F{i}', price=Decimal('1000'))
        product = Product.objects.create(store=self.store, category=self.other_cat, name='Robe', price=Decimal('1000'))
        res = self.api.patch(f'/api/v1/products/{product.id}/update/', {'category': self.food_cat.id}, format='json')
        self.assertEqual(res.status_code, 403)
        # Modifier un produit alimentaire existant reste possible même au plafond.
        food_product = Product.objects.filter(category=self.food_cat).first()
        res = self.api.patch(f'/api/v1/products/{food_product.id}/update/', {'price': '1500'}, format='json')
        self.assertEqual(res.status_code, 200, res.content)

    def test_other_manager_cannot_add_to_store(self):
        self.api.force_authenticate(self.other)
        self.assertEqual(self.create(self.other_cat).status_code, 403)

    def test_features_list_hides_old_non_food_rule(self):
        self.plan.features_json = ['5 produits non alimentaires']
        features = self.plan.get_features_list()
        self.assertFalse(any('non alimentaire' in f for f in features))
        self.assertIn('Dont 2 produits alimentaires au plus', features)
