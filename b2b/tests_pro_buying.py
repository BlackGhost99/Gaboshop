"""Le forfait Pro commande chez les grossistes avec une limite plus basse que Business (17 oct. 2026)."""
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from b2b.models import B2BProductPricing, B2BProfile
from b2b.tests_wholesale_tools import WholesaleBase, make_store
from orders.models import Order
from payments.default_plans import PRO_B2B_LIMITS
from payments.models import SubscriptionPlan
from products.models import Product


class ProCommandeChezLesGrossistesTests(WholesaleBase):
    def setUp(self):
        super().setUp()
        self.price(15000)
        self.subscribe_wholesaler()

    def set_limits(self, suppliers=None, orders=None):
        SubscriptionPlan.objects.filter(plan_type='pro').update(
            can_access_b2b=True, max_b2b_suppliers=suppliers, max_b2b_monthly_orders=orders)

    def second_wholesaler(self):
        manager, store = make_store('+24107630202', 'Deuxième grossiste', self.category, True)
        product = Product.objects.create(store=store, name='Huile 5 L', price=9000, stock=100)
        B2BProductPricing.objects.create(product=product, b2b_store=store, b2b_price=8000, min_quantity=1)
        return store, product

    def test_seeded_range_gives_pro_a_limit_and_business_none(self):
        pro = SubscriptionPlan.objects.get(plan_type='pro')
        business = SubscriptionPlan.objects.get(plan_type='business')
        self.assertTrue(pro.can_access_b2b)
        self.assertEqual((pro.max_b2b_suppliers, pro.max_b2b_monthly_orders),
                         (PRO_B2B_LIMITS['max_b2b_suppliers'], PRO_B2B_LIMITS['max_b2b_monthly_orders']))
        self.assertTrue(business.can_access_b2b)
        self.assertIsNone(business.max_b2b_suppliers)
        self.assertIsNone(business.max_b2b_monthly_orders)
        self.assertFalse(SubscriptionPlan.objects.get(plan_type='free').can_access_b2b)

    def test_pro_card_states_the_limits(self):
        pro = SubscriptionPlan.objects.get(plan_type='pro')
        text = ' | '.join(pro.get_features_list())
        self.assertIn('grossistes (B2B) : jusqu\'à 3 grossistes et 10 commandes par mois', text)
        business = SubscriptionPlan.objects.get(plan_type='business')
        self.assertIn('grossistes (B2B) : sans limite', ' | '.join(business.get_features_list()))

    def test_monthly_order_limit_refuses_with_a_clear_message(self):
        self.set_limits(orders=2)
        _, api = self.new_buyer(1)
        self.assertEqual(self.order(api, 1).status_code, 201)
        self.assertEqual(self.order(api, 1).status_code, 201)
        res = self.order(api, 1)
        self.assertEqual(res.status_code, 400, res.content)
        message = res.json()['error']['message']
        self.assertIn('2 commandes en gros par mois', message)
        self.assertIn('1er du mois prochain', message)
        self.assertIn('Aucun forfait en vente', message)  # Business est fermé : jamais proposé
        self.assertEqual(Order.objects.filter(is_b2b=True).count(), 2)

    def test_cancelled_orders_do_not_count(self):
        self.set_limits(orders=1)
        _, api = self.new_buyer(1)
        self.assertEqual(self.order(api, 1).status_code, 201)
        Order.objects.filter(is_b2b=True).update(status='cancelled')
        self.assertEqual(self.order(api, 1).status_code, 201)

    def test_supplier_limit_blocks_a_new_wholesaler_but_not_a_usual_one(self):
        self.set_limits(suppliers=1)
        other, other_product = self.second_wholesaler()
        _, api = self.new_buyer(1)
        self.assertEqual(self.order(api, 1).status_code, 201)
        res = api.post('/api/v1/b2b/orders/', {
            'wholesaler_id': other.id, 'items': [{'product_id': other_product.id, 'quantity': 1}],
            'delivery_address': 'Quartier Louis', 'delivery_phone': '+24107640999', 'delivery_zone': 'Centre',
            'city': 'Libreville'}, format='json')
        self.assertEqual(res.status_code, 400, res.content)
        self.assertIn('1 grossistes différents', res.json()['error']['message'])
        self.assertIn('fournisseurs habituels', res.json()['error']['message'])
        self.assertEqual(self.order(api, 1).status_code, 201)

    def test_business_buyer_has_no_limit(self):
        business = SubscriptionPlan.objects.get(plan_type='business')
        self.buyer_plan = business
        _, api = self.new_buyer(1)
        for _ in range(12):
            self.assertEqual(self.order(api, 1).status_code, 201)

    def test_free_shop_still_cannot_buy_wholesale(self):
        self.buyer_plan = SubscriptionPlan.objects.get(plan_type='free')
        _, api = self.new_buyer(1)
        res = self.order(api, 1)
        self.assertIn(res.status_code, (400, 403), res.content)
        self.assertEqual(Order.objects.filter(is_b2b=True).count(), 0)
