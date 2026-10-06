"""Limites anti-force brute sur la connexion et l'inscription."""
from rest_framework.throttling import SimpleRateThrottle


class _SafeThrottle(SimpleRateThrottle):
	# Si le cache est indisponible, on laisse passer plutôt que de bloquer tout le monde.
	def allow_request(self, request, view):
		try:
			return super().allow_request(request, view)
		except Exception:
			return True


class AuthIPThrottle(_SafeThrottle):
	"""Par adresse IP : 20 essais par minute."""
	scope = 'auth_ip'
	rate = '20/min'

	def get_cache_key(self, request, view):
		return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}


class LoginPhoneThrottle(_SafeThrottle):
	"""Par numéro de téléphone visé : 10 essais par quart d'heure."""
	scope = 'login_phone'
	rate = '10/15m'

	def parse_rate(self, rate):
		return (10, 15 * 60)

	def get_cache_key(self, request, view):
		phone = ''.join(ch for ch in str(request.data.get('phone') or request.data.get('username') or '') if ch.isdigit())[-8:]
		if not phone:
			return None
		return self.cache_format % {'scope': self.scope, 'ident': phone}
