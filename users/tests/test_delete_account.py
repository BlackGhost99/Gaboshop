from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from orders.models import Order
from stores.models import Store, StoreCategory
from users.models import User


class DeleteAccountTests(TestCase):
	"""Suppression de compte par l'utilisateur (exigence Google Play)."""

	URL = '/api/v1/auth/account/delete/'

	def setUp(self):
		self.api = APIClient()
		self.user = User.objects.create_user(phone='+24106111111', password='secret123', user_type='client', first_name='Awa', email='awa@example.com')
		self.api.force_authenticate(self.user)

	def test_wrong_password_is_refused(self):
		res = self.api.post(self.URL, {'password': 'nope'}, format='json')
		self.assertEqual(res.status_code, 400)
		self.user.refresh_from_db()
		self.assertTrue(self.user.is_active)

	def test_account_is_anonymised_and_cannot_log_in(self):
		res = self.api.post(self.URL, {'password': 'secret123'}, format='json')
		self.assertEqual(res.status_code, 200, res.content)
		self.user.refresh_from_db()
		self.assertFalse(self.user.is_active)
		self.assertEqual((self.user.first_name, self.user.email), ('', ''))
		self.assertNotIn('24106111111', self.user.phone)
		login = APIClient().post('/api/v1/auth/login/', {'phone': '+24106111111', 'password': 'secret123'}, format='json')
		self.assertNotEqual(login.status_code, 200)

	def test_order_in_progress_blocks_deletion(self):
		manager = User.objects.create_user(phone='+24106111112', password='x', user_type='store_manager')
		store = Store.objects.create(name='Boutique', category=StoreCategory.objects.create(name='Mode'), manager=manager, phone='+24106000100', address='Libreville', zone='Centre')
		Order.objects.create(client=self.user, store=store, delivery_address='Akanda', delivery_phone='+24106111111', delivery_zone='Centre', delivery_fee=Decimal('0'))
		res = self.api.post(self.URL, {'password': 'secret123'}, format='json')
		self.assertEqual(res.status_code, 409)
		self.user.refresh_from_db()
		self.assertTrue(self.user.is_active)

	def test_admin_cannot_delete_itself(self):
		admin = User.objects.create_user(phone='+24106111113', password='secret123', user_type='admin', is_staff=True)
		self.api.force_authenticate(admin)
		self.assertEqual(self.api.post(self.URL, {'password': 'secret123'}, format='json').status_code, 409)
