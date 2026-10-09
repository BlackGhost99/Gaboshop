"""Paiement unique en ligne : Airtel/Moov seulement, option « tout au commerce »,
livreur payé quand le client confirme la réception."""
from datetime import time
from decimal import Decimal
from unittest import mock

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from api.models import SystemSettings
from delivery.models import Delivery
from orders.models import Order
from payments.configuration import DEFAULT_PAYMENT_POLICY, available_payment_options, matching_option
from payments.direct_service import create_arrangement, store_delivers
from payments.models import DeliveryPayout, Payment
from payments.services import PaymentService
from stores.models import Store, StoreCategory
from users.models import LivreurProfile, User

SINGPAY = dict(SINGPAY_CLIENT_ID='id', SINGPAY_CLIENT_SECRET='secret', SINGPAY_WALLET_ID='wallet')
TRANSFER = 'payments.services.call_singpay_transfer'


@override_settings(**SINGPAY)
class SinglePaymentTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(phone='+24107100002', password='x', user_type='store_manager')
        self.client_user = User.objects.create_user(phone='+24107100003', password='x', user_type='client')
        self.courier = User.objects.create_user(phone='+24107100004', password='x', user_type='delivery_agent')
        self.store = Store.objects.create(
            name='Commerce', category=StoreCategory.objects.create(name='Cat'), manager=self.manager,
            phone='+24107100100', address='Libreville', zone='Centre',
            opening_time=time(0, 0), closing_time=time(23, 59),
        )
        settings = SystemSettings.get_settings()
        settings.payment_policy = {**DEFAULT_PAYMENT_POLICY,
                                   'enabled_flows': DEFAULT_PAYMENT_POLICY['enabled_flows'] + ['platform_online']}
        settings.save(update_fields=['payment_policy'])
        patcher = mock.patch('delivery.tasks.assign_nearest_delivery_agent')
        patcher.start()
        self.addCleanup(patcher.stop)

    def make_order(self, delivery_by='gaboshop'):
        order = Order.objects.create(
            client=self.client_user, store=self.store, delivery_address='Akanda', delivery_phone='+24107100003',
            delivery_zone='Centre', delivery_fee=Decimal('2000'), items_total=Decimal('10000'),
            total_amount=Decimal('12000'), commission_amount=Decimal('800'),
        )
        create_arrangement(order, 'platform_online', 'airtel_money', delivery_by)
        return order

    # --- choix proposés -------------------------------------------------------------
    def test_only_airtel_and_moov_are_offered_when_online_payment_is_ready(self):
        _, options = available_payment_options(self.store)
        self.assertEqual({(o['flow'], o['method'], o['delivery_by']) for o in options},
                         {('platform_online', 'airtel_money', 'gaboshop'), ('platform_online', 'moov_money', 'gaboshop')})

    def test_store_that_delivers_gets_the_pay_everything_to_store_option(self):
        self.store.offers_delivery = True
        self.store.save(update_fields=['offers_delivery'])
        _, options = available_payment_options(self.store)
        self.assertTrue(matching_option(options, 'platform_online', 'moov_money', 'store'))
        # Retrait en magasin : pas de livraison, donc pas d'option « tout au commerce ».
        _, pickup = available_payment_options(self.store, delivery_requested=False)
        self.assertIsNone(matching_option(pickup, 'platform_online', 'moov_money', 'store'))

    def test_store_option_is_refused_when_the_store_does_not_deliver(self):
        order = Order.objects.create(client=self.client_user, store=self.store, delivery_address='A',
                                     delivery_phone='+24107100003', delivery_zone='Centre')
        with self.assertRaises(Exception):
            create_arrangement(order, 'platform_online', 'airtel_money', 'store')

    # --- livraison par le commerce --------------------------------------------------
    def test_store_delivery_order_is_confirmed_by_client_without_courier(self):
        self.store.offers_delivery = True
        self.store.save(update_fields=['offers_delivery'])
        order = self.make_order('store')
        self.assertTrue(store_delivers(order))
        Order.objects.filter(pk=order.pk).update(status='in_transit')
        api = APIClient()
        api.force_authenticate(self.client_user)
        response = api.post(f'/api/v1/orders/{order.id}/confirm-delivery/', {}, format='json')
        self.assertEqual(response.status_code, 200, response.content)
        order.refresh_from_db()
        self.assertEqual(order.status, 'delivered')

    # --- versement du livreur -------------------------------------------------------
    def make_delivered(self):
        order = self.make_order()
        Payment.objects.create(order=order, payment_method='airtel_money', status='success', amount=order.total_amount)
        Order.objects.filter(pk=order.pk).update(status='delivered')
        order.refresh_from_db()
        Delivery.objects.filter(order=order).delete()
        delivery = Delivery.objects.create(order=order, delivery_agent=self.courier, status='delivered',
                                           delivery_fee=Decimal('2000'), agent_commission=Decimal('1500'))
        return delivery

    @override_settings(SINGPAY_ENABLE_TRANSFER=True)
    def test_courier_without_singpay_disbursement_waits(self):
        delivery = self.make_delivered()
        with mock.patch(TRANSFER) as transfer:
            result = PaymentService.payout_delivery_agent(delivery)
        transfer.assert_not_called()
        self.assertTrue(result.get('pending'))
        payout = DeliveryPayout.objects.get(order=delivery.order)
        self.assertEqual(payout.status, 'pending')
        self.assertIn('Mobile Money', payout.note)

    @override_settings(SINGPAY_ENABLE_TRANSFER=True)
    def test_courier_is_paid_once_from_the_client_payment(self):
        self.courier.singpay_disbursement_id = 'DISB-LIV'
        self.courier.save(update_fields=['singpay_disbursement_id'])
        delivery = self.make_delivered()
        with mock.patch(TRANSFER, return_value={'status': 'ok'}) as transfer:
            PaymentService.payout_delivery_agent(delivery)
            PaymentService.payout_delivery_agent(delivery)
        transfer.assert_called_once()
        self.assertEqual(transfer.call_args.kwargs['disbursement'], 'DISB-LIV')
        self.assertEqual(transfer.call_args.kwargs['reference'], f'GABOSHOP_{delivery.order.order_number}')
        self.assertEqual(DeliveryPayout.objects.get(order=delivery.order).status, 'completed')

    @override_settings(SINGPAY_ENABLE_TRANSFER=False)
    def test_transfers_off_leaves_payout_for_manual_payment(self):
        self.courier.singpay_disbursement_id = 'DISB-LIV'
        self.courier.save(update_fields=['singpay_disbursement_id'])
        delivery = self.make_delivered()
        with mock.patch(TRANSFER) as transfer:
            PaymentService.payout_delivery_agent(delivery)
        transfer.assert_not_called()
        self.assertIn('manuel', DeliveryPayout.objects.get(order=delivery.order).note)


class CourierMobileMoneyTests(TestCase):
    def setUp(self):
        self.courier = User.objects.create_user(phone='+24107100009', password='x', user_type='delivery_agent')
        self.api = APIClient()
        self.api.force_authenticate(self.courier)

    def test_courier_saves_a_normalized_mobile_money_number(self):
        response = self.api.post('/api/v1/dashboard/delivery/profile/update/', {'mobile_money_phone': '077 12 34 56'})
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(LivreurProfile.objects.get(user=self.courier).mobile_money_phone, '+24177123456')

    def test_invalid_or_empty_number_is_refused(self):
        for value in ('012345678', ''):
            response = self.api.post('/api/v1/dashboard/delivery/profile/update/', {'mobile_money_phone': value})
            self.assertEqual(response.status_code, 400, value)
