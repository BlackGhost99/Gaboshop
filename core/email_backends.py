"""Envoi des e-mails par l'API HTTP de Brevo.

Render bloque le SMTP sortant sur les services gratuits : avec BREVO_API_KEY défini,
Django envoie ses e-mails par HTTPS au lieu du SMTP.
"""
import logging
from email.utils import parseaddr

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

BREVO_URL = 'https://api.brevo.com/v3/smtp/email'


class BrevoEmailBackend(BaseEmailBackend):
	def send_messages(self, email_messages):
		sent = 0
		for message in email_messages:
			name, address = parseaddr(message.from_email or settings.DEFAULT_FROM_EMAIL)
			payload = {
				'sender': {'name': name or 'Gaboshop', 'email': address},
				'to': [{'email': parseaddr(to)[1]} for to in message.to],
				'subject': message.subject,
				'textContent': message.body,
			}
			try:
				response = requests.post(BREVO_URL, json=payload, timeout=10, headers={
					'api-key': settings.BREVO_API_KEY, 'accept': 'application/json',
				})
				response.raise_for_status()
				sent += 1
			except requests.RequestException:
				logger.exception("Envoi e-mail Brevo impossible")
				if not self.fail_silently:
					raise
		return sent
