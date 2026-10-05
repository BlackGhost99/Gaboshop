import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient

from stores.models import Store, StoreCategory
from users.models import User


def _image(name):
	buf = io.BytesIO()
	Image.new('RGB', (20, 20), 'red').save(buf, format='PNG')
	return SimpleUploadedFile(name, buf.getvalue(), content_type='image/png')


class StoreProfileUpdateTests(TestCase):
	"""Le gérant peut modifier tout le profil du magasin, quel que soit son forfait."""

	def setUp(self):
		self.manager = User.objects.create_user(phone='077000010', password='secret123', user_type='store_manager')
		category = StoreCategory.objects.create(name='Épicerie')
		self.store = Store.objects.create(
			name='TestMag1', category=category, manager=self.manager,
			phone='077000011', zone='Louis', address='Rue 1',
		)
		self.client = APIClient()
		self.client.force_authenticate(self.manager)

	def test_full_profile_form_without_subscription(self):
		details = self.client.get(f'/api/v1/stores/{self.store.id}/').json()['data']
		payload = {
			'name': 'TestMag1 modifié',
			'description': 'Nouvelle description',
			'phone': details['phone'],
			'address': details['address'],
			'zone': details['zone'],
			'opening_time': details['opening_time'],
			'closing_time': details['closing_time'],
			'delivery_fee': details['delivery_fee'],
			'min_order_amount': details['min_order_amount'],
			'offers_delivery': 'true',
			'agent_code': '',
			'manager_first_name': 'Jean',
			'manager_last_name': 'Dupont',
			'logo': _image('logo.png'),
			'banner_image': _image('banner.png'),
		}
		res = self.client.patch(f'/api/v1/stores/{self.store.id}/update/', payload, format='multipart')
		self.assertEqual(res.status_code, 200, res.content)
		self.store.refresh_from_db()
		self.assertEqual(self.store.description, 'Nouvelle description')
		self.assertTrue(self.store.banner_image)


class AdminProductCategoryTests(TestCase):
	"""L'admin crée une catégorie de produit liée à un type de magasin ; le magasin la voit."""

	def setUp(self):
		self.admin = User.objects.create_superuser(phone='062300001', password='secret123', email='')
		self.manager = User.objects.create_user(phone='077000020', password='secret123', user_type='store_manager')
		self.category = StoreCategory.objects.create(name='Supermarché')
		self.store = Store.objects.create(
			name='Mag', category=self.category, manager=self.manager,
			phone='077000021', zone='Louis', address='Rue 1',
		)
		from payments.models import SubscriptionPlan
		SubscriptionPlan.objects.get_or_create(plan_type='free', defaults={'name': 'Free', 'slug': 'free', 'price': 0})
		self.client = APIClient()

	def test_create_then_store_sees_and_assigns_it(self):
		self.client.force_authenticate(self.admin)
		res = self.client.post('/api/v1/admin/product-categories/', {
			'name': 'Boissons', 'store_category_id': self.category.id, 'order': 1,
		}, format='json')
		self.assertEqual(res.status_code, 201, res.content)
		cat_id = res.json()['data']['id']
		self.assertEqual(res.json()['data']['store_category_name'], 'Supermarché')

		dup = self.client.post('/api/v1/admin/product-categories/', {
			'name': 'Boissons', 'store_category_id': self.category.id,
		}, format='json')
		self.assertEqual(dup.status_code, 400)

		self.client.force_authenticate(self.manager)
		cats = self.client.get(f'/api/v1/stores/{self.store.id}/categories/').json()['data']
		self.assertEqual([c['id'] for c in cats], [cat_id])

		res = self.client.post(f'/api/v1/stores/{self.store.id}/products/create/', {
			'name': 'Coca', 'price': '500', 'stock': '10', 'category': cat_id,
			'weight_kg': '1', 'length_m': '0.3',
		}, format='multipart')
		self.assertIn(res.status_code, (200, 201), res.content)
		self.assertEqual(self.store.products.get().category_id, cat_id)

	def test_create_requires_store_type(self):
		self.client.force_authenticate(self.admin)
		res = self.client.post('/api/v1/admin/product-categories/', {'name': 'X'}, format='json')
		self.assertEqual(res.status_code, 400)
