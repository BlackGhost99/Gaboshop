"""Limite les essais de code PIN de livraison (par défaut 5 erreurs bloquent 30 minutes ; réglable dans l'admin)."""
from django.core.cache import cache

MAX_ATTEMPTS = 5
LOCK_MINUTES = 30


def max_attempts():
	from api.models import SystemSettings
	return int(SystemSettings.current('pin_max_attempts', MAX_ATTEMPTS) or MAX_ATTEMPTS)


def lock_minutes():
	from api.models import SystemSettings
	return int(SystemSettings.current('pin_lock_minutes', LOCK_MINUTES) or LOCK_MINUTES)


def _key(delivery):
	return f'delivery_pin_fail:{delivery.pk}'


def is_locked(delivery):
	try:
		return (cache.get(_key(delivery)) or 0) >= max_attempts()
	except Exception:
		return False


def record_failure(delivery):
	try:
		count = (cache.get(_key(delivery)) or 0) + 1
		cache.set(_key(delivery), count, lock_minutes() * 60)
	except Exception:
		pass


def reset(delivery):
	try:
		cache.delete(_key(delivery))
	except Exception:
		pass


def locked_message():
	return f'Trop de codes PIN erronés. Réessayez dans {lock_minutes()} minutes ou contactez le support.'
