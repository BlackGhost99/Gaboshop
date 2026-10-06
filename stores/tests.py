import io
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework.test import APIClient

from stores.models import Store, StoreCategory
from users.models import User


def _image(name):
	buf = io.BytesIO()
	Image.new('RGB', (20, 20), 'red').save(buf, format='PNG')
	return SimpleUploadedFile(name, buf.getvalue(), content_type='image/png')


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
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
		# L'image envoyée est bien servie par l'API
		from urllib.parse import urlparse
		served = self.client.get(urlparse(self.store.logo.url).path)
		self.assertEqual(served.status_code, 200)


@override_settings(STORAGES={
	"default": {"BACKEND": "core.storage.DatabaseStorage"},
	"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}, MEDIA_ROOT=tempfile.mkdtemp())
class MediaInDatabaseTests(TestCase):
	"""Les images envoyées sont gardées dans la base : elles survivent à un redéploiement."""

	def setUp(self):
		self.manager = User.objects.create_user(phone='077000030', password='secret123', user_type='store_manager')
		self.store = Store.objects.create(
			name='MagPhoto', category=StoreCategory.objects.create(name='Mode'), manager=self.manager,
			phone='077000031', zone='Louis', address='Rue 1',
		)
		self.client = APIClient()
		self.client.force_authenticate(self.manager)

	def test_logo_survives_empty_disk_and_big_photo_is_shrunk(self):
		import os
		from urllib.parse import urlparse

		from core.models import StoredFile
		big = io.BytesIO()
		Image.effect_noise((3000, 2000), 80).convert('RGB').save(big, 'JPEG', quality=95)
		big_upload = SimpleUploadedFile('photo.jpg', big.getvalue(), content_type='image/jpeg')
		res = self.client.patch(f'/api/v1/stores/{self.store.id}/update/', {
			'logo': _image('logo.png'), 'banner_image': big_upload,
		}, format='multipart')
		self.assertEqual(res.status_code, 200, res.content)
		self.store.refresh_from_db()
		# Rien sur le disque : tout est dans la base
		self.assertEqual(os.listdir(settings.MEDIA_ROOT), [])
		self.assertEqual(StoredFile.objects.count(), 2)
		served = self.client.get(urlparse(self.store.logo.url).path)
		self.assertEqual(served.status_code, 200)
		self.assertEqual(served['Content-Type'], 'image/png')
		banner = StoredFile.objects.get(name=self.store.banner_image.name)
		self.assertLess(banner.size, len(big.getvalue()))
		self.assertLessEqual(max(Image.open(io.BytesIO(bytes(banner.content))).size), 1600)


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


class AdminProductFormTests(TestCase):
	"""Le formulaire produit de l'admin enregistre poids, taille et caractéristiques."""

	def setUp(self):
		self.admin = User.objects.create_superuser(phone='062300002', password='secret123', email='')
		manager = User.objects.create_user(phone='077000030', password='secret123', user_type='store_manager')
		category = StoreCategory.objects.create(name='Prêt-à-porter')
		self.store = Store.objects.create(
			name='Mode', category=category, manager=manager,
			phone='077000031', zone='Louis', address='Rue 1',
		)
		self.client = APIClient()
		self.client.force_authenticate(self.admin)

	def test_create_keeps_weight_length_and_attributes(self):
		res = self.client.post('/api/v1/admin/products/create/', {
			'name': 'T-shirt', 'store_id': self.store.id, 'price': '15000', 'stock': '10',
			'weight_kg': '0.1', 'length_m': '0.3',
			'attributes': {'brand': 'Nike', 'sizes': '40, 41', 'secret': 'x'},
		}, format='json')
		self.assertEqual(res.status_code, 201, res.content)
		product = self.store.products.get()
		self.assertEqual(str(product.weight_kg), '0.10')
		self.assertEqual(str(product.length_m), '0.30')
		self.assertEqual(product.attributes, {'brand': 'Nike', 'sizes': '40, 41'})

	def test_update_changes_specs(self):
		from products.models import Product
		product = Product.objects.create(name='Chaussure', store=self.store, price=20000, stock=1)
		res = self.client.patch(f'/api/v1/admin/products/{product.id}/update/', {
			'weight_kg': '0.8', 'length_m': '0.35', 'attributes': {'model': 'Air Max'},
		}, format='json')
		self.assertEqual(res.status_code, 200, res.content)
		product.refresh_from_db()
		self.assertEqual(str(product.weight_kg), '0.80')
		self.assertEqual(product.attributes, {'model': 'Air Max'})

	def test_create_reports_error_instead_of_hanging(self):
		res = self.client.post('/api/v1/admin/products/create/', {
			'name': 'Sans magasin', 'price': '1000',
		}, format='json')
		self.assertEqual(res.status_code, 400)
		self.assertIn('error', res.json())


@override_settings(
	AI_PROVIDER='local',
	CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class ShoppingAssistantTests(TestCase):
	"""L'assistant d'achat trouve de vrais produits, sans clé d'IA et sans être connecté."""

	def setUp(self):
		from products.models import Product
		manager = User.objects.create_user(phone='077000040', password='secret123', user_type='store_manager')
		self.store = Store.objects.create(
			name='Chez Paul', category=StoreCategory.objects.create(name='Mode'), manager=manager,
			phone='077000041', zone='Louis', address='Rue 1',
		)
		Product.objects.create(store=self.store, name='Baskets Nike Air', price=25000, stock=3,
			attributes={'brand': 'Nike', 'sizes': '40, 41, 42'})
		Product.objects.create(store=self.store, name='Baskets en toile', price=8000, stock=5)
		Product.objects.create(store=self.store, name='Riz parfumé 5 kg', price=4500, stock=10)
		self.client = APIClient()

	def ask(self, message):
		res = self.client.post('/api/v1/ai/shop/', {'message': message}, format='json')
		self.assertEqual(res.status_code, 200, res.content)
		return res.json()['data']

	def test_finds_products_with_budget(self):
		data = self.ask('Je cherche des baskets à moins de 10 000 F')
		self.assertEqual([p['name'] for p in data['products']], ['Baskets en toile'])
		self.assertIn('Chez Paul', data['message'])
		self.assertIn('8 000 FCFA', data['message'])
		self.assertEqual(data['provider'], 'local')

	def test_best_match_first(self):
		data = self.ask('baskets nike')
		self.assertEqual(data['products'][0]['name'], 'Baskets Nike Air')
		self.assertEqual(data['products'][0]['sizes'], '40, 41, 42')

	def test_small_questions(self):
		self.assertIn('Mobile Money', self.ask('Comment je paie ?')['message'])
		data = self.ask('Combien coûte la livraison ?')
		self.assertIn('livraison', data['message'].lower())
		self.assertEqual(data['products'], [])

	def test_nothing_found(self):
		data = self.ask('télévision samsung')
		self.assertEqual(data['products'], [])
		self.assertIn('aucun produit', data['message'].lower())

	@override_settings(AI_PROVIDER='groq', GROQ_API_KEY='test-key')
	def test_uses_free_ai_with_real_products_only(self):
		from unittest import mock
		with mock.patch('api.v1.ai.shopping.AIProvider.call_ai', return_value='Je vous conseille le riz parfumé.') as call:
			data = self.ask('du riz svp')
		self.assertEqual(data['provider'], 'groq')
		self.assertEqual(data['message'], 'Je vous conseille le riz parfumé.')
		self.assertIn('Riz parfumé 5 kg', call.call_args[0][1])


@override_settings(
	AI_PROVIDER='local',
	CACHES={'default': {'BACKEND': 'django.core.cache.backends.locmem.LocMemCache'}},
)
class AssistantTests(TestCase):
	"""L'assistant agit selon le rôle : client jusqu'au panier, commerce sur son stock, etc."""

	def setUp(self):
		from products.models import Product
		self.manager = User.objects.create_user(phone='077000050', password='secret123', user_type='store_manager')
		self.store = Store.objects.create(
			name='TestMag1', category=StoreCategory.objects.create(name='Mode'), manager=self.manager,
			phone='077000051', zone='Louis', address='Rue 1',
		)
		self.nike = Product.objects.create(store=self.store, name='Baskets', price=15000, stock=3,
			attributes={'brand': 'Nike', 'sizes': '40, 41'})
		self.adidas = Product.objects.create(store=self.store, name='Baskets', price=20000, stock=4,
			attributes={'brand': 'Adidas', 'sizes': '40, 42'})
		self.client_user = User.objects.create_user(phone='077000052', password='secret123', user_type='client')
		self.client = APIClient()

	def ask(self, message, user=None, **extra):
		self.client.force_authenticate(user)
		res = self.client.post('/api/v1/ai/assistant/', {'message': message, **extra}, format='json')
		self.assertEqual(res.status_code, 200, res.content)
		return res.json()['data']

	def test_small_talk_is_not_a_search(self):
		data = self.ask('comment vas tu ?')
		self.assertEqual(data['products'], [])
		self.assertIn('bien', data['message'])

	def test_brand_filters_results(self):
		data = self.ask('je cherche une basket adidas')
		self.assertEqual([p['id'] for p in data['products']], [self.adidas.id])

	def test_client_order_goes_to_cart(self):
		data = self.ask('commande moi 2 adidas de taille 40', user=self.client_user)
		add = [a for a in data['actions'] if a['type'] == 'add_to_cart']
		self.assertEqual(len(add), 1, data)
		self.assertEqual(add[0]['product']['id'], self.adidas.id)
		self.assertEqual(add[0]['quantity'], 2)
		self.assertEqual(add[0]['size'], '40')

	def test_visitor_is_asked_to_log_in(self):
		data = self.ask('ajoute la basket adidas au panier')
		self.assertEqual(data['actions'][0]['type'], 'login_required')

	def test_store_manager_summary_and_confirmed_update(self):
		from api.v1.ai.assistant import Ctx, t_update_product
		data = self.ask('résume ma boutique', user=self.manager)
		self.assertIn('TestMag1', data['message'])
		# La modification passe par une confirmation signée
		req = type('R', (), {'user': self.manager, 'build_absolute_uri': lambda self, x: x})()
		ctx = Ctx(req, 'store_manager', [])
		t_update_product(ctx, self.nike.id, stock=12)
		token = ctx.confirmations[0]['token']
		other = User.objects.create_user(phone='077000053', password='secret123', user_type='store_manager')
		self.client.force_authenticate(other)
		self.assertEqual(self.client.post('/api/v1/ai/assistant/confirm/', {'token': token}, format='json').status_code, 403)
		self.client.force_authenticate(self.manager)
		self.assertEqual(self.client.post('/api/v1/ai/assistant/confirm/', {'token': token}, format='json').status_code, 200)
		self.nike.refresh_from_db()
		self.assertEqual(self.nike.stock, 12)

	def test_tools_are_limited_by_role(self):
		from api.v1.ai.assistant import tools_for
		self.assertNotIn('update_product', tools_for('client'))
		self.assertNotIn('platform_stats', tools_for('store_manager'))
		self.assertIn('add_to_cart', tools_for('visitor'))

	@override_settings(AI_PROVIDER='groq', GROQ_API_KEY='test-key')
	def test_llm_agent_calls_tools(self):
		from unittest import mock
		from types import SimpleNamespace as NS

		def reply(tool_calls=None, content=None):
			return NS(choices=[NS(message=NS(tool_calls=tool_calls, content=content))])

		call = NS(id='c1', function=NS(name='add_to_cart', arguments=f'{{"product_id": {self.adidas.id}, "quantity": 1}}'))
		fake = mock.MagicMock()
		fake.chat.completions.create.side_effect = [reply([call]), reply(content='Ajouté à votre panier !')]
		with mock.patch('api.v1.ai.assistant._client', return_value=fake):
			data = self.ask('je prends les adidas', user=self.client_user)
		self.assertEqual(data['provider'], 'groq')
		self.assertEqual(data['actions'][0]['type'], 'add_to_cart')
		status = self.client.get('/api/v1/ai/assistant/status/').json()['data']
		self.assertTrue(status['key_present'])
		self.assertTrue(status['last_call']['ok'])

	@override_settings(AI_PROVIDER='groq', GROQ_API_KEY='bad-key')
	def test_llm_failure_falls_back_and_is_reported(self):
		from unittest import mock
		fake = mock.MagicMock()
		fake.chat.completions.create.side_effect = Exception('Error code: 401 - invalid api key')
		with mock.patch('api.v1.ai.assistant._client', return_value=fake):
			data = self.ask('bonjour')
		self.assertEqual(data['provider'], 'local')
		status = self.client.get('/api/v1/ai/assistant/status/').json()['data']
		self.assertFalse(status['last_call']['ok'])
		self.assertIn('invalid api key', status['last_call']['error'])


	@override_settings(AI_PROVIDER='groq', GROQ_API_KEY='test-key')
	def test_status_live_check(self):
		from unittest import mock
		from types import SimpleNamespace as NS
		from api.v1.ai import assistant
		assistant._LAST_STATUS.clear()
		fake = mock.MagicMock()
		fake.chat.completions.create.return_value = NS(choices=[NS(message=NS(content='OK'))])
		with mock.patch('api.v1.ai.assistant._client', return_value=fake):
			data = self.client.get('/api/v1/ai/assistant/status/?test=1').json()['data']
			self.assertTrue(data['test']['ok'])
			self.assertTrue(data['last_call']['ok'])
			again = self.client.get('/api/v1/ai/assistant/status/?test=1').json()['data']
		self.assertIn('skipped', again['test'])


	@override_settings(AI_PROVIDER='groq', GROQ_API_KEY='test-key')
	def test_failed_model_is_skipped_and_no_double_cart(self):
		from unittest import mock
		from types import SimpleNamespace as NS
		from api.v1.ai import assistant
		assistant._MODEL_STATE.update({'working': None, 'failed': {}})
		call = NS(id='c1', function=NS(name='add_to_cart', arguments=f'{{"product_id": {self.adidas.id}}}'))
		used = []

		def create(**kw):
			used.append(kw['model'])
			if kw['model'] != 'openai/gpt-oss-20b':
				if kw.get('messages', [{}])[-1].get('role') == 'tool':
					raise Exception('model_decommissioned')
				return NS(choices=[NS(message=NS(tool_calls=[call], content=None))])
			if kw['messages'][-1].get('role') == 'tool':
				return NS(choices=[NS(message=NS(tool_calls=None, content='Ajouté !'))])
			return NS(choices=[NS(message=NS(tool_calls=[call], content=None))])

		fake = mock.MagicMock()
		fake.chat.completions.create.side_effect = create
		with mock.patch('api.v1.ai.assistant._client', return_value=fake), \
				mock.patch('api.v1.ai.assistant.FALLBACK_MODELS', ['openai/gpt-oss-120b', 'openai/gpt-oss-20b']):
			data = self.ask('je prends les adidas', user=self.client_user)
			self.assertEqual(data['provider'], 'groq')
			self.assertEqual(len(data['actions']), 1)
			self.assertEqual(assistant._MODEL_STATE['working'], 'openai/gpt-oss-20b')
			used.clear()
			self.ask('et un autre', user=self.client_user)
		self.assertEqual(used[0], 'openai/gpt-oss-20b')
		assistant._MODEL_STATE.update({'working': None, 'failed': {}})

	def test_store_manager_creates_product_locally_with_confirmation(self):
		from products.models import Product
		from payments.models import SubscriptionPlan
		SubscriptionPlan.objects.get_or_create(plan_type='free', defaults={'name': 'Free', 'slug': 'free', 'price': 0})
		data = self.ask("je veux que tu fasses l'ajout de 10 all stars couleur noir", user=self.manager)
		self.assertIn('prix', data['message'])
		self.assertEqual(data['confirmations'], [])
		data = self.ask('ajoute 10 all stars noires à 25 000 F tailles 38 à 44', user=self.manager)
		self.assertEqual(len(data['confirmations']), 1, data)
		label = data['confirmations'][0]['label']
		self.assertIn('All Stars', label)
		self.assertIn('25 000 FCFA', label)
		token = data['confirmations'][0]['token']
		res = self.client.post('/api/v1/ai/assistant/confirm/', {'token': token}, format='json')
		self.assertEqual(res.status_code, 200, res.content)
		p = Product.objects.get(name='All Stars')
		self.assertEqual((p.stock, int(p.price), p.store_id), (10, 25000, self.store.id))
		self.assertEqual(p.attributes.get('color'), 'Noire')
		self.assertEqual(p.attributes.get('sizes'), '38-44')
		# Un double appui ne crée pas un deuxième produit
		again = self.client.post('/api/v1/ai/assistant/confirm/', {'token': token}, format='json')
		self.assertEqual(again.status_code, 400)
		self.assertEqual(Product.objects.filter(name='All Stars').count(), 1)

	def test_store_manager_moves_order_forward(self):
		from orders.models import Order
		from api.v1.ai.assistant import Ctx, t_set_order_status
		order = Order.objects.create(client=self.client_user, store=self.store, status='paid',
			delivery_address='Rue 2', delivery_phone='077000099', delivery_zone='Louis')
		req = type('R', (), {'user': self.manager, 'build_absolute_uri': lambda self, x: x})()
		ctx = Ctx(req, 'store_manager', [])
		self.assertIn('error', t_set_order_status(ctx, order.order_number, 'ready'))
		order.refresh_from_db()
		res0 = t_set_order_status(ctx, order.order_number, 'preparing')
		self.assertTrue(ctx.confirmations, (order.status, res0))
		token = ctx.confirmations[0]['token']
		self.client.force_authenticate(self.manager)
		res = self.client.post('/api/v1/ai/assistant/confirm/', {'token': token}, format='json')
		self.assertEqual(res.status_code, 200, res.content)
		order.refresh_from_db()
		self.assertEqual(order.status, 'preparing')
