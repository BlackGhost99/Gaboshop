"""Correctifs de sécurité du 15/10/2026 : mots de passe par défaut, droits admin, IP des limites,
clés API, jetons JWT, taille des envois, médias privés, justificatifs, fournisseurs, webhook WhatsApp,
force brute sur /admin/login/, limites IA."""
from unittest import mock

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import Http404
from django.test import RequestFactory, TestCase, override_settings
from rest_framework.request import Request
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from users.models import DeliveryAgentApiKey, User

PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 32


class AdminCreateGeneratedPasswordTests(TestCase):
	"""1. Plus de mot de passe par défaut (téléphone ou 123456) : un mot de passe aléatoire est renvoyé une fois."""

	def setUp(self):
		self.admin = User.objects.create_user(phone='077100001', password='secret123', user_type='admin', is_staff=True)
		self.api = APIClient()
		self.api.force_authenticate(self.admin)

	def test_admin_users_create_without_password(self):
		res = self.api.post('/api/v1/admin/users/', {'phone': '077100002', 'user_type': 'client'}, format='json')
		self.assertEqual(res.status_code, 201, res.content)
		generated = res.json()['data']['generated_password']
		self.assertEqual(len(generated), 10)
		user = User.objects.get(id=res.json()['data']['id'])
		self.assertTrue(user.check_password(generated))
		self.assertFalse(user.check_password('077100002'))
		self.assertFalse(user.check_password(user.phone))

	def test_admin_users_create_with_password_returns_nothing(self):
		res = self.api.post('/api/v1/admin/users/', {'phone': '077100003', 'password': 'Choisi123'}, format='json')
		self.assertEqual(res.status_code, 201, res.content)
		self.assertNotIn('generated_password', res.json()['data'])
		self.assertTrue(User.objects.get(id=res.json()['data']['id']).check_password('Choisi123'))

	def test_delivery_agent_create_without_password(self):
		res = self.api.post('/api/v1/delivery/agents/', {'phone': '077100004', 'first_name': 'Paul'}, format='json')
		self.assertEqual(res.status_code, 201, res.content)
		generated = res.json()['generated_password']
		user = User.objects.get(id=res.json()['id'])
		self.assertTrue(user.check_password(generated))
		self.assertFalse(user.check_password('123456'))
		# Plus jamais affiché ensuite
		self.assertNotIn('generated_password', self.api.get(f'/api/v1/delivery/agents/{user.id}/').json())

	def test_delivery_agent_blank_password_is_generated(self):
		res = self.api.post('/api/v1/delivery/agents/', {'phone': '077100005', 'password': ''}, format='json')
		self.assertEqual(res.status_code, 201, res.content)
		self.assertTrue(res.json()['generated_password'])


class DeliveryAgentPasswordUpdateTests(TestCase):
	"""2. Modifier le mot de passe d'un livreur le hache (plus jamais en clair)."""

	def test_update_hashes_password(self):
		admin = User.objects.create_user(phone='077100010', password='secret123', user_type='admin', is_staff=True)
		agent = User.objects.create_user(phone='077100011', password='ancien123', user_type='delivery_agent')
		api = APIClient()
		api.force_authenticate(admin)
		res = api.patch(f'/api/v1/delivery/agents/{agent.id}/', {'password': 'Nouveau456'}, format='json')
		self.assertEqual(res.status_code, 200, res.content)
		agent.refresh_from_db()
		self.assertNotEqual(agent.password, 'Nouveau456')
		self.assertTrue(agent.check_password('Nouveau456'))


class AdminCannotTouchSuperuserTests(TestCase):
	"""3. Un admin non superutilisateur ne modifie ni ne supprime un superutilisateur ; booléens bien lus."""

	def setUp(self):
		self.admin = User.objects.create_user(phone='077100020', password='secret123', user_type='admin', is_staff=True)
		self.root = User.objects.create_superuser(phone='077100021', password='secret123', email='')
		self.client_user = User.objects.create_user(phone='077100022', password='secret123')
		self.api = APIClient()
		self.api.force_authenticate(self.admin)

	def test_patch_superuser_forbidden(self):
		res = self.api.patch('/api/v1/admin/users/', {'id': self.root.id, 'password': 'pirate123'}, format='json')
		self.assertEqual(res.status_code, 403)
		self.root.refresh_from_db()
		self.assertTrue(self.root.check_password('secret123'))

	def test_delete_superuser_forbidden(self):
		res = self.api.delete('/api/v1/admin/users/', {'id': self.root.id}, format='json')
		self.assertEqual(res.status_code, 403)
		self.assertTrue(User.objects.filter(id=self.root.id).exists())

	def test_superuser_can_manage_superuser(self):
		other = User.objects.create_superuser(phone='077100023', password='secret123', email='')
		api = APIClient()
		api.force_authenticate(self.root)
		self.assertEqual(api.patch('/api/v1/admin/users/', {'id': other.id, 'first_name': 'Chef'}, format='json').status_code, 200)

	def test_string_booleans(self):
		res = self.api.patch('/api/v1/admin/users/', {'id': self.client_user.id, 'is_active': 'false', 'is_verified': '0'}, format='json')
		self.assertEqual(res.status_code, 200, res.content)
		self.client_user.refresh_from_db()
		self.assertFalse(self.client_user.is_active)
		self.assertFalse(self.client_user.is_verified)
		self.api.patch('/api/v1/admin/users/', {'id': self.client_user.id, 'is_active': 'true'}, format='json')
		self.client_user.refresh_from_db()
		self.assertTrue(self.client_user.is_active)


class ClientIPTests(TestCase):
	"""4. L'IP des limites ne se falsifie plus avec un X-Forwarded-For inventé."""

	def setUp(self):
		self.rf = RequestFactory()

	def test_cloudflare_header_first(self):
		from users.throttles import client_ip
		req = self.rf.get('/', HTTP_CF_CONNECTING_IP='41.158.1.1', HTTP_X_FORWARDED_FOR='1.1.1.1, 2.2.2.2', REMOTE_ADDR='10.0.0.1')
		self.assertEqual(client_ip(req), '41.158.1.1')

	def test_last_forwarded_entry(self):
		from users.throttles import client_ip
		req = self.rf.get('/', HTTP_X_FORWARDED_FOR='6.6.6.6, 41.158.2.2', REMOTE_ADDR='10.0.0.1')
		self.assertEqual(client_ip(req), '41.158.2.2')

	def test_remote_addr_fallback(self):
		from users.throttles import client_ip
		self.assertEqual(client_ip(self.rf.get('/', REMOTE_ADDR='10.0.0.9')), '10.0.0.9')

	def test_throttles_use_client_ip(self):
		from api.v1.ai.shopping import ShopAnonThrottle
		from users.throttles import AuthIPThrottle
		req = Request(self.rf.get('/', HTTP_X_FORWARDED_FOR='6.6.6.6, 41.158.3.3'))
		self.assertEqual(AuthIPThrottle().get_ident(req), '41.158.3.3')
		self.assertEqual(ShopAnonThrottle().get_ident(req), '41.158.3.3')


class ApiKeyInactiveUserTests(TestCase):
	"""5. La clé API d'un compte désactivé est refusée."""

	def test_inactive_user_key_rejected(self):
		from rest_framework.exceptions import AuthenticationFailed
		from users.authentication import ApiKeyAuthentication
		agent = User.objects.create_user(phone='077100030', password='secret123', user_type='delivery_agent')
		key = DeliveryAgentApiKey.create_for_user(agent).key
		req = Request(RequestFactory().get('/', HTTP_X_API_KEY=key))
		self.assertEqual(ApiKeyAuthentication().authenticate(req)[0], agent)
		agent.is_active = False
		agent.save()
		with self.assertRaises(AuthenticationFailed):
			ApiKeyAuthentication().authenticate(Request(RequestFactory().get('/', HTTP_X_API_KEY=key)))


class PasswordResetRevokesTokensTests(TestCase):
	"""6. Après « mot de passe oublié », les anciennes sessions ne peuvent plus se rafraîchir."""

	def test_refresh_token_blacklisted_after_reset(self):
		from users.password_reset import reset_password
		user = User.objects.create_user(phone='077100040', password='secret123')
		refresh = str(RefreshToken.for_user(user))
		api = APIClient()
		self.assertEqual(api.post('/api/v1/auth/token/refresh/', {'refresh': refresh}, format='json').status_code, 200)
		# Avec la rotation, le jeton utilisé est déjà en liste noire : on en prend un neuf.
		refresh = str(RefreshToken.for_user(user))
		with mock.patch('users.password_reset._check_code', return_value=(True, '')):
			ok, _ = reset_password(user.phone, '000000', 'NouveauMdp789')
		self.assertTrue(ok)
		self.assertEqual(api.post('/api/v1/auth/token/refresh/', {'refresh': refresh}, format='json').status_code, 401)


class UploadSizeMiddlewareTests(TestCase):
	"""7. Un envoi de plus de 15 Mo est refusé (413) avant d'être lu."""

	def test_too_large_request_rejected(self):
		res = self.client.post('/api/v1/auth/login/', data='{}', content_type='application/json', CONTENT_LENGTH=str(16 * 1024 * 1024))
		self.assertEqual(res.status_code, 413)
		self.assertIn('15 Mo', res.json()['error']['message'])

	def test_normal_request_passes(self):
		res = self.client.post('/api/v1/auth/login/', data='{}', content_type='application/json')
		self.assertNotEqual(res.status_code, 413)


class MediaPathNormalisationTests(TestCase):
	"""8. « ./delivery_proofs/… » ou « //delivery_proofs/… » ne contournent plus le préfixe privé."""

	def setUp(self):
		from core.models import StoredFile
		StoredFile.objects.create(name='delivery_proofs/photos/secret.png', content=PNG, content_type='image/png', size=len(PNG))
		StoredFile.objects.create(name='logos/public.png', content=PNG, content_type='image/png', size=len(PNG))
		self.rf = RequestFactory()

	def _serve(self, path):
		from core.media_views import serve_media
		return serve_media(self.rf.get('/media/' + path), path)

	def test_private_variants_blocked(self):
		for path in ('delivery_proofs/photos/secret.png', './delivery_proofs/photos/secret.png',
					 '/delivery_proofs/photos/secret.png', 'delivery_proofs/./photos/secret.png',
					 'logos/../delivery_proofs/photos/secret.png', './/delivery_proofs/photos/secret.png'):
			with self.subTest(path=path), self.assertRaises(Http404):
				self._serve(path)

	def test_public_file_still_served(self):
		self.assertEqual(self._serve('logos/public.png').status_code, 200)
		self.assertEqual(self._serve('./logos/public.png').status_code, 200)


class ProofFileValidatorTests(TestCase):
	"""9. Justificatifs : photo ou PDF, 5 Mo au plus, contenu vérifié."""

	def test_accepts_png_and_pdf(self):
		from core.validators import validate_proof_file
		validate_proof_file(SimpleUploadedFile('recu.png', PNG, content_type='image/png'))
		validate_proof_file(SimpleUploadedFile('recu.pdf', b'%PDF-1.4\n...', content_type='application/pdf'))

	def test_rejects_bad_extension_content_or_size(self):
		from core.validators import validate_proof_file
		for f in (
			SimpleUploadedFile('page.html', b'<script>alert(1)</script>', content_type='text/html'),
			SimpleUploadedFile('faux.png', b'<svg onload=alert(1)>', content_type='image/png'),
			SimpleUploadedFile('gros.pdf', b'%PDF-' + b'0' * (5 * 1024 * 1024), content_type='application/pdf'),
		):
			with self.subTest(name=f.name), self.assertRaises(ValidationError):
				validate_proof_file(f)


class ExpenseSupplierOwnershipTests(TestCase):
	"""10. Une dépense ne peut pas viser le fournisseur d'un autre commerce."""

	def setUp(self):
		from finance.models import Supplier
		from stores.models import Store, StoreCategory
		category = StoreCategory.objects.create(name='Épicerie')
		self.manager = User.objects.create_user(phone='077100050', password='secret123', user_type='store_manager')
		other = User.objects.create_user(phone='077100051', password='secret123', user_type='store_manager')
		self.store = Store.objects.create(is_verified=True, name='Mag A', category=category, manager=self.manager, phone='077100052', zone='Louis', address='Rue 1')
		other_store = Store.objects.create(is_verified=True, name='Mag B', category=category, manager=other, phone='077100053', zone='Louis', address='Rue 2')
		self.mine = Supplier.objects.create(store=self.store, name='Mon fournisseur')
		self.foreign = Supplier.objects.create(store=other_store, name='Fournisseur de B')
		self.api = APIClient()
		self.api.force_authenticate(self.manager)

	def _payload(self, supplier):
		return {'expense_type': 'OTHER', 'supplier': supplier.id, 'amount': '1500.00', 'expense_date': '2026-10-15', 'payment_method': 'CASH'}

	def test_serializer_rejects_foreign_supplier(self):
		from finance.serializers import ExpenseSerializer
		request = mock.Mock(user=self.manager)
		ser = ExpenseSerializer(data=self._payload(self.foreign), context={'request': request})
		self.assertFalse(ser.is_valid())
		self.assertIn('supplier', ser.errors)

	def test_serializer_accepts_own_supplier(self):
		from finance.serializers import ExpenseSerializer
		from finance.models import Expense
		valid_types = [c[0] for c in Expense._meta.get_field('expense_type').choices]
		valid_methods = [c[0] for c in Expense._meta.get_field('payment_method').choices]
		payload = dict(self._payload(self.mine), expense_type=valid_types[0], payment_method=valid_methods[0])
		ser = ExpenseSerializer(data=payload, context={'request': mock.Mock(user=self.manager)})
		self.assertTrue(ser.is_valid(), ser.errors)


class WhatsAppWebhookHardeningTests(TestCase):
	"""11. Sans clé ni jeton configurés, le webhook WhatsApp refuse tout."""
	URL = '/api/v1/webhooks/whatsapp/'

	@override_settings(WHATSAPP_APP_SECRET='')
	def test_post_refused_without_app_secret(self):
		res = APIClient().post(self.URL, b'{"entry": []}', content_type='application/json')
		self.assertEqual(res.status_code, 403)

	@override_settings(WHATSAPP_VERIFY_TOKEN='')
	def test_verify_refused_without_token(self):
		res = APIClient().get(self.URL, {'hub.mode': 'subscribe', 'hub.challenge': '123'})
		self.assertEqual(res.status_code, 403)
		res = APIClient().get(self.URL, {'hub.verify_token': '', 'hub.challenge': '123'})
		self.assertEqual(res.status_code, 403)

	def test_default_verify_token_is_empty(self):
		from pathlib import Path
		source = (Path(__file__).resolve().parents[2] / 'settings.py').read_text(encoding='utf-8')
		self.assertIn("WHATSAPP_VERIFY_TOKEN = env('WHATSAPP_VERIFY_TOKEN', default='')", source)


class AdminLoginBruteForceTests(TestCase):
	"""12. /admin/login/ : après 10 échecs (par IP ou par identifiant) en 15 min, 429."""

	def setUp(self):
		cache.clear()
		self.addCleanup(cache.clear)

	def _attempt(self, username, password='mauvais', ip='41.158.9.9'):
		return self.client.post('/admin/login/', {'username': username, 'password': password}, REMOTE_ADDR=ip)

	def test_blocked_after_ten_failures_per_ip(self):
		for i in range(10):
			self.assertEqual(self._attempt(f'07710{i:04d}').status_code, 200)
		self.assertEqual(self._attempt('077109999').status_code, 429)
		# Une autre IP avec un autre identifiant passe encore
		self.assertEqual(self._attempt('077108888', ip='41.158.9.10').status_code, 200)

	def test_blocked_after_ten_failures_per_username(self):
		for i in range(10):
			self._attempt('077100060', ip=f'41.158.10.{i}')
		self.assertEqual(self._attempt('077100060', ip='41.158.10.200').status_code, 429)

	def test_cache_error_lets_through(self):
		with mock.patch('core.middleware_admin_login.cache.get_many', side_effect=RuntimeError('redis HS')):
			self.assertEqual(self._attempt('077100061').status_code, 200)

	def test_success_redirects(self):
		User.objects.create_superuser(phone='077100062', password='secret123', email='')
		user = User.objects.get(is_superuser=True)
		res = self.client.post('/admin/login/', {'username': getattr(user, User.USERNAME_FIELD), 'password': 'secret123'}, REMOTE_ADDR='41.158.11.1')
		self.assertEqual(res.status_code, 302)


class AIThrottleTests(TestCase):
	"""13. ai_chat et prepare_order sont limités par utilisateur."""

	def test_throttle_classes(self):
		from api.v1.ai.actions import prepare_order
		from api.v1.ai.gateway import ai_chat
		from api.v1.ai.shopping import ShopUserThrottle
		self.assertIn(ShopUserThrottle, ai_chat.cls.throttle_classes)
		self.assertIn(ShopUserThrottle, prepare_order.cls.throttle_classes)
