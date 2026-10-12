from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import ScheduledTaskRun
from delivery.models import Delivery
from orders.models import Order, OrderItem
from products.models import Product
from stores.models import Store, StoreCategory
from users.models import User

TICK = '/api/v1/internal/tick/'


class SchedulerTests(TestCase):
	def setUp(self):
		self.client_user = User.objects.create_user(phone='+24177400001', password='x', user_type='client')
		manager = User.objects.create_user(phone='+24177400002', password='x', user_type='store_manager')
		self.store = Store.objects.create(name='Boutique', category=StoreCategory.objects.create(name='Mode'), manager=manager,
			phone='+24106000201', address='Libreville', zone='Centre')
		self.product = Product.objects.create(store=self.store, name='Robe', price=Decimal('5000'), stock=2,
			weight_kg=Decimal('0.5'), length_m=Decimal('1'))

	def _order(self, status='created', hours_ago=30):
		order = Order.objects.create(client=self.client_user, store=self.store, delivery_address='Akanda',
			delivery_phone='+24177400001', delivery_zone='Centre', delivery_fee=Decimal('0'), status=status)
		OrderItem.objects.create(order=order, product=self.product, quantity=3, unit_price=Decimal('5000'))
		Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(hours=hours_ago))
		return order

	def test_tick_requires_configured_token(self):
		with override_settings(CRON_TOKEN=''):
			self.assertEqual(APIClient().post(TICK).status_code, 503)
		with override_settings(CRON_TOKEN='jeton-secret'):
			self.assertEqual(APIClient().post(TICK, HTTP_X_CRON_TOKEN='faux').status_code, 403)
			res = APIClient().post(TICK, HTTP_X_CRON_TOKEN='jeton-secret')
			self.assertEqual(res.status_code, 200, res.content)
			self.assertIn('livraisons', res.json()['data'])
			# Juste après, rien n'est dû : chaque tâche ne tourne qu'une fois par intervalle.
			again = APIClient().post(TICK, HTTP_X_CRON_TOKEN='jeton-secret').json()['data']
			self.assertEqual(again, {})
		self.assertTrue(ScheduledTaskRun.objects.filter(name='commandes_abandonnees', last_ok=True).exists())

	def test_abandoned_order_is_cancelled_and_stock_restored(self):
		from core.scheduled import cancel_abandoned_orders
		old = self._order(hours_ago=30)
		recent = self._order(hours_ago=1)
		confirmed = self._order(status='confirmed', hours_ago=30)
		cancel_abandoned_orders()
		old.refresh_from_db(); recent.refresh_from_db(); confirmed.refresh_from_db()
		self.assertEqual(old.status, 'cancelled')
		self.assertEqual(recent.status, 'created')
		self.assertEqual(confirmed.status, 'confirmed')
		self.product.refresh_from_db()
		self.assertEqual(self.product.stock, 5)

	def test_paid_order_is_never_cancelled(self):
		from core.scheduled import cancel_abandoned_orders
		from payments.models import Payment
		order = self._order(hours_ago=30)
		payment = Payment.objects.create(order=order, payment_method='airtel_money', amount=Decimal('15000'))
		Payment.objects.filter(pk=payment.pk).update(status='success')
		cancel_abandoned_orders()
		order.refresh_from_db()
		self.assertNotEqual(order.status, 'cancelled')

	def test_driver_who_does_not_answer_is_replaced(self):
		from core.scheduled import advance_deliveries
		agent = User.objects.create_user(phone='+24177400003', password='x', user_type='delivery_agent')
		order = self._order(status='assigned', hours_ago=1)
		delivery, _ = Delivery.objects.get_or_create(order=order)
		Delivery.objects.filter(pk=delivery.pk).update(
			delivery_agent=agent, status='assigned', auto_assignment_enabled=True, assignment_round=1,
			assigned_at=timezone.now() - timedelta(hours=1), assignment_started_at=timezone.now() - timedelta(minutes=3),
		)
		with mock.patch('delivery.assignment_flow.handle_assignment_timeout') as timeout:
			advance_deliveries()
		timeout.assert_called_once_with(delivery.id, 1)

	def test_health_page_is_public_and_has_no_private_data(self):
		res = APIClient().get('/api/v1/health/')
		self.assertEqual(res.status_code, 200)
		data = res.json()['data']
		self.assertTrue(data['database'])
		self.assertIn('orders_ready_without_driver_30min', data)
		self.assertNotIn('+241', res.content.decode())
