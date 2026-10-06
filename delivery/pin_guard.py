"""Limite les essais de code PIN de livraison : 5 erreurs bloquent la livraison 30 minutes."""
from django.core.cache import cache

MAX_ATTEMPTS = 5
LOCK_SECONDS = 30 * 60


def _key(delivery):
	return f'delivery_pin_fail:{delivery.pk}'


def is_locked(delivery):
	try:
		return (cache.get(_key(delivery)) or 0) >= MAX_ATTEMPTS
	except Exception:
		return False


def record_failure(delivery):
	try:
		count = (cache.get(_key(delivery)) or 0) + 1
		cache.set(_key(delivery), count, LOCK_SECONDS)
	except Exception:
		pass


def reset(delivery):
	try:
		cache.delete(_key(delivery))
	except Exception:
		pass


LOCKED_MESSAGE = 'Trop de codes PIN erronés. Réessayez dans 30 minutes ou contactez le support.'
