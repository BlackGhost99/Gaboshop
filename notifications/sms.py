"""SMS service with multiple provider support.

This module implements a priority-based sender for Gabon: Hub2SMS ->
Twilio -> Infobip, with graceful simulation when provider keys are not set.
"""
import logging
import requests
from django.conf import settings
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class SMSService:
    """
    Service d'envoi de SMS avec support multiple providers
    Priorité: Hub2SMS (Gabon) ? Twilio ? Fallback
    """
    
    @staticmethod
    def send_sms(phone, message, provider=None):
        """
        Envoyer un SMS avec fallback automatique
        """
        # Aucun appel payant quand le site est volontairement en mode e-mail.
        if getattr(settings, 'NOTIFICATION_CHANNEL_MODE', 'auto') == 'email_only':
            return False
        providers = provider or settings.SMS_PROVIDER
        
        if isinstance(providers, str):
            providers = [providers]
        
        # Ordre de priorité des providers
        provider_order = ['hub2sms', 'twilio', 'infobip']
        providers = providers + [p for p in provider_order if p not in providers]
        # Dès qu'un vrai fournisseur a ses clés, on n'essaie que ceux-là : un échec ne doit
        # jamais être masqué par un envoi simulé (qui répond toujours « envoyé »).
        configured = [p for p in providers if SMSService._is_configured(p)]
        if configured:
            providers = configured
        
        for provider in providers:
            try:
                if provider == 'hub2sms':
                    success = Hub2SMSService.send_sms(phone, message)
                elif provider == 'twilio':
                    success = TwilioService.send_sms(phone, message)
                elif provider == 'infobip':
                    success = InfobipService.send_sms(phone, message)
                else:
                    continue
                
                if success:
                    return True
                    
            except Exception as e:
                logger.error(f"? Erreur SMS {provider}: {e}")
                continue
        
        # Fallback: log et retour échec
        logger.error(f"? Tous les providers SMS ont échoué pour {phone}")
        return False
    
    @staticmethod
    def _is_configured(provider):
        if provider == 'hub2sms':
            return bool(getattr(settings, 'HUB2SMS_API_KEY', ''))
        if provider == 'twilio':
            return bool(getattr(settings, 'TWILIO_ACCOUNT_SID', '') and getattr(settings, 'TWILIO_AUTH_TOKEN', ''))
        return False

    @staticmethod
    def _format_phone(phone):
        """
        Formater le numéro pour SMS Gabon
        """
        clean_phone = ''.join(filter(str.isdigit, str(phone)))
        
        # Format pour providers internationaux: +241...
        if clean_phone.startswith('241') and len(clean_phone) == 11:
            return '+' + clean_phone
        elif clean_phone.startswith('0') and len(clean_phone) == 9:
            return '+241' + clean_phone[1:]
        elif len(clean_phone) == 8:
            return '+241' + clean_phone
        else:
            return phone

class Hub2SMSService:
    """
    Service SMS spécialisé pour le Gabon via Hub2SMS
    """
    
    @staticmethod
    def send_sms(phone, message):
        """
        Envoyer un SMS via Hub2SMS Gabon
        """
        try:
            if not settings.HUB2SMS_API_KEY:
                logger.warning("?? Hub2SMS non configuré - Simulation")
                return Hub2SMSService._simulate_send(phone, message)
            
            formatted_phone = SMSService._format_phone(phone)
            
            # Hub2SMS accepte le format international
            payload = {
                'api_key': settings.HUB2SMS_API_KEY,
                'to': formatted_phone,
                'text': message,
                'from': settings.HUB2SMS_SENDER_ID,
                'type': 'text'
            }
            
            response = requests.post(
                'https://api.hub2sms.com/sms/send',
                data=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    logger.info(f"? SMS Hub2 envoyé à {formatted_phone}")
                    return True
                else:
                    logger.error(f"? Hub2SMS error: {result.get('message')}")
                    return False
            else:
                logger.error(f"? Hub2SMS HTTP error: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"? Erreur Hub2SMS: {e}")
            return False
    
    @staticmethod
    def _simulate_send(phone, message):
        logger.info(f"?? SMS Hub2 simulé à {phone}: {message}")
        return True

class TwilioService:
    """
    Service SMS via Twilio (fallback international)
    """
    
    @staticmethod
    def send_sms(phone, message):
        try:
            if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
                logger.warning("?? Twilio non configuré - Simulation")
                return TwilioService._simulate_send(phone, message)
            
            formatted_phone = SMSService._format_phone(phone)
            data = {'To': formatted_phone, 'Body': message}
            # Un « Messaging Service » Twilio (MG…) choisit lui-même l'expéditeur ; sinon le numéro ou nom d'expéditeur.
            if getattr(settings, 'TWILIO_MESSAGING_SERVICE_SID', ''):
                data['MessagingServiceSid'] = settings.TWILIO_MESSAGING_SERVICE_SID
            else:
                data['From'] = settings.TWILIO_PHONE_NUMBER
            response = requests.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}/Messages.json",
                data=data, auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN), timeout=15,
            )
            if response.status_code not in (200, 201):
                logger.error(f"? Twilio HTTP {response.status_code}: {response.text[:300]}")
                return False
            logger.info(f"? SMS Twilio envoyé à {formatted_phone} - SID: {response.json().get('sid')}")
            return True
            
        except Exception as e:
            logger.error(f"? Erreur Twilio: {e}")
            return False
    
    @staticmethod
    def _simulate_send(phone, message):
        logger.info(f"?? SMS Twilio simulé à {phone}: {message}")
        return True

class InfobipService:
    """
    Service SMS via Infobip (fallback)
    """
    
    @staticmethod
    def send_sms(phone, message):
        # Implémentation similaire à Twilio
        logger.info(f"?? SMS Infobip simulé à {phone}: {message}")
        return True
