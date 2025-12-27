from celery import shared_task
from django.utils import timezone
from .models import Delivery
from users.models import LivreurProfile
from orders.models import Order
from .utils import haversine_distance
from notifications.service import NotificationService
from decimal import Decimal

@shared_task
def assign_nearest_delivery_agent(order_id):
    """
    Tâche Celery pour assigner automatiquement le livreur le plus proche
    """
    try:
        order = Order.objects.get(id=order_id)
        store = order.store
        
        # 1. Récupérer les livreurs disponibles dans la même ville
        all_available_agents = LivreurProfile.objects.filter(
            user__city=order.city,
            disponible=True,
        )

        # Priorité aux livreurs vérifiés (documents) et avec position
        verified_agents = all_available_agents.filter(documents_verifies=True)

        agents_with_distance = []
        # Calculer distances pour les livreurs vérifiés (si positions disponibles)
        for agent in verified_agents:
            dist = haversine_distance(
                store.latitude, store.longitude,
                agent.position_lat, agent.position_lng
            )
            if dist is not None:
                agents_with_distance.append((agent, dist))

        # Si on a des agents vérifiés avec distance, on choisit le plus proche
        if agents_with_distance:
            agents_with_distance.sort(key=lambda x: x[1])
            best_agent, distance = agents_with_distance[0]

        else:
            # Fallback: si aucun agent vérifié/coordonné, utiliser le premier agent disponible
            if all_available_agents.exists():
                best_agent = all_available_agents.first()
                distance = None
                print(f"⚠️ Fallback assignment: aucun agent vérifié/coordonné, assignation à {best_agent.user.phone}")
            else:
                print(f"⚠️ Aucun livreur disponible pour la commande #{order.order_number}")
                return "No agents available"

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
        try:
            NotificationService.notify_delivery_assigned(delivery)
        except Exception:
            pass

        if distance is not None:
            print(f"✅ Livreur {best_agent.user.phone} assigné à {distance:.2f}km")
        else:
            print(f"✅ Livreur {best_agent.user.phone} assigné (fallback, distance inconnue)")
        return f"Assigned to {best_agent.user.phone}"
        
    except Order.DoesNotExist:
        return "Order not found"
    except Exception as e:
        print(f"❌ Erreur assignation: {e}")
        return f"Error: {e}"
