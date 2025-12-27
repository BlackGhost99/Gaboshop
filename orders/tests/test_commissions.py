from django.test import TestCase
from decimal import Decimal
from datetime import time
from users.models import User
from stores.models import StoreCategory, Store
from products.models import ProductCategory, Product
from payments.models import CategoryCommission, SubscriptionPlan, StoreSubscription
from orders.models import Order, OrderItem
from orders.services import OrderService
from django.utils import timezone


class CommissionCalculationTests(TestCase):
    def setUp(self):
        # Users
        self.client_user = User.objects.create_user(phone='070000001', password='pass', user_type='client')
        self.manager = User.objects.create_user(phone='070000002', password='pass', user_type='store_manager')

        # Category / Store
        self.cat = StoreCategory.objects.create(name='Épicerie')
        self.store = Store.objects.create(
            name='Test Store',
            category=self.cat,
            manager=self.manager,
            phone='09999999',
            address='Rue Test',
            zone='Centre',
        )
        # Ensure time and Decimal fields are correct to avoid comparison/type issues in tests
        self.store.opening_time = time(8, 0)
        self.store.closing_time = time(20, 0)
        # Ensure delivery and service fees stored as Decimal values
        self.store.delivery_fee = Decimal('2000.00')
        self.store.delivery_fee_express = Decimal('3500.00')
        self.store.service_fee = Decimal('0.00')
        self.store.save()

        # Product category and product
        self.prod_cat = ProductCategory.objects.create(store=self.store, store_category=self.cat, name='Alcools')
        self.product = Product.objects.create(
            store=self.store,
            category=self.prod_cat,
            name='Test Product',
            price=Decimal('1000.00'),
            stock=10,
        )

        # Default plan (starter)
        self.starter = SubscriptionPlan.objects.create(name='Starter', slug='starter', plan_type='starter', price=Decimal('0.00'), commission_multiplier=Decimal('1.00'))
        # Pro plan
        self.pro = SubscriptionPlan.objects.create(name='Pro', slug='pro', plan_type='pro', price=Decimal('15000.00'), commission_multiplier=Decimal('0.60'))

        # Category commission base rate 10%
        self.cat_comm = CategoryCommission.objects.create(store_category=self.cat, base_rate=Decimal('10.00'))

    def create_order_with_item(self, plan=None, unit_price=Decimal('1000.00')):
        # Optionally attach subscription
        if plan:
            StoreSubscription.objects.create(
                store=self.store,
                plan=plan,
                plan_name=plan.name,
                monthly_fee=plan.price,
                status='active',
                start_date=timezone.now().date(),
                end_date=timezone.now().date().replace(year=timezone.now().year + 1),
            )

        order = Order.objects.create(
            client=self.client_user,
            store=self.store,
            delivery_address='Addr',
            delivery_phone='070000001',
            delivery_zone='Centre',
            items_total=Decimal('0.00'),
            delivery_fee=self.store.delivery_fee,
            tax_amount=Decimal('0.00'),
            total_amount=Decimal('0.00')
        )
        # ensure Decimal typed payment_fees to avoid float/Decimal arithmetic issues
        order.payment_fees = Decimal('0.00')
        order.save()

        OrderItem.objects.create(order=order, product=self.product, quantity=1, unit_price=unit_price)
        # Recalculate totals
        order.calculate_totals()
        return order

    def test_commission_with_starter_plan(self):
        order = self.create_order_with_item(plan=self.starter)
        res = OrderService.calculate_order_commission(order)

        # Commission should be 1000 * 10% = 100
        self.assertIsNotNone(res)
        self.assertEqual(res['commission_amount'], Decimal('100.00'))
        self.assertEqual(res['commission_rate'], Decimal('10.00'))
        self.assertEqual(res['store_earnings'], Decimal('900.00'))

    def test_commission_with_pro_plan_multiplier(self):
        order = self.create_order_with_item(plan=self.pro)
        res = OrderService.calculate_order_commission(order)

        # Effective rate = 10% * 0.6 = 6% -> commission = 60.00
        self.assertIsNotNone(res)
        self.assertEqual(res['commission_amount'], Decimal('60.00'))
        self.assertEqual(res['commission_rate'], Decimal('6.00'))
        self.assertEqual(res['store_earnings'], Decimal('940.00'))
