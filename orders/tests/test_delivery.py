from decimal import Decimal

from django.test import TestCase

from delivery.models import VehicleType
from orders.models import Order, OrderItem
from products.models import Product, ProductCategory
from stores.models import Store, StoreCategory
from users.models import User


class OrderDeliveryTests(TestCase):
    def setUp(self):
        cat = StoreCategory.objects.create(name='Default')
        mgr = User.objects.create_user(phone='+2419000001', password='mgrpass', user_type='store_manager')
        self.store = Store.objects.create(name='TestStore', category=cat, manager=mgr, phone='+2419000001', address='addr', city='CityA', zone='Zone')
        self.store.delivery_fee = Decimal('2000.00')
        self.store.delivery_fee_express = Decimal('3500.00')
        self.store.save(update_fields=['delivery_fee', 'delivery_fee_express'])
        self.category = ProductCategory.objects.create(store=self.store, name='Cat1')
        VehicleType.objects.create(
            name='MOTO',
            max_weight_kg=Decimal('30.00'),
            max_length_m=Decimal('0.50'),
            max_items=0,
            max_distance_km=Decimal('50.00')
        )
        VehicleType.objects.create(
            name='CAR',
            max_weight_kg=Decimal('80.00'),
            max_length_m=Decimal('1.00'),
            max_items=0,
            max_distance_km=Decimal('100.00'),
            allow_intercity=True
        )
        VehicleType.objects.create(
            name='VAN',
            max_weight_kg=Decimal('150.00'),
            max_length_m=Decimal('2.00'),
            max_items=0,
            max_distance_km=Decimal('200.00'),
            allow_intercity=True
        )
        VehicleType.objects.create(
            name='TRUCK',
            max_weight_kg=Decimal('9999.00'),
            max_length_m=Decimal('5.00'),
            max_items=0,
            max_distance_km=Decimal('500.00'),
            allow_intercity=True
        )
        self.product_light = Product.objects.create(
            store=self.store,
            category=self.category,
            name='Light',
            price=1000,
            stock=10,
            weight_kg=Decimal('1.00'),
            length_m=Decimal('0.40')
        )
        self.product_heavy = Product.objects.create(
            store=self.store,
            category=self.category,
            name='Heavy',
            price=5000,
            stock=5,
            weight_kg=Decimal('25.00'),
            length_m=Decimal('1.20')
        )
        self.client_user = User.objects.create_user(phone='+2419000002', password='clientpass')

    def test_delivery_cost_same_city_moto(self):
        order = Order.objects.create(client=self.client_user, store=self.store, city='CityA')
        OrderItem.objects.create(order=order, product=self.product_light, quantity=1, unit_price=self.product_light.price)
        order.calculate_totals()
        self.assertEqual(order.vehicle_type, 'MOTO')
        self.assertEqual(order.delivery_fee, self.store.delivery_fee)

    def test_delivery_cost_same_city_van(self):
        order = Order.objects.create(client=self.client_user, store=self.store, city='CityA')
        OrderItem.objects.create(order=order, product=self.product_heavy, quantity=1, unit_price=self.product_heavy.price)
        order.calculate_totals()
        self.assertEqual(order.vehicle_type, 'VAN')
        self.assertEqual(order.delivery_fee, self.store.delivery_fee)

    def test_operator_fee_calculation(self):
        order = Order.objects.create(client=self.client_user, store=self.store, city='CityA')
        OrderItem.objects.create(order=order, product=self.product_light, quantity=3, unit_price=self.product_light.price)
        OrderItem.objects.create(order=order, product=self.product_heavy, quantity=1, unit_price=self.product_heavy.price)
        order.calculate_totals()
        expected_subtotal = self.product_light.price * 3 + self.product_heavy.price * 1
        self.assertEqual(order.items_total, expected_subtotal)
        self.assertEqual(order.service_fee, Decimal('0.00'))
        expected_operator = order.calculate_operator_fee()
        self.assertEqual(order.operator_fee, expected_operator)
        expected_total = order.items_total + order.delivery_fee + order.operator_fee + order.tax_amount + order.payment_fees
        self.assertEqual(order.total_amount, expected_total)
