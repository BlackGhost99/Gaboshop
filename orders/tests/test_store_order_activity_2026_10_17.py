"""Traçabilité des opérations de vente : auteur, date, sécurité et aucun log fictif."""
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from core.models import AuditLog
from orders.models import Order
from stores.models import Store, StoreCategory
from users.models import User


class StoreOrderActivityTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            phone='+241077530001', password='test', user_type='store_manager',
            first_name='Gestionnaire', last_name='Un',
        )
        self.other_owner = User.objects.create_user(
            phone='+241077530002', password='test', user_type='store_manager',
        )
        self.customer = User.objects.create_user(
            phone='+241077530003', password='test', user_type='client',
        )
        self.admin = User.objects.create_user(
            phone='+241077530004', password='test', user_type='admin', is_staff=True,
        )
        category = StoreCategory.objects.create(name='Activité commande')
        self.shop = Store.objects.create(
            manager=self.owner, category=category, name='Boutique première',
            phone='+241077530005', address='Libreville',
        )
        self.other_shop = Store.objects.create(
            manager=self.other_owner, category=category, name='Boutique deuxième',
            phone='+241077530006', address='Libreville',
        )
        self.order = Order.objects.create(
            client=self.customer, store=self.shop, status='confirmed',
            delivery_address='Libreville', delivery_phone=self.customer.phone,
            items_total=Decimal('1000'), total_amount=Decimal('1000'),
        )

    def api(self, user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    def test_manager_status_action_is_logged_and_accessible_in_chronology(self):
        manager = self.api(self.owner)
        response = manager.patch(
            f'/api/v1/orders/{self.order.id}/status/',
            {'status': 'preparing'}, format='json',
        )
        self.assertEqual(response.status_code, 200, getattr(response, 'data', None))
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'preparing')

        log = AuditLog.objects.get(
            object_type='order', object_id=self.order.id,
            action_type='order_status_change',
        )
        self.assertEqual(log.user_id, self.owner.id)
        self.assertEqual((log.old_value, log.new_value), ('confirmed', 'preparing'))
        timeline = manager.get(f'/api/v1/orders/{self.order.id}/activity/')
        self.assertEqual(timeline.status_code, 200)
        events = timeline.data['data']['events']
        self.assertTrue(any(e['id'] == f'audit-{log.id}' and
                            e['actor'] == 'Gestionnaire Un' for e in events))
        self.assertTrue(any(e['type'] == 'order_created' for e in events))

    def test_invalid_transition_does_not_generate_audit_log(self):
        response = self.api(self.owner).patch(
            f'/api/v1/orders/{self.order.id}/status/',
            {'status': 'delivered'}, format='json',
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(AuditLog.objects.filter(
            object_type='order', object_id=self.order.id,
        ).exists())

    def test_foreign_manager_and_customer_cannot_read_activity(self):
        for user in (self.other_owner, self.customer):
            response = self.api(user).get(f'/api/v1/orders/{self.order.id}/activity/')
            self.assertIn(response.status_code, (403, 404))
        admin_response = self.api(self.admin).get(
            f'/api/v1/orders/{self.order.id}/activity/'
        )
        self.assertEqual(admin_response.status_code, 200)
        self.assertIn('shared_account_notice', admin_response.data['data'])

    def test_older_orders_do_not_claim_any_employee_processed_them(self):
        response = self.api(self.owner).get(
            f'/api/v1/orders/{self.order.id}/activity/'
        )
        self.assertEqual(response.status_code, 200)
        events = response.data['data']['events']
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]['actor_role'], 'client')
