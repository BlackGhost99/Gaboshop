from django.test import TestCase
from decimal import Decimal
from products.models import Product, ProductCategory
from stores.models import Store, StoreCategory
from users.models import User
from .models import Order, OrderItem


class OrderDeliveryTests(TestCase):
	def setUp(self):
		cat = StoreCategory.objects.create(name='Default')
		mgr = User.objects.create_user(phone='+2419000001', password='mgrpass', user_type='store_manager')
		self.store = Store.objects.create(name='TestStore', category=cat, manager=mgr, phone='+2419000001', address='addr', city='CityA', zone='Zone')
		self.category = ProductCategory.objects.create(store=self.store, name='Cat1')
		self.product_light = Product.objects.create(store=self.store, category=self.category, name='Light', price=1000, stock=10, weight_kg=Decimal('1.00'))
		self.product_heavy = Product.objects.create(store=self.store, category=self.category, name='Heavy', price=5000, stock=5, weight_kg=Decimal('25.00'))
		# create client
		self.client_user = User.objects.create_user(phone='+2419000002', password='clientpass')

	def test_delivery_cost_same_city_bike(self):
		order = Order.objects.create(client=self.client_user, store=self.store, city='CityA')
		OrderItem.objects.create(order=order, product=self.product_light, quantity=1, unit_price=self.product_light.price)
		order.calculate_totals()
		# weight 1kg -> bike multiplier 1.0 -> delivery_fee should be store.delivery_fee
		self.assertEqual(order.vehicle_type, 'bike')
		self.assertEqual(order.delivery_fee, self.store.delivery_fee)

	def test_delivery_cost_same_city_van(self):
		order = Order.objects.create(client=self.client_user, store=self.store, city='CityA')
		OrderItem.objects.create(order=order, product=self.product_heavy, quantity=1, unit_price=self.product_heavy.price)
		order.calculate_totals()
		# weight 25kg -> van multiplier 2.5 -> delivery_fee should be store.delivery_fee * 2.5
		expected = (self.store.delivery_fee * Decimal('2.50')).quantize(Decimal('0.01'))
		self.assertEqual(order.vehicle_type, 'van')
		self.assertEqual(order.delivery_fee, expected)

	def test_service_fee_fixed_and_operator_absorbed(self):
		# Create order with two items (subtotal = 6000)
		order = Order.objects.create(client=self.client_user, store=self.store, city='CityA')
		OrderItem.objects.create(order=order, product=self.product_light, quantity=3, unit_price=self.product_light.price)
		OrderItem.objects.create(order=order, product=self.product_heavy, quantity=1, unit_price=self.product_heavy.price)
		# Force calculate totals
		order.calculate_totals()
		# Subtotal: 3*1000 + 1*5000 = 8000? Wait check: 3*1000=3000 + 5000 = 8000
		expected_subtotal = self.product_light.price * 3 + self.product_heavy.price * 1
		self.assertEqual(order.items_total, expected_subtotal)
		# Service fee = 5% of subtotal
		expected_service = (expected_subtotal * Decimal('0.05')).quantize(Decimal('0.01'))
		self.assertEqual(order.service_fee, expected_service)
		# Operator fee computed but not included in total_amount
		expected_operator = order.calculate_operator_fee()
		self.assertEqual(order.operator_fee, expected_operator)
		# Total amount should NOT include operator_fee
		expected_total = order.items_total + order.delivery_fee + order.service_fee + order.tax_amount + order.payment_fees
		self.assertEqual(order.total_amount, expected_total)
