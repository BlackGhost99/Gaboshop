from django.test import SimpleTestCase

from payments.references import next_reference, order_number_from_reference, paid_reference, payment_references


class _Order:
    order_number = 'CMD12345678'


class _Payment:
    def __init__(self, webhook_data=None):
        self.order = _Order()
        self.webhook_data = webhook_data


class OrderReferenceTests(SimpleTestCase):
    def test_order_number_is_read_with_or_without_attempt_number(self):
        self.assertEqual(order_number_from_reference('GABOSHOP_CMD12345678'), 'CMD12345678')
        self.assertEqual(order_number_from_reference('GABOSHOP_CMD12345678_3'), 'CMD12345678')
        self.assertEqual(order_number_from_reference('AUTRE_CMD12345678'), '')
        self.assertEqual(order_number_from_reference(None), '')

    def test_first_attempt_keeps_the_plain_reference(self):
        payment = _Payment()
        self.assertEqual(next_reference(payment, first_attempt=True), 'GABOSHOP_CMD12345678')
        self.assertEqual(next_reference(payment, first_attempt=False), 'GABOSHOP_CMD12345678_2')
        self.assertEqual(payment_references(payment), ['GABOSHOP_CMD12345678', 'GABOSHOP_CMD12345678_2'])

    def test_retry_of_a_payment_made_before_references_were_noted(self):
        payment = _Payment({'singpay_init_error': {'message': 'x'}})
        self.assertEqual(next_reference(payment, first_attempt=False), 'GABOSHOP_CMD12345678_2')
        self.assertEqual(payment.webhook_data['singpay_init_error'], {'message': 'x'})

    def test_paid_reference_prefers_the_successful_attempt(self):
        refs = ['GABOSHOP_CMD12345678', 'GABOSHOP_CMD12345678_2']
        self.assertEqual(paid_reference(_Payment({'singpay_references': refs})), 'GABOSHOP_CMD12345678_2')
        paid = _Payment({'singpay_references': refs, 'singpay_paid_reference': 'GABOSHOP_CMD12345678'})
        self.assertEqual(paid_reference(paid), 'GABOSHOP_CMD12345678')
        self.assertEqual(paid_reference(_Payment()), 'GABOSHOP_CMD12345678')
