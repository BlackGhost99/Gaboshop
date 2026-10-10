import re
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from users.models import PasswordResetCode, User

URL = '/api/v1/auth/password-reset/'
CONFIRM = '/api/v1/auth/password-reset/confirm/'


@override_settings(HUB2SMS_API_KEY='test-key', EMAIL_HOST_USER='')
class PasswordResetTests(TestCase):
	def setUp(self):
		cache.clear()
		self.api = APIClient()
		self.user = User.objects.create_user(phone='+24177111111', password='ancien123', user_type='client')

	def _request_code(self, phone='077111111'):
		with mock.patch('users.password_reset.SMSService.send_sms', return_value=True) as sms:
			res = self.api.post(URL, {'phone': phone}, format='json')
		self.assertEqual(res.status_code, 200, res.content)
		return sms

	def test_code_by_sms_then_new_password_works(self):
		sms = self._request_code()
		sms.assert_called_once()
		code = re.search(r'\b(\d{6})\b', sms.call_args[0][1]).group(1)
		self.assertNotIn(code, PasswordResetCode.objects.get().code_hash)
		res = self.api.post(CONFIRM, {'phone': '+24177111111', 'code': code, 'password': 'nouveau123'}, format='json')
		self.assertEqual(res.status_code, 200, res.content)
		login = APIClient().post('/api/v1/auth/login/', {'phone': '077111111', 'password': 'nouveau123'}, format='json')
		self.assertEqual(login.status_code, 200, login.content)
		again = self.api.post(CONFIRM, {'phone': '+24177111111', 'code': code, 'password': 'autre1234'}, format='json')
		self.assertEqual(again.status_code, 400)

	def test_unknown_number_gets_same_answer_and_no_sms(self):
		sms = self._request_code('066999999')
		sms.assert_not_called()
		self.assertFalse(PasswordResetCode.objects.exists())

	def test_wrong_codes_lock_the_code(self):
		sms = self._request_code()
		code = re.search(r'\b(\d{6})\b', sms.call_args[0][1]).group(1)
		wrong = '000000' if code != '000000' else '111111'
		for _ in range(5):
			self.assertEqual(self.api.post(CONFIRM, {'phone': '077111111', 'code': wrong, 'password': 'nouveau123'}, format='json').status_code, 400)
		cache.clear()
		res = self.api.post(CONFIRM, {'phone': '077111111', 'code': code, 'password': 'nouveau123'}, format='json')
		self.assertEqual(res.status_code, 400)
		self.user.refresh_from_db()
		self.assertTrue(self.user.check_password('ancien123'))

	def test_short_password_refused(self):
		res = self.api.post(CONFIRM, {'phone': '077111111', 'code': '123456', 'password': '123'}, format='json')
		self.assertEqual(res.status_code, 400)


@override_settings(HUB2SMS_API_KEY='', TWILIO_ACCOUNT_SID='', TWILIO_AUTH_TOKEN='', EMAIL_HOST_USER='')
class PasswordResetWithoutSmsTests(TestCase):
	def test_no_fake_code_without_sms_provider(self):
		cache.clear()
		User.objects.create_user(phone='+24177222222', password='ancien123', user_type='client')
		api = APIClient()
		self.assertFalse(api.get(URL).json()['data']['sms_available'])
		with mock.patch('users.password_reset.SMSService.send_sms') as sms:
			self.assertEqual(api.post(URL, {'phone': '077222222'}, format='json').status_code, 200)
		sms.assert_not_called()
		self.assertFalse(PasswordResetCode.objects.exists())
