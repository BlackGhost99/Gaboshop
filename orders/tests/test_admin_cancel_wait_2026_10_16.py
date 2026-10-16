"""Régression staging : attribution vs préparation et annulations financières sûres."""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from api.v1.delivery_admin import _delivery_row
from delivery.models import Delivery
from orders.models import Order, OrderItem
from payments.models import Payment
from products.models import Product, ProductCategory
from stores.models import Store, StoreCategory
from users.models import User


class AdminCancellationAndDispatchTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(phone='+24176766011', password='safe-test-2026', user_type='store_manager')
        self.customer = User.objects.create_user(phone='+24176766012', password='safe-test-2026', user_type='client')
        self.admin = User.objects.create_user(phone='+24176766013', password='safe-test-2026', user_type='admin')
        category = StoreCategory.objects.create(name='Magasins test annulation')
        self.store = Store.objects.create(name='Commerce test attente', category=category, manager=self.manager,
                                          phone='+24176766011', address='Libreville', city='Libreville')
        product_category = ProductCategory.objects.create(name='Produits test annulation', store_category=category)
        self.product = Product.objects.create(store=self.store, category=product_category, name='Article test',
                                              stock=4, price=Decimal('10000'))
        self.order = Order.objects.create(client=self.customer, store=self.store, status='preparing',
                                          city='Libreville', delivery_zone='Louis',
                                          delivery_address='Libreville', delivery_phone='+24176766012',
                                          items_total=Decimal('10000'), total_amount=Decimal('12000'),
                                          delivery_fee=Decimal('2000'))
        OrderItem.objects.create(order=self.order, product=self.product, quantity=1, unit_price=Decimal('10000'))
        self.api = APIClient()
        self.api.force_authenticate(self.admin)

    def test_preparation_is_not_driver_wait_and_long_age_is_displayed(self):
        old = timezone.now() - timedelta(hours=5, minutes=56)
        Order.objects.filter(pk=self.order.id).update(created_at=old)
        Delivery.objects.filter(order=self.order).update(created_at=old)
        self.order.refresh_from_db()
        delivery = Delivery.objects.get(order=self.order)
        row = _delivery_row(delivery, timezone.now())
        self.assertIsNone(row['minutes_waiting'])
        self.assertGreaterEqual(row['minutes_since_order'], 355)
        self.assertEqual(row['order_status'], 'preparing')
        self.order.status = 'ready'
        self.order.save(update_fields=['status'])
        delivery.refresh_from_db()
        row_ready = _delivery_row(delivery, timezone.now())
        self.assertIsNotNone(row_ready['minutes_waiting'])
        self.assertLess(row_ready['minutes_waiting'], 2)

    def test_admin_can_cancel_unpaid_preparation_with_stock_restore(self):
        result = self.api.post(f'/api/v1/admin/orders/{self.order.id}/cancel/',
                               {'reason': 'Commande non préparée depuis plusieurs heures'}, format='json')
        self.assertEqual(result.status_code, 200, result.content)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'cancelled')
        self.assertEqual(Delivery.objects.get(order=self.order).status, 'cancelled')
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 5)

    def test_cannot_cancel_when_payment_record_exists(self):
        Payment.objects.create(order=self.order, payment_method='cash', status='success', amount=Decimal('12000'))
        response = self.api.post(f'/api/v1/admin/orders/{self.order.id}/cancel/',
                                 {'reason': 'Commande non préparée'}, format='json')
        self.assertEqual(response.status_code, 409, response.content)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'preparing')

    def test_cannot_cancel_if_payment_pending(self):
        Payment.objects.create(order=self.order, payment_method='card', status='pending', amount=Decimal('12000'))
        response = self.api.post(f'/api/v1/admin/orders/{self.order.id}/cancel/',
                                 {'reason': 'Commande trop ancienne'}, format='json')
        self.assertEqual(response.status_code, 409)

    def test_cannot_cancel_if_delivery_assigned(self):
        Delivery.objects.filter(order=self.order).update(status='assigned', delivery_agent=self.manager)
        response = self.api.post(f'/api/v1/admin/orders/{self.order.id}/cancel/',
                                 {'reason': 'Commande trop ancienne'}, format='json')
        self.assertEqual(response.status_code, 409)

    def test_cannot_cancel_when_course_is_open_to_couriers(self):
        Delivery.objects.filter(order=self.order).update(is_open_to_all=True)
        response = self.api.post(f'/api/v1/admin/orders/{self.order.id}/cancel/',
                                 {'reason': 'Commande trop ancienne'}, format='json')
        self.assertEqual(response.status_code, 409)

    def test_preparation_delay_creates_one_alert_per_recipient(self):
        from core.scheduled import alert_stale_preparation
        from notifications.models import Notification

        Order.objects.filter(pk=self.order.pk).update(updated_at=timezone.now() - timedelta(minutes=65))
        first = alert_stale_preparation()
        second = alert_stale_preparation()
        alerts = Notification.objects.filter(order=self.order, title='Retard de préparation de commande')
        self.assertEqual(alerts.count(), 2, (first, second))
        self.assertIn('2 alerte', first)
        self.assertIn('0 alerte', second)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'preparing')

    def test_client_cannot_use_admin_cancel_endpoint(self):
        self.api.force_authenticate(self.customer)
        response = self.api.post(f'/api/v1/admin/orders/{self.order.id}/cancel/',
                                 {'reason': 'Je ne veux plus la commande'}, format='json')
        self.assertEqual(response.status_code, 403)
