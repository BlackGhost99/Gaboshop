"""Limites anti-force brute sur la connexion et l'inscription."""
from rest_framework.throttling import SimpleRateThrottle


def client_ip(request):
	"""Adresse IP du client, sans faire confiance à un X-Forwarded-For fabriqué par l'appelant.

	Ordre : en-tête Cloudflare, sinon DERNIÈRE adresse de X-Forwarded-For (celle ajoutée par
	notre proxy, l'appelant ne peut écrire que le début), sinon REMOTE_ADDR."""
	meta = getattr(request, 'META', {}) or {}
	cf = (meta.get('HTTP_CF_CONNECTING_IP') or '').strip()
	if cf:
		return cf
	xff = meta.get('HTTP_X_FORWARDED_FOR') or ''
	parts = [p.strip() for p in xff.split(',') if p.strip()]
	if parts:
		return parts[-1]
	return (meta.get('REMOTE_ADDR') or '').strip()


class ClientIPMixin:
	# Remplace get_ident de DRF, qui croit tout X-Forwarded-For (contournement trop facile).
	def get_ident(self, request):
		return client_ip(request)


class _SafeThrottle(ClientIPMixin, SimpleRateThrottle):
	# Si le cache est indisponible, on laisse passer plutôt que de bloquer tout le monde.
	def allow_request(self, request, view):
		try:
			return super().allow_request(request, view)
		except Exception:
			return True


class AuthIPThrottle(_SafeThrottle):
	"""Par adresse IP : 60 essais par minute (au Gabon, beaucoup de clients mobiles partagent la même IP opérateur ;
	la vraie protection anti-force brute est la limite par numéro ci-dessous)."""
	scope = 'auth_ip'
	rate = '60/min'

	def get_cache_key(self, request, view):
		return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}


class OrderCreateThrottle(_SafeThrottle):
	"""Par compte : 20 commandes par heure au plus (au-delà, c'est un robot ou un sabotage de stock)."""
	scope = 'order_create'
	rate = '20/hour'

	def get_cache_key(self, request, view):
		if not request.user or not request.user.is_authenticated:
			return None
		return self.cache_format % {'scope': self.scope, 'ident': request.user.pk}


class LoginPhoneThrottle(_SafeThrottle):
	"""Par numéro de téléphone visé : 10 essais par quart d'heure."""
	scope = 'login_phone'
	rate = '10/15m'
	ATTEMPTS = 10

	def parse_rate(self, rate):
		return (self.ATTEMPTS, 15 * 60)

	def get_cache_key(self, request, view):
		phone = ''.join(ch for ch in str(request.data.get('phone') or request.data.get('username') or '') if ch.isdigit())[-8:]
		if not phone:
			return None
		return self.cache_format % {'scope': self.scope, 'ident': phone}
