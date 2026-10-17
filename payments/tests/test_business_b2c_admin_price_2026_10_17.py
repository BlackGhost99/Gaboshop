"""Regressions : le forfait Business B2C utilise les valeurs configurees par l'administrateur."""
from decimal import Decimal
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from b2b.models import B2BSubscriptionPlan
from payments.default_plans import ensure_range
from payments.models import SubscriptionPlan, StoreSubscription
from payments.subscription_check import SubscriptionChecker
from payments.views import _get_subscription_price
from stores.models import Store, StoreCategory
from users.models import User


class BusinessB2CPlanSettingsTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(
            phone='+241077800201', password='CheckBusiness8', user_type='store_manager')
        self.admin = User.objects.create_user(
            phone='+241077800202', password='CheckBusiness8', user_type='admin', is_staff=True)
        self.store = Store.objects.create(
            name='Boutique Business Test', manager=self.manager,
            category=StoreCategory.objects.create(name='Test abonnement Business'),
            phone='+241077800203', address='Libreville', zone='Centre',
        )
        self.business = SubscriptionPlan.objects.get(plan_type='business')

    def change_plan(self, **changes):
        api = APIClient()
        api.force_authenticate(user=self.admin)
        return api.patch(
            f'/api/v1/admin/subscription-plans/{self.business.pk}/update/',
            {'price': '30000.00', 'max_products': 123,
             'is_available': True, **changes}, format='json')

    def test_admin_price_is_respected_by_checkout_and_card(self):
        response = self.change_plan()
        self.assertEqual(response.status_code, 200)
        self.business.refresh_from_db()
        self.assertEqual(self.business.price, Decimal('30000.00'))
        self.assertEqual(self.business.max_products, 123)
        self.assertTrue(self.business.is_available)
        self.assertEqual(_get_subscription_price(self.store, self.business), 30000)
        api = APIClient()
        api.force_authenticate(user=self.manager)
        result = api.get('/api/v1/payments/subscription-plans/')
        self.assertEqual(result.status_code, 200)
        row = next(p for p in result.data['plans'] if p['plan_type'] == 'business')
        self.assertEqual(row['actual_price'], 30000)
        self.assertIn('30 000', row['price_label'])

    def test_active_business_uses_recorded_plan_price(self):
        self.change_plan()
        self.business.refresh_from_db()
        StoreSubscription.objects.create(
            store=self.store, plan=self.business, plan_name=self.business.name,
            monthly_fee=self.business.price, status='active',
            end_date=timezone.now().date() + timedelta(days=30),
        )
        self.assertEqual(SubscriptionChecker.get_subscription_price(self.store), Decimal('30000'))

    def test_plan_initialization_does_not_erase_admin_decisions(self):
        self.change_plan()
        ensure_range(SubscriptionPlan, B2BSubscriptionPlan)
        self.business.refresh_from_db()
        self.assertTrue(self.business.is_available)
        self.assertEqual(self.business.price, Decimal('30000'))
        self.assertEqual(self.business.max_products, 123)

    def test_business_can_be_made_unavailable_by_admin(self):
        self.change_plan(is_available=False)
        self.business.refresh_from_db()
        self.assertFalse(self.business.is_available)
        ensure_range(SubscriptionPlan)
        self.business.refresh_from_db()
        self.assertFalse(self.business.is_available)
