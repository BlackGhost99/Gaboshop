"""Services métier pour la gestion des livraisons"""
import logging
from decimal import Decimal
from django.db import transaction, models
from django.utils import timezone
from datetime import timedelta
from delivery.models import Delivery, DeliveryTracking
from orders.models import Order
# Try to import LocationService if available
try:
    from services.location_service import LocationService
except ImportError:
    LocationService = None
# Persisted notifications (DB + multi-channel)
from notifications.service import NotificationService

logger = logging.getLogger(__name__)


class DeliveryService:
    """Services métier pour la gestion des livraisons"""
    
    @staticmethod
    def assign_delivery_agent(order, delivery_agent):
        """
        Assigner un livreur à une commande
        """
        try:
            with transaction.atomic():
                # Vérifications
                if order.status != 'ready':
                    raise ValueError("La commande doit être prête pour livraison.")
                
                if not delivery_agent.is_available:
                    raise ValueError("Le livreur n'est pas disponible.")
                
                # Créer ou récupérer la livraison
                delivery, created = Delivery.objects.get_or_create(order=order)
                
                # Assigner le livreur
                delivery.delivery_agent = delivery_agent
                delivery.status = 'assigned'
                delivery.assigned_at = timezone.now()
                
                # Calculer la commission du livreur (80% des frais de livraison)
                delivery.agent_commission = order.delivery_fee * Decimal('0.8')
                delivery.save()
                
                # Mettre à jour le statut de la commande
                order.status = 'assigned'
                order.save()
                
                # Notifier le livreur
                NotificationService.notify_delivery_assigned(delivery)
                
                logger.info(
                    f"🚗 Livraison assignée: #{delivery.tracking_number} "
                    f"à {delivery_agent.phone}"
                )
                
                return delivery
                
        except Exception as e:
            logger.error(f"❌ Erreur assignation livraison: {e}")
            raise

    @staticmethod
    def find_available_delivery_agents(store, max_distance_km=10):
        """
        Trouver les livreurs disponibles les plus proches
        """
        try:
            if not store.latitude or not store.longitude:
                logger.warning(f"📍 Coordonnées manquantes pour {store.name}")
                return []
            
            # Trouver les livreurs les plus proches
            nearest_agents = LocationService.find_nearest_delivery_agents(
                store.latitude, store.longitude
            )
            
            # Filtrer par distance maximale
            available_agents = []
            
            for agent in nearest_agents:
                if ',' in agent.current_location:
                    try:
                        agent_lat, agent_lon = map(float, agent.current_location.split(','))
                        distance = LocationService.calculate_distance(
                            store.latitude, store.longitude, agent_lat, agent_lon
                        )
                        
                        if distance <= max_distance_km:
                            available_agents.append({
                                'agent': agent,
                                'distance_km': round(distance, 2),
                                'estimated_time': LocationService.estimate_delivery_time(distance)
                            })
                    except (ValueError, TypeError):
                        continue
            
            return sorted(available_agents, key=lambda x: x['distance_km'])
            
        except Exception as e:
            logger.error(f"❌ Erreur recherche livreurs: {e}")
            return []

    @staticmethod
    def update_delivery_status(delivery, new_status, tracking_data=None):
        """
        Mettre à jour le statut d'une livraison avec tracking
        """
        try:
            old_status = delivery.status
            delivery.status = new_status
            
            # Mettre à jour les timestamps
            if new_status == 'picked_up' and not delivery.picked_up_at:
                delivery.picked_up_at = timezone.now()
            elif new_status == 'delivered' and not delivery.delivered_at:
                delivery.delivered_at = timezone.now()
            
            delivery.save()
            
            # Créer un enregistrement de tracking
            if tracking_data:
                DeliveryTracking.objects.create(
                    delivery=delivery,
                    status=new_status,
                    **tracking_data
                )
            
            # Mettre à jour le statut de la commande si livrée
            if new_status == 'delivered':
                delivery.order.status = 'delivered'
                delivery.order.save()
            
            logger.info(
                f"📦 Statut livraison #{delivery.tracking_number} mis à jour: "
                f"{old_status} → {new_status}"
            )
            
            return delivery
            
        except Exception as e:
            logger.error(f"❌ Erreur mise à jour livraison: {e}")
            raise

    @staticmethod
    def confirm_delivery(delivery, confirmation_data):
        """
        Confirmer la livraison avec feedback
        """
        try:
            with transaction.atomic():
                delivery.delivery_notes = confirmation_data.get('delivery_notes', '')
                delivery.customer_feedback = confirmation_data.get('customer_feedback', '')
                delivery.rating = confirmation_data.get('rating')
                
                # Marquer comme livrée
                delivery = DeliveryService.update_delivery_status(
                    delivery, 
                    'delivered'
                )
                
                # Libérer le livreur
                delivery.delivery_agent.is_available = True
                delivery.delivery_agent.save()
                
                logger.info(
                    f"✅ Livraison confirmée: #{delivery.tracking_number} "
                    f"Note: {delivery.rating}/5"
                )
                
                return delivery
                
        except Exception as e:
            logger.error(f"❌ Erreur confirmation livraison: {e}")
            raise

    @staticmethod
    def calculate_delivery_metrics(agent_id, period_days=30):
        """
        Calculer les métriques de performance d'un livreur
        """
        try:
            from django.db.models import Count, Avg, Sum
            from django.utils import timezone
            
            start_date = timezone.now() - timedelta(days=period_days)
            
            deliveries = Delivery.objects.filter(
                delivery_agent_id=agent_id,
                assigned_at__gte=start_date
            )
            
            stats = deliveries.aggregate(
                total_deliveries=Count('id'),
                completed_deliveries=Count('id', filter=models.Q(status='delivered')),
                avg_rating=Avg('rating', filter=models.Q(rating__isnull=False)),
                total_earnings=Sum('agent_commission', filter=models.Q(status='delivered')),
                avg_delivery_time=Avg(
                    models.F('delivered_at') - models.F('assigned_at'),
                    filter=models.Q(status='delivered')
                )
            )
            
            return {
                'period': f"{period_days} jours",
                'stats': stats,
                'completion_rate': (
                    (stats['completed_deliveries'] / stats['total_deliveries'] * 100)
                    if stats['total_deliveries'] > 0 else 0
                )
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur calcul métriques: {e}")
            return None


def auto_assign_delivery(order):
    """Assigner automatiquement un livreur disponible à la commande prête.

    Cette fonction est compatible avec l'usage direct depuis les vues/admins.
    """
    try:
        with transaction.atomic():
            # Verrouiller la livraison si existante
            try:
                delivery = Delivery.objects.select_for_update().get(order=order)
            except Delivery.DoesNotExist:
                delivery, _ = Delivery.objects.get_or_create(order=order)

            if delivery.delivery_agent is not None:
                return delivery

            # Chercher un profil de livreur disponible
            profile = (
                DeliveryProfile.objects
                .select_for_update()
                .filter(status='available')
                .select_related('user')
                .first()
            )

            if not profile:
                logger.info(f"auto_assign: pas de livreur disponible pour order {order.id}")
                return None

            # Assigner via le service existant
            delivery = DeliveryService.assign_delivery_agent(order, profile.user)

            # Marquer le profil occupé
            try:
                profile.status = 'busy'
                profile.save()
            except Exception:
                logger.exception('Impossible de mettre à jour le statut du profil livreur')

            delivery.is_auto_assigned = True
            delivery.assigned_at = delivery.assigned_at or timezone.now()
            delivery.save()

            logger.info(f"Auto-assign: livraison {delivery.id} → livreur {profile.user.id}")
            return delivery

    except Exception:
        logger.exception('Erreur auto_assign_delivery')
        return None
