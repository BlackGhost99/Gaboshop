"""Connexion et inscription : messages clairs, essais restants, blocage annoncé (15 oct. 2026)."""
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from notifications.models import Notification
from users.models import User


class LoginMessageTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(phone='+24177600101', password='bon-mot-de-passe', user_type='client')
        self.admin = User.objects.create_user(phone='+24107600109', password='x', user_type='admin', is_staff=True)
        self.api = APIClient()

    def login(self, password='faux', phone='077600101'):
        return self.api.post('/api/v1/auth/login/', {'phone': phone, 'password': password}, format='json')

    def test_wrong_password_says_how_many_tries_are_left(self):
        res = self.login()
        self.assertEqual(res.status_code, 401)
        error = res.json()['error']
        self.assertIn('mot de passe incorrect', error['message'])
        self.assertEqual(error['attempts_left'], 9)
        self.assertIn('9 essais', error['reason'])

    def test_lockout_is_announced_to_the_user_owner_and_admin(self):
        for _ in range(10):
            res = self.login()
        self.assertEqual(res.json()['error']['attempts_left'], 0)
        res = self.login(password='bon-mot-de-passe')  # même le bon mot de passe attend la fin du blocage
        self.assertEqual(res.status_code, 429)
        error = res.json()['error']
        self.assertTrue(error['locked'])
        self.assertIn('Connexion bloquée', error['message'])
        self.assertIn('mots de passe faux', error['reason'])
        self.assertTrue(Notification.objects.filter(user=self.user, title__startswith='Connexion bloquée').exists())
        self.assertTrue(Notification.objects.filter(user=self.admin, title__startswith='Connexion bloquée').exists())

    def test_good_password_works(self):
        self.assertEqual(self.login(password='bon-mot-de-passe').status_code, 200)


class RegisterMessageTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_duplicate_number_is_explained(self):
        api = APIClient()
        payload = {'phone': '077600201', 'password': 'Mapeto88x', 'password_confirm': 'Mapeto88x',
                   'user_type': 'client'}
        self.assertEqual(api.post('/api/v1/auth/register/', payload, format='json').status_code, 201)
        res = api.post('/api/v1/auth/register/', dict(payload, phone='+24177600201'), format='json')
        self.assertEqual(res.status_code, 400)
        error = res.json()['error']
        self.assertIn('Inscription impossible', error['message'])
        self.assertIn('déjà un compte', str(error['details']['phone']))


class LoginPhoneFormTests(TestCase):
    def test_number_stored_with_the_zero_still_logs_in(self):
        cache.clear()
        User.objects.create_user(phone='+241077600301', password='bon-mot-de-passe', user_type='client')
        res = APIClient().post('/api/v1/auth/login/', {'phone': '077600301', 'password': 'bon-mot-de-passe'}, format='json')
        self.assertEqual(res.status_code, 200)
