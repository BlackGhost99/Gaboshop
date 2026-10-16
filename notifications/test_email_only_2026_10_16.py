"""Tests du canal e-mail gratuit (aucun appel réseau ni SMS réel)."""
from unittest.mock import patch

from django.test import TestCase, override_settings

from notifications.email import EmailService
from notifications.service import NotificationService
from users.models import User
from users.password_reset import send_phone_verification, request_code
from users.models import PasswordResetCode


EMAIL_SETTINGS = {
    'NOTIFICATION_CHANNEL_MODE': 'email_only',
    'BREVO_API_KEY': 'fake-ci-key',
    'EMAIL_HOST_USER': '',
    'EMAIL_BACKEND': 'core.email_backends.BrevoEmailBackend',
    'DEFAULT_FROM_EMAIL': 'Gaboshop <expediteur@example.org>',
}


@override_settings(**EMAIL_SETTINGS)
class EmailOnlyTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            phone='+241077123456', password='test-password-123', user_type='client',
            email='testdestinataire@example.org',
        )

    @patch('notifications.service.SMSService.send_sms')
    @patch('core.email_backends.requests.post')
    def test_message_reaches_email_for_each_role_without_sms(self, post, sms):
        post.return_value.status_code = 201
        post.return_value.raise_for_status.return_value = None
        template = {'sms': 'Votre commande de test est disponible'}
        senders = [
            lambda: NotificationService._send_to_client(self.user.phone, self.user.email, template, 'Nouvelle commande'),
            lambda: NotificationService._send_to_store(self.user.phone, template, 'Commerce', self.user.email),
            lambda: NotificationService._send_to_agent(self.user.phone, template, 'Livraison', self.user.email),
        ]
        for send in senders:
            self.assertTrue(send())
        sms.assert_not_called()
        self.assertEqual(post.call_count, 3)
        for call in post.call_args_list:
            payload = call.kwargs['json']
            self.assertEqual(payload['to'], [{'email': self.user.email}])
            self.assertEqual(payload['sender']['email'], 'expediteur@example.org')
            self.assertIn('commande de test', payload['textContent'])

    @patch('notifications.sms.SMSService.send_sms')
    @patch('core.email_backends.requests.post')
    def test_password_reset_is_sent_by_email_only(self, post, sms):
        post.return_value.status_code = 201
        post.return_value.raise_for_status.return_value = None
        request_code(self.user.phone)
        self.assertEqual(PasswordResetCode.objects.filter(user=self.user, purpose='reset').count(), 1)
        sms.assert_not_called()
        self.assertEqual(post.call_count, 1)
        self.assertIn('expire dans 15 min', post.call_args.kwargs['json']['textContent'])

    @patch('core.email_backends.requests.post')
    def test_email_does_not_confirm_phone_number(self, post):
        self.assertFalse(send_phone_verification(self.user))
        self.assertFalse(PasswordResetCode.objects.filter(user=self.user, purpose='verify_phone').exists())
        post.assert_not_called()

    @override_settings(BREVO_API_KEY='', EMAIL_HOST_USER='')
    @patch('core.email_backends.requests.post')
    def test_missing_provider_never_fakes_success(self, post):
        self.assertFalse(EmailService.send_text_email(self.user.email, 'Test', 'test message'))
        post.assert_not_called()

    @patch('notifications.service.SMSService.send_sms')
    @patch('notifications.sms.requests.post')
    @patch('notifications.whatsapp.requests.post')
    def test_no_external_sms_or_whatsapp_even_if_called_directly(self, wa_post, sms_post):
        from notifications.sms import SMSService
        from notifications.whatsapp import WhatsAppService
        self.assertFalse(SMSService.send_sms(self.user.phone, 'Test'))
        self.assertFalse(WhatsAppService.send_text_message(self.user.phone, 'Test'))
        self.assertFalse(WhatsAppService.send_template_message(self.user.phone, 'test_template', []))
        wa_post.assert_not_called()
        sms_post.assert_not_called()

    def test_without_email_only_in_app_remains(self, sms):
        self.user.email = ''
        self.user.save(update_fields=['email'])
        result = NotificationService._send_to_client(self.user.phone, '', {'sms': 'Test'}, 'Test')
        self.assertFalse(result)
        sms.assert_not_called()
