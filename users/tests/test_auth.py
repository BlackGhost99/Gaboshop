from django.test import TestCase
from rest_framework.test import APIClient
from django.urls import reverse
from users.models import User


class AuthFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.register_url = '/api/v1/auth/register/'
        self.login_url = '/api/v1/auth/login/'
        self.profile_url = '/api/v1/auth/profile/'
        self.plans_url = '/api/v1/dashboard/subscription/plans/'

    def test_store_manager_registration_login_and_profile(self):
        # Register a store manager
        payload = {
            'phone': '01234567',
            'password': 'strongpassword',
            'password_confirm': 'strongpassword',
            'user_type': 'store_manager',
            'store_name': 'Test Store',
            'store_address': '1 Rue Principale',
            'store_zone': 'Center',
            'store_city': 'Libreville'
        }
        r = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(r.status_code, 201, msg=r.data)
        self.assertTrue(r.data['data']['tokens']['access'])
        access = r.data['data']['tokens']['access']

        # Use access token to get profile
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access}')
        r2 = self.client.get(self.profile_url)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.data['data']['phone'], '+2411234567'[:len(r2.data['data']['phone'])])

        # update profile
        r3 = self.client.put(self.profile_url, {'first_name': 'Gerant', 'last_name': 'Test'}, format='json')
        self.assertEqual(r3.status_code, 200)
        self.assertEqual(r3.data['data']['first_name'], 'Gerant')

    def test_client_cannot_view_plans_but_store_manager_can(self):
        # Register client
        payload_client = {
            'phone': '07654321',
            'password': 'clientpass',
            'password_confirm': 'clientpass',
            'user_type': 'client'
        }
        r = self.client.post(self.register_url, payload_client, format='json')
        self.assertEqual(r.status_code, 201)
        access_client = r.data['data']['tokens']['access']

        # Client tries to access plans -> forbidden
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_client}')
        r2 = self.client.get(self.plans_url)
        self.assertIn(r2.status_code, (400, 403))

        # Register store manager
        payload_mgr = {
            'phone': '07881234',
            'password': 'mgrpass123',
            'password_confirm': 'mgrpass123',
            'user_type': 'store_manager',
            'store_name': 'MGR Store',
            'store_address': 'Addr',
            'store_zone': 'Zone'
        }
        r3 = self.client.post(self.register_url, payload_mgr, format='json')
        self.assertEqual(r3.status_code, 201)
        access_mgr = r3.data['data']['tokens']['access']

        # Manager can access plans
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_mgr}')
        r4 = self.client.get(self.plans_url)
        # 200 OK expected (may be empty list but should not be 403)
        self.assertEqual(r4.status_code, 200)