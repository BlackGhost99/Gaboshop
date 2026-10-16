"""Email helpers and a small EmailService for notifications.

Provides template-based email sending and a simulation mode when SMTP
is not configured. Uses Django's template loader so templates should live
under a registered templates directory (e.g. `templates/emails/`).
"""
import logging
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings

logger = logging.getLogger(__name__)


class EmailService:
    """
    Service d'envoi d'emails (pour clients avec email)
    """
    
    @staticmethod
    def send_template_email(to_email, template_name, context, subject=None):
        """
        Envoyer un email avec template
        """
        try:
            if not (getattr(settings, 'BREVO_API_KEY', '') or settings.EMAIL_HOST_USER):
                logger.warning("E-mail non configuré : envoi réel impossible")
                return False
            
            # Rendre le template HTML
            html_content = render_to_string(f"emails/{template_name}", context)
            text_content = strip_tags(html_content)
            
            # Sujet par défaut
            if not subject:
                subject = "GABOSHOP - Notification"
            
            email = EmailMultiAlternatives(
                subject,
                text_content,
                settings.DEFAULT_FROM_EMAIL,
                [to_email]
            )
            email.attach_alternative(html_content, "text/html")
            count = email.send(fail_silently=False)
            if count != 1:
                return False

            logger.info(f"? Email envoyé à {to_email}: {template_name}")
            return True
            
        except Exception as e:
            logger.error(f"? Erreur envoi email: {e}")
            return False
    
    @staticmethod
    def send_text_email(to_email, subject, message):
        """
        Envoyer un email texte simple
        """
        try:
            if not (getattr(settings, 'BREVO_API_KEY', '') or settings.EMAIL_HOST_USER):
                logger.warning("E-mail non configuré : envoi réel impossible")
                return False
            count = send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [to_email],
                fail_silently=False,
            )
            return count == 1
        except Exception as e:
            logger.error(f"? Erreur envoi email texte: {e}")
            return False
    
 