"""Contrôle complet (2026-10-15) : stock, produits pro, étapes réservées au livreur, annulation, commission."""
from datetime import time
from decimal import Decimal
from unittest import mock

from django.test import TestCase
from rest_framework.test import APIClient

from api.models import SystemSettings
from orders.models import Order
from payments.configuration import DEFAULT_PAYMENT_POLICY
from payments.models import Commission
from products.models import Product, ProductCategory
from stores.models import Store, StoreCategory
from users.models import User


class ControleCompletTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(phone='+24107100001', password='x', user_type='store_manager')
        self.client_user = User.objects.create_user(phone='+24107100002', password='x', user_type='client')
        self.admin = User.objects.create_user(phone='+24107100003', password='x', user_type='admin', is_staff=True)
        category = StoreCategory.objects.create(name='Test')
        self.store = Store.objects.create(
            is_verified=True, name='Commerce', category=category, manager=self.manager, phone='+24107100010',
            address='Libreville', zone='Centre', commission_rate=Decimal('8'), opening_time=time(0, 0), closing_time=time(0, 0),
        )
        product_category = ProductCategory.objects.create(store_category=category, name='P', commission_rate=Decimal('8'))
        self.product = Product.objects.create(
            store=self.store, category=product_category, name='Article', price=Decimal('1000'), stock=5, weight_kg=Decimal('1'),
        )
        self.pro_product = Product.objects.create(
            store=self.store, category=product_category, name='Carton pro', price=Decimal('100'), stock=50,
            weight_kg=Decimal('1'), market_type='b2b',
        )
        settings = SystemSettings.get_settings()
        settings.payment_policy = DEFAULT_PAYMENT_POLICY
        settings.save(update_fields=['payment_policy'])
        self.api = APIClient()

    def order(self, items):
        self.api.force_authenticate(self.client_user)
        payload = {
            'store': self.store.id, 'city': 'Libreville', 'delivery_address': 'Akanda', 'delivery_phone': '077391199',
            'delivery_zone': 'Centre', 'delivery_requested': True, 'payment_flow': 'direct_split',
            'payment_method': 'cash', 'items': items,
        }
        with mock.patch('delivery.tasks.assign_nearest_delivery_agent'):
            return self.api.post('/api/v1/orders/create/', payload, format='json')

    def stock(self):
        self.product.refresh_from_db()
        return self.product.stock

    def test_same_article_twice_cannot_exceed_stock(self):
        response = self.order([{'product_id': self.product.id, 'quantity': 3}, {'product_id': self.product.id, 'quantity': 3}])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.stock(), 5)
        self.assertFalse(Order.objects.exists())

    def test_professional_article_cannot_be_ordered_at_public_counter(self):
        response = self.order([{'product_id': self.pro_product.id, 'quantity': 1}])
        self.assertEqual(response.status_code, 400)

    def test_store_cancel_puts_articles_back_in_stock_once(self):
        order_id = self.order([{'product_id': self.product.id, 'quantity': 2}]).json()['data']['id']
        self.assertEqual(self.stock(), 3)
        self.api.force_authenticate(self.manager)
        response = self.api.patch(f'/api/v1/orders/{order_id}/status/', {'status': 'cancelled'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.stock(), 5)
        order = Order.objects.get(pk=order_id)
        order.save()  # une nouvelle sauvegarde ne remet rien en stock
        self.assertEqual(self.stock(), 5)

    def test_admin_cancel_restocks_and_refuses_delivered_orders(self):
        order_id = self.order([{'product_id': self.product.id, 'quantity': 1}]).json()['data']['id']
        self.api.force_authenticate(self.admin)
        self.assertEqual(self.api.post(f'/api/v1/admin/orders/{order_id}/cancel/', {}, format='json').status_code, 200)
        self.assertEqual(self.stock(), 5)
        delivered_id = self.order([{'product_id': self.product.id, 'quantity': 1}]).json()['data']['id']
        Order.objects.filter(pk=delivered_id).update(status='delivered')
        self.api.force_authenticate(self.admin)
        self.assertEqual(self.api.post(f'/api/v1/admin/orders/{delivered_id}/cancel/', {}, format='json').status_code, 409)
        self.assertEqual(self.stock(), 4)

    def test_store_cannot_deliver_an_order_meant_for_a_gaboshop_driver(self):
        order_id = self.order([{'product_id': self.product.id, 'quantity': 1}]).json()['data']['id']
        Order.objects.filter(pk=order_id).update(status='ready')
        self.api.force_authenticate(self.manager)
        response = self.api.patch(f'/api/v1/orders/{order_id}/status/', {'status': 'assigned'}, format='json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Order.objects.get(pk=order_id).status, 'ready')

    def test_commission_record_matches_amount_kept_on_order(self):
        order_id = self.order([{'product_id': self.product.id, 'quantity': 2}]).json()['data']['id']
        order = Order.objects.get(pk=order_id)
        order.status = 'paid'
        order.save()
        commission = Commission.objects.get(order=order)
        self.assertEqual(commission.commission_amount, order.commission_amount)

    def test_status_labels_are_readable(self):
        self.assertEqual(dict(Order.ORDER_STATUS_CHOICES)['delivered'], 'Livrée')

    def test_phone_status_check_does_not_use_login_attempts(self):
        self.api.force_authenticate(self.client_user)
        for _ in range(25):
            self.assertEqual(self.api.get('/api/v1/auth/phone/verify/').status_code, 200)
