"""Un commerce active un plan payant (Pro) : paiement Mobile Money, simulé sur le site de test."""
from datetime import time
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from payments import singpay_simulator
from payments.models import PaymentIntent, SubscriptionPlan
from stores.models import Store, StoreCategory
from users.models import User

LATER = singpay_simulator.SIMULATED_DELAY_SECONDS + 1


def later(seconds=LATER):
    real = singpay_simulator.time.time
    return mock.patch('payments.singpay_simulator.time.time', side_effect=lambda: real() + seconds)


@override_settings(PAYMENTS_SIMULATED=True, PAYMENTS_DISABLED=False,
                   SINGPAY_CLIENT_ID='', SINGPAY_CLIENT_SECRET='', SINGPAY_WALLET_ID='')
class AbonnementPlanTests(TestCase):
    def setUp(self):
        cache.clear()
        self.manager = User.objects.create_user(phone='+24107600101', password='Mapeto88x', user_type='store_manager')
        category = StoreCategory.objects.create(name='Abonnement test')
        self.store = Store.objects.create(
            is_verified=True, name='Boutique abonnement', category=category, manager=self.manager,
            phone='+24107600110', address='Libreville', zone='Centre', commission_rate=Decimal('5'),
            opening_time=time(0, 0), closing_time=time(23, 59))
        self.pro = SubscriptionPlan.objects.get(plan_type='pro')
        self.api = APIClient()
        self.api.force_authenticate(self.manager)
        http = mock.patch('payments.utils.requests.request', side_effect=AssertionError('appel réseau'))
        http.start()
        self.addCleanup(http.stop)

    def subscribe(self, **extra):
        body = {'plan_id': self.pro.id, 'provider': 'airtel', 'phone_number': '077600101', **extra}
        return self.api.post('/api/v1/payments/subscriptions/intent/', body, format='json')

    def current_plan(self):
        cache.clear()
        return self.api.get('/api/v1/payments/subscription-plans/').json()['current_plan']['plan_type']

    def test_pro_plan_is_activated_after_the_simulated_payment(self):
        self.assertEqual(self.current_plan(), 'free')
        res = self.subscribe()
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(self.current_plan(), 'free')  # le client n'a pas encore tapé son code
        with later():
            self.assertEqual(self.current_plan(), 'pro')
        self.assertEqual(PaymentIntent.objects.get().status, 'SUCCESS')

    def test_refusal_explains_why_when_payments_are_cut(self):
        with override_settings(PAYMENTS_DISABLED=True):
            res = self.subscribe()
            self.assertEqual(res.status_code, 400, res.content)
            error = res.json()['error']
            self.assertEqual(error['code'], 'payment_init_disabled')
            self.assertIn('coupés', error['reason'])
            self.assertTrue(error['next_step'])
            self.assertIn('coupés', res.json()['detail'])
            self.assertEqual(self.api.get('/api/v1/health/').json()['data']['payments_mode'], 'disabled')
        self.assertEqual(PaymentIntent.objects.get().status, 'FAILED')

    def test_refusal_explains_why_when_keys_are_missing(self):
        with override_settings(PAYMENTS_SIMULATED=False, SINGPAY_BASE_URL='https://example.invalid'):
            res = self.subscribe()
            self.assertEqual(res.status_code, 400, res.content)
            self.assertEqual(res.json()['error']['code'], 'payment_init_not_configured')
            self.assertIn('clés SingPay', res.json()['error']['reason'])
            self.assertEqual(self.api.get('/api/v1/health/').json()['data']['payments_mode'], 'not_configured')

    def test_health_reports_the_simulation(self):
        self.assertEqual(self.api.get('/api/v1/health/').json()['data']['payments_mode'], 'simulated')

    def test_number_refused_by_the_operator_is_explained(self):
        refusal = {'error': 'SingPay HTTP 400', 'response': {'message': 'Invalid msisdn'}}
        with mock.patch('payments.views.call_airtel_money_init', return_value=refusal):
            res = self.subscribe()
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()['error']['failure_code'], 'number')
