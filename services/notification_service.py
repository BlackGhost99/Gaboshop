import requests
import logging
from django.conf import settings
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

class NotificationService:
    """Service de gestion des notifications WhatsApp/SMS"""
    
    @staticmethod
    def send_whatsapp_message(phone, template_name, parameters):
        """
        Envoyer un message WhatsApp via l'API Cloud
        """
        try:
            # Format du numéro Gabon
            formatted_phone = NotificationService._format_phone(phone)
            
            # En production, utiliser l'API WhatsApp Business
            # Pour le MVP, on simule l'envoi
            logger.info(f"📱 WhatsApp envoyé à {formatted_phone}: {template_name} - {parameters}")
            
            # Simulation d'envoi réussi
            return True
            
            # Code pour l'API réelle (à décommenter en production):
            """
            response = requests.post(
                f"https://graph.facebook.com/v17.0/{settings.WHATSAPP_PHONE_ID}/messages",
                headers={
                    "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
                    "Content-Type": "application/json"
                },
                json={
                    "messaging_product": "whatsapp",
                    "to": formatted_phone,
                    "type": "template",
                    "template": {
                        "name": template_name,
                        "language": {"code": "fr"},
                        "components": parameters
                    }
                },
                timeout=10
            )
            return response.status_code == 200
            """
            
        except Exception as e:
            logger.error(f"❌ Erreur envoi WhatsApp: {e}")
            return False
    
    @staticmethod
    def send_sms(phone, message):
        """
        Envoyer un SMS (fallback si WhatsApp échoue)
        """
        try:
            formatted_phone = NotificationService._format_phone(phone)
            logger.info(f"📞 SMS envoyé à {formatted_phone}: {message}")
            
            # Intégration avec service SMS (Twilio, InfoBip, etc.)
            return True
        except Exception as e:
            logger.error(f"❌ Erreur envoi SMS: {e}")
            return False
    
    @staticmethod
    def _format_phone(phone):
        """Formater le numéro de téléphone pour le Gabon"""
        if phone.startswith('0'):
            return '+241' + phone[1:]
        elif not phone.startswith('+'):
            return '+241' + phone
        return phone
    
    @staticmethod
    def notify_new_order(order):
        """Notifier le magasin d'une nouvelle commande"""
        store_phone = order.store.phone
        message = f"🛍️ Nouvelle commande #{order.order_number} - {order.total_amount} FCFA"
        
        # WhatsApp
        success = NotificationService.send_whatsapp_message(
            phone=store_phone,
            template_name="nouvelle_commande",
            parameters=[{
                "type": "body",
                "parameters": [
                    {"type": "text", "text": f"#{order.order_number}"},
                    {"type": "text", "text": f"{order.total_amount} FCFA"},
                    {"type": "text", "text": f"{order.client.phone}"}
                ]
            }]
        )
        
        # Fallback SMS
        if not success:
            NotificationService.send_sms(store_phone, message)
    
    @staticmethod
    def notify_delivery_assigned(delivery):
        """Notifier le livreur d'une nouvelle mission"""
        if delivery.delivery_agent:
            message = f"🚗 Nouvelle livraison #{delivery.tracking_number} - {delivery.delivery_fee} FCFA"
            
            NotificationService.send_whatsapp_message(
                phone=delivery.delivery_agent.phone,
                template_name="nouvelle_livraison",
                parameters=[{
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": f"#{delivery.tracking_number}"},
                        {"type": "text", "text": f"{delivery.delivery_fee} FCFA"},
                        {"type": "text", "text": delivery.pickup_address},
                        {"type": "text", "text": delivery.delivery_address}
                    ]
                }]
            )
    
    @staticmethod
    def notify_order_status_update(order, old_status, new_status):
        """Notifier le client du changement de statut"""
        message = f"📦 Commande #{order.order_number}: {old_status} → {new_status}"
        
        NotificationService.send_whatsapp_message(
            phone=order.client.phone,
            template_name="statut_commande",
            parameters=[{
                "type": "body",
                "parameters": [
                    {"type": "text", "text": f"#{order.order_number}"},
                    {"type": "text", "text": order.get_status_display()}
                ]
            }]
        )
