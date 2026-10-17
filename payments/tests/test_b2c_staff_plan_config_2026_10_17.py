"""L'administration choisit librement la disponibilité et le quota équipe pour CHAQUE forfait B2C."""
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from payments.models import SubscriptionPlan, StoreSubscription
from payments.staff_entitlements import get_b2c_staff_policy
from stores.models import Store, StoreCategory
from users.models import User


class TeamSubscriptionPlanConfigurationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            phone='+241077541001', password='safe', user_type='admin', is_staff=True)
        self.manager = User.objects.create_user(
            phone='+241077541002', password='safe', user_type='store_manager')
        self.other = User.objects.create_user(
            phone='+241077541003', password='safe', user_type='store_manager')
        self.customer = User.objects.create_user(
            phone='+241077541004', password='safe', user_type='client')
        self.store = Store.objects.create(
            name='Boutique équipe B2C', manager=self.manager,
            category=StoreCategory.objects.create(name='Catégorie équipe B2C'),
            phone='+241077541005', address='Libreville', zone='Centre')
        self.free = SubscriptionPlan.objects.get(plan_type='free')
        self.pro = SubscriptionPlan.objects.get(plan_type='pro')

    def api(self, user):
        api = APIClient()
        api.force_authenticate(user=user)
        return api

    def test_existing_plans_are_not_assigned_arbitrary_staff_quotas(self):
        self.assertFalse(self.free.can_manage_staff)
        self.assertEqual(self.free.max_staff_accounts, 0)
        self.assertFalse(self.pro.can_manage_staff)
        self.assertEqual(self.pro.max_staff_accounts, 0)

    def test_admin_can_configure_free_independently_of_pro_and_existing_quotas(self):
        self.free.max_products = 50
        self.free.max_orders_per_month = 50
        self.free.max_products_food = 10
        self.free.can_access_b2b = True
        self.free.max_b2b_suppliers = 3
        self.free.max_b2b_monthly_orders = 3
        self.free.history_limit_days = 5
        self.free.save()
        response = self.api(self.admin).patch(
            f'/api/v1/admin/subscription-plans/{self.free.id}/update/',
            {'can_manage_staff': True, 'max_staff_accounts': 2},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.free.refresh_from_db()
        self.pro.refresh_from_db()
        self.assertTrue(self.free.can_manage_staff)
        self.assertEqual(self.free.max_staff_accounts, 2)
        self.assertEqual(self.free.max_products, 50)
        self.assertEqual(self.free.max_orders_per_month, 50)
        self.assertEqual(self.free.max_products_food, 10)
        self.assertTrue(self.free.can_access_b2b)
        self.assertEqual(self.free.max_b2b_suppliers, 3)
        self.assertEqual(self.free.max_b2b_monthly_orders, 3)
        self.assertEqual(self.free.history_limit_days, 5)
        self.assertEqual(self.pro.max_staff_accounts, 0)
        data = self.api(self.manager).get('/api/v1/store/team/policy/').data['data']
        self.assertTrue(data['can_manage_staff'])
        self.assertEqual(data['max_staff_accounts'], 2)
        self.assertEqual(data['plan_type'], 'free')

    def test_pay_plan_rights_take_priority_and_expiry_falls_back_to_free(self):
        self.free.can_manage_staff = True
        self.free.max_staff_accounts = 1
        self.free.save()
        self.pro.can_manage_staff = True
        self.pro.max_staff_accounts = 8
        self.pro.save()
        sub = StoreSubscription.objects.create(
            store=self.store, plan=self.pro, plan_name=self.pro.name,
            monthly_fee=self.pro.price, status='active',
            start_date=timezone.now().date(),
            end_date=timezone.now().date() + timedelta(days=30),
        )
        self.assertEqual(get_b2c_staff_policy(self.store)['max_staff_accounts'], 8)
        sub.end_date = timezone.now().date() - timedelta(days=1)
        sub.save(update_fields=['end_date'])
        self.assertEqual(get_b2c_staff_policy(self.store)['max_staff_accounts'], 1)

    def test_no_access_when_checkbox_off_even_with_positive_quota(self):
        self.free.can_manage_staff = False
        self.free.max_staff_accounts = 30
        self.free.save()
        self.assertEqual(get_b2c_staff_policy(self.store)['max_staff_accounts'], 0)

    def test_no_employee_access_to_manager_only_capability(self):
        for user in (self.customer, self.other):
            response = self.api(user).get('/api/v1/store/team/policy/')
            self.assertIn(response.status_code, (403, 404))

    def test_negative_quota_cannot_be_saved_via_admin(self):
        response = self.api(self.admin).patch(
            f'/api/v1/admin/subscription-plans/{self.free.id}/update/',
            {'can_manage_staff': True, 'max_staff_accounts': -1},
            format='json',
        )
        self.assertEqual(response.status_code, 400)
