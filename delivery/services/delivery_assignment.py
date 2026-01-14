"""Service pour l'assignation automatique des livreurs"""
import logging
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from django.db.models import Q
from delivery.models import Delivery, DeliveryProfile, VehicleType
from orders.models import Order
from users.models import User

logger = logging.getLogger(__name__)


class DeliveryAssignmentService:
	"""Service pour l'assignation automatique des livreurs"""
	
	@staticmethod
	def find_eligible_drivers(delivery, vehicle_type):
		"""
		Trouve les livreurs éligibles pour une livraison
		
		Critères:
		- Disponible (is_available=True, status='available')
		- VehicleType compatible
		- allow_intercity compatible si inter-ville
		- max_distance_km >= distance de livraison
		- Même ville priorisée
		
		Returns:
			Liste de DeliveryProfile triés par priorité
		"""
		try:
			if not vehicle_type:
				logger.warning("Aucun type de véhicule fourni")
				return []
			
			# Vérifier si inter-ville
			is_intercity = delivery.is_intra_city is False
			
			# Base query: livreurs disponibles avec le bon véhicule
			query = DeliveryProfile.objects.filter(
				status='available',
				user__is_available=True,
				user__user_type='delivery_agent',
				vehicle_type=vehicle_type
			).select_related('user', 'vehicle_type')
			
			# Filtrer par allow_intercity si nécessaire
			if is_intercity:
				query = query.filter(allow_intercity=True)
			
			# Filtrer par distance si disponible
			if delivery.distance_km:
				# Note: max_distance_km est sur VehicleType, pas DeliveryProfile
				# On vérifie que le véhicule peut faire la distance
				if vehicle_type.max_distance_km > 0:
					query = query.filter(
						vehicle_type__max_distance_km__gte=delivery.distance_km
					)
			
			# Récupérer les profils
			profiles = list(query)
			
			# Trier par priorité
			def sort_key(profile):
				# Priorité 1: même ville
				same_city = 1 if profile.user.city == delivery.city else 0
				
				# Priorité 2: distance (si disponible)
				# Note: on pourrait utiliser GPS ici si disponible
				distance_priority = 0
				
				# Priorité 3: ancienneté de disponibilité (plus ancien = mieux)
				# Utiliser updated_at comme proxy
				availability_age = (
					(timezone.now() - profile.updated_at).total_seconds()
					if profile.updated_at else 0
				)
				
				return (-same_city, -distance_priority, -availability_age)
			
			profiles.sort(key=sort_key)
			
			logger.info(
				f"Trouvé {len(profiles)} livreurs éligibles pour livraison "
				f"{delivery.tracking_number} (véhicule: {vehicle_type.get_name_display()})"
			)
			
			return profiles
			
		except Exception as e:
			logger.error(f"Erreur recherche livreurs éligibles: {e}")
			return []
	
	@staticmethod
	def auto_assign_delivery(order, timeout_minutes=2):
		"""
		Assignation automatique avec timeout
		
		Processus:
		1. Vérifie que commande est payée
		2. Vérifie que véhicule est validé
		3. Trouve livreurs éligibles
		4. Propose au premier (notification)
		5. Attend timeout
		6. Si refus/timeout : passe au suivant
		
		Returns:
			Delivery ou None
		"""
		try:
			with transaction.atomic():
				# Vérifications préalables
				if order.status != 'paid':
					logger.warning(
						f"Commande {order.order_number} non payée, "
						"assignation automatique impossible"
					)
					return None
				
				# Récupérer ou créer la livraison
				try:
					delivery = Delivery.objects.select_for_update().get(order=order)
				except Delivery.DoesNotExist:
					delivery = Delivery.objects.create(order=order)
				
				# Vérifier que véhicule est sélectionné
				if not delivery.selected_vehicle_type:
					logger.warning(
						f"Commande {order.order_number} sans véhicule sélectionné, "
						"assignation automatique impossible"
					)
					delivery.status = 'pending_vehicle_validation'
					delivery.save()
					return None
				
				vehicle_type = delivery.selected_vehicle_type
				
				# Trouver livreurs éligibles
				eligible_drivers = DeliveryAssignmentService.find_eligible_drivers(
					delivery,
					vehicle_type
				)
				
				if not eligible_drivers:
					logger.warning(
						f"Aucun livreur éligible pour livraison {delivery.tracking_number}"
					)
					delivery.status = 'ready_for_assignment'
					delivery.save()
					return None
				
				# Essayer d'assigner au premier livreur disponible
				# Note: Dans un vrai système, on enverrait une notification et on attendrait
				# Pour l'instant, on assigne directement
				first_driver = eligible_drivers[0]
				
				# Assigner
				delivery.delivery_agent = first_driver.user
				delivery.vehicle_type = vehicle_type
				delivery.status = 'assigned'
				delivery.assigned_at = timezone.now()
				delivery.is_auto_assigned = True
				
				# Calculer commission (80% des frais de livraison)
				delivery.agent_commission = order.delivery_fee * Decimal('0.8')
				
				delivery.save()
				
				# Mettre à jour le statut du livreur
				first_driver.status = 'busy'
				first_driver.save()
				
				# Mettre à jour le statut de la commande
				order.status = 'assigned'
				order.save()
				
				# Notifier le livreur (si service disponible)
				try:
					from notifications.service import NotificationService
					NotificationService.notify_delivery_assigned(delivery)
				except Exception as e:
					logger.warning(f"Impossible de notifier le livreur: {e}")
				
				logger.info(
					f"Livraison {delivery.tracking_number} assignée automatiquement "
					f"à {first_driver.user.phone}"
				)
				
				return delivery
				
		except Exception as e:
			logger.error(f"Erreur assignation automatique: {e}")
			return None


