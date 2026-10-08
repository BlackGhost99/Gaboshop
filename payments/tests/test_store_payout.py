from datetime import time, timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from api.models import SystemSettings
from orders.models import Order, OrderItem
from payments.configuration import DEFAULT_PAYMENT_POLICY
from payments.direct_service import create_arrangement
from payments.models import Commission, Payment, StorePayout
from payments.services import PaymentService
from payments.store_payout_service import release_store_payment
from products.models import Product, ProductCategory
from stores.models import Store, StoreCategory
from stores.serializers import StoreDetailSerializer, StoreUpdateSerializer
from users.models import User

TRANSFER = 'payments.store_payout_service.call_singpay_transfer'


class StorePayoutTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(phone='+24107000002', password='x', user_type='store_manager')
        self.other_manager = User.objects.create_user(phone='+24107000005', password='x', user_type='store_manager')
        self.client_user = User.objects.create_user(phone='+24107000003', password='x', user_type='client')
        category = StoreCategory.objects.create(name='Test')
        self.store = Store.objects.create(
            name='Commerce test', category=category, manager=self.manager, phone='+24107000100',
            address='Libreville', zone='Centre', commission_rate=Decimal('8'), agent_code='AGENT-001',
            singpay_disbursement_id='DISB-001',
            opening_time=time(0, 0), closing_time=time(23, 59),
        )
        product_category = ProductCategory.objects.create(store_category=category, name='Produits', commission_rate=Decimal('8'))
        self.product = Product.objects.create(store=self.store, category=product_category, name='Article', price=Decimal('10000'), stock=20, weight_kg=Decimal('1'))
        settings = SystemSettings.get_settings()
        settings.payment_policy = DEFAULT_PAYMENT_POLICY
        settings.save(update_fields=['payment_policy'])
        # La création d'un paiement réussi planifie une assignation Celery : pas de broker en test.
        patcher = mock.patch('delivery.tasks.assign_nearest_delivery_agent')
        patcher.start()
        self.addCleanup(patcher.stop)

    def make_order(self, paid_online=True, status='confirmed'):
        order = Order.objects.create(client=self.client_user, store=self.store, delivery_address='Akanda', delivery_phone='+24107000003', delivery_zone='Centre', delivery_fee=Decimal('2000'))
        OrderItem.objects.create(order=order, product=self.product, quantity=1, unit_price=self.product.price)
        order.items_total = Decimal('10000')
        order.delivery_fee = Decimal('2000')
        order.commission_rate = Decimal('8')
        order.commission_amount = Decimal('800')
        order.total_amount = Decimal('12000')
        order.save()
        if paid_online:
            # Un paiement réussi passe la commande à « paid » (signal historique)
            Payment.objects.create(order=order, payment_method='airtel_money', status='success', amount=order.total_amount)
        Order.objects.filter(pk=order.pk).update(status=status)
        order.refresh_from_db()
        return order

    # --- montants et déclenchement -------------------------------------------------
    @override_settings(SINGPAY_ENABLE_TRANSFER=False)
    def test_transfers_disabled_keeps_payout_pending_with_frozen_amounts(self):
        order = self.make_order()
        payout = release_store_payment(order.id)
        self.assertEqual(payout.status, 'pending')
        self.assertEqual(payout.amount, Decimal('9200.00'))
        self.assertFalse(payout.includes_delivery)
        self.assertIn('manuel', payout.note)

    @override_settings(SINGPAY_ENABLE_TRANSFER=True)
    def test_enabled_transfer_pays_store_share_to_its_singpay_disbursement(self):
        order = self.make_order()
        with mock.patch(TRANSFER, return_value={'status': 'ok'}) as transfer:
            payout = release_store_payment(order.id)
        self.assertEqual(payout.status, 'paid')
        self.assertIsNotNone(payout.paid_at)
        transfer.assert_called_once()
        kwargs = transfer.call_args.kwargs
        self.assertEqual(kwargs['disbursement'], 'DISB-001')
        self.assertEqual(kwargs['amount'], 9200)
        # SingPay retrouve l'encaissement du client par sa référence marchande.
        self.assertEqual(kwargs['reference'], f'GABOSHOP_{order.order_number}')

    @override_settings(SINGPAY_ENABLE_TRANSFER=True)
    def test_repeated_release_never_pays_twice(self):
        order = self.make_order()
        with mock.patch(TRANSFER, return_value={'status': 'ok'}) as transfer:
            first = release_store_payment(order.id)
            second = release_store_payment(order.id)
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(transfer.call_count, 1)
        self.assertEqual(StorePayout.objects.filter(order=order).count(), 1)

    @override_settings(SINGPAY_ENABLE_TRANSFER=True)
    def test_missing_singpay_disbursement_waits_then_can_be_retried(self):
        # Le code agent seul ne suffit pas : SingPay ne verse qu'à un décaissement enregistré.
        self.store.singpay_disbursement_id = ''
        self.store.save(update_fields=['singpay_disbursement_id'])
        order = self.make_order()
        with mock.patch(TRANSFER, return_value={'status': 'ok'}) as transfer:
            waiting = release_store_payment(order.id)
            self.assertEqual(waiting.status, 'pending')
            self.assertIn('décaissement SingPay', waiting.note)
            transfer.assert_not_called()
            self.store.singpay_disbursement_id = 'DISB-002'
            self.store.save(update_fields=['singpay_disbursement_id'])
            paid = release_store_payment(order.id)
        self.assertEqual(paid.status, 'paid')
        self.assertEqual(paid.agent_code, 'DISB-002')
        self.assertEqual(transfer.call_count, 1)

    @override_settings(SINGPAY_ENABLE_TRANSFER=True)
    def test_provider_error_marks_failed_and_retry_succeeds(self):
        order = self.make_order()
        with mock.patch(TRANSFER, return_value={'error': 'solde insuffisant'}):
            failed = release_store_payment(order.id)
        self.assertEqual(failed.status, 'failed')
        self.assertIn('solde', failed.note)
        with mock.patch(TRANSFER, side_effect=RuntimeError('réseau coupé')):
            failed_again = release_store_payment(order.id)
        self.assertEqual(failed_again.status, 'failed')
        with mock.patch(TRANSFER, return_value={'status': 'ok'}):
            paid = release_store_payment(order.id)
        self.assertEqual(paid.status, 'paid')
        self.assertEqual(paid.attempts, 3)

    @override_settings(SINGPAY_ENABLE_TRANSFER=True)
    def test_processing_payout_is_not_sent_again(self):
        order = self.make_order()
        with mock.patch(TRANSFER, return_value={'status': 'ok'}):
            payout = release_store_payment(order.id)
        StorePayout.objects.filter(pk=payout.pk).update(status='processing')
        with mock.patch(TRANSFER, return_value={'status': 'ok'}) as transfer:
            again = release_store_payment(order.id)
        self.assertEqual(again.status, 'processing')
        transfer.assert_not_called()

    # --- livreur du commerce : un seul paiement --------------------------------------
    @override_settings(SINGPAY_ENABLE_TRANSFER=True)
    def test_store_with_own_courier_gets_delivery_share_in_one_payment(self):
        self.store.offers_delivery = True
        self.store.save(update_fields=['offers_delivery'])
        order = self.make_order()
        with mock.patch(TRANSFER, return_value={'status': 'ok'}) as transfer:
            payout = release_store_payment(order.id)
        self.assertTrue(payout.includes_delivery)
        self.assertEqual(payout.amount, Decimal('11200.00'))
        self.assertEqual(transfer.call_args.kwargs['amount'], 11200)

        delivery = SimpleNamespace(status='delivered', order=order, agent_commission=Decimal('1200'))
        result = PaymentService.payout_delivery_agent(delivery)
        self.assertTrue(result['success'])
        self.assertTrue(result['skipped'])

    def test_independent_courier_flow_is_not_skipped_by_default(self):
        self.assertFalse(self.store.offers_delivery)
        order = self.make_order()
        delivery = SimpleNamespace(status='delivered', order=order, agent_commission=Decimal('1200'))
        result = PaymentService.payout_delivery_agent(delivery)
        self.assertFalse(result.get('skipped', False))

    # --- cas où rien ne doit être versé ----------------------------------------------
    @override_settings(SINGPAY_ENABLE_TRANSFER=True)
    def test_nothing_is_paid_when_gaboshop_did_not_collect(self):
        with mock.patch(TRANSFER, return_value={'status': 'ok'}) as transfer:
            unpaid = self.make_order(paid_online=False)
            self.assertIsNone(release_store_payment(unpaid.id))

            cancelled = self.make_order(status='cancelled')
            self.assertIsNone(release_store_payment(cancelled.id))

            manual = self.make_order()
            Payment.objects.filter(order=manual).delete()
            Payment.objects.create(order=manual, payment_method='airtel_money', status='success', amount=manual.total_amount)
            create_arrangement(manual, 'direct_split', 'cash', user=self.client_user)
            self.assertIsNone(release_store_payment(manual.id))
        transfer.assert_not_called()
        self.assertEqual(StorePayout.objects.count(), 0)

    # --- déclenchement par la confirmation du commerce -------------------------------
    @override_settings(SINGPAY_ENABLE_TRANSFER=False)
    def test_store_confirmation_triggers_one_payout(self):
        order = self.make_order(status='confirmed')
        with self.captureOnCommitCallbacks(execute=True):
            order.status = 'preparing'
            order.save()
        self.assertEqual(StorePayout.objects.filter(order=order).count(), 1)
        with self.captureOnCommitCallbacks(execute=True):
            order.status = 'ready'
            order.save()
            order.status = 'preparing'
            order.save()
        self.assertEqual(StorePayout.objects.filter(order=order).count(), 1)

    # --- pas de double versement avec les reversements périodiques --------------------
    @override_settings(SINGPAY_ENABLE_TRANSFER=True)
    def test_periodic_reversement_skips_orders_already_paid_to_the_store(self):
        order = self.make_order(status='delivered')
        order.delivered_at = timezone.now()
        order.save(update_fields=['delivered_at'])
        Commission.objects.get_or_create(order=order, defaults=dict(store=self.store, order_amount=order.items_total, commission_rate=Decimal('8'), commission_amount=Decimal('800')))
        Commission.objects.filter(order=order).update(is_settled=False)
        with mock.patch(TRANSFER, return_value={'status': 'ok'}):
            release_store_payment(order.id)
        result = PaymentService.process_store_payout(self.store.id, timezone.now() - timedelta(days=1), timezone.now() + timedelta(days=1))
        self.assertTrue(result['success'])
        self.assertIsNone(result['reversement'])

    # --- confidentialité et permissions du code agent --------------------------------
    def test_agent_code_is_never_in_the_public_store_payload(self):
        self.assertNotIn('agent_code', StoreDetailSerializer(self.store).data)
        response = APIClient().get(f'/api/v1/stores/{self.store.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('AGENT-001', response.content.decode())

    def test_only_the_store_manager_can_set_the_agent_code(self):
        url = f'/api/v1/stores/{self.store.id}/update/'
        for user in (self.other_manager, self.client_user):
            api = APIClient()
            api.force_authenticate(user)
            self.assertEqual(api.patch(url, {'agent_code': 'HACK-999'}, format='json').status_code, 403)
        self.store.refresh_from_db()
        self.assertEqual(self.store.agent_code, 'AGENT-001')

        api = APIClient()
        api.force_authenticate(self.manager)
        response = api.patch(url, {'agent_code': ' AGENT-777 '}, format='json')
        self.assertEqual(response.status_code, 200)
        self.store.refresh_from_db()
        self.assertEqual(self.store.agent_code, 'AGENT-777')

    def test_invalid_agent_code_is_rejected(self):
        for bad in ('ab', 'code avec espaces', "x'; DROP TABLE", '<script>'):
            serializer = StoreUpdateSerializer(self.store, data={'agent_code': bad}, partial=True)
            self.assertFalse(serializer.is_valid(), bad)

    def test_agent_code_is_visible_to_its_owner_dashboard_only(self):
        api = APIClient()
        api.force_authenticate(self.other_manager)
        response = api.get('/api/v1/dashboard/store/')
        self.assertNotIn('AGENT-001', response.content.decode())

    # --- numéro Mobile Money du commerce et identifiant SingPay -------------------------
    def test_store_sets_its_mobile_money_number(self):
        api = APIClient()
        api.force_authenticate(self.manager)
        url = f'/api/v1/stores/{self.store.id}/update/'
        for typed, saved, operator in (('077 12 34 56', '+24177123456', 'airtel'), ('+241 62 30 83 63', '+24162308363', 'moov'), ('', '', '')):
            response = api.patch(url, {'payout_phone': typed}, format='json')
            self.assertEqual(response.status_code, 200, response.content)
            self.store.refresh_from_db()
            self.assertEqual(self.store.payout_phone, saved)
            self.assertEqual(self.store.payout_operator, operator)
        for bad in ('011234567', '12345', '0771234567890'):
            self.assertEqual(api.patch(url, {'payout_phone': bad}, format='json').status_code, 400, bad)

    def test_store_cannot_set_its_own_singpay_disbursement(self):
        api = APIClient()
        api.force_authenticate(self.manager)
        api.patch(f'/api/v1/stores/{self.store.id}/update/', {'singpay_disbursement_id': 'HACK'}, format='json')
        self.store.refresh_from_db()
        self.assertEqual(self.store.singpay_disbursement_id, 'DISB-001')
        dashboard = api.get('/api/v1/dashboard/store/').json()['data']['store']
        self.assertTrue(dashboard['payouts_ready'])
        self.assertNotIn('DISB-001', str(dashboard))

    def test_payout_details_stay_private(self):
        self.store.payout_phone = '+24177123456'
        self.store.save(update_fields=['payout_phone'])
        content = APIClient().get(f'/api/v1/stores/{self.store.id}/').content.decode()
        for private in ('77123456', 'DISB-001'):
            self.assertNotIn(private, content)

    def test_admin_sets_the_singpay_disbursement(self):
        admin_user = User.objects.create_user(phone='+24107000009', password='x', user_type='admin', is_staff=True, is_superuser=True)
        api = APIClient()
        api.force_authenticate(admin_user)
        listed = next(s for s in api.get('/api/v1/admin/stores/list/').json()['data'] if s['id'] == self.store.id)
        self.assertEqual(listed['agent_code'], 'AGENT-001')
        url = f'/api/v1/admin/stores/{self.store.id}/update/'
        self.assertEqual(api.patch(url, {'singpay_disbursement_id': ' DISB-777 '}, format='json').status_code, 200)
        self.store.refresh_from_db()
        self.assertEqual(self.store.singpay_disbursement_id, 'DISB-777')
        self.assertEqual(api.patch(url, {'singpay_disbursement_id': 'avec espaces'}, format='json').status_code, 400)
