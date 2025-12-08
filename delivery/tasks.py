from celery import shared_task
from django.utils import timezone
from .models import Delivery
from users.models import LivreurProfile
from orders.models import Order
from .utils import haversine_distance
from notifications.service import NotificationService

@shared_task
def assign_nearest_delivery_agent(order_id):
    """
    Tâche Celery pour assigner automatiquement le livreur le plus proche
    """
    try:
        order = Order.objects.get(id=order_id)
        store = order.store
        
        # 1. Trouver les livreurs disponibles dans la même ville
        available_agents = LivreurProfile.objects.filter(
            user__city=order.city,  # Filtrer par la ville de la commande
            disponible=True,
            documents_verifies=True
        )
        
        if not available_agents.exists():
            print(f"⚠️ Aucun livreur disponible pour la commande #{order.order_number}")
            return "No agents available"
            
        # 2. Calculer les distances
        agents_with_distance = []
        for agent in available_agents:
            dist = haversine_distance(
                store.latitude, store.longitude,
                agent.position_lat, agent.position_lng
            )
            if dist is not None:
                agents_with_distance.append((agent, dist))
        
        # 3. Trier par distance (le plus proche d'abord)
        agents_with_distance.sort(key=lambda x: x[1])
        
        # 4. Assigner le premier (algorithme simple pour MVP)
        # Dans une version avancée, on enverrait une notif "First to accept"
        if agents_with_distance:
            best_agent, distance = agents_with_distance[0]
            
            # Créer ou mettre à jour la livraison
            delivery, created = Delivery.objects.get_or_create(order=order)
            
            delivery.delivery_agent = best_agent.user
            delivery.status = 'assigned'
            delivery.assigned_at = timezone.now()
            delivery.distance_to_store = distance
            delivery.is_auto_assigned = True
            delivery.save()
            
            # Mettre à jour le statut de la commande
            order.status = 'assigned'
            order.save(update_fields=['status'])
            
            # Notifier le livreur
            NotificationService.notify_delivery_assigned(delivery)
            
            print(f"✅ Livreur {best_agent.user.phone} assigné à {distance:.2f}km")
            return f"Assigned to {best_agent.user.phone}"
            
        return "No agents in range"
        
    except Order.DoesNotExist:
        return "Order not found"
    except Exception as e:
        print(f"❌ Erreur assignation: {e}")
        return f"Error: {e}"
