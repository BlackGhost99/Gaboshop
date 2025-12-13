from django.test import TestCase
from rest_framework.test import APIClient
from users.models import User


class UserEdgeCaseTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/v1/auth/register/'
        self.login_url = '/api/v1/auth/login/'

    def test_inactive_account_cannot_login(self):
        # Create inactive user
        user = User.objects.create_user(phone='+2417770000', password='pass1234', user_type='client')
        user.is_active = False
        user.save()

        resp = self.client.post(self.login_url, {'phone': '07770000', 'password': 'pass1234'}, format='json')
        # Login should fail (401)
        self.assertEqual(resp.status_code, 401)

    def test_duplicate_email_registration_is_blocked(self):
        # First registration with an email
        payload1 = {
            'phone': '07000001',
            'password': 'secret123',
            'password_confirm': 'secret123',
            'user_type': 'client',
            'email': 'dup@example.com'
        }
        r1 = self.client.post(self.register_url, payload1, format='json')
        self.assertEqual(r1.status_code, 201)

        # Second registration with a different phone but same email should be rejected
        payload2 = {
            'phone': '07000002',
            'password': 'secret123',
            'password_confirm': 'secret123',
            'user_type': 'client',
            'email': 'dup@example.com'
        }
        r2 = self.client.post(self.register_url, payload2, format='json')
        self.assertEqual(r2.status_code, 400)

    def test_password_reset_via_set_password_allows_login(self):
        # Create user and then reset password via model (simulate reset flow)
        user = User.objects.create_user(phone='+2417000003', password='oldpass', user_type='client')
        user.set_password('newpass123')
        user.save()

        resp = self.client.post(self.login_url, {'phone': '07000003', 'password': 'newpass123'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('data', resp.data)
        self.assertIn('tokens', resp.data['data'])
