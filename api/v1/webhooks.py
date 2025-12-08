from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
import json
import logging

from notifications.whatsapp import WhatsAppService

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class WhatsAppWebhookView(APIView):
    """
    Webhook pour recevoir les messages WhatsApp
    """
    
    def get(self, request):
        # Vérification du webhook
        challenge = WhatsAppService.verify_webhook(request)
        if challenge:
            return HttpResponse(challenge)
        return HttpResponse('Verification failed', status=400)
    
    def post(self, request):
        try:
            data = json.loads(request.body)
            logger.info(f"📨 Webhook WhatsApp reçu: {data}")
            
            # Traiter le webhook
            WhatsAppService.process_webhook(data)
            
            return HttpResponse('OK')
            
        except Exception as e:
            logger.error(f"❌ Erreur webhook WhatsApp: {e}")
            return HttpResponse('Error', status=500)
