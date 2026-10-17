"""Forfait Gratuit par défaut, jamais « Aucun forfait trouvé » ; Business visible mais grisé (15 oct. 2026)."""
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from b2b.models import B2BSubscriptionPlan
from payments.default_plans import ensure_range
from payments.models import SubscriptionPlan
from products.models import Product, ProductCategory
from stores.models import Store, StoreCategory
from users.models import User


class ForfaitGratuitTests(TestCase):
    def setUp(self):
        cache.clear()
        self.manager = User.objects.create_user(phone='+24177600301', password='Mapeto88x', user_type='store_manager')
        mode = StoreCategory.objects.create(name='Chaussures test')
        self.store = Store.objects.create(
            name='Boutique Timberland', category=mode, manager=self.manager, phone='+24177600302',
            address='Libreville', zone='Centre', commission_rate=Decimal('6'),
        )
        self.category = ProductCategory.objects.create(store_category=mode, name='Bottes', commission_rate=Decimal('6'))
        self.api = APIClient()
        self.api.force_authenticate(self.manager)

    def create(self, name='Timberland'):
        return self.api.post(
            f'/api/v1/stores/{self.store.id}/products/create/',
            {'name': name, 'price': '45000', 'stock': 2, 'weight_kg': '1', 'length_m': '0.3', 'category': self.category.id},
            format='json',
        )

    def test_no_plan_in_database_still_creates_product(self):
        SubscriptionPlan.objects.all().delete()
        res = self.create()
        self.assertEqual(res.status_code, 201, res.content)
        free = SubscriptionPlan.objects.get(plan_type='free')
        self.assertEqual(free.max_products, 20)
        self.assertEqual(free.price, 0)

    def test_free_limit_message(self):
        SubscriptionPlan.objects.filter(plan_type='free').update(max_products=2)
        for i in range(2):
            Product.objects.create(store=self.store, name=f'P{i}', price=1000, stock=1, category=self.category)
        res = self.create()
        self.assertNotEqual(res.status_code, 201)
        text = res.content.decode()
        self.assertIn('limite de 2 produits du forfait Gratuit', text)
        self.assertIn('Passez au forfait Pro', text)

    def test_range_business_greyed_and_not_buyable(self):
        ensure_range(SubscriptionPlan, B2BSubscriptionPlan)
        types = set(SubscriptionPlan.objects.values_list('plan_type', flat=True))
        self.assertTrue({'free', 'pro', 'business'} <= types)
        business = SubscriptionPlan.objects.get(plan_type='business')
        self.assertTrue(business.is_active)
        self.assertFalse(business.is_available)
        self.assertFalse(B2BSubscriptionPlan.objects.get(plan_type='business').is_available)

        res = self.api.get('/api/v1/payments/subscription-plans/')
        self.assertEqual(res.status_code, 200, res.content)
        by_type = {p['plan_type']: p for p in res.json()['plans']}
        self.assertFalse(by_type['business']['is_available'])
        self.assertTrue(by_type['pro']['is_available'])
        self.assertEqual(res.json()['current_plan']['plan_type'], 'free')

        res = self.api.post('/api/v1/payments/subscriptions/intent/',
                            {'plan_id': business.id, 'provider': 'airtel', 'phone_number': '077600303'}, format='json')
        self.assertEqual(res.status_code, 400, res.content)
        self.assertIn('pas encore disponible', res.json()['detail'])

    def test_existing_plan_keeps_its_price(self):
        SubscriptionPlan.objects.filter(plan_type='pro').delete()
        SubscriptionPlan.objects.create(name='Pro maison', slug='pro-maison', plan_type='pro', price=Decimal('15000'))
        ensure_range(SubscriptionPlan)
        self.assertEqual(SubscriptionPlan.objects.get(plan_type='pro').price, Decimal('15000'))
