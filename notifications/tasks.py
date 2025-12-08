from celery import shared_task
from django.utils import timezone
import logging
from datetime import timedelta

from notifications.service import NotificationService
from orders.models import Order
from delivery.models import Delivery
from django.db import models

logger = logging.getLogger(__name__)

@shared_task
def envoyer_rapports_quotidiens():
    """
    Envoyer les rapports quotidiens aux gérants de magasin
    Exécutée quotidiennement à 8h00
    """
    try:
        from stores.models import Store
        from django.db.models import Count, Sum
        from datetime import datetime
        
        hier = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=1)
        
        magasins_actifs = Store.objects.filter(is_active=True)
        
        rapports_envoyes = 0
        
        for magasin in magasins_actifs:
            try:
                # Statistiques du magasin pour hier
                stats = Order.objects.filter(
                    store=magasin,
                    created_at__range=[hier, hier + timedelta(days=1)]
                ).aggregate(
                    total_commandes=Count('id'),
                    commandes_livrees=Count('id', filter=models.Q(status='delivered')),
                    chiffre_affaires=Sum('total_amount', filter=models.Q(status='delivered'))
                )
                
                # Préparer le message
                message_rapport = (
                    f"📊 RAPPORT QUOTIDIEN - {magasin.name}\n"
                    f"📅 Date: {hier.date()}\n"
                    f"🛍️ Commandes: {stats['total_commandes'] or 0}\n"
                    f"✅ Livrées: {stats['commandes_livrees'] or 0}\n"
                    f"💰 Chiffre d'affaires: {stats['chiffre_affaires'] or 0} FCFA\n"
                    f"🏪 Taux de livraison: {round((stats['commandes_livrees'] or 0) / (stats['total_commandes'] or 1) * 100, 1)}%\n"
                    f"\nBonne journée ! 🚀"
                )
                
                # Envoyer via WhatsApp
                from notifications.whatsapp import WhatsAppService
                WhatsAppService.send_text_message(magasin.phone, message_rapport)
                
                rapports_envoyes += 1
                logger.info(f"📤 Rapport envoyé à {magasin.name}")
                
            except Exception as e:
                logger.error(f"❌ Erreur rapport {magasin.name}: {e}")
                continue
        
        return {"rapports_envoyes": rapports_envoyes}
        
    except Exception as e:
        logger.error(f"❌ Erreur tâche rapports: {e}")
        return {"erreur": str(e)}

@shared_task
def envoyer_rappel_commandes_en_attente():
    """
    Envoyer des rappels pour les commandes en attente de paiement
    Commandes en 'pending' depuis plus de 1 heure
    """
    try:
        delai_rappel = timezone.now() - timedelta(hours=1)
        
        commandes_en_attente = Order.objects.filter(
            status='pending',
            created_at__lt=delai_rappel
        ).select_related('client')
        
        rappels_envoyes = 0
        
        for commande in commandes_en_attente:
            try:
                message_rappel = (
                    f"⏰ RAPPEL - Commande #{commande.order_number}\n"
                    f"Votre commande de {commande.total_amount} FCFA est en attente de paiement.\n"
                    f"Pour finaliser, rendez-vous dans vos commandes.\n"
                    f"Après 24h, la commande sera automatiquement annulée."
                )
                
                from notifications.whatsapp import WhatsAppService
                WhatsAppService.send_text_message(commande.client.phone, message_rappel)
                
                rappels_envoyes += 1
                logger.info(f"⏰ Rappel envoyé pour #{commande.order_number}")
                
            except Exception as e:
                logger.error(f"❌ Erreur rappel #{commande.order_number}: {e}")
                continue
        
        return {"rappels_envoyes": rappels_envoyes}
        
    except Exception as e:
        logger.error(f"❌ Erreur tâche rappels: {e}")
        return {"erreur": str(e)}
