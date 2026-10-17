"""Accès API des grossistes : clés d'intégration, authentification, endpoints, forfait et isolation."""
from datetime import time, timedelta
from decimal import Decimal
from unittest import mock

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from b2b.api_keys.authentication import ApiKeyRateThrottle
from b2b.models import B2BProductPricing, B2BStoreSubscription, B2BSubscriptionPlan, WholesalerApiKey
from b2b.models.api_key import hash_api_key
from orders.models import Order, OrderItem
from products.models import Product
from stores.models import Store, StoreCategory
from users.models import User

KEYS = '/api/v1/b2b/api-keys/'
INTEGRATION = '/api/v1/b2b/integration/'


def make_store(phone, name, wholesaler=True):
    manager = User.objects.create_user(phone=phone, password='Mapeto88x', user_type='store_manager')
    category, _ = StoreCategory.objects.get_or_create(name='Grossiste test API')
    store = Store.objects.create(
        is_verified=True, name=name, category=category, manager=manager, phone=phone, address='Libreville',
        zone='Centre', commission_rate=Decimal('5'), opening_time=time(0, 0), closing_time=time(23, 59))
    if wholesaler:
        store.set_market_mode('b2b')
        store.save()
    return store


class Base(TestCase):
    def setUp(self):
        cache.clear()
        self.free = B2BSubscriptionPlan.objects.get(plan_type='free')
        self.pro = B2BSubscriptionPlan.objects.get(plan_type='pro')
        for plan, value in ((self.free, False), (self.pro, True)):
            plan.has_api_access = value
            plan.is_active = True
            plan.is_available = True
            plan.save()
        self.store = make_store('+24107620101', 'Grossiste Alpha')
        self.other = make_store('+24107620102', 'Grossiste Beta')
        self.retailer = make_store('+24107620103', 'Détaillant Gamma', wholesaler=False)
        self.subscribe(self.store, self.pro)
        self.subscribe(self.other, self.pro)
        self.session = APIClient()
        self.session.force_authenticate(self.store.manager)
        self.client_key = APIClient()

    def subscribe(self, store, plan, days_left=20):
        B2BStoreSubscription.objects.filter(store=store).delete()
        return B2BStoreSubscription.objects.create(
            store=store, plan=plan, plan_name=plan.name, monthly_fee=plan.price, status='active',
            end_date=timezone.now().date() + timedelta(days=days_left))

    def create_key(self, name='Logiciel de caisse'):
        response = self.session.post(KEYS, {'name': name}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        return response.json()['data']['api_key'], response.json()['data']['key']

    def with_key(self, raw):
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Api-Key {raw}')
        return client

    def product(self, store=None, name='Riz 25 kg', price='15000', stock=10):
        return Product.objects.create(store=store or self.store, name=name, price=Decimal(price), stock=stock,
                                      weight_kg=Decimal('25'), length_m=Decimal('0.5'))

    def order(self, store=None, status='paid', is_b2b=True, product=None, quantity=2):
        store = store or self.store
        buyer = self.retailer
        client = buyer.manager
        order = Order.objects.create(
            client=client, store=store, source_store=buyer, is_b2b=is_b2b, status=status, items_total=Decimal('30000'),
            total_amount=Decimal('30000'), delivery_address='Akanda', delivery_phone='+24107000000', delivery_zone='Nord')
        Order.objects.filter(pk=order.pk).update(status=status)  # la création confirme seule les commandes payées
        order.refresh_from_db()
        OrderItem.objects.create(order=order, product=product or self.product(store), quantity=quantity,
                                 unit_price=Decimal('15000'))
        return order


class CreationTests(Base):
    def test_key_is_shown_once_and_only_its_hash_is_stored(self):
        raw, shown = self.create_key()
        self.assertTrue(raw.startswith('gbw_'))
        row = WholesalerApiKey.objects.get()
        self.assertEqual(row.key_hash, hash_api_key(raw))
        self.assertEqual(len(row.key_hash), 64)
        self.assertEqual(row.prefix, raw[:8])
        self.assertEqual(shown['prefix'], raw[:8])
        # Aucun champ de la base ne contient la clé complète.
        for value in (row.name, row.prefix, row.key_hash):
            self.assertNotIn(raw, str(value))
        listing = self.session.get(KEYS)
        self.assertNotIn(raw, listing.content.decode())
        self.assertNotIn('api_key', listing.json()['data'])
        self.assertEqual(listing.json()['data']['keys'][0]['prefix'], raw[:8])

    def test_name_is_required(self):
        response = self.session.post(KEYS, {'name': '  '}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(WholesalerApiKey.objects.count(), 0)

    def test_at_most_five_active_keys(self):
        for i in range(5):
            self.create_key(f'Clé {i}')
        response = self.session.post(KEYS, {'name': 'Sixième'}, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('5 clés actives', response.json()['error']['message'])
        WholesalerApiKey.objects.filter(store=self.store).first().revoke()
        self.assertEqual(self.session.post(KEYS, {'name': 'Sixième'}, format='json').status_code, 201)

    def test_plan_without_the_option_cannot_create_and_is_told_which_plan_offers_it(self):
        self.subscribe(self.store, self.free)
        response = self.session.post(KEYS, {'name': 'Logiciel'}, format='json')
        self.assertEqual(response.status_code, 403)
        message = response.json()['error']['message']
        self.assertIn(self.pro.name, message)
        self.assertEqual(WholesalerApiKey.objects.count(), 0)
        data = self.session.get(KEYS).json()['data']
        self.assertFalse(data['enabled'])
        self.assertEqual(data['required_plan']['name'], self.pro.name)
        self.assertIn(self.pro.name, data['message'])

    def test_a_retailer_has_no_api_access(self):
        retail = APIClient()
        retail.force_authenticate(self.retailer.manager)
        self.assertEqual(retail.get(KEYS).status_code, 403)
        self.assertEqual(retail.post(KEYS, {'name': 'x'}, format='json').status_code, 403)

    def test_management_needs_a_session(self):
        self.assertIn(APIClient().get(KEYS).status_code, (401, 403))
        self.assertIn(APIClient().post(KEYS, {'name': 'x'}, format='json').status_code, (401, 403))
        self.assertEqual(WholesalerApiKey.objects.count(), 0)


class RevocationTests(Base):
    def test_revoked_key_stops_working(self):
        raw, shown = self.create_key()
        self.assertEqual(self.with_key(raw).get(INTEGRATION + 'products/').status_code, 200)
        response = self.session.post(f"{KEYS}{shown['id']}/revoke/")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['data']['is_active'])
        self.assertIsNotNone(WholesalerApiKey.objects.get().revoked_at)
        denied = self.with_key(raw).get(INTEGRATION + 'products/')
        self.assertEqual(denied.status_code, 401)
        self.assertIn('révoquée', denied.json()['error']['message'])

    def test_revoking_twice_is_harmless(self):
        _, shown = self.create_key()
        self.session.post(f"{KEYS}{shown['id']}/revoke/")
        again = self.session.post(f"{KEYS}{shown['id']}/revoke/")
        self.assertEqual(again.status_code, 200)
        self.assertIn('déjà révoquée', again.json()['message'])

    def test_cannot_revoke_another_wholesalers_key(self):
        other_key, _ = WholesalerApiKey.generate(self.other, 'Beta')
        response = self.session.post(f'{KEYS}{other_key.id}/revoke/')
        self.assertEqual(response.status_code, 404)
        other_key.refresh_from_db()
        self.assertTrue(other_key.is_active)

    def test_revocation_is_allowed_even_after_losing_the_option(self):
        _, shown = self.create_key()
        self.subscribe(self.store, self.free)
        self.assertEqual(self.session.post(f"{KEYS}{shown['id']}/revoke/").status_code, 200)


class AuthenticationTests(Base):
    def test_both_headers_work_and_last_use_is_recorded(self):
        raw, _ = self.create_key()
        self.assertIsNone(WholesalerApiKey.objects.get().last_used_at)
        self.assertEqual(self.with_key(raw).get(INTEGRATION + 'products/').status_code, 200)
        self.assertIsNotNone(WholesalerApiKey.objects.get().last_used_at)
        client = APIClient()
        client.credentials(HTTP_X_API_KEY=raw)
        self.assertEqual(client.get(INTEGRATION + 'products/').status_code, 200)

    def test_missing_wrong_or_foreign_credentials_are_refused(self):
        raw, _ = self.create_key()
        self.assertEqual(APIClient().get(INTEGRATION + 'products/').status_code, 401)
        self.assertEqual(self.with_key(raw + 'x').get(INTEGRATION + 'products/').status_code, 401)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Api-Key')
        self.assertEqual(client.get(INTEGRATION + 'products/').status_code, 401)
        # Une session normale (JWT) n'ouvre pas les endpoints d'intégration.
        bearer = APIClient()
        bearer.credentials(HTTP_AUTHORIZATION='Bearer abc.def.ghi')
        self.assertEqual(bearer.get(INTEGRATION + 'products/').status_code, 401)
        self.assertEqual(self.session.get(INTEGRATION + 'products/').status_code, 403)
        # Et une clé n'ouvre pas la gestion des clés.
        self.assertIn(self.with_key(raw).get(KEYS).status_code, (401, 403))

    def test_losing_the_option_cuts_the_key_and_getting_it_back_restores_it(self):
        raw, _ = self.create_key()
        client = self.with_key(raw)
        self.subscribe(self.store, self.free)
        denied = client.get(INTEGRATION + 'products/')
        self.assertEqual(denied.status_code, 403)
        message = denied.json()['error']['message']
        self.assertIn("L'accès API n'est plus inclus dans votre forfait", message)
        self.assertIn(self.pro.name, message)
        self.assertTrue(WholesalerApiKey.objects.get().is_active)
        self.subscribe(self.store, self.pro)
        self.assertEqual(client.get(INTEGRATION + 'products/').status_code, 200)

    def test_expired_subscription_cuts_the_key(self):
        raw, _ = self.create_key()
        self.subscribe(self.store, self.pro, days_left=-2)
        self.assertEqual(self.with_key(raw).get(INTEGRATION + 'products/').status_code, 403)

    def test_deactivated_store_cuts_the_key(self):
        raw, _ = self.create_key()
        Store.objects.filter(pk=self.store.pk).update(is_active=False)
        self.assertEqual(self.with_key(raw).get(INTEGRATION + 'products/').status_code, 403)

    def test_throttle_limits_requests_per_key(self):
        raw, _ = self.create_key()
        with mock.patch.object(ApiKeyRateThrottle, 'rate', '3/minute'):
            client = self.with_key(raw)
            codes = [client.get(INTEGRATION + 'products/').status_code for _ in range(5)]
            self.assertEqual(codes, [200, 200, 200, 429, 429])
            blocked = client.get(INTEGRATION + 'products/')
            self.assertIn('Trop de requêtes', blocked.json()['error']['message'])
            self.assertTrue(blocked.has_header('Retry-After'))
            # Une autre clé a son propre quota.
            fresh = WholesalerApiKey.generate(self.other, 'Autre')[1]
            self.assertEqual(self.with_key(fresh).get(INTEGRATION + 'products/').status_code, 200)

    def test_default_rate_is_sixty_per_minute(self):
        self.assertEqual(ApiKeyRateThrottle.rate, '60/minute')


class ProductTests(Base):
    def setUp(self):
        super().setUp()
        self.raw, _ = self.create_key()
        self.api = self.with_key(self.raw)

    def test_list_shows_stock_price_and_status_of_my_products_only(self):
        mine = self.product(name='Riz 25 kg', stock=7)
        self.product(store=self.other, name='Huile Beta')
        B2BProductPricing.objects.create(product=mine, b2b_store=self.store, b2b_price=Decimal('13000'), min_quantity=10)
        body = self.api.get(INTEGRATION + 'products/').json()
        self.assertEqual(body['count'], 1)
        item = body['results'][0]
        self.assertEqual((item['id'], item['stock'], item['price'], item['is_available']), (mine.id, 7, '15000.00', True))
        self.assertEqual(item['b2b_prices'], [{'min_quantity': 10, 'max_quantity': None, 'price': '13000.00'}])

    def test_pagination_and_filters(self):
        for i in range(5):
            self.product(name=f'Article {i}')
        off = self.product(name='Retiré')
        Product.objects.filter(pk=off.pk).update(is_available=False)
        page = self.api.get(INTEGRATION + 'products/?page_size=2').json()
        self.assertEqual((page['count'], len(page['results'])), (6, 2))
        self.assertIsNotNone(page['next'])
        self.assertEqual(self.api.get(INTEGRATION + 'products/?is_available=false').json()['count'], 1)
        self.assertEqual(self.api.get(INTEGRATION + 'products/?search=article 3').json()['count'], 1)

    def test_patch_updates_stock_and_price(self):
        product = self.product()
        response = self.api.patch(f'{INTEGRATION}products/{product.id}/', {'stock': 42, 'price': '16500.50'}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        product.refresh_from_db()
        self.assertEqual((product.stock, product.price), (42, Decimal('16500.50')))
        self.assertEqual(response.json()['stock'], 42)
        only_stock = self.api.patch(f'{INTEGRATION}products/{product.id}/', {'stock': 0}, format='json')
        self.assertEqual(only_stock.status_code, 200)
        product.refresh_from_db()
        self.assertEqual((product.stock, product.price), (0, Decimal('16500.50')))

    def test_patch_applies_the_app_rules(self):
        product = self.product(stock=10)
        url = f'{INTEGRATION}products/{product.id}/'
        for payload in ({'stock': -1}, {'price': 0}, {'price': '-5'}, {'stock': 'beaucoup'}, {'stock': 1.5},
                        {'price': 'abc'}, {}, {'name': 'Autre nom'}, {'stock': 5, 'is_available': False},
                        {'total_amount': 1}):
            response = self.api.patch(url, payload, format='json')
            self.assertEqual(response.status_code, 400, payload)
            self.assertFalse(response.json()['success'])
        product.refresh_from_db()
        self.assertEqual((product.stock, product.price, product.name, product.is_available),
                         (10, Decimal('15000'), 'Riz 25 kg', True))

    def test_negative_stock_message_is_clear(self):
        product = self.product()
        response = self.api.patch(f'{INTEGRATION}products/{product.id}/', {'stock': -3}, format='json')
        self.assertIn('Le stock ne peut pas être négatif', str(response.json()))
        response = self.api.patch(f'{INTEGRATION}products/{product.id}/', {'price': 0}, format='json')
        self.assertIn('Le prix doit être plus grand que 0', str(response.json()))

    def test_another_wholesalers_product_is_invisible_and_untouchable(self):
        foreign = self.product(store=self.other, stock=5)
        self.assertEqual(self.api.get(f'{INTEGRATION}products/{foreign.id}/').status_code, 404)
        response = self.api.patch(f'{INTEGRATION}products/{foreign.id}/', {'stock': 999}, format='json')
        self.assertEqual(response.status_code, 404)
        foreign.refresh_from_db()
        self.assertEqual(foreign.stock, 5)

    def test_no_delete_no_create(self):
        product = self.product()
        self.assertEqual(self.api.delete(f'{INTEGRATION}products/{product.id}/').status_code, 405)
        self.assertEqual(self.api.post(INTEGRATION + 'products/', {'name': 'x'}, format='json').status_code, 405)
        self.assertTrue(Product.objects.filter(pk=product.pk).exists())


class OrderTests(Base):
    def setUp(self):
        super().setUp()
        self.raw, _ = self.create_key()
        self.api = self.with_key(self.raw)

    def test_list_only_my_received_b2b_orders(self):
        mine = self.order(status='paid')
        self.order(status='delivered')
        self.order(store=self.other)
        self.order(is_b2b=False)
        body = self.api.get(INTEGRATION + 'orders/').json()
        self.assertEqual(body['count'], 2)
        numbers = {row['order_number'] for row in body['results']}
        self.assertIn(mine.order_number, numbers)
        self.assertEqual(body['results'][0]['buyer_store'], 'Détaillant Gamma')

    def test_filter_by_status_and_unknown_status(self):
        self.order(status='paid')
        self.order(status='delivered')
        self.order(status='cancelled')
        self.assertEqual(self.api.get(INTEGRATION + 'orders/?status=paid').json()['count'], 1)
        self.assertEqual(self.api.get(INTEGRATION + 'orders/?status=paid,delivered').json()['count'], 2)
        bad = self.api.get(INTEGRATION + 'orders/?status=inconnu')
        self.assertEqual(bad.status_code, 400)
        self.assertIn('Statut inconnu', bad.json()['error']['message'])

    def test_pagination(self):
        for _ in range(3):
            self.order()
        page = self.api.get(INTEGRATION + 'orders/?page_size=2').json()
        self.assertEqual((page['count'], len(page['results'])), (3, 2))
        self.assertEqual(len(self.api.get(INTEGRATION + 'orders/?page_size=2&page=2').json()['results']), 1)
        self.assertEqual(self.api.get(INTEGRATION + 'orders/?page=9').status_code, 404)

    def test_detail_shows_items_and_refuses_foreign_orders(self):
        order = self.order(quantity=3)
        body = self.api.get(f'{INTEGRATION}orders/{order.id}/').json()
        self.assertEqual(body['order_number'], order.order_number)
        self.assertEqual(body['items'][0]['quantity'], 3)
        self.assertEqual(body['items'][0]['unit_price'], '15000.00')
        self.assertEqual(body['delivery_address'], 'Akanda')
        foreign = self.order(store=self.other)
        self.assertEqual(self.api.get(f'{INTEGRATION}orders/{foreign.id}/').status_code, 404)
        retail = self.order(is_b2b=False)
        self.assertEqual(self.api.get(f'{INTEGRATION}orders/{retail.id}/').status_code, 404)

    def test_orders_are_read_only(self):
        order = self.order(status='paid')
        url = f'{INTEGRATION}orders/{order.id}/'
        for method in ('patch', 'put', 'post', 'delete'):
            self.assertEqual(getattr(self.api, method)(url, {'status': 'refunded'}, format='json').status_code, 405)
        order.refresh_from_db()
        self.assertEqual(order.status, 'paid')
        self.assertNotIn('commission_amount', self.api.get(url).json())
