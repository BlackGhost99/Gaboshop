"""« Mot de passe oublié » : un code à 6 chiffres envoyé par SMS (et par e-mail si le compte en a un).

Le code expire au bout de 15 minutes, 5 essais au plus. On ne dit jamais si un numéro a un compte.
Sans fournisseur SMS configuré, aucun code n'est simulé : l'utilisateur est orienté vers le support,
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


def email_available():
	return bool(getattr(settings, 'EMAIL_HOST_USER', ''))


def _find_user(phone):
	from users.models import User
	return User.objects.filter(phone=normalize_phone(phone), is_active=True).first()


def request_code(phone):
	"""Crée et envoie un code si le compte existe. Ne renvoie rien qui trahisse l'existence du compte."""
	from users.models import PasswordResetCode
	user = _find_user(phone)
	if user is None:
		return
	now = timezone.now()
	if PasswordResetCode.objects.filter(user=user, created_at__gte=now - timedelta(hours=1)).count() >= MAX_CODES_PER_HOUR:
		return
	can_sms, can_email = sms_available(), email_available() and bool(user.email)
	if not (can_sms or can_email):
		return
	code = f"{secrets.randbelow(1_000_000):06d}"
	PasswordResetCode.objects.filter(user=user, used_at__isnull=True).update(used_at=now)
	PasswordResetCode.objects.create(
		user=user, code_hash=make_password(code), expires_at=now + timedelta(minutes=CODE_MINUTES),
	)
	message = f"Gaboshop : votre code pour changer de mot de passe est {code}. Il expire dans {CODE_MINUTES} min. Ne le donnez à personne."
	if can_sms:
		try:
			SMSService.send_sms(user.phone, message)
		except Exception:
			logger.exception("Envoi SMS du code de réinitialisation impossible")
	if can_email:
		try:
			send_mail('Gaboshop : changer votre mot de passe', message, settings.DEFAULT_FROM_EMAIL, [user.email])
		except Exception:
			logger.exception("Envoi e-mail du code de réinitialisation impossible")


def reset_password(phone, code, new_password):
	"""Renvoie (True, '') si le mot de passe a été changé, sinon (False, raison lisible)."""
	from users.models import PasswordResetCode
	invalid = "Code incorrect ou expiré. Demandez un nouveau code."
	user = _find_user(phone)
	if user is None:
		return False, invalid
	entry = PasswordResetCode.objects.filter(user=user, used_at__isnull=True, expires_at__gt=timezone.now()).first()
	if entry is None or entry.attempts >= MAX_ATTEMPTS:
		return False, invalid
	if not check_password(str(code or '').strip(), entry.code_hash):
		entry.attempts += 1
		entry.save(update_fields=['attempts'])
		left = MAX_ATTEMPTS - entry.attempts
		return False, (f"Code incorrect. Il vous reste {left} essai(s)." if left > 0 else invalid)
	user.set_password(new_password)
	user.save(update_fields=['password'])
	entry.used_at = timezone.now()
	entry.save(update_fields=['used_at'])
	return True, ''
