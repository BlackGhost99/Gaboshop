"""Rapport financier détaillé par catégorie : outil « detailed_finance » du forfait, commerces et grossistes."""
from datetime import time, timedelta
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from b2b.models import B2BStoreSubscription, B2BSubscriptionPlan
from orders.models import Order, OrderItem
from payments.models import StoreSubscription, SubscriptionPlan
from products.models import Product, ProductCategory
from stores.models import Store, StoreCategory
from users.models import User

URL = '/api/v1/store/finance/summary/'


class DetailedReportBase(TestCase):
    wholesaler = False

    def setUp(self):
        cache.clear()
        self.category = StoreCategory.objects.create(name='Finance détaillée')
        self.manager = User.objects.create_user(phone='+24107650101', password='Mapeto88x', user_type='store_manager')
        self.store = Store.objects.create(
            is_verified=True, name='Commerce finance', category=self.category, manager=self.manager, phone='+24107650110',
            address='Libreville', zone='Centre', commission_rate=Decimal('5'),
            opening_time=time(0, 0), closing_time=time(23, 59))
        if self.wholesaler:
            self.store.set_market_mode('b2b')
            self.store.save()
        self.client_user = User.objects.create_user(
            phone='+24107650102', password='Mapeto88x', user_type='client', first_name='Awa', last_name='Nzamba')
        self.shoes = ProductCategory.objects.create(name='Chaussures', store_category=self.category)
        self.bags = ProductCategory.objects.create(name='Sacs', store_category=self.category)
        self.sneakers = Product.objects.create(store=self.store, name='Baskets', price=10000, stock=50, category=self.shoes)
        self.bag = Product.objects.create(store=self.store, name='Sac', price=5000, stock=50, category=self.bags)
        self.loose = Product.objects.create(store=self.store, name='Divers', price=1000, stock=50)
        self.api = APIClient()
        self.api.force_authenticate(self.manager)

    def subscribe_b2c(self, plan_type='pro'):
        plan = SubscriptionPlan.objects.get(plan_type=plan_type)
        return StoreSubscription.objects.create(
            store=self.store, plan=plan, plan_name=plan.name, monthly_fee=plan.price, status='active',
            end_date=timezone.now().date() + timedelta(days=20))

    def subscribe_b2b(self, plan_type='pro'):
        plan = B2BSubscriptionPlan.objects.get(plan_type=plan_type)
        return B2BStoreSubscription.objects.create(
            store=self.store, plan=plan, plan_name=plan.name, monthly_fee=plan.price, status='active',
            end_date=timezone.now().date() + timedelta(days=20))

    def sale(self, lines, status='delivered', days_ago=0, buyer_store=None):
        order = Order.objects.create(
            client=self.client_user, store=self.store, status=status, is_b2b=buyer_store is not None,
            source_store=buyer_store, delivery_address='Louis', delivery_phone='+24107650999', delivery_zone='Centre')
        for product, quantity, price in lines:
            OrderItem.objects.create(order=order, product=product, quantity=quantity, unit_price=price)
        if days_ago:
            Order.objects.filter(pk=order.pk).update(created_at=timezone.now() - timedelta(days=days_ago))
        return order

    def summary(self, **params):
        res = self.api.get(URL, params)
        self.assertEqual(res.status_code, 200, res.content)
        return res.json()['data']


class CommerceReportTests(DetailedReportBase):
    def test_pro_shop_gets_the_report_grouped_by_category(self):
        self.subscribe_b2c()
        first = self.sale([(self.sneakers, 2, 10000), (self.bag, 1, 5000)])
        second = self.sale([(self.sneakers, 1, 10000), (self.loose, 3, 1000)], days_ago=1)
        self.sale([(self.bag, 9, 5000)], status='cancelled')  # jamais comptée
        data = self.summary()
        self.assertTrue(data['detailed_report']['available'])
        self.assertEqual(data['detailed_report']['message'], '')
        report = data['category_detailed_report']
        self.assertEqual([c['category_name'] for c in report], ['Chaussures', 'Sacs', 'Sans catégorie'])
        shoes = report[0]
        self.assertEqual(Decimal(shoes['total_sales']), Decimal('30000'))
        self.assertEqual((shoes['items_sold'], shoes['orders_count']), (3, 2))
        self.assertEqual([o['order_number'] for o in shoes['orders']], [first.order_number, second.order_number])
        self.assertEqual(shoes['orders'][0]['buyer_name'], 'Awa Nzamba')
        self.assertEqual(Decimal(shoes['orders'][0]['sales']), Decimal('20000'))
        self.assertEqual(Decimal(report[1]['total_sales']), Decimal('5000'))
        self.assertEqual(Decimal(report[2]['total_sales']), Decimal('3000'))
        # Le total du rapport retombe sur les ventes livrées
        self.assertEqual(sum(Decimal(c['total_sales']) for c in report), Decimal('38000'))

    def test_free_shop_gets_no_report_and_is_told_which_plan_has_it(self):
        self.sale([(self.sneakers, 1, 10000)])
        data = self.summary()
        self.assertFalse(data['detailed_report']['available'])
        self.assertEqual(data['category_detailed_report'], [])
        message = data['detailed_report']['message']
        self.assertIn('Rapport financier détaillé', message)
        self.assertIn('Pro', message)

    def test_last_day_of_the_range_is_included(self):
        self.subscribe_b2c()
        self.sale([(self.sneakers, 1, 10000)])
        today = timezone.now().date().isoformat()
        report = self.summary(date_from=today, date_to=today)['category_detailed_report']
        self.assertEqual(len(report), 1)
        yesterday = (timezone.now().date() - timedelta(days=5)).isoformat()
        self.assertEqual(self.summary(date_from=yesterday, date_to=yesterday)['category_detailed_report'], [])

    def test_another_shops_sales_never_appear(self):
        self.subscribe_b2c()
        other_manager = User.objects.create_user(phone='+24107650103', password='Mapeto88x', user_type='store_manager')
        other = Store.objects.create(is_verified=True, name='Autre', category=self.category, manager=other_manager,
                                     phone='+24107650111', address='Libreville', zone='Centre')
        product = Product.objects.create(store=other, name='Chapeau', price=2000, stock=5)
        order = Order.objects.create(client=self.client_user, store=other, status='delivered', delivery_address='x',
                                     delivery_phone='+24107650998', delivery_zone='Centre')
        OrderItem.objects.create(order=order, product=product, quantity=1, unit_price=2000)
        self.assertEqual(self.summary()['category_detailed_report'], [])

    def test_sales_list_includes_the_last_day_too(self):
        self.subscribe_b2c()
        self.sale([(self.sneakers, 1, 10000)])
        today = timezone.now().date().isoformat()
        res = self.api.get('/api/v1/store/finance/sales/', {'date_from': today, 'date_to': today})
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()['count'], 1)


class WholesalerReportTests(DetailedReportBase):
    wholesaler = True

    def test_pro_wholesaler_sees_buyer_shops_in_the_report(self):
        self.subscribe_b2b('pro')
        buyer_manager = User.objects.create_user(phone='+24107650104', password='Mapeto88x', user_type='store_manager')
        buyer = Store.objects.create(is_verified=True, name='Boutique Océane', category=self.category,
                                     manager=buyer_manager, phone='+24107650112', address='Libreville', zone='Centre')
        self.sale([(self.sneakers, 12, 9000)], buyer_store=buyer)
        data = self.summary()
        self.assertTrue(data['detailed_report']['available'])
        order = data['category_detailed_report'][0]['orders'][0]
        self.assertEqual(order['buyer_name'], 'Boutique Océane')
        self.assertTrue(order['is_b2b'])
        self.assertEqual(Decimal(order['sales']), Decimal('108000'))

    def test_free_wholesaler_is_pointed_to_the_wholesale_plan(self):
        self.subscribe_b2b('free')
        self.sale([(self.sneakers, 1, 10000)])
        data = self.summary()
        self.assertFalse(data['detailed_report']['available'])
        self.assertEqual(data['category_detailed_report'], [])
        self.assertIn(B2BSubscriptionPlan.objects.get(plan_type='pro').name, data['detailed_report']['message'])
