import hashlib
import hmac
import json
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory

from api.v1.payments import PaymentWebhookView
from orders.models import Order
from payments.models import Payment
from stores.models import Store, StoreCategory
from users.models import User


@override_settings(
    PAYMENT_WEBHOOK_SECRET='webhook-test-secret',
    PAYMENT_WEBHOOK_SIGNATURE_REQUIRED=True,
)
class PaymentWebhookTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            phone='+24107000001', password='password', user_type='client'
        )
        manager = User.objects.create_user(
            phone='+24107000002', password='password', user_type='store_manager'
        )
        category = StoreCategory.objects.create(name='Test')
        store = Store.objects.create(
            name='Test Store',
            category=category,
            manager=manager,
            phone='+24107000003',
            address='Libreville',
            zone='Centre',
        )
        self.order = Order.objects.create(
            client=self.user,
            store=store,
            status='pending_payment',
            total_amount=Decimal('12500.00'),
            items_total=Decimal('10500.00'),
            delivery_fee=Decimal('2000.00'),
            delivery_address='Libreville',
            delivery_phone='+24107000001',
            delivery_zone='Centre',
        )
        self.payment = Payment.objects.create(
            order=self.order,
            payment_method='airtel_money',
            amount=Decimal('12500.00'),
            status='pending',
            transaction_id='PAY-TEST-1',
        )
        self.url = '/api/v1/payments/webhook/'

    def post_webhook(self, payload, signature=True):
        body = json.dumps(payload, separators=(',', ':')).encode()
        headers = {}
        if signature:
            headers['HTTP_X_WEBHOOK_SIGNATURE'] = hmac.new(
                b'webhook-test-secret', body, hashlib.sha256
            ).hexdigest()
        request = self.factory.generic(
            'POST', self.url, body, content_type='application/json', **headers
        )
        return PaymentWebhookView.as_view()(request)

    def success_payload(self, amount='12500.00'):
        return {
            'transaction_id': self.payment.transaction_id,
            'status': 'SUCCESS',
            'amount': amount,
        }

    def test_rejects_missing_signature(self):
        response = self.post_webhook(self.success_payload(), signature=False)

        self.assertEqual(response.status_code, 401)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'pending')

    def test_rejects_wrong_amount(self):
        response = self.post_webhook(self.success_payload(amount='12500.01'))

        self.assertEqual(response.status_code, 400)
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'pending')

    def test_confirms_payment_and_replays_idempotently(self):
        with patch('orders.signals.NotificationService.notify_order_status_update'), \
             patch('delivery.tasks.assign_nearest_delivery_agent.delay'):
            response = self.post_webhook(self.success_payload())
            replay = self.post_webhook(self.success_payload())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(replay.status_code, 200)
        self.payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.payment.status, 'success')
        self.assertEqual(self.order.status, 'confirmed')