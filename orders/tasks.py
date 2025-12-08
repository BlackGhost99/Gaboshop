from celery import shared_task
from django.utils import timezone
from django.db import transaction
import logging
from datetime import timedelta

from orders.models import Order
from delivery.services import DeliveryService
from notifications.service import NotificationService

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def assigner_livreurs_automatique(self):
    """
    Tâche automatique pour assigner des livreurs aux commandes prêtes
    Exécutée toutes les 5 minutes
    """
    try:
        with transaction.atomic():
            # Récupérer les commandes prêtes sans livreur assigné
            commandes_pretes = Order.objects.filter(
                status='ready',
                delivery__isnull=True
            ).select_related('store', 'delivery')
            
            if not commandes_pretes:
                logger.info("🤖 Aucune commande prête pour assignation automatique")
                return {"assignées": 0, "total": 0}
            
            commandes_assignees = 0
            
            for commande in commandes_pretes:
                try:
                    # Trouver les livreurs disponibles proches
                    livreurs_disponibles = DeliveryService.find_available_delivery_agents(
                        commande.store,
                        max_distance_km=15  # 15km max autour du magasin
                    )
                    
                    if not livreurs_disponibles:
                        logger.warning(f"🚫 Aucun livreur disponible pour {commande.store.name}")
                        continue
                    
                    # Prendre le livreur le plus proche
                    meilleur_livreur = livreurs_disponibles[0]['agent']
                    
                    # Assigner le livreur
                    livraison = DeliveryService.assign_delivery_agent(
                        commande, 
                        meilleur_livreur
                    )
                    
                    if livraison:
                        commandes_assignees += 1
                        logger.info(
                            f"✅ Livreur auto-assigné: {meilleur_livreur.phone} "
                            f"à la commande #{commande.order_number}"
                        )
                        
                except Exception as e:
                    logger.error(
                        f"❌ Erreur assignation commande #{commande.order_number}: {e}"
                    )
                    continue
            
            resultat = {
                "assignées": commandes_assignees,
                "total": len(commandes_pretes),
                "timestamp": timezone.now().isoformat()
            }
            
            logger.info(f"🤖 Assignation auto terminée: {resultat}")
            return resultat
            
    except Exception as e:
        logger.error(f"❌ Erreur tâche assignation auto: {e}")
        # Retry après 5 minutes
        self.retry(countdown=300, exc=e)

@shared_task
def nettoyer_paniers_abandonnes():
    """
    Nettoyer les paniers abandonnés (créés il y a plus de 24h)
    Exécutée toutes les heures
    """
    try:
        from orders.models import Order
        from datetime import timedelta
        
        delai_abandon = timezone.now() - timedelta(hours=24)
        
        # Commandes en attente de paiement depuis plus de 24h
        paniers_abandonnes = Order.objects.filter(
            status='pending',
            created_at__lt=delai_abandon
        )
        
        count = paniers_abandonnes.count()
        
        if count > 0:
            # Annuler les commandes abandonnées
            for commande in paniers_abandonnes:
                try:
                    commande.status = 'cancelled'
                    commande.save()
                    
                    logger.info(
                        f"🗑️ Commande abandonnée annulée: #{commande.order_number} "
                        f"(crée le {commande.created_at})"
                    )
                    
                except Exception as e:
                    logger.error(f"❌ Erreur annulation commande #{commande.order_number}: {e}")
                    continue
            
            logger.info(f"🧹 Nettoyage terminé: {count} paniers abandonnés supprimés")
        else:
            logger.info("🧹 Aucun panier abandonné à nettoyer")
        
        return {"supprimés": count}
        
    except Exception as e:
        logger.error(f"❌ Erreur nettoyage paniers: {e}")
        return {"erreur": str(e)}

@shared_task
def notifier_retard_livraison():
    """
    Notifier les retards de livraison
    Commandes 'in_transit' depuis plus de 2 heures
    """
    try:
        delai_retard = timezone.now() - timedelta(hours=2)
        
        commandes_en_retard = Order.objects.filter(
            status='in_transit',
            delivery__assigned_at__lt=delai_retard,
            delivery__delivered_at__isnull=True
        ).select_related('delivery', 'client', 'store')
        
        notifications_envoyees = 0
        
        for commande in commandes_en_retard:
            try:
                # Notifier le client du retard
                message_retard = (
                    f"⚠️ Votre commande #{commande.order_number} prend plus de temps que prévu.\n"
                    f"Notre livreur est en route. Désolé pour ce retard !\n"
                    f"Livreur: {commande.delivery.delivery_agent.phone if commande.delivery.delivery_agent else 'En attente'}"
                )
                
                # Utiliser le service de notification
                from notifications.service import NotificationService
                NotificationService.notify_order_status_update(
                    commande, 
                    'in_transit', 
                    'delayed'
                )
                
                notifications_envoyees += 1
                logger.info(f"⚠️ Notification retard envoyée pour #{commande.order_number}")
                
            except Exception as e:
                logger.error(f"❌ Erreur notification retard #{commande.order_number}: {e}")
                continue
        
        return {"notifications_retard": notifications_envoyees}
        
    except Exception as e:
        logger.error(f"❌ Erreur tâche retards: {e}")
        return {"erreur": str(e)}
