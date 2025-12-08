import logging
from django.conf import settings
from .whatsapp import WhatsAppService
from .sms import SMSService
from .email import EmailService
from .templates import NotificationTemplates
from .models import Notification

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Service unifié de notifications GABOSHOP
    Gère l'envoi multi-canaux avec fallback intelligent
    """
    
    # Priorité des canaux de notification
    CHANNEL_PRIORITY = ['whatsapp', 'sms', 'email']
    
    @staticmethod
    def notify_new_order(order):
        """
        Notifier le magasin d'une nouvelle commande
        """
        try:
            store = getattr(order, 'store', None)
            if store and hasattr(store, 'is_open') and not store.is_open():
                # Magasin fermé : on enregistre quand même la notification pour historique
                NotificationService._save_notification(
                    user=store.manager,
                    title=f"Nouvelle commande #{order.order_number}",
                    body="Magasin fermé : notification non envoyée",
                    notif_type='warning',
                    order=order,
                    metadata={'reason': 'store_closed'},
                )
                logger.warning("⚠️ Magasin fermé, notification non envoyée")
                return False

            template = NotificationTemplates.new_order_store(order)
            NotificationService._save_notification(
                user=order.store.manager,
                title=f"Nouvelle commande #{order.order_number}",
                body=NotificationService._body_from_template(template, 'Nouvelle commande'),
                notif_type='order',
                order=order,
            )
            success = NotificationService._send_to_store(
                order.store.phone,
                template,
                f"Nouvelle commande #{order.order_number}"
            )
            
            if success:
                logger.info(f"📢 Notification nouvelle commande envoyée à {order.store.name}")
            else:
                logger.error(f"❌ Échec notification nouvelle commande à {order.store.name}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Erreur notification nouvelle commande: {e}")
            return False
    
    @staticmethod
    def notify_order_status_update(order, old_status, new_status):
        """
        Notifier le client du changement de statut
        """
        try:
            template = NotificationTemplates.order_status_client(order, old_status, new_status)
            NotificationService._save_notification(
                user=order.client,
                title=f"Commande #{order.order_number}",
                body=NotificationService._body_from_template(template, f"Statut mis à jour: {old_status} → {new_status}"),
                notif_type='order',
                order=order,
                metadata={'from': old_status, 'to': new_status},
            )
            success = NotificationService._send_to_client(
                order.client.phone,
                order.client.email,
                template,
                f"Statut commande #{order.order_number}"
            )
            
            if success:
                logger.info(f"📢 Notification statut envoyée à {order.client.phone}")
            else:
                logger.warning(f"⚠️ Échec notification statut à {order.client.phone}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Erreur notification statut: {e}")
            return False
    
    @staticmethod
    def notify_delivery_assigned(delivery):
        """
        Notifier le livreur d'une nouvelle mission
        """
        try:
            if not delivery.delivery_agent:
                logger.warning("⚠️ Aucun livreur assigné pour notification")
                return False
            
            template = NotificationTemplates.delivery_assigned_agent(delivery)
            NotificationService._save_notification(
                user=delivery.delivery_agent,
                title=f"Livraison #{delivery.tracking_number}",
                body=NotificationService._body_from_template(template, 'Livraison assignée'),
                notif_type='delivery',
                delivery=delivery,
            )
            success = NotificationService._send_to_agent(
                delivery.delivery_agent.phone,
                template,
                f"Nouvelle livraison #{delivery.tracking_number}"
            )
            
            if success:
                logger.info(f"📢 Notification livraison envoyée à {delivery.delivery_agent.phone}")
            else:
                logger.error(f"❌ Échec notification livraison à {delivery.delivery_agent.phone}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Erreur notification livraison: {e}")
            return False
    
    @staticmethod
    def notify_payment_success(order, payment):
        """
        Notifier le client d'un paiement réussi
        """
        try:
            template = NotificationTemplates.payment_success_client(order, payment)
            NotificationService._save_notification(
                user=order.client,
                title=f"Paiement confirmé #{order.order_number}",
                body=NotificationService._body_from_template(template, 'Paiement confirmé'),
                notif_type='payment',
                order=order,
                metadata={'payment_id': payment.id},
            )
            success = NotificationService._send_to_client(
                order.client.phone,
                order.client.email,
                template,
                f"Paiement confirmé #{order.order_number}"
            )
            
            if success:
                logger.info(f"📢 Notification paiement réussi à {order.client.phone}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Erreur notification paiement réussi: {e}")
            return False
    
    @staticmethod
    def notify_payment_failed(order):
        """
        Notifier le client d'un paiement échoué
        """
        try:
            template = NotificationTemplates.payment_failed_client(order)
            NotificationService._save_notification(
                user=order.client,
                title=f"Paiement échoué #{order.order_number}",
                body=NotificationService._body_from_template(template, 'Paiement échoué'),
                notif_type='payment',
                order=order,
            )
            success = NotificationService._send_to_client(
                order.client.phone,
                order.client.email,
                template,
                f"Paiement échoué #{order.order_number}"
            )
            
            if success:
                logger.info(f"📢 Notification paiement échoué à {order.client.phone}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Erreur notification paiement échoué: {e}")
            return False
    
    @staticmethod
    def notify_delivery_in_transit(delivery):
        """
        Notifier le client que sa livraison est en route
        """
        try:
            template = NotificationTemplates.delivery_in_transit_client(delivery)
            NotificationService._save_notification(
                user=delivery.order.client,
                title=f"Livraison en route #{delivery.tracking_number}",
                body=NotificationService._body_from_template(template, 'Livraison en route'),
                notif_type='delivery',
                delivery=delivery,
                order=delivery.order,
            )
            success = NotificationService._send_to_client(
                delivery.order.client.phone,
                delivery.order.client.email,
                template,
                f"Livraison en route #{delivery.tracking_number}"
            )
            
            if success:
                logger.info(f"📢 Notification livraison en route à {delivery.order.client.phone}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Erreur notification livraison en route: {e}")
            return False
    
    # ===== MÉTHODES D'ENVOI SPÉCIALISÉES =====
    
    @staticmethod
    def _send_to_store(store_phone, template, fallback_message):
        """Envoyer une notification à un magasin"""
        # Magasins préfèrent WhatsApp pour les commandes
        if not store_phone:
            logger.warning("⚠️ Téléphone magasin manquant, notification non envoyée")
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
                logger.error(f"❌ Erreur canal {channel}: {e}")
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
            logger.error(f"❌ Erreur enregistrement notification DB: {e}")
            return None

    @staticmethod
    def notify_delivery_agent_payment(agent, delivery, payment, message=''):
        """
        Notifier le livreur qu'il a reçu son paiement Airtel Money
        """
        try:
            title = f"💰 Paiement reçu - Livraison #{delivery.id}"
            body = (
                f"✅ Vous avez reçu {delivery.agent_commission} FCFA "
                f"pour la livraison #{delivery.id} (Commande {delivery.order.order_number})\n"
                f"{message}"
            )
            
            NotificationService._save_notification(
                user=agent,
                title=title,
                body=body,
                notif_type='payment',
                delivery=delivery,
                metadata={
                    'amount': float(delivery.agent_commission),
                    'payment_id': payment.id,
                    'transaction_id': payment.transaction_id,
                    'delivery_id': delivery.id,
                    'order_number': delivery.order.order_number
                },
            )
            
            # Envoyer via SMS/WhatsApp
            success = NotificationService._send_to_agent(
                agent.phone_number,
                body,
                title
            )
            
            if success:
                logger.info(f"💳 Notification paiement livreur envoyée à {agent.username}: {delivery.agent_commission}F")
            else:
                logger.warning(f"⚠️ Échec notification paiement livreur à {agent.username}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Erreur notification paiement livreur: {e}")
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
