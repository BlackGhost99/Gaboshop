import hashlib
import hmac
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from users.models import User


@override_settings(WHATSAPP_ACCESS_TOKEN='t', WHATSAPP_PHONE_ID='1', HUB2SMS_API_KEY='', TWILIO_ACCOUNT_SID='', EMAIL_HOST_USER='')
class PhoneVerificationTests(TestCase):
	def setUp(self):
		cache.clear()
		self.user = User.objects.create_user(phone='+24177444444', password='secret123', user_type='client')
		self.api = APIClient()
		self.api.force_authenticate(self.user)

	def test_optional_code_marks_number_verified(self):
		self.assertFalse(self.api.get('/api/v1/auth/profile/').json()['data']['phone_verified'])
		with mock.patch('notifications.whatsapp.WhatsAppService.send_template_message', return_value=True) as wa:
			self.assertEqual(self.api.post('/api/v1/auth/phone/verify/').status_code, 200)
		code = wa.call_args[0][2][0]['parameters'][0]['text']
		bad = self.api.post('/api/v1/auth/phone/verify/confirm/', {'code': '000000' if code != '000000' else '111111'}, format='json')
		self.assertEqual(bad.status_code, 400)
		ok = self.api.post('/api/v1/auth/phone/verify/confirm/', {'code': code}, format='json')
		self.assertEqual(ok.status_code, 200, ok.content)
		self.assertTrue(self.api.get('/api/v1/auth/profile/').json()['data']['phone_verified'])

	def test_reset_code_cannot_verify_phone(self):
		with mock.patch('notifications.whatsapp.WhatsAppService.send_template_message', return_value=True) as wa:
			APIClient().post('/api/v1/auth/password-reset/', {'phone': '077444444'}, format='json')
		code = wa.call_args[0][2][0]['parameters'][0]['text']
		self.assertEqual(self.api.post('/api/v1/auth/phone/verify/confirm/', {'code': code}, format='json').status_code, 400)


class WhatsAppWebhookTests(TestCase):
	URL = '/api/v1/webhooks/whatsapp/'

	@override_settings(WHATSAPP_VERIFY_TOKEN='mot-secret')
	def test_meta_verification_works_without_login(self):
		res = APIClient().get(self.URL, {'hub.mode': 'subscribe', 'hub.verify_token': 'mot-secret', 'hub.challenge': '12345'})
		self.assertEqual((res.status_code, res.content), (200, b'12345'))
		self.assertEqual(APIClient().get(self.URL, {'hub.verify_token': 'faux', 'hub.challenge': '1'}).status_code, 403)

	@override_settings(WHATSAPP_APP_SECRET='cle')
	def test_events_need_meta_signature(self):
		body = b'{"entry": []}'
		self.assertEqual(APIClient().post(self.URL, body, content_type='application/json').status_code, 403)
		sig = 'sha256=' + hmac.new(b'cle', body, hashlib.sha256).hexdigest()
		res = APIClient().post(self.URL, body, content_type='application/json', HTTP_X_HUB_SIGNATURE_256=sig)
		self.assertEqual(res.status_code, 200)
