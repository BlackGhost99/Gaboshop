"""WhatsApp Business API service optimized for Gabon (full helper).

Provides template and text sending, webhook verification and webhook
processing helpers. In development the class simulates sends when the
WhatsApp tokens/IDs are not configured.
"""
import requests
import logging
from django.conf import settings
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class WhatsAppService:
    """
    Service d'envoi de messages via WhatsApp Business API
    Optimisé pour le marché Gabonais
    """
    
    @staticmethod
    def send_template_message(phone, template_name, parameters, language_code="fr"):
        """
        Envoyer un message template WhatsApp
        """
        try:
            formatted_phone = WhatsAppService._format_phone(phone)
            
            # Vérifier la configuration
            if not settings.WHATSAPP_ACCESS_TOKEN or not settings.WHATSAPP_PHONE_ID:
                logger.warning("⚠️ WhatsApp non configuré - Simulation d'envoi")
                return WhatsAppService._simulate_send(phone, template_name, parameters)
            
            payload = {
                "messaging_product": "whatsapp",
                "to": formatted_phone,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": language_code},
                    "components": parameters
                }
            }
            
            response = requests.post(
                f"{settings.WHATSAPP_BUSINESS_API_URL}/{settings.WHATSAPP_PHONE_ID}/messages",
                headers={
                    "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                logger.info(f"✅ WhatsApp envoyé à {formatted_phone}: {template_name}")
                return True
            else:
                logger.error(f"❌ Erreur WhatsApp {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error("❌ Timeout WhatsApp API")
            return False
        except Exception as e:
            logger.error(f"❌ Erreur WhatsApp: {e}")
            return False
    
    @staticmethod
    def send_text_message(phone, message):
        """
        Envoyer un message texte simple
        """
        try:
            formatted_phone = WhatsAppService._format_phone(phone)
            
            if not settings.WHATSAPP_ACCESS_TOKEN:
                logger.info(f"📱 WhatsApp simulé à {formatted_phone}: {message}")
                return True
            
            payload = {
                "messaging_product": "whatsapp",
                "to": formatted_phone,
                "type": "text",
                "text": {"body": message}
            }
            
            response = requests.post(
                f"{settings.WHATSAPP_BUSINESS_API_URL}/{settings.WHATSAPP_PHONE_ID}/messages",
                headers={
                    "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=15
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"❌ Erreur WhatsApp texte: {e}")
            return False
    
    @staticmethod
    def _format_phone(phone):
        """
        Formater le numéro pour WhatsApp (format international Gabon)
        """
        # Nettoyer le numéro
        clean_phone = ''.join(filter(str.isdigit, str(phone)))
        
        # Format Gabon: +241XXXXXXXX
        if clean_phone.startswith('241') and len(clean_phone) == 11:
            return '+' + clean_phone
        elif clean_phone.startswith('0') and len(clean_phone) == 9:
            return '+241' + clean_phone[1:]
        elif len(clean_phone) == 8:  # Juste les 8 chiffres
            return '+241' + clean_phone
        else:
            # Supposer que c'est déjà formaté
            return phone if phone.startswith('+') else f"+{phone}"
    
    @staticmethod
    def _simulate_send(phone, template_name, parameters):
        """
        Simuler l'envoi pendant le développement
        """
        logger.info(
            f"🎯 WhatsApp simulé - À: {phone} | "
            f"Template: {template_name} | "
            f"Params: {parameters}"
        )
        return True
    
    @staticmethod
    def verify_webhook(request):
        """
        Vérifier le webhook WhatsApp (pour callback)
        """
        verify_token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        
        if verify_token == settings.WHATSAPP_VERIFY_TOKEN:
            return challenge
        return None
    
    @staticmethod
    def process_webhook(data):
        """
        Traiter les webhooks WhatsApp (réponses des utilisateurs)
        """
        try:
            entry = data.get('entry', [{}])[0]
            changes = entry.get('changes', [{}])[0]
            value = changes.get('value', {})
            messages = value.get('messages', [])
            
            for message in messages:
                phone = message.get('from')
                message_type = message.get('type')
                
                if message_type == 'text':
                    text_body = message.get('text', {}).get('body', '')
                    WhatsAppService._handle_text_response(phone, text_body)
                elif message_type == 'button':
                    # Gérer les réponses aux boutons
                    button_response = message.get('button', {}).get('text', '')
                    WhatsAppService._handle_button_response(phone, button_response)
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Erreur traitement webhook WhatsApp: {e}")
            return False
    
    @staticmethod
    def _handle_text_response(phone, text):
        """
        Traiter les réponses texte des utilisateurs
        """
        # Exemple: confirmation de livraison, statut commande, etc.
        logger.info(f"📨 Réponse WhatsApp de {phone}: {text}")
        
        # Ici on peut intégrer avec le chatbot GABOSHOP
        # Pour le MVP, on log simplement
    
    @staticmethod
    def _handle_button_response(phone, button_text):
        """
        Traiter les réponses aux boutons interactifs
        """
        logger.info(f"🔘 Bouton WhatsApp de {phone}: {button_text}")
        
        # Actions possibles:
        # - "Confirmer livraison"
        # - "Annuler commande" 
        # - "Voir statut"
        # - "Contacter support"
