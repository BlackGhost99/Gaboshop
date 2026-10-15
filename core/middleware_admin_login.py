"""Protection anti-force brute de la page de connexion de l'admin Django (/admin/login/).

Au plus MAX_FAILURES échecs par adresse IP et par identifiant sur WINDOW_SECONDS, puis 429.
Si le cache est indisponible, on laisse passer plutôt que de bloquer l'admin.
"""
import hashlib

from django.core.cache import cache
from django.http import HttpResponse
from django.urls import NoReverseMatch, reverse

from users.throttles import client_ip

MAX_FAILURES = 10
WINDOW_SECONDS = 15 * 60


def _admin_login_path():
	try:
		return reverse('admin:login')
	except NoReverseMatch:
		return None


def _keys(request):
	ip = client_ip(request) or 'inconnue'
	username = (request.POST.get('username') or '').strip().lower()
	keys = ['admin_login_fail:ip:' + ip]
	if username:
		# Identifiant haché : pas de numéro de téléphone en clair dans le cache.
		keys.append('admin_login_fail:user:' + hashlib.sha256(username.encode()).hexdigest()[:32])
	return keys


class AdminLoginThrottleMiddleware:
	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		if request.method != 'POST' or request.path != _admin_login_path():
			return self.get_response(request)
		try:
			keys = _keys(request)
			counts = cache.get_many(keys)
			blocked = any((counts.get(k) or 0) >= MAX_FAILURES for k in keys)
		except Exception:
			return self.get_response(request)
		if blocked:
			response = HttpResponse(
				'Trop de tentatives de connexion. Réessayez dans 15 minutes.',
				status=429, content_type='text/plain; charset=utf-8',
			)
			response['Retry-After'] = str(WINDOW_SECONDS)
			return response
		response = self.get_response(request)
		try:
			# Connexion réussie = redirection ; formulaire réaffiché (200) = échec.
			if response.status_code == 200:
				for key in keys:
					if cache.add(key, 1, WINDOW_SECONDS) is False:
						try:
							cache.incr(key)
						except ValueError:
							cache.set(key, 1, WINDOW_SECONDS)
			elif response.status_code in (301, 302, 303):
				cache.delete_many(keys[1:])
		except Exception:
			pass
		return response
