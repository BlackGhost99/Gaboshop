from datetime import time
from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from notifications.messages import payment_failure_code
from notifications.models import Notification
from orders.models import Order
from payments.models import Payment
from stores.models import Store, StoreCategory
from users.models import User

STATUS_CALL = 'payments.online_verification.call_singpay_status'
SEARCH_CALL = 'payments.online_verification.call_singpay_transaction_by_reference'


def singpay(result, reference='GABOSHOP_CMD-NOTIF'):
    return {'transaction': {'id': 'SP-N-1', 'status': 'Terminate', 'result': result, 'amount': 12500,
                            'reference': reference}, 'status': {'success': True}}


class FailureReasonTests(TestCase):
    def test_singpay_results_become_plain_reasons(self):
        self.assertEqual(payment_failure_code(singpay('PasswordError')), 'password')
        self.assertEqual(payment_failure_code(singpay('BalanceError')), 'balance')
        self.assertEqual(payment_failure_code(singpay('TimeOutError')), 'timeout')
        self.assertEqual(payment_failure_code('SingPay HTTP 500'), 'service')
        # Les noms de champs (client_msisdn...) ne comptent pas, seul le résultat compte.
        self.assertEqual(payment_failure_code({'transaction': {'result': 'Error', 'client_msisdn': '1'}}), 'unknown')


@override_settings(AI_PROVIDER='local')
class PaymentNotificationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client_user = User.objects.create_user(phone='+24107300001', password='password', user_type='client')
        self.manager = User.objects.create_user(phone='+24107300002', password='password', user_type='store_manager')
        store = Store.objects.create(
            name='Boutique Test', category=StoreCategory.objects.create(name='Cat'), manager=self.manager,
            phone='+24107300004', address='Libreville', zone='Centre',
        )
        self.order = Order.objects.create(
            client=self.client_user, store=store, status='pending_payment', order_number='CMD-NOTIF',
            total_amount=Decimal('12500.00'), items_total=Decimal('10500.00'), delivery_fee=Decimal('2000.00'),
            delivery_address='Libreville', delivery_phone='+24107300001', delivery_zone='Centre',
        )
        self.payment = Payment.objects.create(
            order=self.order, payment_method='airtel_money', amount=Decimal('12500.00'),
            status='pending', transaction_id='SP-N-1', operator_reference='AIRTEL', client_phone='+24177391199',
        )
        self.api = APIClient()
        self.api.force_authenticate(self.client_user)

    def verify(self, answer):
        with patch(STATUS_CALL, return_value=answer), patch(SEARCH_CALL, return_value={'transactions': []}), \
             patch('notifications.service.NotificationService._send_notification', return_value=True), \
             patch('delivery.tasks.assign_nearest_delivery_agent.delay'), \
             self.captureOnCommitCallbacks(execute=True):
            return self.api.post(f'/api/v1/orders/{self.order.pk}/payments/verify/')

    def test_failed_payment_tells_the_client_why_and_what_to_do(self):
        self.verify(singpay('PasswordError'))
        note = Notification.objects.get(user=self.client_user, notif_type='payment')
        self.assertEqual(note.metadata['level'], 'error')
        self.assertIn('Code secret', note.metadata['reason'])
        self.assertIn('Relancez', note.metadata['next_step'])
        self.assertIn('12 500 F CFA', note.body)

        # Une deuxième vérification du même échec ne renvoie pas de notification.
        cache.clear()
        self.verify(singpay('PasswordError'))
        self.assertEqual(Notification.objects.filter(user=self.client_user, notif_type='payment').count(), 1)

    def test_successful_payment_details_go_to_client_and_store(self):
        self.verify(singpay('Success'))
        client_note = Notification.objects.get(user=self.client_user, notif_type='payment')
        store_note = Notification.objects.get(user=self.manager, notif_type='payment')
        self.assertEqual(client_note.metadata['level'], 'success')
        self.assertIn('Airtel Money', client_note.body)
        self.assertIn('+24177391199', client_note.body)
        self.assertIn('En préparation', store_note.metadata['next_step'])

    def test_launch_error_is_explained_in_the_answer_and_a_notification(self):
        with patch(SEARCH_CALL, return_value={'transactions': []}), patch(STATUS_CALL, return_value={}), \
             patch('notifications.service.NotificationService._send_notification', return_value=True), \
             patch('payments.services.PaymentService._call_operator_api', side_effect=Exception('BalanceError')):
            response = self.api.post(
                f'/api/v1/orders/{self.order.pk}/payments/init/',
                {'payment_method': 'airtel_money', 'phone_number': '077391199'}, format='json',
            )
        self.assertEqual(response.status_code, 502)
        self.assertIn('Solde', response.data['error']['reason'])
        self.assertIn('Rechargez', response.data['error']['next_step'])
        self.assertTrue(Notification.objects.filter(user=self.client_user, metadata__level='error').exists())

    def test_assistant_explains_the_last_problem(self):
        self.verify(singpay('TimeOutError'))
        response = self.api.post('/api/v1/ai/assistant/', {'message': "Pourquoi mon paiement n'a pas marché ?"},
                                 format='json')
        text = response.data['data']['message']
        self.assertIn('Pourquoi', text)
        self.assertIn('expiré', text)
        self.assertIn('Que faire', text)

    def test_assistant_explains_an_error_shown_on_screen(self):
        problem = {'action': 'Enregistrer le produit', 'message': 'Prix : ce champ est obligatoire.', 'status': '400'}
        response = self.api.post('/api/v1/ai/assistant/', {'message': 'Que faire ?', 'problem': problem},
                                 format='json')
        text = response.data['data']['message']
        self.assertIn('Prix', text)
        self.assertIn('Que faire', text)


class StoreClosedNotificationTests(TestCase):
    def test_order_received_while_closed_says_why_and_how_to_fix(self):
        client_user = User.objects.create_user(phone='+24107400001', password='password', user_type='client')
        manager = User.objects.create_user(phone='+24107400002', password='password', user_type='store_manager')
        store = Store.objects.create(
            name='Fermé', category=StoreCategory.objects.create(name='Cat'), manager=manager, phone='+24107400004',
            address='Libreville', zone='Centre', opening_time=time(8, 0), closing_time=time(8, 1),
        )
        with patch('stores.models.Store.is_open', return_value=False):
            Order.objects.create(
                client=client_user, store=store, status='created', order_number='CMD-CLOSED',
                total_amount=Decimal('5000.00'), items_total=Decimal('5000.00'), delivery_fee=Decimal('0'),
                delivery_address='Libreville', delivery_phone='+24107400001', delivery_zone='Centre',
            )
        note = Notification.objects.get(user=manager)
        self.assertEqual(note.metadata['level'], 'warning')
        self.assertIn('fermé', note.body)
        self.assertIn('horaires', note.metadata['next_step'])
