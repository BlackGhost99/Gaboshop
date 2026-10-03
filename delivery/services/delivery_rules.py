"""Service pour déterminer le véhicule minimum requis pour une commande"""
import logging
from decimal import Decimal
from django.db.models import Q
from delivery.models import VehicleType

logger = logging.getLogger(__name__)


class DeliveryRulesService:
	"""Service pour calculer les règles d'éligibilité des véhicules"""
	
	# Poids par défaut si non renseigné (en kg)
	DEFAULT_WEIGHT_PER_ITEM = Decimal('0.5')  # 500g par défaut
	# Longueur par défaut si non renseignée (en mètres)
	DEFAULT_LENGTH_PER_ITEM = Decimal('0.5')  # 50cm par défaut
	
	@staticmethod
	def calculate_order_weight(order):
		"""
		Calcule le poids total estimé d'une commande
		"""
		total_weight = Decimal('0.00')
		
		for item in order.items.all():
			product = item.product
			quantity = Decimal(item.quantity)
			
			# Utiliser weight_kg si disponible, sinon estimated_weight_kg, sinon défaut
			if product.weight_kg:
				item_weight = product.weight_kg
			elif product.estimated_weight_kg:
				item_weight = product.estimated_weight_kg
			else:
				item_weight = DeliveryRulesService.DEFAULT_WEIGHT_PER_ITEM
			
			total_weight += item_weight * quantity
		
		return total_weight
	
	@staticmethod
	def calculate_order_items_count(order):
		"""
		Compte le nombre total d'articles dans une commande
		"""
		return sum(item.quantity for item in order.items.all())

	@staticmethod
	def calculate_order_length(order):
		"""
		Calcule la longueur totale estimée d'une commande
		"""
		total_length = Decimal('0.00')
		
		for item in order.items.all():
			product = item.product
			quantity = Decimal(item.quantity)
			
			# Utiliser length_m si disponible, sinon valeur par défaut
			if getattr(product, 'length_m', None):
				item_length = product.length_m
			else:
				item_length = DeliveryRulesService.DEFAULT_LENGTH_PER_ITEM
			
			total_length += item_length * quantity
		
		return total_length

	@staticmethod
	def _vehicle_can_handle(vehicle_type, total_weight, total_length, items_count, is_intercity):
		if total_weight > vehicle_type.max_weight_kg:
			return False
		if total_length > vehicle_type.max_length_m:
			return False
		if vehicle_type.max_items > 0 and items_count > vehicle_type.max_items:
			return False
		if is_intercity and not vehicle_type.allow_intercity:
			return False
		return True

	@staticmethod
	def select_vehicle_for_load(total_weight, total_length, items_count, is_intercity):
		"""
		Sélectionne le véhicule minimum requis selon poids + longueur
		"""
		vehicle_types = VehicleType.objects.filter(is_active=True).order_by('max_weight_kg')
		
		for vehicle_type in vehicle_types:
			if DeliveryRulesService._vehicle_can_handle(
				vehicle_type, total_weight, total_length, items_count, is_intercity
			):
				return vehicle_type
		
		return None
	
	@staticmethod
	def is_intercity_delivery(order):
		"""
		Détermine si la livraison est inter-ville
		"""
		store_city = order.store.city or 'Libreville'
		order_city = order.city or 'Libreville'
		
		# Normaliser les noms de villes (majuscules, sans accents)
		store_city_normalized = store_city.strip().upper()
		order_city_normalized = order_city.strip().upper()
		
		return store_city_normalized != order_city_normalized
	
	@staticmethod
	def calculate_minimum_vehicle_type(order):
		"""
		Calcule le type de véhicule minimum requis pour une commande
		
		Retourne le VehicleType minimum requis ou None si aucun véhicule ne convient
		"""
		try:
			total_weight = DeliveryRulesService.calculate_order_weight(order)
			total_length = DeliveryRulesService.calculate_order_length(order)
			items_count = DeliveryRulesService.calculate_order_items_count(order)
			is_intercity = DeliveryRulesService.is_intercity_delivery(order)
			
			logger.debug(
				f"Calcul véhicule minimum - Poids: {total_weight}kg, "
				f"Longueur: {total_length}m, Items: {items_count}, "
				f"Inter-ville: {is_intercity}"
			)
			
			# Récupérer tous les véhicules actifs, triés par capacité croissante
			vehicle_types = VehicleType.objects.filter(is_active=True).order_by('max_weight_kg')
			
			# Filtrer selon les règles
			for vehicle_type in vehicle_types:
				if not DeliveryRulesService._vehicle_can_handle(
					vehicle_type, total_weight, total_length, items_count, is_intercity
				):
					continue
				
				# Si on arrive ici, le véhicule convient
				logger.info(
					f"Véhicule minimum requis pour commande {order.order_number}: "
					f"{vehicle_type.get_name_display()}"
				)
				return vehicle_type
			
			# Aucun véhicule ne convient
			logger.warning(
				f"Aucun véhicule disponible pour commande {order.order_number} "
				f"(Poids: {total_weight}kg, Longueur: {total_length}m, "
				f"Items: {items_count}, Inter-ville: {is_intercity})"
			)
			return None
			
		except Exception as e:
			logger.error(f"Erreur calcul véhicule minimum: {e}")
			return None
	
	@staticmethod
	def get_eligible_vehicle_types(order):
		"""
		Retourne la liste des types de véhicules éligibles pour une commande
		"""
		try:
			total_weight = DeliveryRulesService.calculate_order_weight(order)
			total_length = DeliveryRulesService.calculate_order_length(order)
			items_count = DeliveryRulesService.calculate_order_items_count(order)
			is_intercity = DeliveryRulesService.is_intercity_delivery(order)
			
			eligible = []
			vehicle_types = VehicleType.objects.filter(is_active=True).order_by('max_weight_kg')
			
			for vehicle_type in vehicle_types:
				if DeliveryRulesService._vehicle_can_handle(
					vehicle_type, total_weight, total_length, items_count, is_intercity
				):
					eligible.append(vehicle_type)
			
			return eligible
			
		except Exception as e:
			logger.error(f"Erreur récupération véhicules éligibles: {e}")
			return []
	
	@staticmethod
	def validate_vehicle_selection(order, vehicle_type):
		"""
		Valide le choix d'un véhicule par le client
		
		Retourne (is_valid, error_message, minimum_required)
		"""
		try:
			if not vehicle_type:
				return False, "Type de véhicule requis", None
			
			if not vehicle_type.is_active:
				return False, "Ce type de véhicule n'est plus actif", None
			
			minimum_required = DeliveryRulesService.calculate_minimum_vehicle_type(order)
			
			if not minimum_required:
				return False, "Aucun véhicule ne peut livrer cette commande", None
			
			total_weight = DeliveryRulesService.calculate_order_weight(order)
			total_length = DeliveryRulesService.calculate_order_length(order)
			items_count = DeliveryRulesService.calculate_order_items_count(order)
			is_intercity = DeliveryRulesService.is_intercity_delivery(order)
			
			# Vérifier capacité véhicule
			if not DeliveryRulesService._vehicle_can_handle(
				vehicle_type, total_weight, total_length, items_count, is_intercity
			):
				return (
					False,
					f"Ce véhicule ne peut pas transporter cette commande. "
					f"Véhicule minimum requis: {minimum_required.get_name_display()}",
					minimum_required
				)
			
			return True, None, minimum_required
			
		except Exception as e:
			logger.error(f"Erreur validation véhicule: {e}")
			return False, f"Erreur de validation: {str(e)}", None


