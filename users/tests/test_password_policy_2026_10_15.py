"""Mots de passe trop faibles refusés, avec la raison en français (15 oct. 2026)."""
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from users.password_policy import password_problem


class PolicyTests(SimpleTestCase):
    def test_weak_passwords_are_refused(self):
        for weak in ('123456789', '12345678', 'abcd1234', 'aaaa1111', 'azerty123', 'password1', 'motdepasse',
                     'court1', 'Gaboshop2025'):
            self.assertTrue(password_problem(weak, '+24177600101'), weak)

    def test_phone_inside_is_refused(self):
        self.assertIn('numéro', password_problem('x77600101', '+24177600101'))

    def test_good_passwords_pass(self):
        for good in ('Mapeto88', 'soleil2024', 'k7Pm2qXw', 'Brice77!x'):
            self.assertEqual(password_problem(good, '+24177600101'), '', good)


class RegisterPolicyTests(TestCase):
    def test_register_refuses_123456789_with_a_clear_reason(self):
        cache.clear()
        res = APIClient().post('/api/v1/auth/register/', {
            'phone': '077600401', 'password': '123456789', 'password_confirm': '123456789', 'user_type': 'client',
        }, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('lettre et un chiffre', str(res.json()['error']['details']['password']))
