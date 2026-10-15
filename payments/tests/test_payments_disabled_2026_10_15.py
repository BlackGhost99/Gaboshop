"""Site de test sans paiement (PAYMENTS_DISABLED) : SingPay n'est jamais appelé."""
from unittest import mock

from django.test import TestCase, override_settings

from api.models import SystemSettings
from payments.configuration import DEFAULT_PAYMENT_POLICY, get_payment_policy, platform_online_ready
from payments.utils import call_airtel_money_init

KEYS = dict(SINGPAY_CLIENT_ID='id', SINGPAY_CLIENT_SECRET='secret', SINGPAY_WALLET_ID='wallet',
            SINGPAY_BASE_URL='https://gateway.singpay.ga/v1')


@override_settings(PAYMENTS_DISABLED=True, **KEYS)
class PaymentsDisabledTests(TestCase):
    def test_no_online_payment_even_with_keys(self):
        self.assertFalse(platform_online_ready())

    def test_singpay_is_never_called(self):
        with mock.patch('payments.utils.requests.request') as http:
            response = call_airtel_money_init(phone='077000000', amount=100, reference='REF1', metadata={})
        http.assert_not_called()
        self.assertTrue(response.get('error'))

    def test_saved_online_policy_does_not_break_the_site(self):
        s = SystemSettings.get_settings()
        s.payment_policy = {**DEFAULT_PAYMENT_POLICY, 'enabled_flows': ['platform_online', 'direct_split'],
                            'default_flow': 'platform_online'}
        s.save()
        policy = get_payment_policy()
        self.assertNotIn('platform_online', policy['enabled_flows'])
        self.assertEqual(policy['default_flow'], 'direct_split')


@override_settings(PAYMENTS_DISABLED=False, **KEYS)
class PaymentsEnabledTests(TestCase):
    def test_online_ready_with_keys(self):
        self.assertTrue(platform_online_ready())
