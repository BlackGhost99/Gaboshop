"""Modèle économique V2 (15 oct. 2026) : simulateur, part Gaboshop de la livraison en paiement direct, dettes."""
from decimal import Decimal

from django.test import TestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from api.models import SystemSettings
from delivery.models import Delivery
from orders.models import Order, OrderItem
from payments.configuration import DEFAULT_PAYMENT_POLICY
from payments.direct_service import (
    collect_platform_debt, courier_earning, create_arrangement, platform_debts, sync_on_order_status,
)
from payments.economics import clean_inputs, simulate
from products.models import Product, ProductCategory
from stores.models import Store, StoreCategory
from users.models import User


def sim(**over):
    base = {
        'basket': 15000, 'delivery_fee': 2000, 'commission_percent': 8, 'courier_share_percent': 80,
        'client_fee_percent': 0, 'singpay_fee_percent': 2.5, 'singpay_payout_fee_percent': 0,
        'forfait_discount_percent': 0, 'debt_recovery_percent': 100, 'flow': 'online',
    }
    base.update(over)
    return simulate(clean_inputs(base))


class SimulatorTests(TestCase):
    def test_online_today(self):
        r = sim()
        self.assertEqual(r['client_pays'], '17000')
        self.assertEqual(r['store_receives'], '13800')
        self.assertEqual(r['courier_receives'], '1600')
        # 1 200 commission + 400 livraison - 425 SingPay
        self.assertEqual(r['gaboshop'], '1175')

    def test_online_client_fee_and_payout_fees(self):
        r = sim(commission_percent=5, client_fee_percent=1.5, singpay_payout_fee_percent=2.5)
        lines = {line['key']: line['amount'] for line in r['lines']}
        self.assertEqual(lines['client_fee'], '255')
        self.assertEqual(r['client_pays'], '17255')
        self.assertEqual(lines['payouts'], '-396')
        self.assertEqual(r['gaboshop'], str(750 + 400 + 255 - 431 - 396))

    def test_forfait_above_margin_loses_money_on_delivery(self):
        r = sim(forfait_discount_percent=50, commission_percent=0, singpay_fee_percent=0)
        self.assertEqual(r['gaboshop'], '-600')  # 400 de marge - 1 000 de réduction

    def test_store_delivers_online(self):
        r = sim(store_delivers=True)
        self.assertEqual(r['courier_receives'], '0')
        self.assertEqual(r['store_receives'], '15800')

    def test_direct_with_and_without_margin(self):
        on = sim(flow='direct', direct_delivery_margin=True, debt_recovery_percent=50)
        self.assertEqual(on['courier_receives'], '1600')
        self.assertEqual(on['debt_to_gaboshop'], '1600')
        self.assertEqual(on['gaboshop'], '800')
        off = sim(flow='direct', direct_delivery_margin=False)
        self.assertEqual(off['courier_receives'], '2000')
        self.assertEqual(off['debt_to_gaboshop'], '1200')

    def test_small_order_fee_only_under_threshold(self):
        small = sim(basket=4000, small_order_fee=200, small_order_threshold=5000)
        self.assertIn({'key': 'small_order', 'label': 'Frais petit panier', 'amount': '200'}, small['lines'])
        big = sim(basket=50000, small_order_fee=200, small_order_threshold=5000)
        self.assertIn({'key': 'small_order', 'label': 'Frais petit panier', 'amount': '0'}, big['lines'])

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            sim(commission_percent=150)
        with self.assertRaises(ValueError):
            sim(basket='abc')
        with self.assertRaises(ValueError):
            sim(flow='autre')


class SimulatorApiTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(phone='+24106100001', password='x', user_type='admin', is_staff=True)
        self.manager = User.objects.create_user(phone='+24106100002', password='x', user_type='store_manager')
        self.api = APIClient()

    def test_admin_only(self):
        self.api.force_authenticate(self.manager)
        self.assertEqual(self.api.get('/api/v1/admin/finance/simulator/').status_code, 403)
        self.assertEqual(self.api.post('/api/v1/admin/finance/simulator/', {}, format='json').status_code, 403)

    def test_defaults_then_simulate(self):
        self.api.force_authenticate(self.admin)
        res = self.api.get('/api/v1/admin/finance/simulator/')
        self.assertEqual(res.status_code, 200)
        defaults = res.json()['data']['defaults']
        self.assertEqual(Decimal(defaults['singpay_fee_percent']), Decimal('2.5'))
        self.assertEqual(res.json()['data']['real']['delivered_orders'], 0)
        res = self.api.post('/api/v1/admin/finance/simulator/', defaults, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        res = self.api.post('/api/v1/admin/finance/simulator/', {**defaults, 'basket': -1}, format='json')
        self.assertEqual(res.status_code, 400)

    def test_singpay_cost_hidden_from_public_settings(self):
        res = APIClient().get('/api/v1/settings/')
        self.assertNotIn('singpay_fee_percent', res.json()['data'])
        self.assertIn('sponsoring_enabled', res.json()['data'])


class DirectDeliveryMarginTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(phone='+24106200001', password='x', user_type='admin', is_staff=True)
        self.manager = User.objects.create_user(phone='+24106200002', password='x', user_type='store_manager')
        self.buyer = User.objects.create_user(phone='+24106200003', password='x', user_type='client')
        self.courier = User.objects.create_user(phone='+24106200004', password='x', user_type='delivery_agent')
        category = StoreCategory.objects.create(name='Test')
        self.store = Store.objects.create(name='Commerce', category=category, manager=self.manager, phone='+24106200100',
                                          address='Libreville', zone='Centre', commission_rate=Decimal('8'))
        pcat = ProductCategory.objects.create(store_category=category, name='Produits', commission_rate=Decimal('8'))
        self.product = Product.objects.create(store=self.store, category=pcat, name='Article', price=Decimal('10000'), stock=50, weight_kg=Decimal('1'))
        settings = SystemSettings.get_settings()
        settings.payment_policy = DEFAULT_PAYMENT_POLICY
        settings.direct_delivery_margin = True
        settings.courier_share_percent = Decimal('80')
        settings.save()

    def make_order(self):
        order = Order.objects.create(client=self.buyer, store=self.store, delivery_address='Louis', delivery_phone='+24106200003',
                                     delivery_zone='Centre', delivery_fee=Decimal('2000'))
        OrderItem.objects.create(order=order, product=self.product, quantity=1, unit_price=self.product.price)
        order.items_total = Decimal('10000')
        order.delivery_fee = Decimal('2000')
        order.commission_rate = Decimal('8')
        order.commission_amount = Decimal('800')
        order.save()
        delivery = Delivery.objects.get(order=order)
        delivery.delivery_agent = self.courier
        delivery.save()
        return order

    def test_direct_split_courier_owes_gaboshop_share(self):
        order = self.make_order()
        arrangement = create_arrangement(order, 'direct_split', 'cash', user=self.buyer)
        margin = arrangement.obligations.get(kind='delivery_margin')
        self.assertEqual((margin.payer, margin.payee, margin.amount, margin.status), ('courier', 'platform', Decimal('400'), 'not_due'))
        order.delivery.refresh_from_db()
        self.assertEqual(order.delivery.agent_commission, Decimal('1600'))
        self.assertEqual(courier_earning(order), Decimal('1600'))

    def test_store_collects_all_store_owes_share_and_pays_courier_his_part(self):
        arrangement = create_arrangement(self.make_order(), 'store_collects_all', 'cash', user=self.buyer)
        self.assertEqual(arrangement.obligations.get(kind='delivery').amount, Decimal('1600'))
        margin = arrangement.obligations.get(kind='delivery_margin')
        self.assertEqual((margin.payer, margin.amount), ('store', Decimal('400')))

    def test_setting_off_keeps_full_fee_for_courier(self):
        SystemSettings.objects.filter(pk=1).update(direct_delivery_margin=False)
        order = self.make_order()
        arrangement = create_arrangement(order, 'direct_split', 'cash', user=self.buyer)
        self.assertFalse(arrangement.obligations.filter(kind='delivery_margin').exists())
        self.assertEqual(courier_earning(order), Decimal('2000'))

    def test_old_direct_order_is_not_changed_retroactively(self):
        order = self.make_order()
        arrangement = create_arrangement(order, 'direct_split', 'cash', user=self.buyer)
        arrangement.policy_snapshot.pop('direct_delivery_margin')
        arrangement.save(update_fields=['policy_snapshot'])
        order.refresh_from_db()
        self.assertEqual(courier_earning(order), Decimal('2000'))

    def test_online_order_unchanged(self):
        order = self.make_order()
        self.assertEqual(courier_earning(order), Decimal('1600'))

    def test_debt_due_on_delivery_cancelled_on_cancel(self):
        order = self.make_order()
        arrangement = create_arrangement(order, 'direct_split', 'cash', user=self.buyer)
        self.assertEqual(platform_debts('courier', self.courier), [])
        order.status = 'delivered'
        sync_on_order_status(order)
        self.assertEqual(arrangement.obligations.get(kind='delivery_margin').status, 'unpaid')
        self.assertEqual(sum(d.remaining_amount for d in platform_debts('courier', self.courier)), Decimal('400'))
        other = self.make_order()
        arr2 = create_arrangement(other, 'direct_split', 'cash', user=self.buyer)
        other.status = 'cancelled'
        sync_on_order_status(other)
        self.assertEqual(arr2.obligations.get(kind='delivery_margin').status, 'cancelled')

    def deliver(self, flow='direct_split'):
        order = self.make_order()
        create_arrangement(order, flow, 'cash', user=self.buyer)
        order.status = 'delivered'
        sync_on_order_status(order)
        return order

    def test_collect_courier_debt_partial_idempotent_and_capped(self):
        self.deliver()
        self.deliver()
        receipts = collect_platform_debt('courier', self.courier, '500', 'cash', '', self.admin, 'k1')
        self.assertEqual(sum(r.amount for r in receipts), Decimal('500'))
        again = collect_platform_debt('courier', self.courier, '500', 'cash', '', self.admin, 'k1')
        self.assertEqual({r.pk for r in again}, {r.pk for r in receipts})
        self.assertEqual(sum(d.remaining_amount for d in platform_debts('courier', self.courier)), Decimal('300'))
        with self.assertRaises(ValidationError):
            collect_platform_debt('courier', self.courier, '301', 'cash', '', self.admin, 'k2')
        with self.assertRaises(ValidationError):
            collect_platform_debt('courier', self.courier, '0', 'cash', '', self.admin, 'k3')

    def test_collect_store_debt_needs_unique_mobile_money_reference(self):
        self.deliver()
        collect_platform_debt('store', self.store, '400', 'airtel_money', 'MP1234', self.admin, 'k1')
        with self.assertRaises(ValidationError):
            collect_platform_debt('store', self.store, '100', 'airtel_money', 'MP1234', self.admin, 'k2')
        with self.assertRaises(ValidationError):
            collect_platform_debt('store', self.store, '100', 'airtel_money', '', self.admin, 'k3')

    def test_debt_api_permissions_and_listing(self):
        self.deliver()
        api = APIClient()
        api.force_authenticate(self.manager)
        self.assertEqual(api.get('/api/v1/payments/debts/').status_code, 403)
        self.assertEqual(api.post('/api/v1/payments/debts/collect/', {}, format='json').status_code, 403)
        mine = api.get('/api/v1/payments/debts/mine/').json()['data']
        self.assertEqual(Decimal(mine['total_due']), Decimal('800'))
        api.force_authenticate(self.courier)
        self.assertEqual(Decimal(api.get('/api/v1/payments/debts/mine/').json()['data']['total_due']), Decimal('400'))
        api.force_authenticate(self.admin)
        rows = api.get('/api/v1/payments/debts/').json()['data']
        self.assertEqual({(r['party'], r['total_due']) for r in rows}, {('store', '800.00'), ('courier', '400.00')})
        res = api.post('/api/v1/payments/debts/collect/', {'party': 'courier', 'id': self.courier.id, 'amount': '400',
                                                            'method': 'cash', 'idempotency_key': 'x1'}, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(Decimal(res.json()['data']['total_due']), Decimal('0'))
