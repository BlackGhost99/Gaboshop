from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from payments.models import SubscriptionPlan
from stores.models import Store, StoreCategory
from users.models import User


class SuperAdminPlanTests(TestCase):
	"""Le magasin du super admin (is_superuser) a tous les avantages sans abonnement."""

	def setUp(self):
		self.category = StoreCategory.objects.create(name='Alimentation')
		self.free = SubscriptionPlan.objects.create(name='Free', slug='free', plan_type='free', price=Decimal('0'))
		self.business = SubscriptionPlan.objects.create(
			name='Business', slug='business', plan_type='business', price=Decimal('25000'), has_custom_page=True,
		)
		self.superadmin = User.objects.create_superuser(phone='+24162308363', password='x', user_type='store_manager')
		self.manager = User.objects.create_user(phone='+24177000001', password='x', user_type='store_manager')
		self.admin_store = self._store(self.superadmin, '+24162000001', 'Boutique admin')
		self.normal_store = self._store(self.manager, '+24177000002', 'Boutique normale')

	def _store(self, manager, phone, name):
		return Store.objects.create(
			category=self.category, manager=manager, name=name, phone=phone,
			zone='Louis', address='Louis', description='Description',
		)

	def test_superadmin_store_gets_top_plan(self):
		self.assertTrue(self.admin_store.is_superadmin_store)
		self.assertEqual(self.admin_store.get_current_plan(), self.business)

	def test_normal_store_without_subscription_stays_free(self):
		self.assertFalse(self.normal_store.is_superadmin_store)
		self.assertEqual(self.normal_store.get_current_plan(), self.free)

	def test_superadmin_can_edit_description(self):
		client = APIClient()
		client.force_authenticate(self.superadmin)
		res = client.patch(f'/api/v1/stores/{self.admin_store.id}/update/', {'description': 'Nouvelle'}, format='multipart')
		self.assertEqual(res.status_code, 200, res.content)
		self.admin_store.refresh_from_db()
		self.assertEqual(self.admin_store.description, 'Nouvelle')

	def test_normal_store_on_free_plan_cannot_edit_description(self):
		client = APIClient()
		client.force_authenticate(self.manager)
		res = client.patch(f'/api/v1/stores/{self.normal_store.id}/update/', {'description': 'Nouvelle'}, format='multipart')
		self.assertEqual(res.status_code, 403)

	def test_dashboard_shows_superadmin_plan_without_expiry(self):
		client = APIClient()
		client.force_authenticate(self.superadmin)
		res = client.get('/api/v1/dashboard/store/')
		self.assertEqual(res.status_code, 200, res.content)
		sub = res.json()['data']['subscription']
		self.assertEqual(sub['plan_type'], 'business')
		self.assertEqual(sub['status'], 'active')
		self.assertIsNone(sub['days_until_expiry'])
