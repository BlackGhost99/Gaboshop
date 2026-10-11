from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
import hashlib
import hmac
import json
import logging

from django.conf import settings

from notifications.whatsapp import WhatsAppService

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppWebhookView(APIView):
    """
    Webhook pour recevoir les messages WhatsApp. Appelé par Meta, sans connexion Gaboshop :
    la vérification se fait par le token (GET) et la signature de Meta (POST).
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        # Vérification du webhook
        challenge = WhatsAppService.verify_webhook(request)
        if challenge:
            return HttpResponse(challenge, content_type='text/plain')
        return HttpResponse('Verification failed', status=403, content_type='text/plain')

    @staticmethod
    def _signature_ok(request):
        """Avec WHATSAPP_APP_SECRET (clé secrète de l'app Meta, dans Render), on refuse les faux envois."""
        secret = getattr(settings, 'WHATSAPP_APP_SECRET', '')
        if not secret:
            return True
        expected = 'sha256=' + hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, request.headers.get('X-Hub-Signature-256', ''))

    def post(self, request):
        if not self._signature_ok(request):
            return HttpResponse('Invalid signature', status=403)
        try:
            data = json.loads(request.body)
            logger.info(f"?? Webhook WhatsApp reçu: {data}")
            
            # Traiter le webhook
            WhatsAppService.process_webhook(data)
            
            return HttpResponse('OK')
            
        except Exception as e:
            logger.error(f"? Erreur webhook WhatsApp: {e}")
            return HttpResponse('Error', status=500)
