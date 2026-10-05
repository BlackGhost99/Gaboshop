from django.test import TestCase
from rest_framework.test import APIClient

from users.models import User


class SuperuserIsAdminTests(TestCase):
	"""Le compte superutilisateur doit être présenté comme admin pour aller vers l'espace admin."""

	def setUp(self):
		self.client = APIClient()

	def _login(self, phone, password):
		return self.client.post('/api/v1/auth/login/', {'phone': phone, 'password': password}, format='json')

	def test_superuser_created_with_old_default_type_logs_in_as_admin(self):
		# Compte créé avant le correctif : user_type resté à « client »
		User.objects.create_superuser(phone='062308363', password='secret123', email='', user_type='client')
		res = self._login('062308363', 'secret123')
		self.assertEqual(res.status_code, 200, res.content)
		self.assertEqual(res.json()['data']['user']['user_type'], 'admin')

	def test_profile_reports_admin_for_superuser(self):
		user = User.objects.create_superuser(phone='062308364', password='secret123', email='')
		self.client.force_authenticate(user)
		res = self.client.get('/api/v1/auth/profile/')
		self.assertEqual(res.json()['data']['user_type'], 'admin')

	def test_new_superuser_defaults_to_admin_type(self):
		user = User.objects.create_superuser(phone='062308365', password='secret123', email='')
		self.assertEqual(user.user_type, 'admin')

	def test_regular_store_manager_unchanged(self):
		user = User.objects.create_user(phone='077000001', password='secret123', user_type='store_manager')
		self.client.force_authenticate(user)
		res = self.client.get('/api/v1/auth/profile/')
		self.assertEqual(res.json()['data']['user_type'], 'store_manager')
