"""Gardien anti-fraude (15/10/2026) : mesures réversibles prises seules, décision finale à l'admin."""
from datetime import timedelta
from decimal import Decimal

from django.test import override_settings
from django.utils import timezone

from core import guardian
from core.models import RiskHold
from delivery.models import Delivery
from orders.models import Order
from orders.tests import test_decisions_2026_10_15 as base
from users.models import User


@override_settings(SINGPAY_ENABLE_TRANSFER=False)
class GardienTests(base.DecisionsTests.__mro__[1]):
    setUp = base.DecisionsTests.setUp
    paid_order = base.DecisionsTests.paid_order

    def create_order_payload(self, method='cash', flow='courier_cash'):
        return {
            'store': self.store.id, 'city': 'Libreville', 'delivery_address': 'Akanda', 'delivery_phone': '+24107200002',
            'delivery_zone': 'Centre', 'items': [{'product_id': self.product.id, 'quantity': 1}],
            'payment_flow': flow, 'payment_method': method,
        }

    # --- clients ---------------------------------------------------------------------
    def test_client_reusing_transaction_ids_is_paused_then_admin_lifts(self):
        for ref in ('AB1', 'AB2', 'AB3'):
            guardian.record_signal('receipt_reused', self.client_user, detail=ref)
        hold = RiskHold.objects.get(user=self.client_user, status='active')
        self.assertEqual(hold.kind, 'pause')
        self.api.force_authenticate(self.client_user)
        response = self.api.post('/api/v1/orders/create/', self.create_order_payload(), format='json')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()['error']['code'], 'compte_en_pause')
        self.assertIn('assistant', response.json()['error']['next_step'])
        # La personne est prévenue, l'admin aussi.
        self.assertTrue(self.client_user.notifications.filter(metadata__source='gardien').exists())
        self.assertTrue(self.admin.notifications.filter(metadata__action='gardien').exists())
        # L'admin voit la mesure et la lève.
        self.api.force_authenticate(self.admin)
        summary = self.api.get('/api/v1/admin/summary/').json()['data']['system_status']['guardian']
        self.assertEqual(summary[0]['id'], hold.id)
        response = self.api.post(f'/api/v1/admin/guardian/{hold.id}/decision/', {'decision': 'lift'}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertIsNone(guardian.pause_refusal(self.client_user))
        # Les faits d'avant le déblocage ne re-bloquent pas.
        self.assertEqual(guardian.evaluate(self.client_user), [])

    def test_client_with_failed_cash_deliveries_can_no_longer_pay_cash(self):
        from payments.configuration import available_payment_options
        from payments.direct_service import create_arrangement
        for _ in range(2):
            order = Order.objects.create(client=self.client_user, store=self.store, delivery_address='Akanda',
                                         delivery_phone='+24107200002', delivery_zone='Centre', delivery_fee=Decimal('2000'))
            create_arrangement(order, 'courier_cash', 'cash')
            Delivery.objects.filter(order=order).update(status='failed')
        guardian.check(self.client_user)
        self.assertTrue(guardian.cash_blocked(self.client_user))
        _, options = available_payment_options(self.store, True, user=self.client_user)
        self.assertFalse([o for o in options if o['method'] == 'cash'])
        _, others = available_payment_options(self.store, True)
        self.assertTrue([o for o in others if o['method'] == 'cash'])
        self.api.force_authenticate(self.client_user)
        response = self.api.post('/api/v1/orders/create/', self.create_order_payload(), format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('espèces est suspendu', str(response.content.decode()))

    # --- commerces -------------------------------------------------------------------
    def test_store_cancelling_many_orders_gets_payouts_held_and_lift_restores(self):
        for _ in range(3):
            order = Order.objects.create(client=self.client_user, store=self.store, delivery_address='Akanda',
                                         delivery_phone='+24107200002', delivery_zone='Centre', delivery_fee=Decimal('2000'))
            Order.objects.filter(pk=order.pk).update(status='confirmed')
            self.api.force_authenticate(self.manager)
            response = self.api.patch(f'/api/v1/orders/{order.id}/status/', {'status': 'cancelled'}, format='json')
            self.assertEqual(response.status_code, 200, response.content)
        self.store.refresh_from_db()
        self.assertTrue(self.store.payouts_frozen)
        hold = RiskHold.objects.get(user=self.manager, status='active')
        self.assertEqual(hold.kind, 'payout_freeze')
        guardian.lift(hold, self.admin, 'Rupture de stock réelle')
        self.store.refresh_from_db()
        self.assertFalse(self.store.payouts_frozen)

    def test_lift_keeps_a_freeze_the_admin_had_set_before(self):
        self.store.payouts_frozen = True
        self.store.save(update_fields=['payouts_frozen'])
        for i in range(3):
            guardian.record_signal('store_cancel', self.manager, store=self.store, detail=f'CMD{i}')
        hold = RiskHold.objects.get(user=self.manager, status='active')
        guardian.lift(hold, self.admin)
        self.store.refresh_from_db()
        self.assertTrue(self.store.payouts_frozen)

    # --- livreurs --------------------------------------------------------------------
    def test_driver_entering_wrong_pins_on_several_orders_is_paused(self):
        self.driver.is_available = True
        self.driver.save(update_fields=['is_available'])
        for _ in range(3):
            order = self.paid_order(status='in_transit')
            Delivery.objects.filter(order=order).update(status='in_transit')
            guardian.record_signal('pin_failure', self.driver, delivery=order.delivery)
        self.driver.refresh_from_db()
        self.assertFalse(self.driver.is_available)
        self.api.force_authenticate(self.driver)
        response = self.api.post('/api/v1/dashboard/delivery/availability/', {'is_available': True}, format='json')
        self.assertEqual(response.status_code, 403)
        response = self.api.post('/api/v1/dashboard/delivery/1/claim/')
        self.assertEqual(response.status_code, 403)
        # Les clients des courses en cours sont prévenus de garder leur code PIN.
        self.assertTrue(self.client_user.notifications.filter(title__contains='gardez votre code PIN').exists())
        hold = RiskHold.objects.get(user=self.driver, status='active')
        guardian.lift(hold, self.admin)
        self.driver.refresh_from_db()
        self.assertTrue(self.driver.is_available)

    # --- décisions de l'admin ----------------------------------------------------------
    def test_sanction_needs_a_reason_and_deactivates_account(self):
        for ref in ('X1', 'X2', 'X3'):
            guardian.record_signal('receipt_reused', self.client_user, detail=ref)
        hold = RiskHold.objects.get(user=self.client_user, status='active')
        self.api.force_authenticate(self.admin)
        url = f'/api/v1/admin/guardian/{hold.id}/decision/'
        self.assertEqual(self.api.post(url, {'decision': 'sanction'}, format='json').status_code, 400)
        self.assertEqual(self.api.post(url, {'decision': 'sanction', 'note': 'Fraude avérée'}, format='json').status_code, 200)
        self.client_user.refresh_from_db()
        self.assertFalse(self.client_user.is_active)
        self.assertEqual(self.api.post(url, {'decision': 'lift'}, format='json').status_code, 409)

    def test_only_admins_reach_the_guardian(self):
        self.api.force_authenticate(self.manager)
        self.assertEqual(self.api.get('/api/v1/admin/guardian/').status_code, 403)

    def test_admins_are_never_held(self):
        for ref in ('Y1', 'Y2', 'Y3'):
            guardian.record_signal('receipt_reused', self.admin, detail=ref)
        self.assertFalse(RiskHold.objects.filter(user=self.admin).exists())

    def test_assistant_explains_the_measure(self):
        from api.v1.ai.assistant import Ctx, t_my_problems
        for ref in ('Z1', 'Z2', 'Z3'):
            guardian.record_signal('receipt_reused', self.client_user, detail=ref)
        from types import SimpleNamespace
        problems = t_my_problems(Ctx(SimpleNamespace(user=self.client_user), 'client', []))['problems']
        self.assertTrue(any('Gardien' in p.get('source', '') for p in problems))

    def test_old_facts_outside_the_window_do_not_count(self):
        from core.models import FraudSignal
        for ref in ('W1', 'W2', 'W3'):
            FraudSignal.objects.create(kind='receipt_reused', user=self.client_user, detail=ref,
                                       created_at=timezone.now() - timedelta(days=40))
        self.assertEqual(guardian.evaluate(self.client_user), [])

    def test_one_store_refusing_everything_cannot_pause_a_client_alone(self):
        from payments.direct_models import PaymentReceipt
        from payments.direct_service import create_arrangement
        order = Order.objects.create(client=self.client_user, store=self.store, delivery_address='Akanda',
                                     delivery_phone='+24107200002', delivery_zone='Centre', delivery_fee=Decimal('2000'))
        obligation = create_arrangement(order, 'courier_cash', 'cash').obligations.first()
        for i in range(4):
            PaymentReceipt.objects.create(
                idempotency_key=f'k{i}', obligation=obligation, actor=self.client_user, amount=Decimal('100'),
                method='airtel_money', reference=f'REF{i}', status='rejected', rejected_by=self.manager,
                rejected_at=timezone.now(), rejection_reason='Pas reçu',
            )
        self.assertEqual(guardian.evaluate(self.client_user), [])
        other = User.objects.create_user(phone='+24107200099', password='x', user_type='store_manager')
        PaymentReceipt.objects.filter(reference='REF3').update(rejected_by=other)
        self.assertEqual(len(guardian.evaluate(self.client_user)), 1)
