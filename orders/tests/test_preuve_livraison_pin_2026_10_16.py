"""Preuve de livraison : seul le code PIN du client prouve la remise (jamais une image ou une signature)."""
from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIRequestFactory, force_authenticate

from core.scheduled import release_unconfirmed_payouts
from delivery.models import Delivery, DeliveryProof
from orders.models import Order
from orders.tests import test_decisions_2026_10_15 as base
from payments.models import StorePayout

PIN = '482913'
GIF = b'GIF89a\x01\x00\x01\x00\x00\x00\x00;'


def image(name='photo.gif'):
    return SimpleUploadedFile(name, GIF, content_type='image/gif')


@override_settings(SINGPAY_ENABLE_TRANSFER=False)
class PreuveLivraisonPinTests(TestCase):
    setUp = base.DecisionsTests.setUp
    paid_order = base.DecisionsTests.paid_order

    def ride(self):
        """Commande en route, livreur assigné, code PIN connu du client seulement."""
        order = self.paid_order(status='in_transit')
        Delivery.objects.filter(order=order).update(status='in_transit', delivery_code=PIN, code_verified=False)
        self.api.force_authenticate(self.driver)
        return order, Delivery.objects.get(order=order)

    def upload(self, delivery, **fields):
        data = {'id_card_photo': image('id.gif'), 'latitude': '0.400000', 'longitude': '9.450000', **fields}
        return self.api.post(f'/api/v1/dashboard/delivery/{delivery.id}/upload-proof/', data, format='multipart')

    def complete(self, delivery):
        return self.api.post(f'/api/v1/dashboard/delivery/{delivery.id}/complete/')

    def assert_not_delivered(self, order, delivery):
        order.refresh_from_db()
        delivery.refresh_from_db()
        self.assertEqual(order.status, 'in_transit')
        self.assertEqual(delivery.status, 'in_transit')
        self.assertFalse(delivery.code_verified)

    # --- La faille : une image quelconque valait « signature » ---------------------------------
    def test_arbitrary_image_as_signature_proves_nothing(self):
        order, delivery = self.ride()
        res = self.upload(delivery, signature=image('nimporte-quoi.gif'))
        self.assertEqual(res.status_code, 400, res.content)
        self.assertEqual(res.json()['error']['code'], 'invalid_proof')
        self.assertIn('pin_code', res.json()['error']['details'])
        self.assertIn('PIN', res.json()['error']['details']['pin_code'])
        self.assertFalse(DeliveryProof.objects.filter(delivery=delivery).exists())
        delivery.refresh_from_db()
        self.assertFalse(delivery.client_signature)
        # Et la finalisation reste refusée, avec la raison et le moyen d'y remédier.
        res = self.complete(delivery)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()['error']['code'], 'proof_required')
        self.assertTrue(res.json()['error']['details']['pin_required'])
        self.assert_not_delivered(order, delivery)

    def test_signature_cannot_replace_a_wrong_pin(self):
        order, delivery = self.ride()
        res = self.upload(delivery, signature=image(), pin_code='000000')
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.json()['error']['code'], 'invalid_pin')
        self.assert_not_delivered(order, delivery)
        self.assertEqual(self.complete(delivery).status_code, 400)

    def test_completing_without_any_proof_is_refused(self):
        order, delivery = self.ride()
        self.assertEqual(self.complete(delivery).status_code, 400)
        self.assert_not_delivered(order, delivery)

    def test_legacy_signature_field_alone_cannot_complete(self):
        """Même une signature déjà enregistrée sur la livraison ne suffit plus à la finaliser."""
        order, delivery = self.ride()
        Delivery.objects.filter(pk=delivery.pk).update(client_signature='deliveries/signatures/x.gif',
                                                       delivery_proof_photo='deliveries/photos/x.gif',
                                                       proof_latitude=Decimal('0.4'), proof_longitude=Decimal('9.45'))
        self.assertEqual(self.complete(delivery).status_code, 400)
        self.assert_not_delivered(order, delivery)

    # --- Le chemin normal reste ouvert ----------------------------------------------------------
    def test_correct_pin_proves_delivery(self):
        order, delivery = self.ride()
        res = self.upload(delivery, pin_code=PIN)
        self.assertEqual(res.status_code, 200, res.content)
        self.assertTrue(res.json()['data']['pin_verified'])
        self.assertTrue(res.json()['data']['can_complete_delivery'])
        res = self.complete(delivery)
        self.assertEqual(res.status_code, 200, res.content)
        order.refresh_from_db()
        delivery.refresh_from_db()
        self.assertEqual((order.status, delivery.status), ('delivered', 'delivered'))
        self.assertTrue(delivery.code_verified)
        proof = DeliveryProof.objects.get(delivery=delivery)
        self.assertEqual(proof.status, 'verified')
        # Le client doit encore confirmer la réception : le livreur ne se déclare pas « reçu » lui-même.
        self.assertFalse(proof.client_received_status)

    def test_signature_sent_with_the_pin_is_not_stored(self):
        order, delivery = self.ride()
        self.assertEqual(self.upload(delivery, pin_code=PIN, signature=image('sig.gif')).status_code, 200)
        proof = DeliveryProof.objects.get(delivery=delivery)
        delivery.refresh_from_db()
        self.assertFalse(proof.signature)
        self.assertFalse(delivery.client_signature)

    def test_pin_checked_beforehand_is_enough_for_the_upload(self):
        order, delivery = self.ride()
        res = self.api.post(f'/api/v1/dashboard/delivery/{delivery.id}/verify-pin/', {'pin_code': PIN}, format='json')
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(self.upload(delivery).status_code, 200)
        self.assertEqual(self.complete(delivery).status_code, 200)
        order.refresh_from_db()
        self.assertEqual(order.status, 'delivered')

    def test_wrong_pin_is_counted_and_refused(self):
        order, delivery = self.ride()
        for _ in range(5):
            self.assertEqual(self.upload(delivery, pin_code='111111').status_code, 400)
        # Après 5 essais, même le bon code est bloqué un moment.
        self.assertEqual(self.upload(delivery, pin_code=PIN).status_code, 429)
        self.assert_not_delivered(order, delivery)

    def test_pin_still_needs_the_id_card_and_gps(self):
        order, delivery = self.ride()
        res = self.api.post(f'/api/v1/dashboard/delivery/{delivery.id}/upload-proof/', {'pin_code': PIN},
                            format='multipart')
        self.assertEqual(res.status_code, 400)
        self.assertIn('id_card_photo', res.json()['error']['details'])

    def test_far_gps_does_not_block_a_pin_proof(self):
        """Le GPS est un indice : un GPS imprécis ne bloque pas une remise prouvée par le code PIN."""
        order, delivery = self.ride()
        Delivery.objects.filter(pk=delivery.pk).update(delivery_lat=Decimal('0.300000'), delivery_lng=Decimal('9.300000'))
        res = self.upload(delivery, pin_code=PIN)
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(self.complete(delivery).status_code, 200)

    # --- Les autres chemins qui passaient une livraison en « livrée » -------------------------------
    def test_status_patch_to_delivered_needs_the_pin(self):
        from api.v1.delivery import DeliveryStatusUpdateView
        order, delivery = self.ride()
        request = APIRequestFactory().patch('/x/', {'status': 'delivered'}, format='json')
        force_authenticate(request, user=self.driver)
        res = DeliveryStatusUpdateView.as_view()(request, delivery_id=delivery.id)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data['error']['code'], 'pin_required')
        self.assert_not_delivered(order, delivery)
        # L'administrateur garde la main.
        request = APIRequestFactory().patch('/x/', {'status': 'delivered'}, format='json')
        force_authenticate(request, user=self.admin)
        self.assertEqual(DeliveryStatusUpdateView.as_view()(request, delivery_id=delivery.id).status_code, 200)

    def test_confirm_endpoint_needs_the_pin(self):
        from api.v1.delivery import DeliveryConfirmView
        order, delivery = self.ride()
        request = APIRequestFactory().post('/x/', {'rating': 5}, format='json')
        force_authenticate(request, user=self.driver)
        res = DeliveryConfirmView.as_view()(request, delivery_id=delivery.id)
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data['error']['code'], 'pin_required')
        self.assert_not_delivered(order, delivery)

    def test_order_service_refuses_a_courier_delivery_without_pin(self):
        from orders.services import OrderService
        order, delivery = self.ride()
        with self.assertRaises(ValueError):
            OrderService.update_order_status(order, 'delivered', self.driver)
        self.assert_not_delivered(order, delivery)
        Delivery.objects.filter(pk=delivery.pk).update(code_verified=True)
        order.refresh_from_db()
        OrderService.update_order_status(order, 'delivered', self.driver)
        self.assertEqual(Order.objects.get(pk=order.pk).status, 'delivered')

    # --- Le modèle de preuve ----------------------------------------------------------------------
    def test_a_new_proof_without_verified_pin_is_refused(self):
        order, delivery = self.ride()
        with self.assertRaises(ValidationError) as caught:
            DeliveryProof.objects.create(delivery=delivery, id_card_photo=image('id.gif'), latitude=Decimal('0.4'),
                                         longitude=Decimal('9.45'), signature=image('sig.gif'))
        self.assertIn('pin_verified', caught.exception.message_dict)

    def test_old_signature_only_proof_is_not_a_proof_but_stays_editable(self):
        order = self.paid_order(status='delivered')
        old = DeliveryProof(delivery=order.delivery, latitude=Decimal('0.4'), longitude=Decimal('9.45'),
                            id_card_photo='x.gif', signature='sig.gif', client_received_status=False)
        DeliveryProof.objects.bulk_create([old])
        proof = DeliveryProof.objects.get(delivery=order.delivery)
        self.assertFalse(proof.has_required_proof)
        self.assertFalse(proof.is_valid)
        # Le client peut quand même confirmer la réception d'une ancienne commande.
        self.assertTrue(proof.client_confirmation_pending)
        proof.client_received_status = True
        proof.save()

    def test_signature_proof_never_triggers_the_48h_payout(self):
        order = self.paid_order(status='delivered', delivered_hours_ago=49)
        DeliveryProof.objects.bulk_create([DeliveryProof(
            delivery=order.delivery, latitude=Decimal('0.4'), longitude=Decimal('9.45'), id_card_photo='x.gif',
            signature='sig.gif', client_received_status=False)])
        self.assertFalse(Delivery.objects.get(order=order).code_verified)
        release_unconfirmed_payouts()
        self.assertFalse(StorePayout.objects.filter(order=order).exists())
        self.assertGreater(timedelta(hours=49), timedelta(hours=48))
