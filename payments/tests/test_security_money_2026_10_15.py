"""Sécurité des flux d'argent (15/10) : double versement, litiges, ID de transaction réutilisés,
arrondis au franc, frais figés, double activation, forfaits, règlements de commission."""
from datetime import time
from decimal import Decimal
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from api.models import SystemSettings
from delivery.models import Delivery
from orders.models import Order, OrderItem
from payments.configuration import DEFAULT_PAYMENT_POLICY
from payments.direct_models import CommissionSettlement, PaymentReceipt
from payments.direct_service import confirm_receipt, confirm_settlement, create_arrangement, create_settlement
from payments.models import DeliveryPayout, Forfait, Payment, PaymentIntent, StorePayout
from payments.online_verification import amount_matches
from payments.services import PaymentService
from payments.store_payout_service import VERIFY_NOTE, release_store_payment
from products.models import Product, ProductCategory
from stores.models import Store, StoreCategory
from users.models import User

STORE_TRANSFER = 'payments.store_payout_service.call_singpay_transfer'
COURIER_TRANSFER = 'payments.services.call_singpay_transfer'
LOOKUP = 'payments.utils.call_singpay_transfers_by_reference'
SINGPAY = dict(SINGPAY_CLIENT_ID='id', SINGPAY_CLIENT_SECRET='secret', SINGPAY_WALLET_ID='wallet')


# Ces scénarios historiques couvrent aussi les règlements cash par les livreurs Gaboshop,
# conservés pour tester la compatibilité des écritures anciennes, mais bloqués au nouveau panier B2C.
@override_settings(B2C_STORE_COURIER_CASH_ONLY=False, **SINGPAY)
class MoneyBase(TestCase):
    ONLINE = True

    def setUp(self):
        self.admin = User.objects.create_user(phone='+24107300001', password='x', user_type='admin', is_staff=True)
        self.manager = User.objects.create_user(phone='+24107300002', password='x', user_type='store_manager')
        self.client_user = User.objects.create_user(phone='+24107300003', password='x', user_type='client')
        self.courier = User.objects.create_user(phone='+24107300004', password='x', user_type='delivery_agent')
        self.courier.singpay_disbursement_id = 'DISB-LIV'
        self.courier.save(update_fields=['singpay_disbursement_id'])
        category = StoreCategory.objects.create(name='Test')
        self.store = Store.objects.create(
            is_verified=True, name='Commerce', category=category, manager=self.manager, phone='+24107300100',
            address='Libreville', zone='Centre', commission_rate=Decimal('8'), singpay_disbursement_id='DISB-001',
            opening_time=time(0, 0), closing_time=time(23, 59), delivery_fee=Decimal('2000'),
        )
        pcat = ProductCategory.objects.create(store_category=category, name='Produits', commission_rate=Decimal('8'))
        self.product = Product.objects.create(store=self.store, category=pcat, name='Article', price=Decimal('10000'), stock=50, weight_kg=Decimal('1'))
        settings = SystemSettings.get_settings()
        # Paiement en ligne actif : seuls les circuits SingPay sont proposés (circuits directs sinon).
        settings.payment_policy = {**DEFAULT_PAYMENT_POLICY,
                                   'enabled_flows': DEFAULT_PAYMENT_POLICY['enabled_flows'] + ['platform_online']} if self.ONLINE else DEFAULT_PAYMENT_POLICY
        settings.save(update_fields=['payment_policy'])
        patcher = mock.patch('delivery.tasks.assign_nearest_delivery_agent')
        patcher.start()
        self.addCleanup(patcher.stop)
        self.api = APIClient()

    def make_order(self, paid_online=True, status='confirmed'):
        order = Order.objects.create(client=self.client_user, store=self.store, delivery_address='Akanda',
                                     delivery_phone='+24107300003', delivery_zone='Centre', delivery_fee=Decimal('2000'))
        OrderItem.objects.create(order=order, product=self.product, quantity=1, unit_price=self.product.price)
        Order.objects.filter(pk=order.pk).update(
            items_total=Decimal('10000'), delivery_fee=Decimal('2000'), commission_rate=Decimal('8'),
            commission_amount=Decimal('800'), total_amount=Decimal('12000'),
        )
        order.refresh_from_db()
        if paid_online:
            Payment.objects.create(order=order, payment_method='airtel_money', status='success', amount=order.total_amount)
        Order.objects.filter(pk=order.pk).update(status=status)
        order.refresh_from_db()
        return order

    def make_delivered(self):
        order = self.make_order(status='delivered')
        Delivery.objects.filter(order=order).delete()
        return Delivery.objects.create(order=order, delivery_agent=self.courier, status='delivered',
                                       delivery_fee=Decimal('2000'), agent_commission=Decimal('1500'))


# --- 1. Pas de double versement après une issue inconnue --------------------------------------
@override_settings(SINGPAY_ENABLE_TRANSFER=True, **SINGPAY)
class PayoutRetryTests(MoneyBase):
    def test_store_timeout_is_not_paid_again_by_the_next_trigger(self):
        order = self.make_order()
        with mock.patch(STORE_TRANSFER, return_value={'error': 'SingPay request failed: Read timed out'}):
            payout = release_store_payment(order.id)
        self.assertEqual(payout.status, 'failed')
        self.assertTrue(payout.note.startswith(VERIFY_NOTE))
        # Déclencheur suivant (tâche planifiée, confirmation...) : SingPay ne répond pas, rien ne repart.
        with mock.patch(LOOKUP, return_value={'error': 'SingPay request failed'}), \
                mock.patch(STORE_TRANSFER, return_value={'status': 'ok'}) as transfer:
            again = release_store_payment(order.id)
            release_store_payment(order.id, admin_retry=True)
        transfer.assert_not_called()
        self.assertEqual(again.status, 'failed')

    def test_store_timeout_reconciled_as_paid_when_singpay_shows_the_transfer(self):
        order = self.make_order()
        with mock.patch(STORE_TRANSFER, side_effect=RuntimeError('timeout')):
            release_store_payment(order.id)
        found = {'data': [{'disbursement': 'DISB-001', 'amount': 9200, 'status': 'Success'}]}
        with mock.patch(LOOKUP, return_value=found), mock.patch(STORE_TRANSFER) as transfer:
            payout = release_store_payment(order.id, admin_retry=True)
        transfer.assert_not_called()
        self.assertEqual(payout.status, 'paid')

    def test_server_error_is_unknown_but_clear_refusal_can_be_retried(self):
        order = self.make_order()
        with mock.patch(STORE_TRANSFER, return_value={'error': 'SingPay HTTP 502', 'response': {}}):
            self.assertTrue(release_store_payment(order.id).note.startswith(VERIFY_NOTE))
        other = self.make_order()
        with mock.patch(STORE_TRANSFER, return_value={'error': 'SingPay HTTP 400', 'response': {'message': 'solde'}}):
            self.assertFalse(release_store_payment(other.id).note.startswith(VERIFY_NOTE))
        with mock.patch(STORE_TRANSFER, return_value={'status': 'ok'}) as transfer:
            self.assertEqual(release_store_payment(other.id).status, 'paid')
        transfer.assert_called_once()

    def test_processing_state_is_committed_before_the_provider_call(self):
        order = self.make_order()
        seen = {}

        def transfer(**kwargs):
            seen['status'] = StorePayout.objects.get(order=order).status
            return {'status': 'ok'}
        with mock.patch(STORE_TRANSFER, side_effect=transfer):
            release_store_payment(order.id)
        self.assertEqual(seen['status'], 'processing')

    def test_courier_timeout_is_not_paid_twice(self):
        delivery = self.make_delivered()
        with mock.patch(COURIER_TRANSFER, return_value={'error': 'SingPay request failed: timeout'}):
            PaymentService.payout_delivery_agent(delivery)
        payout = DeliveryPayout.objects.get(order=delivery.order)
        self.assertEqual(payout.status, 'failed')
        self.assertTrue(payout.note.startswith(VERIFY_NOTE))
        with mock.patch(LOOKUP, return_value={'error': 'SingPay request failed'}), \
                mock.patch(COURIER_TRANSFER, return_value={'status': 'ok'}) as transfer:
            PaymentService.payout_delivery_agent(delivery)
            PaymentService.payout_delivery_agent(delivery, admin_retry=True)
        transfer.assert_not_called()
        # L'admin relance une fois que SingPay confirme qu'aucun transfert n'existe.
        with mock.patch(LOOKUP, return_value={'data': []}), \
                mock.patch(COURIER_TRANSFER, return_value={'status': 'ok'}) as transfer:
            PaymentService.payout_delivery_agent(delivery, admin_retry=True)
            PaymentService.payout_delivery_agent(delivery, admin_retry=True)
        transfer.assert_called_once()
        self.assertEqual(DeliveryPayout.objects.get(order=delivery.order).status, 'completed')
        self.assertEqual(DeliveryPayout.objects.filter(order=delivery.order).count(), 1)


# --- 2. Litige client et commande annulée -----------------------------------------------------
@override_settings(SINGPAY_ENABLE_TRANSFER=True, **SINGPAY)
class PayoutBlockedTests(MoneyBase):
    def test_reported_problem_blocks_store_and_courier_payouts(self):
        delivery = self.make_delivered()
        Order.objects.filter(pk=delivery.order_id).update(client_problem_reported_at=timezone.now())
        delivery.order.refresh_from_db()
        with mock.patch(STORE_TRANSFER) as store_transfer, mock.patch(COURIER_TRANSFER) as courier_transfer:
            self.assertIsNone(release_store_payment(delivery.order_id))
            result = PaymentService.payout_delivery_agent(delivery)
        self.assertFalse(result['success'])
        store_transfer.assert_not_called()
        courier_transfer.assert_not_called()
        # L'admin a vérifié : le versement part avec l'autorisation explicite.
        with mock.patch(STORE_TRANSFER, return_value={'status': 'ok'}):
            self.assertEqual(release_store_payment(delivery.order_id, admin_override=True).status, 'paid')
        with mock.patch(COURIER_TRANSFER, return_value={'status': 'ok'}):
            self.assertTrue(PaymentService.payout_delivery_agent(delivery, admin_override=True)['success'])

    def test_admin_resolve_problem_still_pays(self):
        order = self.make_order(status='delivered')
        Order.objects.filter(pk=order.pk).update(client_problem_reported_at=timezone.now(), client_problem='Colis abîmé')
        self.api.force_authenticate(self.admin)
        with mock.patch(STORE_TRANSFER, return_value={'status': 'ok'}):
            response = self.api.post(f'/api/v1/admin/orders/{order.id}/resolve-problem/')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(StorePayout.objects.get(order=order).status, 'paid')

    def test_cancelled_or_refunded_order_is_never_paid(self):
        delivery = self.make_delivered()
        for state in ('cancelled', 'refunded'):
            Order.objects.filter(pk=delivery.order_id).update(status=state)
            with mock.patch(STORE_TRANSFER) as store_transfer, mock.patch(COURIER_TRANSFER) as courier_transfer:
                self.assertIsNone(release_store_payment(delivery.order_id, admin_override=True))
                # Objet livraison chargé avant l'annulation : la commande est relue sous verrou.
                result = PaymentService.payout_delivery_agent(delivery, admin_override=True)
            self.assertFalse(result['success'])
            store_transfer.assert_not_called()
            courier_transfer.assert_not_called()


# --- 3. ID de transaction déclaré deux fois ---------------------------------------------------
class ReceiptReferenceTests(MoneyBase):
    ONLINE = False

    def setUp(self):
        super().setUp()
        self.store.payment_preferences = {'instructions': {'airtel_money': 'Code Airtel 1', 'moov_money': 'Code Moov 2'}}
        self.store.save(update_fields=['payment_preferences'])

    def products_obligation(self, method='airtel_money'):
        order = self.make_order(paid_online=False, status='pending')
        create_arrangement(order, 'direct_split', method, user=self.client_user)
        return order.payment_arrangement.obligations.get(kind='products')

    def declare(self, obligation, reference, key, method=None):
        self.api.force_authenticate(self.client_user)
        data = {'obligation_id': obligation.id, 'amount': '10000', 'reference': reference, 'idempotency_key': key}
        if method:
            data['method'] = method
        return self.api.post('/api/v1/payments/receipts/', data, format='json')

    def test_method_from_client_is_ignored_and_reference_normalised(self):
        obligation = self.products_obligation()
        res = self.declare(obligation, ' mp 123 abc ', 'k1', method='cash')
        self.assertEqual(res.status_code, 201, res.content)
        receipt = PaymentReceipt.objects.get(idempotency_key='k1')
        self.assertEqual(receipt.method, 'airtel_money')
        self.assertEqual(receipt.reference, 'MP123ABC')

    def test_reference_cannot_be_reused_with_another_method(self):
        first = self.products_obligation()
        self.assertEqual(self.declare(first, 'MP555', 'k1').status_code, 201)
        second = self.products_obligation(method='moov_money')
        res = self.declare(second, 'mp 555', 'k2', method='moov_money')
        self.assertEqual(res.status_code, 400)
        self.assertIn('déjà été utilisé', res.content.decode())
        # Une déclaration refusée libère l'ID.
        PaymentReceipt.objects.filter(idempotency_key='k1').update(status='rejected')
        self.assertEqual(self.declare(second, 'mp 555', 'k3').status_code, 201)

    def test_reference_reuse_is_refused_even_for_cash(self):
        first = self.products_obligation()
        self.assertEqual(self.declare(first, 'REF-77', 'k1').status_code, 201)
        cash = self.products_obligation(method='cash')
        self.api.force_authenticate(self.manager)
        res = self.api.post('/api/v1/payments/receipts/', {
            'obligation_id': cash.id, 'amount': '10000', 'reference': 'ref-77', 'idempotency_key': 'k2'}, format='json')
        self.assertEqual(res.status_code, 400)


# --- 4. Arrondis au franc ---------------------------------------------------------------------
class RoundingTests(MoneyBase):
    def test_amount_matches_tolerates_only_sub_franc_differences(self):
        self.assertTrue(amount_matches(12346, Decimal('12345.50')))
        self.assertTrue(amount_matches('12000', Decimal('12000.00')))
        self.assertFalse(amount_matches(12347, Decimal('12345.50')))
        self.assertFalse(amount_matches(11999, Decimal('12000')))

    def test_operator_fee_and_total_are_whole_francs(self):
        settings = SystemSettings.get_settings()
        settings.airtel_money_fee = Decimal('1.5')
        settings.save(update_fields=['airtel_money_fee'])
        order = self.make_order(paid_online=False)
        Order.objects.filter(pk=order.pk).update(items_total=Decimal('10050'))
        order.refresh_from_db()
        fee = order.calculate_operator_fee('airtel', 'mobile_money')
        # (10050 + 2000) x 1,5 % = 180,75 -> 181
        self.assertEqual(fee, Decimal('181'))
        self.assertEqual(fee, fee.to_integral_value())


# --- 5. Frais figés à la commande ---------------------------------------------------------------
@override_settings(**SINGPAY)
class FrozenFeesTests(MoneyBase):
    def test_store_raising_its_delivery_fee_does_not_change_an_existing_order(self):
        settings = SystemSettings.get_settings()
        settings.airtel_money_fee = Decimal('1.5')
        settings.save(update_fields=['airtel_money_fee'])
        order = self.make_order(paid_online=False, status='created')
        create_arrangement(order, 'platform_online', 'airtel_money', 'gaboshop', user=self.client_user)
        Store.objects.filter(pk=self.store.pk).update(delivery_fee=Decimal('90000'))
        self.api.force_authenticate(self.client_user)
        with mock.patch.object(PaymentService, '_call_operator_api', return_value={'transaction_id': 'TX-1'}):
            self.api.post(f'/api/v1/orders/{order.id}/payments/init/',
                          {'payment_method': 'airtel_money', 'operator': 'airtel', 'phone_number': '074000000'}, format='json')
        order.refresh_from_db()
        self.assertEqual(order.delivery_fee, Decimal('2000'))
        self.assertEqual(order.commission_amount, Decimal('800'))
        self.assertEqual(order.operator_fee, Decimal('180'))  # 12000 x 1,5 %
        self.assertEqual(order.total_amount, Decimal('12180'))

    def test_store_delivery_fee_bounds(self):
        from stores.serializers import StoreUpdateSerializer
        for fee, ok in (('-1', False), ('100001', False), ('0', True), ('2500', True)):
            serializer = StoreUpdateSerializer(self.store, data={'delivery_fee': fee}, partial=True)
            self.assertEqual(serializer.is_valid(), ok, fee)


# --- 6. Double activation d'un abonnement / forfait ---------------------------------------------
class IntentActivationTests(MoneyBase):
    def test_two_notifications_with_different_ids_activate_once(self):
        from payments.models import ClientForfait
        from payments.views import process_intent_outcome
        forfait = Forfait.objects.create(name='Livraison -20 %', monthly_price=Decimal('2000'), discount_rate=20)
        intent = PaymentIntent.objects.create(user=self.client_user, amount=2000, currency='XAF', provider='singpay',
                                              metadata={'purpose': 'client_forfait', 'forfait_id': forfait.id})
        stale = PaymentIntent.objects.get(pk=intent.pk)  # copie lue avant la première activation
        process_intent_outcome(intent, 'TX-A', 'success', {})
        process_intent_outcome(stale, 'TX-B', 'success', {})
        self.assertEqual(ClientForfait.objects.filter(user=self.client_user).count(), 1)
        self.assertTrue(stale.metadata.get('subscription_activated'))

    def test_signed_success_without_amount_is_refused(self):
        import hashlib
        import hmac
        import json
        intent = PaymentIntent.objects.create(user=self.client_user, amount=2000, currency='XAF', provider='airtel')

        def notify(payload):
            body = json.dumps(payload).encode()
            sig = hmac.new(b's3cret', body, hashlib.sha256).hexdigest()
            with override_settings(PAYMENT_WEBHOOK_SECRET='s3cret'):
                return APIClient().post('/api/v1/payments/provider/airtel/notify/', body,
                                        content_type='application/json', HTTP_X_SIGNATURE=sig)
        res = notify({'reference': intent.reference, 'status': 'SUCCESS', 'transaction': {'id': 'TX-1'}})
        self.assertEqual(res.status_code, 400, res.content)
        intent.refresh_from_db()
        self.assertNotEqual(intent.status, 'SUCCESS')
        # Même chose avec le bon montant : accepté.
        intent = PaymentIntent.objects.create(user=self.client_user, amount=2000, currency='XAF', provider='airtel')
        res = notify({'reference': intent.reference, 'status': 'SUCCESS', 'amount': '2000', 'transaction': {'id': 'TX-2'}})
        self.assertEqual(res.status_code, 200, res.content)
        intent.refresh_from_db()
        self.assertEqual(intent.status, 'SUCCESS')


# --- 7. Prix d'un forfait arrondi, jamais tronqué -----------------------------------------------
class ForfaitPriceTests(MoneyBase):
    def subscribe(self, price):
        forfait = Forfait.objects.create(name=f'F{price}', monthly_price=Decimal(price), discount_rate=10)
        self.api.force_authenticate(self.client_user)
        with mock.patch('api.v1.client_forfaits.call_airtel_money_init', return_value={'transaction': {'id': 'TX'}}) as init:
            res = self.api.post('/api/v1/my-forfait/subscribe/', {'forfait_id': forfait.id, 'operator': 'airtel'}, format='json')
        return res, init

    def test_price_is_rounded_to_whole_franc(self):
        res, init = self.subscribe('1999.60')
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(init.call_args.kwargs['amount'], 2000)

    def test_tiny_non_zero_price_is_not_activated_for_free(self):
        from payments.models import ClientForfait
        res, init = self.subscribe('0.40')
        self.assertEqual(res.status_code, 400)
        init.assert_not_called()
        self.assertFalse(ClientForfait.objects.filter(user=self.client_user).exists())


# --- 8. Règlements de commission --------------------------------------------------------------
class SettlementTests(MoneyBase):
    ONLINE = False

    def commission(self):
        order = self.make_order(paid_online=False)
        arrangement = create_arrangement(order, 'courier_cash', 'cash', user=self.client_user)
        commission = arrangement.obligations.get(kind='commission')
        commission.status = 'unpaid'
        commission.save()
        return commission

    def test_two_pending_settlements_cannot_cover_the_same_debt(self):
        self.commission()  # 800 dus
        create_settlement(self.store, '800', 'cash', self.manager, reference='S1')
        with self.assertRaises(ValidationError):
            create_settlement(self.store, '800', 'cash', self.manager, reference='S2')

    def test_confirmation_rechecks_remaining_amount(self):
        commission = self.commission()
        settlement = create_settlement(self.store, '800', 'cash', self.manager, reference='S1')
        # Entre-temps, la commission a été réglée autrement.
        receipt = PaymentReceipt.objects.create(obligation=commission, actor=self.manager, amount=Decimal('800'),
                                                method='cash', reference='DIRECT', idempotency_key='direct')
        confirm_receipt(receipt, self.admin)
        with self.assertRaises(ValidationError):
            confirm_settlement(settlement, self.admin)
        self.assertEqual(commission.receipts.filter(status='confirmed').count(), 1)

    def test_non_pending_settlement_cannot_be_confirmed(self):
        self.commission()
        settlement = create_settlement(self.store, '800', 'cash', self.manager, reference='S1')
        CommissionSettlement.objects.filter(pk=settlement.pk).update(status='cancelled')
        with self.assertRaises(ValidationError):
            confirm_settlement(settlement, self.admin)

    def test_receipt_confirmation_rechecks_remaining_amount(self):
        commission = self.commission()
        first = PaymentReceipt.objects.create(obligation=commission, actor=self.manager, amount=Decimal('800'),
                                              method='cash', reference='R1', idempotency_key='r1')
        second = PaymentReceipt.objects.create(obligation=commission, actor=self.manager, amount=Decimal('800'),
                                               method='cash', reference='R2', idempotency_key='r2')
        confirm_receipt(first, self.admin)
        with self.assertRaises(ValidationError):
            confirm_receipt(second, self.admin)


# --- 9. Métadonnées client ignorées -------------------------------------------------------------
class IntentMetadataTests(TestCase):
    def test_reserved_metadata_keys_are_listed(self):
        from payments.views import RESERVED_INTENT_METADATA
        self.assertTrue({'purpose', 'plan_id', 'forfait_id', 'subscription_activated'} <= RESERVED_INTENT_METADATA)
