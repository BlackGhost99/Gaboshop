import base64
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from core.storage import DatabaseStorage
from delivery.models import Delivery, DeliveryProof
from orders.models import Order
from stores.models import Store, StoreCategory
from users.models import User

PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==')


class PrivateProofPhotoTests(TestCase):
	def setUp(self):
		field = DeliveryProof._meta.get_field('id_card_photo')
		self._old_storage = field.storage
		field.storage = DatabaseStorage()
		self.client_user = User.objects.create_user(phone='+24177300001', password='x', user_type='client')
		self.agent = User.objects.create_user(phone='+24177300002', password='x', user_type='delivery_agent')
		self.stranger = User.objects.create_user(phone='+24177300003', password='x', user_type='client')
		self.admin = User.objects.create_user(phone='+24177300004', password='x', user_type='admin', is_staff=True)
		manager = User.objects.create_user(phone='+24177300005', password='x', user_type='store_manager')
		store = Store.objects.create(name='Boutique', category=StoreCategory.objects.create(name='Mode'), manager=manager, phone='+24106000101', address='Libreville', zone='Centre')
		order = Order.objects.create(client=self.client_user, store=store, delivery_address='Akanda', delivery_phone='+24177300001', delivery_zone='Centre', delivery_fee=Decimal('0'))
		self.delivery, _ = Delivery.objects.get_or_create(order=order)
		self.delivery.delivery_agent = self.agent
		self.delivery.save()
		self.proof = DeliveryProof(delivery=self.delivery, latitude=Decimal('0.4'), longitude=Decimal('9.4'))
		self.proof.id_card_photo.save('IMG_20261009_carte.png', SimpleUploadedFile('IMG_20261009_carte.png', PNG, content_type='image/png'), save=False)
		DeliveryProof.objects.bulk_create([self.proof])

	def tearDown(self):
		DeliveryProof._meta.get_field('id_card_photo').storage = self._old_storage

	def url(self, kind='id_card'):
		return f'/api/v1/dashboard/delivery/{self.delivery.id}/proof-photo/{kind}/'

	def as_user(self, user):
		api = APIClient()
		api.force_authenticate(user)
		return api

	def test_file_name_is_unguessable_and_not_public(self):
		name = self.proof.id_card_photo.name
		self.assertRegex(name, r'^delivery_proofs/id_cards/[0-9a-f]{32}\.png$')
		self.assertEqual(APIClient().get(f'/media/{name}').status_code, 404)

	def test_only_admin_courier_and_client_can_view(self):
		for user in (self.admin, self.agent, self.client_user):
			res = self.as_user(user).get(self.url())
			self.assertEqual(res.status_code, 200, user.phone)
			self.assertEqual(res['Content-Type'], 'image/png')
			self.assertEqual(res.content, PNG)
		self.assertEqual(self.as_user(self.stranger).get(self.url()).status_code, 403)
		self.assertIn(APIClient().get(self.url()).status_code, (401, 403))
		self.assertEqual(self.as_user(self.admin).get(self.url('package')).status_code, 404)
