"""Inscription d'un commerce : le gérant choisit son type de commerce.

Avant, chaque nouveau commerce était rangé d'office dans la première catégorie (« Hypermarchés »).
"""
from django.test import TestCase
from rest_framework.test import APIClient

from stores.models import Store, StoreCategory


class StoreSignupCategoryTests(TestCase):
    register_url = '/api/v1/auth/register/'

    def setUp(self):
        self.client = APIClient()
        self.first = StoreCategory.objects.create(name='Hypermarchés')
        self.fashion = StoreCategory.objects.create(name='Mode')
        self.inactive = StoreCategory.objects.create(name='Fermée', is_active=False)

    def payload(self, phone, **extra):
        data = {
            'phone': phone, 'password': 'Mapeto88d', 'password_confirm': 'Mapeto88d',
            'user_type': 'store_manager', 'store_name': 'Ma boutique',
            'store_address': 'Rue 1', 'store_zone': 'Centre', 'store_city': 'Libreville',
        }
        data.update(extra)
        return data

    def test_chosen_category_is_used(self):
        r = self.client.post(self.register_url, self.payload('+24106000301', store_category_id=str(self.fashion.id)), format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(Store.objects.get(manager__phone='+24106000301').category, self.fashion)

    def test_unknown_or_inactive_category_is_refused(self):
        for value in ('999999', str(self.inactive.id), 'abc'):
            r = self.client.post(self.register_url, self.payload('+24106000302', store_category_id=value), format='json')
            self.assertEqual(r.status_code, 400, value)
            self.assertIn('store_category_id', str(r.data))
        self.assertFalse(Store.objects.exists())

    def test_old_app_without_category_still_registers(self):
        r = self.client.post(self.register_url, self.payload('+24106000303'), format='json')
        self.assertEqual(r.status_code, 201, r.data)
        self.assertTrue(Store.objects.filter(manager__phone='+24106000303').exists())


class StoreCategoryListTests(TestCase):
    def test_categories_carry_store_count_and_come_first_when_filled(self):
        from users.models import User
        empty = StoreCategory.objects.create(name='Aaa vide')
        filled = StoreCategory.objects.create(name='Zzz remplie')
        manager = User.objects.create_user(phone='+24106000310', password='x', user_type='store_manager')
        Store.objects.create(is_verified=True, name='B', category=filled, manager=manager, phone='+24106000311', address='x', zone='Centre')
        r = APIClient().get('/api/v1/stores/categories/')
        self.assertEqual(r.status_code, 200)
        data = r.json()['data']
        self.assertEqual(data[0]['id'], filled.id)
        self.assertEqual(data[0]['store_count'], 1)
        self.assertEqual(next(c for c in data if c['id'] == empty.id)['store_count'], 0)
