"""Outils du forfait grossiste rendus réels : prix dégressifs, promotions, plafond de commerces clients."""
from datetime import time, timedelta
from decimal import Decimal

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from b2b.models import B2BProductPricing, B2BProfile, B2BStoreSubscription, B2BSubscriptionPlan
from b2b.services.permissions import BUYER_CAP_MESSAGE, check_b2c_buyer_quota
from notifications.models import Notification
from orders.models import Order
from payments.models import StoreSubscription, SubscriptionPlan
from products.models import Product
from stores.models import Store, StoreCategory
from users.models import User


def make_store(phone, name, category, wholesaler=False):
    manager = User.objects.create_user(phone=phone, password='Mapeto88x', user_type='store_manager')
    store = Store.objects.create(
        is_verified=True, name=name, category=category, manager=manager, phone='+24165' + phone[-7:],
        address='Libreville', zone='Centre', commission_rate=Decimal('5'),
        opening_time=time(0, 0), closing_time=time(23, 59))
    if wholesaler:
        store.set_market_mode('b2b')
        store.save()
        B2BProfile.objects.update_or_create(store=store, defaults={'is_active': True})
    return manager, store


class WholesaleBase(TestCase):
    def setUp(self):
        cache.clear()
        self.category = StoreCategory.objects.create(name='Gros outils')
        self.b2b_free = B2BSubscriptionPlan.objects.get(plan_type='free')
        self.b2b_pro = B2BSubscriptionPlan.objects.get(plan_type='pro')
        self.wholesaler_manager, self.wholesaler = make_store('+24107630101', 'Grossiste outils', self.category, True)
        self.product = Product.objects.create(store=self.wholesaler, name='Riz 25 kg', price=20000, stock=500)
        self.wholesale_api = APIClient()
        self.wholesale_api.force_authenticate(self.wholesaler_manager)
        SubscriptionPlan.objects.filter(plan_type='pro').update(can_access_b2b=True)
        self.buyer_plan = SubscriptionPlan.objects.get(plan_type='pro')
        self.buyers = []

    def subscribe_wholesaler(self, plan=None, days=20):
        plan = plan or self.b2b_pro
        B2BStoreSubscription.objects.filter(store=self.wholesaler).delete()
        return B2BStoreSubscription.objects.create(
            store=self.wholesaler, plan=plan, plan_name=plan.name, monthly_fee=plan.price, status='active',
            end_date=timezone.now().date() + timedelta(days=days))

    def new_buyer(self, index):
        manager, store = make_store(f'+2410764020{index}', f'Commerce acheteur {index}', self.category)
        StoreSubscription.objects.create(
            store=store, plan=self.buyer_plan, plan_name=self.buyer_plan.name, monthly_fee=self.buyer_plan.price,
            status='active', end_date=timezone.now().date() + timedelta(days=20))
        api = APIClient()
        api.force_authenticate(manager)
        self.buyers.append((store, api))
        return store, api

    def price(self, price, quantity=1, product=None):
        return B2BProductPricing.objects.create(
            product=product or self.product, b2b_store=self.wholesaler, b2b_price=price, min_quantity=quantity)

    def order(self, api, quantity, items=None, **extra):
        payload = {
            'wholesaler_id': self.wholesaler.id, 'items': items or [{'product_id': self.product.id, 'quantity': quantity}],
            'delivery_address': 'Quartier Louis', 'delivery_phone': '+24107640999', 'delivery_zone': 'Centre',
            'city': 'Libreville', **extra,
        }
        return api.post('/api/v1/b2b/orders/', payload, format='json')


class PrixDegressifsApiTests(WholesaleBase):
    def test_any_wholesaler_sets_its_base_price_without_the_tool(self):
        self.subscribe_wholesaler(self.b2b_free)
        res = self.wholesale_api.post('/api/v1/b2b/my-pricing/', {'product_id': self.product.id, 'b2b_price': '15000',
                                                                    'min_quantity': 2}, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        base = res.json()['data']['product']['base']
        self.assertEqual((base['b2b_price'], base['min_quantity']), (15000.0, 2))

    def test_free_plan_cannot_add_a_tier_and_is_told_which_plan_has_it(self):
        self.subscribe_wholesaler(self.b2b_free)
        self.price(15000)
        res = self.wholesale_api.post('/api/v1/b2b/my-pricing/', {'product_id': self.product.id, 'b2b_price': '13000',
                                                                    'min_quantity': 10}, format='json')
        self.assertEqual(res.status_code, 403, res.content)
        message = res.json()['error']['message']
        self.assertIn('Prix dégressifs', message)
        self.assertIn(self.b2b_pro.name, message)
        self.assertEqual(B2BProductPricing.objects.filter(b2b_store=self.wholesaler).count(), 1)

    def test_pro_wholesaler_manages_tiers(self):
        self.subscribe_wholesaler()
        self.price(15000)
        res = self.wholesale_api.post('/api/v1/b2b/my-pricing/', {'product_id': self.product.id, 'b2b_price': '13500',
                                                                    'min_quantity': 10}, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        tier = res.json()['data']['product']['tiers'][0]
        self.assertEqual((tier['min_quantity'], tier['saving_percent']), (10, 10))
        res = self.wholesale_api.put(f"/api/v1/b2b/my-pricing/{tier['id']}/", {'b2b_price': '12000'}, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()['data']['product']['tiers'][0]['b2b_price'], 12000.0)
        res = self.wholesale_api.delete(f"/api/v1/b2b/my-pricing/{tier['id']}/")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['data']['product']['tiers'], [])

    def test_a_tier_must_cost_less_and_start_after_the_base(self):
        self.subscribe_wholesaler()
        self.price(15000, 2)
        post = lambda price, quantity: self.wholesale_api.post(
            '/api/v1/b2b/my-pricing/', {'product_id': self.product.id, 'b2b_price': price, 'min_quantity': quantity},
            format='json')
        self.assertEqual(post('16000', 10).status_code, 400)  # plus cher que le prix de base
        self.assertEqual(post('14000', 2).status_code, 400)   # même seuil que le prix de base
        self.assertEqual(post('14000', 1).status_code, 400)   # avant le prix de base
        self.assertEqual(post('0', 10).status_code, 400)
        self.assertEqual(post('14000', 10).status_code, 201)
        self.assertEqual(post('13000', 10).status_code, 400)  # seuil déjà pris
        self.assertEqual(post('14500', 20).status_code, 400)  # plus cher que le palier précédent
        self.assertEqual(post('12000', 20).status_code, 201)

    def test_a_wholesaler_cannot_touch_another_wholesalers_prices(self):
        self.subscribe_wholesaler()
        other_manager, other = make_store('+24107630102', 'Autre grossiste', self.category, True)
        row = B2BProductPricing.objects.create(
            product=Product.objects.create(store=other, name='Sucre', price=1000, stock=5), b2b_store=other, b2b_price=900)
        self.assertEqual(self.wholesale_api.delete(f'/api/v1/b2b/my-pricing/{row.id}/').status_code, 404)
        res = self.wholesale_api.post('/api/v1/b2b/my-pricing/', {'product_id': row.product_id, 'b2b_price': '800'},
                                      format='json')
        self.assertEqual(res.status_code, 404)

    def test_a_retail_store_has_no_wholesale_prices(self):
        manager, retailer = make_store('+24107630103', 'Détaillant', self.category)
        api = APIClient()
        api.force_authenticate(manager)
        self.assertEqual(api.get('/api/v1/b2b/my-pricing/').status_code, 403)

    def test_lost_plan_keeps_tiers_removable_but_not_editable(self):
        self.subscribe_wholesaler(self.b2b_free)
        self.price(15000)
        tier = self.price(13000, 10)
        listing = self.wholesale_api.get('/api/v1/b2b/my-pricing/').json()['data']
        self.assertFalse(listing['bulk_discounts'])
        self.assertIn('Prix dégressifs', listing['bulk_discounts_message'])
        self.assertFalse(listing['products'][0]['tiers_applied'])
        res = self.wholesale_api.put(f'/api/v1/b2b/my-pricing/{tier.id}/', {'b2b_price': '12000'}, format='json')
        self.assertEqual(res.status_code, 403)
        self.assertEqual(self.wholesale_api.put(f'/api/v1/b2b/my-pricing/{tier.id}/', {'is_active': False},
                                                format='json').status_code, 200)
        self.assertEqual(self.wholesale_api.delete(f'/api/v1/b2b/my-pricing/{tier.id}/').status_code, 200)


class CatalogueEtCommandeTests(WholesaleBase):
    def setUp(self):
        super().setUp()
        self.price(15000, 2)
        self.price(13500, 10)
        self.price(12000, 50)
        self.store, self.buyer = self.new_buyer(1)

    def catalog_product(self):
        res = self.buyer.get(f'/api/v1/b2b/wholesalers/{self.wholesaler.id}/catalog/')
        self.assertEqual(res.status_code, 200, res.content)
        return res.json()['data']['products'][0]

    def test_buyer_sees_the_tiers_when_the_plan_has_the_tool(self):
        self.subscribe_wholesaler()
        product = self.catalog_product()
        self.assertEqual(product['b2b_price'], 15000.0)
        self.assertEqual(product['min_quantity'], 2)
        self.assertEqual([(t['min_qty'], t['price'], t['saving_percent']) for t in product['pricing_tiers']],
                         [(2, 15000.0, 0), (10, 13500.0, 10), (50, 12000.0, 20)])

    def test_buyer_sees_only_the_base_price_without_the_tool(self):
        self.subscribe_wholesaler(self.b2b_free)
        product = self.catalog_product()
        self.assertEqual(product['b2b_price'], 15000.0)
        self.assertEqual(product['pricing_tiers'], [])

    def test_order_is_priced_by_quantity_on_the_server(self):
        self.subscribe_wholesaler()
        for quantity, unit in ((2, 15000), (9, 15000), (10, 13500), (49, 13500), (50, 12000)):
            res = self.order(self.buyer, quantity, items=[{'product_id': self.product.id, 'quantity': quantity,
                                                           'b2b_price': '1'}])
            self.assertEqual(res.status_code, 201, res.content)
            item = res.json()['data']['items'][0]
            self.assertEqual(item['unit_price'], float(unit), quantity)
            self.assertEqual(item['subtotal'], float(unit * quantity))

    def test_split_lines_count_for_their_total_quantity(self):
        self.subscribe_wholesaler()
        res = self.order(self.buyer, 0, items=[{'product_id': self.product.id, 'quantity': 6},
                                               {'product_id': self.product.id, 'quantity': 6}])
        self.assertEqual(res.status_code, 201, res.content)
        items = res.json()['data']['items']
        self.assertEqual([(i['quantity'], i['unit_price']) for i in items], [(12, 13500.0)])

    def test_lost_plan_falls_back_to_the_base_price(self):
        self.subscribe_wholesaler(self.b2b_free)
        res = self.order(self.buyer, 60)
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()['data']['items'][0]['unit_price'], 15000.0)

    def test_below_the_minimum_quantity_is_refused_not_ignored(self):
        self.subscribe_wholesaler()
        res = self.order(self.buyer, 1)
        self.assertEqual(res.status_code, 400, res.content)
        self.assertIn('Quantité minimum de 2', res.json()['error']['message'])
        self.assertFalse(Order.objects.filter(is_b2b=True).exists())

    def test_inactive_tier_is_not_applied(self):
        self.subscribe_wholesaler()
        B2BProductPricing.objects.filter(min_quantity=10).update(is_active=False)
        res = self.order(self.buyer, 20)
        self.assertEqual(res.json()['data']['items'][0]['unit_price'], 15000.0)


class PlafondCommercesClientsTests(WholesaleBase):
    def setUp(self):
        super().setUp()
        self.price(15000)
        self.b2b_pro.max_b2c_buyers = 1
        self.b2b_pro.save()
        self.subscribe_wholesaler()

    def test_new_buyer_over_the_cap_is_refused_and_the_wholesaler_is_told_once(self):
        _, first = self.new_buyer(1)
        _, second = self.new_buyer(2)
        _, third = self.new_buyer(3)
        self.assertEqual(self.order(first, 1).status_code, 201)
        res = self.order(second, 1)
        self.assertEqual(res.status_code, 403, res.content)
        self.assertEqual(res.json()['error']['message'], BUYER_CAP_MESSAGE)
        self.assertEqual(self.order(third, 1).status_code, 403)
        self.assertEqual(Order.objects.filter(is_b2b=True).count(), 1)
        notes = Notification.objects.filter(user=self.wholesaler_manager, metadata__reason_code='b2c_buyer_cap')
        self.assertEqual(notes.count(), 1)
        self.assertIn('Commerce acheteur 2', notes[0].title)
        self.assertIn('1 commerces clients', notes[0].body)

    def test_existing_client_keeps_being_served(self):
        _, first = self.new_buyer(1)
        self.assertEqual(self.order(first, 1).status_code, 201)
        self.assertEqual(self.order(first, 2).status_code, 201)

    def test_cancelled_order_does_not_hold_a_place(self):
        _, first = self.new_buyer(1)
        _, second = self.new_buyer(2)
        self.assertEqual(self.order(first, 1).status_code, 201)
        Order.objects.filter(is_b2b=True).update(status='cancelled')
        self.assertEqual(self.order(second, 1).status_code, 201)

    def test_old_clients_leave_the_30_day_window(self):
        _, first = self.new_buyer(1)
        _, second = self.new_buyer(2)
        self.assertEqual(self.order(first, 1).status_code, 201)
        Order.objects.filter(is_b2b=True).update(created_at=timezone.now() - timedelta(days=45))
        self.assertEqual(self.order(second, 1).status_code, 201)

    def test_no_cap_means_no_refusal(self):
        self.b2b_pro.max_b2c_buyers = None
        self.b2b_pro.save()
        for index in range(1, 4):
            _, api = self.new_buyer(index)
            self.assertEqual(self.order(api, 1).status_code, 201)

    def test_notification_names_the_plan_that_lifts_the_cap(self):
        business = B2BSubscriptionPlan.objects.get(plan_type='business')
        business.is_available = True
        business.max_b2c_buyers = None
        business.save()
        self.b2b_free.max_b2c_buyers = 1
        self.b2b_free.save()
        self.subscribe_wholesaler(self.b2b_free)
        _, first = self.new_buyer(1)
        _, second = self.new_buyer(2)
        self.assertEqual(self.order(first, 1).status_code, 201)
        self.assertEqual(self.order(second, 1).status_code, 403)
        note = Notification.objects.get(user=self.wholesaler_manager, metadata__reason_code='b2c_buyer_cap')
        self.assertIn('Passez au forfait', note.metadata['next_step'])

    def test_catalog_tells_a_new_buyer_up_front(self):
        _, first = self.new_buyer(1)
        _, second = self.new_buyer(2)
        self.assertEqual(self.order(first, 1).status_code, 201)
        res = second.get(f'/api/v1/b2b/wholesalers/{self.wholesaler.id}/catalog/').json()['data']['wholesaler']
        self.assertFalse(res['accepts_new_buyers'])
        self.assertEqual(res['buyer_cap_message'], BUYER_CAP_MESSAGE)
        res = first.get(f'/api/v1/b2b/wholesalers/{self.wholesaler.id}/catalog/').json()['data']['wholesaler']
        self.assertTrue(res['accepts_new_buyers'])

    def test_quota_function(self):
        store, _ = self.new_buyer(1)
        self.assertEqual(check_b2c_buyer_quota(self.wholesaler, store), (True, {
            'max_buyers': 1, 'current_buyers': 0, 'message': ''}))


class PromotionsGrossisteTests(WholesaleBase):
    def create(self):
        return self.wholesale_api.post(
            f'/api/v1/stores/{self.wholesaler.id}/products/create/',
            {'name': 'Huile 5 L', 'price': '8000', 'compare_price': '10000', 'stock': 20, 'weight_kg': '5',
             'length_m': '0.3'}, format='json')

    def test_pro_wholesaler_can_add_a_promotion(self):
        self.subscribe_wholesaler()
        res = self.create()
        self.assertEqual(res.status_code, 201, res.content)

    def test_free_wholesaler_is_refused_with_the_plan_that_has_it(self):
        self.subscribe_wholesaler(self.b2b_free)
        res = self.create()
        self.assertEqual(res.status_code, 400, res.content)
        self.assertIn(self.b2b_pro.name, str(res.json()))

    def test_buyer_sees_the_struck_price_in_the_catalog(self):
        self.subscribe_wholesaler()
        self.product.compare_price = Decimal('25000')
        self.product.save()
        self.price(15000)
        _, buyer = self.new_buyer(1)
        product = buyer.get(f'/api/v1/b2b/wholesalers/{self.wholesaler.id}/catalog/').json()['data']['products'][0]
        self.assertEqual(float(product['compare_price']), 25000.0)
        self.assertEqual(product['promo'], {'compare_price': 25000.0, 'price': 20000.0, 'saving_percent': 20})

    def test_no_struck_price_without_a_promotion(self):
        self.subscribe_wholesaler()
        self.price(15000)
        _, buyer = self.new_buyer(1)
        product = buyer.get(f'/api/v1/b2b/wholesalers/{self.wholesaler.id}/catalog/').json()['data']['products'][0]
        self.assertIsNone(product['promo'])


class BadgePopulaireTests(WholesaleBase):
    def test_wholesale_plans_api_exposes_the_popular_badge(self):
        self.b2b_pro.is_popular = True
        self.b2b_pro.save()
        B2BSubscriptionPlan.objects.exclude(pk=self.b2b_pro.pk).update(is_popular=False)
        res = self.wholesale_api.get('/api/v1/payments/subscription-plans/')
        self.assertEqual(res.status_code, 200, res.content)
        popular = {plan['plan_type']: plan['is_popular'] for plan in res.json()['plans']}
        self.assertTrue(popular['pro'])
        self.assertFalse(popular['free'])

    def test_wholesale_card_shows_the_cap_and_tools(self):
        self.b2b_pro.max_b2c_buyers = 25
        self.b2b_pro.save()
        titles = [f['title'] for f in self.b2b_pro.get_all_features() if f.get('enabled', True)]
        self.assertIn("Jusqu'à 25 commerces clients", titles)
        self.assertIn('Prix dégressifs : tarifs par palier de quantité pour vos acheteurs', titles)
