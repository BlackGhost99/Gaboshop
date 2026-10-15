"""Justificatifs de paiement et de dépenses privés (15/10) : plus de lien public, accès contrôlé."""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from finance.models import Expense
from payments.direct_models import PaymentReceipt
from payments.tests import test_security_money_2026_10_15 as base
from users.models import User

PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 64


def png(name='capture.png'):
    return SimpleUploadedFile(name, PNG, content_type='image/png')


@override_settings(MEDIA_IN_DATABASE=True)
class PrivateProofTests(base.MoneyBase):
    ONLINE = False
    def setUp(self):
        super().setUp()
        self.store.payment_preferences = {'instructions': {'airtel_money': 'Code Airtel 1', 'moov_money': 'Code Moov 2'}}
        self.store.save(update_fields=['payment_preferences'])
    products_obligation = base.ReceiptReferenceTests.products_obligation

    def declare_with_proof(self):
        obligation = self.products_obligation()
        self.api.force_authenticate(self.client_user)
        res = self.api.post('/api/v1/payments/receipts/', {
            'obligation_id': obligation.id, 'amount': '10000', 'reference': 'MP900', 'idempotency_key': 'p1',
            'proof': png()}, format='multipart')
        self.assertEqual(res.status_code, 201, res.content)
        return PaymentReceipt.objects.get(idempotency_key='p1')

    def test_receipt_proof_is_private_and_served_to_the_right_people(self):
        receipt = self.declare_with_proof()
        self.assertTrue(receipt.proof.name.startswith('private/receipt_proofs/'))
        self.assertNotIn('capture', receipt.proof.name)  # nom imprévisible
        # Plus de lien public.
        self.api.force_authenticate(None)
        self.assertEqual(self.api.get(f'/media/{receipt.proof.name}').status_code, 404)
        url = f'/api/v1/payments/receipts/{receipt.id}/proof/'
        self.assertIn(self.api.get(url).status_code, (401, 403))
        stranger = User.objects.create_user(phone='+24107300999', password='x', user_type='client')
        self.api.force_authenticate(stranger)
        self.assertEqual(self.api.get(url).status_code, 403)
        for user in (self.client_user, self.manager, self.admin):
            self.api.force_authenticate(user)
            res = self.api.get(url)
            self.assertEqual(res.status_code, 200, user.user_type)
            self.assertEqual(res['Cache-Control'], 'private, no-store')

    def test_old_public_proof_paths_are_blocked(self):
        from core.models import StoredFile
        StoredFile.objects.create(name='payments/receipt_proofs/IMG-1.png', content=PNG, content_type='image/png', size=len(PNG))
        self.assertEqual(self.api.get('/media/payments/receipt_proofs/IMG-1.png').status_code, 404)

    def test_expense_attachment_only_for_its_store(self):
        self.api.force_authenticate(self.manager)
        expense = Expense.objects.create(store=self.store, amount='5000', expense_date='2026-10-15', attachment=png('facture.png'))
        self.assertTrue(expense.attachment.name.startswith('private/expenses/'))
        url = f'/api/v1/store/finance/expenses/{expense.id}/attachment/'
        listed = self.api.get(f'/api/v1/store/finance/expenses/{expense.id}/').json()
        self.assertEqual(listed.get('attachment_url') or listed.get('data', {}).get('attachment_url'), url)
        other = User.objects.create_user(phone='+24107300998', password='x', user_type='store_manager')
        self.api.force_authenticate(other)
        self.assertIn(self.api.get(url).status_code, (403, 404))
