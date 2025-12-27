from django.test import TestCase
from rest_framework.test import APIClient
from users.models import User
from stores.models import StoreCategory
from payments.models import CategoryCommission, CategoryCommissionChangeLog


class CategoryCommissionAuditTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(phone='071000001', password='pass', user_type='admin', is_staff=True)
        self.cat = StoreCategory.objects.create(name='Électronique')
        self.cc = CategoryCommission.objects.create(store_category=self.cat, base_rate='8.00')
        self.client = APIClient()
        self.client.force_authenticate(user=self.staff)

    def test_update_creates_change_log(self):
        url = f"/api/v1/finance/category-commissions/{self.cc.pk}/"
        resp = self.client.patch(url, {'base_rate': '12.00'}, format='json')
        self.assertIn(resp.status_code, (200, 204))

        # Ensure change log created
        logs = CategoryCommissionChangeLog.objects.filter(category_commission=self.cc)
        self.assertTrue(logs.exists())
        latest = logs.latest('created_at')
        self.assertEqual(str(latest.old_rate), '8.00')
        self.assertEqual(str(latest.new_rate), '12.00')
        self.assertIsNotNone(latest.changed_by)
        self.assertEqual(latest.changed_by.pk, self.staff.pk)
