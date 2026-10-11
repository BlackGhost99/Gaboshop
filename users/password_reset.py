"""« Mot de passe oublié » : un code à 6 chiffres envoyé par WhatsApp ou SMS (et par e-mail si le compte en a un).

Le code expire au bout de 15 minutes, 5 essais au plus. On ne dit jamais si un numéro a un compte.
Sans WhatsApp ni SMS configuré, aucun code n'est simulé : l'utilisateur est orienté vers le support,
qui peut définir un nouveau mot de passe depuis l'admin.
"""
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.utils import timezone

from notifications.sms import SMSService

logger = logging.getLogger(__name__)

CODE_MINUTES = 15
MAX_ATTEMPTS = 5
MAX_CODES_PER_HOUR = 3


def normalize_phone(raw):
	"""Mêmes formats que la connexion : +241…, 241…, 0…, ou 8 chiffres."""
	phone = str(raw or '').strip().replace(' ', '')
	if phone.startswith('241'):
		return '+' + phone
	if phone.startswith('0'):
		return '+241' + phone[1:]
	if phone.isdigit() and len(phone) == 8:
		return '+241' + phone
	return phone


def sms_available():
	"""Vrai seulement si un vrai fournisseur SMS a ses clés (la simulation ne compte pas)."""
	return bool(
		getattr(settings, 'HUB2SMS_API_KEY', '')
		or (getattr(settings, 'TWILIO_ACCOUNT_SID', '') and getattr(settings, 'TWILIO_AUTH_TOKEN', ''))
	)


def whatsapp_available():
	"""WhatsApp Cloud API configuré dans Render, modèle de code approuvé (WHATSAPP_OTP_TEMPLATE) et non coupé dans l'admin."""
	from api.models import SystemSettings
	return bool(
		getattr(settings, 'WHATSAPP_ACCESS_TOKEN', '') and getattr(settings, 'WHATSAPP_PHONE_ID', '')
		and getattr(settings, 'WHATSAPP_OTP_TEMPLATE', '')
		and SystemSettings.current('enable_whatsapp', True)
	)


def send_code_whatsapp(phone, code):
	"""Modèle Meta de catégorie « Authentification » (corps {{1}} + bouton « Copier le code »)."""
	from notifications.whatsapp import WhatsAppService
	return WhatsAppService.send_template_message(phone, settings.WHATSAPP_OTP_TEMPLATE, [
		{'type': 'body', 'parameters': [{'type': 'text', 'text': code}]},
		{'type': 'button', 'sub_type': 'url', 'index': '0', 'parameters': [{'type': 'text', 'text': code}]},
	])


def email_available():
	return bool(getattr(settings, 'BREVO_API_KEY', '') or getattr(settings, 'EMAIL_HOST_USER', ''))


def _find_user(phone):
	from users.models import User
	return User.objects.filter(phone=normalize_phone(phone), is_active=True).first()


def _issue_code(user, purpose):
	"""Crée un code et l'envoie (WhatsApp, sinon SMS ; e-mail en plus). Renvoie False si aucun canal."""
	from users.models import PasswordResetCode
	now = timezone.now()
	recent = PasswordResetCode.objects.filter(user=user, purpose=purpose, created_at__gte=now - timedelta(hours=1))
	if recent.count() >= MAX_CODES_PER_HOUR:
		return False
	can_whatsapp, can_sms = whatsapp_available(), sms_available()
	can_email = email_available() and bool(user.email)
	if not (can_whatsapp or can_sms or can_email):
		return False
	code = f"{secrets.randbelow(1_000_000):06d}"
	PasswordResetCode.objects.filter(user=user, purpose=purpose, used_at__isnull=True).update(used_at=now)
	PasswordResetCode.objects.create(
		user=user, purpose=purpose, code_hash=make_password(code), expires_at=now + timedelta(minutes=CODE_MINUTES),
	)
	what = 'changer de mot de passe' if purpose == 'reset' else 'vérifier votre numéro'
	message = f"Gaboshop : votre code pour {what} est {code}. Il expire dans {CODE_MINUTES} min. Ne le donnez à personne."
	sent = False
	if can_whatsapp:
		try:
			sent = send_code_whatsapp(user.phone, code)
		except Exception:
			logger.exception("Envoi WhatsApp du code impossible")
	if can_sms and not sent:
		try:
			sent = SMSService.send_sms(user.phone, message)
		except Exception:
			logger.exception("Envoi SMS du code impossible")
	if can_email:
		try:
			send_mail('Gaboshop : votre code', message, settings.DEFAULT_FROM_EMAIL, [user.email])
			sent = True
		except Exception:
			logger.exception("Envoi e-mail du code impossible")
	return sent


def _check_code(user, code, purpose):
	"""Renvoie (True, '') et consomme le code s'il est bon, sinon (False, raison lisible)."""
	from users.models import PasswordResetCode
	invalid = "Code incorrect ou expiré. Demandez un nouveau code."
	entry = PasswordResetCode.objects.filter(
		user=user, purpose=purpose, used_at__isnull=True, expires_at__gt=timezone.now(),
	).first()
	if entry is None or entry.attempts >= MAX_ATTEMPTS:
		return False, invalid
	if not check_password(str(code or '').strip(), entry.code_hash):
		entry.attempts += 1
		entry.save(update_fields=['attempts'])
		left = MAX_ATTEMPTS - entry.attempts
		return False, (f"Code incorrect. Il vous reste {left} essai(s)." if left > 0 else invalid)
	entry.used_at = timezone.now()
	entry.save(update_fields=['used_at'])
	return True, ''


def channels_available():
	return whatsapp_available() or sms_available()


def request_code(phone):
	"""Mot de passe oublié : envoie un code si le compte existe, sans jamais le révéler."""
	user = _find_user(phone)
	if user is not None:
		_issue_code(user, 'reset')


def reset_password(phone, code, new_password):
	"""Renvoie (True, '') si le mot de passe a été changé, sinon (False, raison lisible)."""
	user = _find_user(phone)
	if user is None:
		return False, "Code incorrect ou expiré. Demandez un nouveau code."
	ok, reason = _check_code(user, code, 'reset')
	if not ok:
		return False, reason
	user.set_password(new_password)
	user.save(update_fields=['password'])
	return True, ''


def send_phone_verification(user):
	return _issue_code(user, 'verify_phone')


def confirm_phone_verification(user, code):
	ok, reason = _check_code(user, code, 'verify_phone')
	if ok:
		user.phone_verified_at = timezone.now()
		user.save(update_fields=['phone_verified_at'])
	return ok, reason
