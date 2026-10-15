"""Contrôle 2.0 (15/10/2026) : sécurité et anti-fraude des commandes et des livraisons."""
from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone

from core.scheduled import release_unconfirmed_payouts
from delivery.models import Delivery
from orders.models import Order, OrderItem
from orders.tests import test_decisions_2026_10_15 as base
from payments.models import StorePayout
from users.models import User


@override_settings(SINGPAY_ENABLE_TRANSFER=False)
class SecuriteCommandesTests(TestCase):
    setUp = base.DecisionsTests.setUp
    paid_order = base.DecisionsTests.paid_order
    proof = base.DecisionsTests.proof

    def new_order(self, status='created'):
        order = Order.objects.create(client=self.client_user, store=self.store, delivery_address='Akanda',
                                     delivery_phone='+24107200002', delivery_zone='Centre', delivery_fee=Decimal('2000'))
        OrderItem.objects.create(order=order, product=self.product, quantity=1, unit_price=self.product.price)
        Order.objects.filter(pk=order.pk).update(status=status)
        order.refresh_from_db()
        return order

    # --- Prise de course ---------------------------------------------------------------
    def test_driver_cannot_claim_an_order_that_is_not_ready(self):
        order = self.new_order('created')
        self.api.force_authenticate(self.driver)
        res = self.api.post(f'/api/v1/dashboard/delivery/{order.delivery.id}/claim/')
        self.assertEqual(res.status_code, 400)
        order.refresh_from_db()
        self.assertEqual(order.status, 'created')
        self.assertIsNone(Delivery.objects.get(order=order).delivery_agent_id)

    def test_driver_can_claim_a_ready_order_open_to_drivers(self):
        order = self.new_order('ready')
        Delivery.objects.filter(order=order).update(auto_assignment_enabled=False, city='Libreville')
        self.api.force_authenticate(self.driver)
        res = self.api.post(f'/api/v1/dashboard/delivery/{order.delivery.id}/claim/')
        self.assertEqual(res.status_code, 200, res.content)

    # --- Code PIN -------------------------------------------------------------------------
    def test_wrong_pins_are_counted_and_lock_the_delivery(self):
        order = self.paid_order(status='in_transit')
        Delivery.objects.filter(order=order).update(status='in_transit', delivery_code='482913')
        self.api.force_authenticate(self.driver)
        url = f'/api/v1/dashboard/delivery/{order.delivery.id}/upload-proof/'
        codes = []
        for guess in ('000000', '000001', '000002', '000003', '000004', '482913'):
            codes.append(self.api.post(url, {'pin_code': guess}, format='multipart').status_code)
        # Après 5 erreurs, même le bon code est refusé : on ne peut plus essayer tous les codes.
        self.assertEqual(codes[-1], 429)
        self.assertFalse(Delivery.objects.get(order=order).code_verified)

    def test_pin_is_six_digits(self):
        order = self.new_order()
        code = Delivery.objects.get(order=order).delivery_code
        self.assertTrue(code.isdigit() and len(code) == 6)

    # --- Commande annulée : la course s'arrête --------------------------------------------
    def test_cancelling_an_order_stops_its_delivery(self):
        order = self.new_order('ready')
        Delivery.objects.filter(order=order).update(delivery_agent=self.driver, status='assigned')
        self.api.force_authenticate(self.admin)
        self.api.patch(f'/api/v1/orders/{order.id}/status/', {'status': 'cancelled'}, format='json')
        self.assertEqual(Order.objects.get(pk=order.pk).status, 'cancelled')
        self.assertEqual(Delivery.objects.get(order=order).status, 'cancelled')
        self.api.force_authenticate(self.driver)
        res = self.api.post(f'/api/v1/dashboard/delivery/{order.delivery.id}/complete/')
        self.assertEqual(res.status_code, 409)
        self.assertEqual(Order.objects.get(pk=order.pk).status, 'cancelled')

    # --- Annulation par le commerce -----------------------------------------------------
    def test_store_cannot_cancel_a_paid_order_even_while_preparing(self):
        order = self.paid_order(status='preparing')
        self.api.force_authenticate(self.manager)
        res = self.api.patch(f'/api/v1/orders/{order.id}/status/', {'status': 'cancelled'}, format='json')
        self.assertEqual(res.status_code, 409)
        self.assertNotIn('http', res.json()['error'])
        self.assertEqual(Order.objects.get(pk=order.pk).status, 'preparing')

    def test_store_can_still_cancel_an_unpaid_order(self):
        order = self.new_order('confirmed')
        self.api.force_authenticate(self.manager)
        res = self.api.patch(f'/api/v1/orders/{order.id}/status/', {'status': 'cancelled'}, format='json')
        self.assertEqual(res.status_code, 200, res.content)

    def test_ai_assistant_cannot_cancel_a_paid_order(self):
        from django.core import signing
        from api.v1.ai.assistant import CONFIRM_SALT
        order = self.paid_order(status='in_transit')
        token = signing.dumps({'u': self.manager.id, 'a': 'order_status', 'o': order.id, 'st': 'cancelled'}, salt=CONFIRM_SALT)
        self.api.force_authenticate(self.manager)
        res = self.api.post('/api/v1/ai/assistant/confirm/', {'token': token}, format='json')
        self.assertEqual(res.status_code, 409)
        self.assertEqual(Order.objects.get(pk=order.pk).status, 'in_transit')

    def test_ai_confirmation_works_only_once(self):
        from django.core import signing
        from api.v1.ai.assistant import CONFIRM_SALT
        token = signing.dumps({'u': self.manager.id, 'a': 'update_product', 'p': self.product.id, 'c': {'price': '9000'}}, salt=CONFIRM_SALT)
        self.api.force_authenticate(self.manager)
        self.assertEqual(self.api.post('/api/v1/ai/assistant/confirm/', {'token': token}, format='json').status_code, 200)
        self.assertEqual(self.api.post('/api/v1/ai/assistant/confirm/', {'token': token}, format='json').status_code, 400)

    # --- Le commerce qui livre lui-même --------------------------------------------------
    def test_store_delivering_itself_needs_the_client_pin_to_mark_delivered(self):
        self.store.offers_delivery = True
        self.store.save(update_fields=['offers_delivery'])
        order = self.new_order('in_transit')
        Delivery.objects.filter(order=order).update(delivery_code='274615')
        self.api.force_authenticate(self.manager)
        res = self.api.patch(f'/api/v1/orders/{order.id}/status/', {'status': 'delivered'}, format='json')
        self.assertEqual(res.status_code, 400)
        res = self.api.patch(f'/api/v1/orders/{order.id}/status/', {'status': 'delivered', 'pin_code': '274615'}, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        self.assertTrue(Delivery.objects.get(order=order).code_verified)

    # --- Versement automatique : remise prouvée exigée -----------------------------------
    def test_no_automatic_payment_without_pin_or_client_confirmation(self):
        order = self.paid_order()
        release_unconfirmed_payouts()
        self.assertFalse(StorePayout.objects.filter(order=order).exists())
        # L'admin la voit et peut payer après avoir appelé le client.
        self.api.force_authenticate(self.admin)
        problems = self.api.get('/api/v1/admin/summary/').json()['data']['system_status']['client_problems']
        self.assertIn(order.id, [p['id'] for p in problems])
        self.assertEqual(self.api.post(f'/api/v1/admin/orders/{order.id}/resolve-problem/').status_code, 200)
        self.assertTrue(StorePayout.objects.filter(order=order).exists())

    # --- Fuites ---------------------------------------------------------------------------
    def test_delivery_price_check_refuses_other_peoples_orders(self):
        order = self.new_order()
        stranger = User.objects.create_user(phone='+24107200099', password='x', user_type='client')
        self.api.force_authenticate(stranger)
        res = self.api.post('/api/v1/delivery/calculate-price/', {'order_id': order.id, 'vehicle_type_id': 1}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('order_id', str(res.content))

    def test_old_products_api_route_is_gone(self):
        self.api.force_authenticate(self.client_user)
        self.assertEqual(self.api.get('/api/v1/products-api/').status_code, 404)

    def test_unverified_store_cannot_buy_wholesale(self):
        from b2b.services.permissions import can_purchase_from_wholesaler
        self.store.is_verified = False
        ok, message = can_purchase_from_wholesaler(self.store, self.store)
        self.assertFalse(ok)
        self.assertIn('validé', message)
