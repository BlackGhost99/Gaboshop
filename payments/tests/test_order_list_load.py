"""Liste et détail des commandes : rafraîchis automatiquement, ils doivent rester légers.

Avant, chaque commande affichée coûtait des dizaines de requêtes et réécrivait ses obligations de
paiement : le serveur gratuit ne répondait plus (« Network Error » chez le client).
"""
from datetime import timedelta
from decimal import Decimal

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from api.models import SystemSettings
from orders.models import Order, OrderItem
from payments.configuration import DEFAULT_PAYMENT_POLICY
from payments.direct_models import PaymentReceipt
from payments.direct_service import create_arrangement, payment_summary
from products.models import Product, ProductCategory
from stores.models import Store, StoreCategory
from users.models import User


def _writes(ctx):
    return [q['sql'] for q in ctx.captured_queries if q['sql'].lstrip().upper().startswith(('UPDATE', 'INSERT', 'DELETE'))]


class OrderListLoadTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(phone='+24106000012', password='x', user_type='store_manager')
        self.client_user = User.objects.create_user(phone='+24106000013', password='x', user_type='client')
        category = StoreCategory.objects.create(name='Test')
        self.store = Store.objects.create(name='Commerce test', category=category, manager=self.manager, phone='+24106000110', address='Libreville', zone='Centre', commission_rate=Decimal('8'))
        product_category = ProductCategory.objects.create(store_category=category, name='Produits', commission_rate=Decimal('8'))
        self.product = Product.objects.create(store=self.store, category=product_category, name='Article', price=Decimal('10000'), stock=100, weight_kg=Decimal('1'))
        settings = SystemSettings.get_settings()
        settings.payment_policy = DEFAULT_PAYMENT_POLICY
        settings.save(update_fields=['payment_policy'])
        self.api = APIClient()
        self.api.force_authenticate(self.client_user)

    def add_orders(self, count):
        orders = []
        for _ in range(count):
            order = Order.objects.create(client=self.client_user, store=self.store, delivery_address='Akanda', delivery_phone='+24106000013', delivery_zone='Centre', delivery_fee=Decimal('2000'))
            OrderItem.objects.create(order=order, product=self.product, quantity=2, unit_price=self.product.price)
            OrderItem.objects.create(order=order, product=self.product, quantity=1, unit_price=self.product.price)
            order.items_total = Decimal('30000')
            order.commission_rate = Decimal('8')
            order.commission_amount = Decimal('2400')
            order.total_amount = Decimal('32000')
            order.save()
            arrangement = create_arrangement(order, 'direct_split', 'cash', user=self.client_user)
            products = arrangement.obligations.get(kind='products')
            PaymentReceipt.objects.create(obligation=products, actor=self.client_user, amount=products.amount, method='cash', reference=f'R{order.pk}', idempotency_key=f'k{order.pk}')
            orders.append(order)
        return orders

    def list_orders(self):
        with CaptureQueriesContext(connection) as ctx:
            response = self.api.get('/api/v1/orders/')
        self.assertEqual(response.status_code, 200)
        return response, ctx

    def test_list_cost_does_not_grow_with_orders_and_writes_nothing(self):
        self.add_orders(2)
        response, small = self.list_orders()
        self.add_orders(4)
        response, large = self.list_orders()
        self.assertEqual(len(response.json()['results']), 6)
        self.assertEqual(len(large.captured_queries), len(small.captured_queries))
        self.assertLessEqual(len(large.captured_queries), 12)
        self.assertEqual(_writes(large), [])

    def test_list_still_shows_payment_details(self):
        order = self.add_orders(1)[0]
        response, _ = self.list_orders()
        arrangement = response.json()['results'][0]['payment_arrangement']
        products = next(o for o in arrangement['obligations'] if o['kind'] == 'products')
        self.assertEqual(arrangement['order_number'], order.order_number)
        self.assertTrue(products['i_am_payer'])
        self.assertEqual(products['remaining_amount'], '30000.00')
        self.assertEqual([r['status'] for r in products['receipts']], ['pending'])

    def test_detail_and_payment_panel_write_nothing(self):
        order = self.add_orders(1)[0]
        for url in (f'/api/v1/orders/{order.pk}/', f'/api/v1/payments/arrangements/order/{order.pk}/'):
            with CaptureQueriesContext(connection) as ctx:
                response = self.api.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assertEqual(_writes(ctx), [], url)

    def test_overdue_status_is_still_saved_once(self):
        order = self.add_orders(1)[0]
        products = order.payment_arrangement.obligations.get(kind='products')
        products.due_at = timezone.now() - timedelta(days=1)
        products.save(update_fields=['due_at'])
        payment_summary(order, self.client_user)
        products.refresh_from_db()
        self.assertEqual(products.status, 'overdue')
