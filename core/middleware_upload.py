"""Refuse les envois trop gros avant que Django ne les lise (mémoire, disque, base)."""
from django.http import JsonResponse

MAX_REQUEST_BYTES = 15 * 1024 * 1024  # 15 Mo


class MaxUploadSizeMiddleware:
	def __init__(self, get_response):
		self.get_response = get_response

	def __call__(self, request):
		try:
			length = int(request.META.get('CONTENT_LENGTH') or 0)
		except (TypeError, ValueError):
			length = 0
		if length > MAX_REQUEST_BYTES:
			return JsonResponse({
				'success': False,
				'error': {
					'code': 413,
					'message': 'Fichier ou envoi trop volumineux (15 Mo au maximum).',
					'next_step': 'Réduisez la taille du fichier (photo compressée, PDF allégé), puis réessayez.',
				},
			}, status=413)
		return self.get_response(request)
