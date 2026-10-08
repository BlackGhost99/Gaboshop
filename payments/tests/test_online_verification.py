import json
from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient, APIRequestFactory

from api.v1.payments import PaymentWebhookView
from orders.models import Order
from payments.models import Payment, PaymentIntent
from payments.online_verification import read_singpay_status
from payments.views import ProviderCallbackAPIView
from stores.models import Store, StoreCategory
from users.models import User

STATUS_CALL = 'payments.online_verification.call_singpay_status'


def singpay_answer(result=None, step='Terminate', amount=12500, reference='GABOSHOP_CMD-TEST'):
    tx = {'id': 'SP-TX-1', 'status': step, 'amount': amount, 'reference': reference}
    if result:
        tx['result'] = result
    return {'transaction': tx, 'status': {'success': True, 'code': '200'}}


class ReadSingpayStatusTests(TestCase):
    def test_reads_success_failure_and_pending(self):
        self.assertEqual(read_singpay_status(singpay_answer('Success'))[0], 'success')
        self.assertEqual(read_singpay_status(singpay_answer('Failed'))[0], 'failed')
        self.assertEqual(read_singpay_status(singpay_answer(step='Start'))[0], 'pending')

    def test_successful_api_call_is_not_a_successful_payment(self):
        # « status.success = true » veut dire que l'appel a abouti, pas que le client a payé.
        answer = {'transaction': {'id': 'SP-TX-1', 'status': 'Start'}, 'status': {'success': True, 'code': '201'}}
        self.assertEqual(read_singpay_status(answer)[0], 'pending')
        self.assertEqual(read_singpay_status({'status': {'success': True}})[0], 'unknown')

    def test_call_error_is_unknown(self):
        self.assertEqual(read_singpay_status({'error': 'SingPay HTTP 500'})[0], 'unknown')
        self.assertEqual(read_singpay_status(None)[0], 'unknown')


@override_settings(PAYMENT_WEBHOOK_SECRET='webhook-test-secret', PAYMENT_WEBHOOK_SIGNATURE_REQUIRED=True)
class OrderPaymentVerificationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.factory = APIRequestFactory()
        self.client_user = User.objects.create_user(phone='+24107100001', password='password', user_type='client')
        self.manager = User.objects.create_user(phone='+24107100002', password='password', user_type='store_manager')
        self.stranger = User.objects.create_user(phone='+24107100003', password='password', user_type='client')
        category = StoreCategory.objects.create(name='Test')
        store = Store.objects.create(
            name='Boutique', category=category, manager=self.manager, phone='+24107100004',
            address='Libreville', zone='Centre',
        )
        self.order = Order.objects.create(
            client=self.client_user, store=store, status='pending_payment', order_number='CMD-TEST',
            total_amount=Decimal('12500.00'), items_total=Decimal('10500.00'), delivery_fee=Decimal('2000.00'),
            delivery_address='Libreville', delivery_phone='+24107100001', delivery_zone='Centre',
        )
        self.payment = Payment.objects.create(
            order=self.order, payment_method='airtel_money', amount=Decimal('12500.00'),
            status='pending', transaction_id='SP-TX-1', operator_reference='AIRTEL',
        )

    def notify(self, payload):
        request = self.factory.generic(
            'POST', '/api/v1/payments/webhook/', json.dumps(payload), content_type='application/json'
        )
        with patch('orders.signals.NotificationService.notify_order_status_update'), \
             patch('delivery.tasks.assign_nearest_delivery_agent.delay'):
            return PaymentWebhookView.as_view()(request)

    def forged_success(self):
        return {'transaction': {'id': 'SP-TX-1', 'result': 'Success', 'amount': 12500, 'reference': 'GABOSHOP_CMD-TEST'}}

    def test_forged_notification_is_checked_with_singpay(self):
        with patch(STATUS_CALL, return_value=singpay_answer(step='Start')) as status_call:
            response = self.notify(self.forged_success())

        status_call.assert_called_once_with('SP-TX-1')
        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.payment.status, 'processing')
        self.assertEqual(self.order.status, 'pending_payment')

    def test_payment_confirmed_when_singpay_confirms(self):
        with patch(STATUS_CALL, return_value=singpay_answer('Success')):
            response = self.notify({'transaction': {'id': 'SP-TX-1'}})

        self.assertEqual(response.status_code, 200)
        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.payment.status, 'success')
        self.assertEqual(self.order.status, 'confirmed')
        self.assertEqual(self.payment.webhook_data['singpay_verification']['outcome'], 'success')

    def test_wrong_amount_from_singpay_is_not_confirmed(self):
        with patch(STATUS_CALL, return_value=singpay_answer('Success', amount=100)):
            self.notify({'transaction': {'id': 'SP-TX-1'}})

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'pending')

    def test_failed_payment_is_recorded(self):
        with patch(STATUS_CALL, return_value=singpay_answer('Failed')):
            self.notify({'transaction': {'id': 'SP-TX-1'}})

        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'failed')

    def test_found_by_reference_and_unknown_payment_rejected(self):
        with patch(STATUS_CALL, return_value=singpay_answer('Success')):
            self.notify({'reference': 'GABOSHOP_CMD-TEST'})
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'success')

        with patch(STATUS_CALL) as status_call:
            response = self.notify({'transaction': {'id': 'INCONNU', 'reference': 'XYZ'}})
        self.assertEqual(response.status_code, 404)
        status_call.assert_not_called()

    def test_repeated_notifications_do_not_flood_singpay(self):
        with patch(STATUS_CALL, return_value=singpay_answer(step='Start')) as status_call:
            self.notify({'transaction': {'id': 'SP-TX-1'}})
            second = self.notify({'transaction': {'id': 'SP-TX-1'}})

        self.assertEqual(second.status_code, 202)
        self.assertEqual(status_call.call_count, 1)

    def test_cancelled_order_is_not_reopened(self):
        Order.objects.filter(pk=self.order.pk).update(status='cancelled')
        with patch(STATUS_CALL, return_value=singpay_answer('Success')):
            self.notify({'transaction': {'id': 'SP-TX-1'}})

        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.payment.status, 'success')
        self.assertEqual(self.order.status, 'cancelled')

    def test_client_can_ask_for_a_check_but_not_a_stranger(self):
        api = APIClient()
        url = f'/api/v1/orders/{self.order.pk}/payments/verify/'

        api.force_authenticate(self.stranger)
        with patch(STATUS_CALL) as status_call:
            self.assertEqual(api.post(url).status_code, 404)
        status_call.assert_not_called()

        api.force_authenticate(self.client_user)
        with patch(STATUS_CALL, return_value=singpay_answer('Success')), \
             patch('orders.signals.NotificationService.notify_order_status_update'), \
             patch('delivery.tasks.assign_nearest_delivery_agent.delay'):
            response = api.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['payment_status'], 'success')
        self.assertEqual(response.data['data']['order_status'], 'confirmed')


@override_settings(PAYMENT_WEBHOOK_SECRET='webhook-test-secret')
class SubscriptionIntentVerificationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(phone='+24107200001', password='password', user_type='store_manager')
        self.intent = PaymentIntent.objects.create(
            user=self.user, amount=5000, provider='singpay', status='PENDING',
            raw_response={'transaction': {'id': 'SP-INT-1', 'status': 'Start'}},
        )

    def notify(self, payload):
        request = self.factory.generic(
            'POST', '/api/v1/payments/provider/singpay/notify/', json.dumps(payload), content_type='application/json'
        )
        return ProviderCallbackAPIView.as_view()(request, provider='singpay')

    def test_unsigned_notification_checked_with_singpay(self):
        answer = {'transaction': {'id': 'SP-INT-1', 'result': 'Success', 'amount': 5000, 'reference': self.intent.reference}}
        with patch(STATUS_CALL, return_value=answer) as status_call:
            response = self.notify({'transaction': {'reference': self.intent.reference, 'result': 'Success'}})

        status_call.assert_called_once_with('SP-INT-1')
        self.assertEqual(response.status_code, 200)
        self.intent.refresh_from_db()
        self.assertEqual(self.intent.status, 'SUCCESS')

    def test_forged_success_rejected_when_singpay_disagrees(self):
        answer = {'transaction': {'id': 'SP-INT-1', 'status': 'Start'}}
        with patch(STATUS_CALL, return_value=answer):
            self.notify({'transaction': {'reference': self.intent.reference, 'result': 'Success'}})

        self.intent.refresh_from_db()
        self.assertEqual(self.intent.status, 'PENDING')

    def test_other_providers_still_need_a_signature(self):
        request = self.factory.generic(
            'POST', '/api/v1/payments/provider/cinetpay/notify/',
            json.dumps({'transaction_id': self.intent.reference, 'status': 'SUCCESS'}), content_type='application/json',
        )
        response = ProviderCallbackAPIView.as_view()(request, provider='cinetpay')
        self.assertEqual(response.status_code, 401)
