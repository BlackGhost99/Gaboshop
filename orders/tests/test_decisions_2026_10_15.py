"""Décisions du 15/10/2026 : versement après 48 h, annulation bloquée en route, problème signalé,
forfaits clients, articles B2B reçus masqués."""
from datetime import time, timedelta
from decimal import Decimal
from unittest import mock

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from api.models import SystemSettings
from core.scheduled import release_unconfirmed_payouts
from delivery.models import Delivery, DeliveryProof
from orders.models import Order, OrderItem
from payments.client_forfaits import active_forfait, delivery_discount
from payments.configuration import DEFAULT_PAYMENT_POLICY
from payments.models import ClientForfait, Forfait, Payment, PaymentIntent, StorePayout
from products.models import Product, ProductCategory
from stores.models import Store, StoreCategory
from users.models import User


@override_settings(SINGPAY_ENABLE_TRANSFER=False)
class DecisionsTests(TestCase):
    def setUp(self):
        self.manager = User.objects.create_user(phone='+24107200001', password='x', user_type='store_manager')
        self.client_user = User.objects.create_user(phone='+24107200002', password='x', user_type='client')
        self.driver = User.objects.create_user(phone='+24107200003', password='x', user_type='delivery_agent')
        self.admin = User.objects.create_user(phone='+24107200004', password='x', user_type='admin', is_staff=True)
        category = StoreCategory.objects.create(name='Test')
        self.store = Store.objects.create(
            is_verified=True, name='Commerce', category=category, manager=self.manager, phone='+24107200010',
            address='Libreville', zone='Centre', commission_rate=Decimal('8'), singpay_disbursement_id='DISB-1',
            opening_time=time(0, 0), closing_time=time(0, 0),
        )
        self.product_category = ProductCategory.objects.create(store_category=category, name='P', commission_rate=Decimal('8'))
        self.product = Product.objects.create(store=self.store, category=self.product_category, name='Article',
                                              price=Decimal('10000'), stock=20, weight_kg=Decimal('1'))
        settings = SystemSettings.get_settings()
        settings.payment_policy = DEFAULT_PAYMENT_POLICY
        settings.save(update_fields=['payment_policy'])
        patcher = mock.patch('delivery.tasks.assign_nearest_delivery_agent')
        patcher.start()
        self.addCleanup(patcher.stop)
        self.api = APIClient()

    def paid_order(self, status='delivered', delivered_hours_ago=49):
        order = Order.objects.create(client=self.client_user, store=self.store, delivery_address='Akanda',
                                     delivery_phone='+24107200002', delivery_zone='Centre', delivery_fee=Decimal('2000'))
        OrderItem.objects.create(order=order, product=self.product, quantity=1, unit_price=self.product.price)
        Order.objects.filter(pk=order.pk).update(items_total=Decimal('10000'), commission_amount=Decimal('800'),
                                                 total_amount=Decimal('12000'), status=status)
        Payment.objects.create(order=order, payment_method='airtel_money', status='pending', amount=Decimal('12000'))
        Payment.objects.filter(order=order).update(status='success')
        Delivery.objects.filter(order=order).update(
            delivery_agent=self.driver, status='delivered', agent_commission=Decimal('1600'),
            delivered_at=timezone.now() - timedelta(hours=delivered_hours_ago),
        )
        order.refresh_from_db()
        return order

    def proof(self, order):
        from django.core.files.uploadedfile import SimpleUploadedFile
        photo = SimpleUploadedFile('id.gif', b'GIF89a\x01\x00\x01\x00\x00\x00\x00;', content_type='image/gif')
        return DeliveryProof.objects.create(delivery=order.delivery, id_card_photo=photo, latitude=Decimal('0.4'),
                                            longitude=Decimal('9.45'), pin_code='123456', pin_verified=True,
                                            client_received_status=False)

    # --- 1. versement automatique 48 h après la livraison --------------------------------
    def test_store_is_paid_48h_after_delivery_without_confirmation(self):
        order = self.paid_order()
        self.proof(order)
        release_unconfirmed_payouts()
        self.assertTrue(StorePayout.objects.filter(order=order).exists())

    def test_nothing_is_paid_before_48h(self):
        order = self.paid_order(delivered_hours_ago=10)
        release_unconfirmed_payouts()
        self.assertFalse(StorePayout.objects.filter(order=order).exists())

    def test_reported_problem_blocks_automatic_payment_until_admin_decides(self):
        order = self.paid_order()
        self.api.force_authenticate(self.client_user)
        response = self.api.post(f'/api/v1/orders/{order.id}/report-problem/', {'problem': 'Article cassé'}, format='json')
        self.assertEqual(response.status_code, 200)
        release_unconfirmed_payouts()
        self.assertFalse(StorePayout.objects.filter(order=order).exists())
        self.api.force_authenticate(self.admin)
        self.assertEqual(self.api.post(f'/api/v1/admin/orders/{order.id}/resolve-problem/').status_code, 200)
        self.assertTrue(StorePayout.objects.filter(order=order).exists())

    def test_driver_cannot_confirm_reception_for_the_client(self):
        order = self.paid_order(status='in_transit')
        Delivery.objects.filter(order=order).update(status='in_transit')
        self.api.force_authenticate(self.driver)
        from django.core.files.uploadedfile import SimpleUploadedFile
        photo = SimpleUploadedFile('id.gif', b'GIF89a\x01\x00\x01\x00\x00\x00\x00;', content_type='image/gif')
        self.api.post(f'/api/v1/dashboard/delivery/{order.delivery.id}/upload-proof/', {
            'id_card_photo': photo, 'latitude': '0.400000', 'longitude': '9.450000', 'client_received_status': 'true',
        }, format='multipart')
        proof = DeliveryProof.objects.filter(delivery=order.delivery).first()
        if proof is not None:
            self.assertFalse(proof.client_received_status)

    def test_client_confirmation_answers_ok(self):
        order = self.paid_order()
        self.proof(order)
        self.api.force_authenticate(self.client_user)
        response = self.api.post(f'/api/v1/orders/{order.id}/confirm-delivery/', {}, format='json')
        self.assertEqual(response.status_code, 200, response.content)

    # --- 2. pas d'annulation par le commerce d'une commande payée en route ----------------
    def test_store_cannot_cancel_paid_order_on_its_way(self):
        order = self.paid_order(status='in_transit')
        self.api.force_authenticate(self.manager)
        response = self.api.patch(f'/api/v1/orders/{order.id}/status/', {'status': 'cancelled'}, format='json')
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Order.objects.get(pk=order.pk).status, 'in_transit')
        listed = self.api.get(f'/api/v1/orders/{order.id}/').json()['data']
        self.assertFalse(listed['store_can_cancel'])

    def test_store_can_still_cancel_unpaid_order_on_its_way(self):
        order = self.paid_order(status='in_transit')
        Payment.objects.filter(order=order).update(status='failed')
        self.api.force_authenticate(self.manager)
        response = self.api.patch(f'/api/v1/orders/{order.id}/status/', {'status': 'cancelled'}, format='json')
        self.assertEqual(response.status_code, 200)

    # --- 3. forfaits clients --------------------------------------------------------------
    def test_forfait_routes_are_for_clients_not_admin_only(self):
        Forfait.objects.create(name='Livraison -20 %', monthly_price=Decimal('2000'), discount_rate=20)
        self.assertEqual(APIClient().get('/api/v1/forfaits/').status_code, 200)
        self.api.force_authenticate(self.client_user)
        self.assertEqual(self.api.get('/api/v1/my-forfait/').status_code, 200)

    def test_paid_forfait_is_activated_once_and_gives_delivery_discount(self):
        forfait = Forfait.objects.create(name='Livraison -20 %', monthly_price=Decimal('2000'), discount_rate=20)
        self.api.force_authenticate(self.client_user)
        with mock.patch('api.v1.client_forfaits.call_airtel_money_init', return_value={'transaction': {'id': 'TX1'}}):
            response = self.api.post('/api/v1/my-forfait/subscribe/', {'forfait_id': forfait.id, 'operator': 'airtel'}, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        self.assertIsNone(active_forfait(self.client_user))
        intent = PaymentIntent.objects.get(reference=response.json()['data']['reference'])
        from payments.views import process_intent_outcome
        process_intent_outcome(intent, 'TX1', 'success', {})
        process_intent_outcome(intent, 'TX1', 'success', {})
        self.assertEqual(ClientForfait.objects.filter(user=self.client_user).count(), 1)
        self.assertIsNotNone(active_forfait(self.client_user))
        self.assertEqual(delivery_discount(self.client_user, Decimal('2000')), Decimal('400'))

    def test_discount_is_paid_by_gaboshop_not_the_driver(self):
        order = self.paid_order(status='confirmed')
        order.forfait_discount = Decimal('400')
        order.save(update_fields=['forfait_discount'])
        from payments.direct_service import create_arrangement
        with mock.patch('payments.direct_service.available_payment_options', return_value=({'commission_settlement_days': 7}, [])), \
                mock.patch('payments.direct_service.matching_option', return_value=True):
            arrangement = create_arrangement(order, 'platform_online', 'airtel_money', 'gaboshop')
        amounts = {o.kind: o.amount for o in arrangement.obligations.all()}
        self.assertEqual(amounts['delivery_collection'], Decimal('1600'))
        self.assertEqual(amounts['delivery'], Decimal('2000'))

    # --- 4. B2B : articles reçus masqués ---------------------------------------------------
    def test_b2b_received_products_are_hidden_until_priced(self):
        buyer_manager = User.objects.create_user(phone='+24107200020', password='x', user_type='store_manager')
        buyer = Store.objects.create(is_verified=True, name='Acheteur', category=self.store.category, manager=buyer_manager,
                                     phone='+24107200021', address='Owendo', zone='Owendo')
        order = Order.objects.create(client=buyer_manager, store=self.store, source_store=buyer, is_b2b=True,
                                     delivery_address='Owendo', delivery_phone='+24107200020', delivery_zone='Owendo')
        OrderItem.objects.create(order=order, product=self.product, quantity=3, unit_price=self.product.price)
        order.status = 'delivered'
        order.save()
        received = Product.objects.get(store=buyer, name='Article')
        self.assertEqual(received.stock, 3)
        self.assertFalse(received.is_available)
