import logging
from django.conf import settings
from .whatsapp import WhatsAppService
from .sms import SMSService
from .email import EmailService
from .templates import NotificationTemplates
from .models import Notification
from . import messages

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service unifié de notifications GABOSHOP
    Gère l'envoi multi-canaux avec fallback intelligent
    """
    
    # Priorité des canaux de notification
    CHANNEL_PRIORITY = ['whatsapp', 'sms', 'email']
    
    # ===== Notifications métier (textes dans notifications/messages.py) =====

    @staticmethod
    def notify_user(user, message, notif_type='info', order=None, delivery=None, metadata=None):
        """Enregistre une notification détaillée : niveau, cause et étape suivante vont dans les métadonnées."""
        if not user or not message:
            return None
        meta = {
            'level': message.get('level', 'info'),
            'reason': message.get('reason', ''),
            'next_step': message.get('next_step', ''),
            **(metadata or {}),
        }
        return NotificationService._save_notification(
            user=user, title=message['title'][:200], body=message['body'],
            notif_type=notif_type, order=order, delivery=delivery, metadata=meta,
        )

    @staticmethod
    def notify_new_order(order):
        """
        Notifier le magasin d'une nouvelle commande
        """
        try:
            store = getattr(order, 'store', None)
            if store is None:
                return False
            closed = hasattr(store, 'is_open') and not store.is_open()
            message = messages.new_order_for_store(order, store_closed=closed)
            NotificationService.notify_user(
                store.manager, message, notif_type='warning' if closed else 'order', order=order,
                metadata={'reason_code': 'store_closed'} if closed else None,
            )
            if closed:
                logger.warning("Commerce fermé : SMS de nouvelle commande non envoyé (%s)", order.order_number)
                return False

            template = NotificationTemplates.new_order_store(order)
            template['sms'] = message['sms']
            success = NotificationService._send_to_store(store.phone, template, message['title'])
            if not success:
                logger.error("Échec de l'envoi de la nouvelle commande à %s", store.name)
            return success

        except Exception as e:
            logger.error(f"Erreur notification nouvelle commande: {e}")
            return False

    @staticmethod
    def notify_order_status_update(order, old_status, new_status):
        """
        Notifier le client (et le commerce quand ça le concerne) du changement de statut
        """
        try:
            message = messages.order_update_for_client(order, old_status, new_status)
            NotificationService.notify_user(
                order.client, message, notif_type='order', order=order,
                metadata={'from': old_status, 'to': new_status},
            )
            store_message = messages.order_update_for_store(order, new_status)
            if store_message and getattr(order, 'store', None):
                NotificationService.notify_user(
                    order.store.manager, store_message, notif_type='order', order=order,
                    metadata={'from': old_status, 'to': new_status},
                )
            template = NotificationTemplates.order_status_client(order, old_status, new_status)
            template['sms'] = message['sms']
            return NotificationService._send_to_client(
                order.client.phone, order.client.email, template, message['title'],
            )

        except Exception as e:
            logger.error(f"Erreur notification statut: {e}")
            return False

    @staticmethod
    def notify_delivery_assigned(delivery):
        """
        Notifier le livreur d'une nouvelle mission
        """
        try:
            if not delivery.delivery_agent:
                logger.warning("Aucun livreur assigné pour notification")
                return False

            order = delivery.order
            template = NotificationTemplates.delivery_assigned_agent(delivery)
            NotificationService.notify_user(
                delivery.delivery_agent,
                {
                    'title': f"Nouvelle livraison #{delivery.tracking_number}",
                    'body': (
                        f"Récupérez la commande #{order.order_number} chez {order.store.name} "
                        f"({delivery.pickup_address}) et livrez-la à : {delivery.delivery_address}. "
                        f"Votre gain : {messages.money(delivery.agent_commission)}."
                    ),
                    'level': 'info',
                    'next_step': "Ouvrez « Mes livraisons » pour accepter la course et voir le contact du client.",
                },
                notif_type='delivery', delivery=delivery, order=order,
            )
            success = NotificationService._send_to_agent(
                delivery.delivery_agent.phone,
                template,
                f"Nouvelle livraison #{delivery.tracking_number}"
            )
            if not success:
                logger.error("Échec de l'envoi de la livraison au livreur %s", delivery.delivery_agent.phone)
            return success

        except Exception as e:
            logger.error(f"Erreur notification livraison: {e}")
            return False

    @staticmethod
    def notify_payment_success(order, payment):
        """
        Paiement en ligne confirmé : le client et le commerce reçoivent le détail.
        """
        try:
            message = messages.payment_success_for_client(order, payment)
            NotificationService.notify_user(
                order.client, message, notif_type='payment', order=order, metadata={'payment_id': payment.id},
            )
            if getattr(order, 'store', None):
                NotificationService.notify_user(
                    order.store.manager, messages.payment_success_for_store(order, payment),
                    notif_type='payment', order=order, metadata={'payment_id': payment.id},
                )
            template = NotificationTemplates.payment_success_client(order, payment)
            template['sms'] = message['sms']
            return NotificationService._send_to_client(
                order.client.phone, order.client.email, template, message['title'],
            )

        except Exception as e:
            logger.error(f"Erreur notification paiement réussi: {e}")
            return False

    @staticmethod
    def notify_payment_failed(order, payment=None, details=None):
        """
        Paiement non abouti : le client reçoit la cause (code erroné, solde, demande expirée...) et quoi faire.
        """
        try:
            if payment is None:
                payment = getattr(order, 'payment', None)
            if payment is None:
                return False
            message = messages.payment_failed_for_client(order, payment, details)
            NotificationService.notify_user(
                order.client, message, notif_type='payment', order=order,
                metadata={'payment_id': payment.id, 'reason_code': message['failure_code']},
            )
            template = NotificationTemplates.payment_failed_client(order)
            template['sms'] = message['sms']
            return NotificationService._send_to_client(
                order.client.phone, order.client.email, template, message['title'],
            )

        except Exception as e:
            logger.error(f"Erreur notification paiement échoué: {e}")
            return False

    @staticmethod
    def notify_store_payout(payout):
        """Versement au commerce : envoyé, en attente (et pourquoi) ou échoué."""
        try:
            message = messages.store_payout_message(payout)
            if not message:
                return None
            return NotificationService.notify_user(
                payout.store.manager, message, notif_type='payment', order=payout.order,
                metadata={'payout_id': payout.id, 'payout_status': payout.status},
            )
        except Exception as e:
            logger.error(f"Erreur notification versement commerce: {e}")
            return None

    @staticmethod
    def notify_delivery_in_transit(delivery):
        """
        Notifier le client que sa livraison est en route
        """
        try:
            order = delivery.order
            message = messages.order_update_for_client(order, order.status, 'in_transit')
            NotificationService.notify_user(
                order.client, message, notif_type='delivery', delivery=delivery, order=order,
            )
            template = NotificationTemplates.delivery_in_transit_client(delivery)
            template['sms'] = message['sms']
            return NotificationService._send_to_client(
                order.client.phone, order.client.email, template, message['title'],
            )

        except Exception as e:
            logger.error(f"Erreur notification livraison en route: {e}")
            return False

    # ===== MÉTHODES D'ENVOI SPÉCIALISÉES =====
    
    @staticmethod
    def _send_to_store(store_phone, template, fallback_message):
        """Envoyer une notification à un magasin"""
        # Magasins préfèrent WhatsApp pour les commandes
        if not store_phone:
            logger.warning("?? Téléphone magasin manquant, notification non envoyée")
            return False
        channels = ['whatsapp', 'sms']
        return NotificationService._send_notification(store_phone, None, template, channels)
    
    @staticmethod
    def _send_to_client(client_phone, client_email, template, fallback_message):
        """Envoyer une notification à un client"""
        channels = ['whatsapp', 'sms']
        if client_email:
            channels.append('email')
        return NotificationService._send_notification(client_phone, client_email, template, channels)
    
    @staticmethod
    def _send_to_agent(agent_phone, template, fallback_message):
        """Envoyer une notification à un livreur"""
        # Livreurs préfèrent SMS pour rapidité
        channels = ['sms', 'whatsapp']
        return NotificationService._send_notification(agent_phone, None, template, channels)
    
    @staticmethod
    def _send_notification(phone, email, template, channels):
        """
        Envoyer une notification via multiple canaux avec fallback
        """
        success = False
        
        for channel in channels:
            try:
                if channel == 'whatsapp' and 'whatsapp' in template:
                    success = WhatsAppService.send_template_message(
                        phone,
                        template['whatsapp']['template_name'],
                        template['whatsapp']['parameters']
                    )
                
                elif channel == 'sms' and 'sms' in template:
                    success = SMSService.send_sms(phone, template['sms'])
                
                elif channel == 'email' and email and 'email' in template:
                    success = EmailService.send_template_email(
                        email,
                        template['email'],
                        template.get('email_context', {})
                    )
                
                if success:
                    break
                    
            except Exception as e:
                logger.error(f"? Erreur canal {channel}: {e}")
                continue
        
        return success

    # ===== Enregistrement base =====
    @staticmethod
    def _save_notification(user, title, body, notif_type='info', order=None, delivery=None, metadata=None):
        try:
            if not user:
                return None
            return Notification.objects.create(
                user=user,
                title=title,
                body=body,
                notif_type=notif_type,
                order=order,
                delivery=delivery,
                metadata=metadata or {},
            )
        except Exception as e:
            logger.error(f"? Erreur enregistrement notification DB: {e}")
            return None

    @staticmethod
    def notify_delivery_agent_payment(agent, delivery, payment, message=''):
        """
        Notifier le livreur qu'il a reçu son paiement Airtel Money
        """
        try:
            title = f"Gain reçu : {messages.money(delivery.agent_commission)}"
            body = (
                f"Vous avez reçu {messages.money(delivery.agent_commission)} pour la livraison de la commande "
                f"#{delivery.order.order_number}. Vérifiez le SMS de votre opérateur Mobile Money."
                + (f"\n{message}" if message else '')
            )

            transaction_id = getattr(payment, 'transaction_id', None)
            if not transaction_id:
                transaction_id = getattr(payment, 'transaction_reference', None)

            NotificationService._save_notification(
                user=agent,
                title=title,
                body=body,
                notif_type='payment',
                delivery=delivery,
                metadata={
                    'level': 'success',
                    'amount': float(delivery.agent_commission),
                    'payment_id': payment.id,
                    'transaction_id': transaction_id,
                    'delivery_id': delivery.id,
                    'order_number': delivery.order.order_number
                },
            )
            
            # Envoyer via SMS/WhatsApp
            success = NotificationService._send_to_agent(agent.phone, {'sms': f"GABOSHOP - {body}"}, title)
            
            if success:
                logger.info(f"?? Notification paiement livreur envoyée à {agent.username}: {delivery.agent_commission}F")
            else:
                logger.warning(f"?? Échec notification paiement livreur à {agent.username}")
            
            return success
            
        except Exception as e:
            logger.error(f"? Erreur notification paiement livreur: {e}")
            return False

    @staticmethod
    def _body_from_template(template, default_text):
        if not template:
            return default_text
        for key in ['sms', 'whatsapp', 'email']:
            if key not in template:
                continue
            val = template.get(key)
            # Si déjà une chaîne lisible, on la renvoie
            if isinstance(val, str):
                return val
            # Si dict de template, on renvoie un libellé humain
            if isinstance(val, dict):
                name = val.get('template_name') or key
                return f"Notification {name} prête à envoyer"
        return default_text
