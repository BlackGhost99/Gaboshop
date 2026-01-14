"""Service pour calculer les prix de livraison"""
import logging
from decimal import Decimal
from delivery.models import VehicleType, CityDistance
from orders.models import Order
from stores.models import Store

logger = logging.getLogger(__name__)


class DeliveryPricingService:
	"""Service pour calculer les prix de livraison"""
	
	# Distances par défaut si non calculables
	DEFAULT_INTRA_CITY_DISTANCE = Decimal('10.00')  # 10 km par défaut intra-ville
	DEFAULT_INTER_CITY_DISTANCE = Decimal('50.00')  # 50 km par défaut inter-ville
	
	@staticmethod
	def estimate_distance(store, order):
		"""
		Estime la distance entre le magasin et l'adresse de livraison
		
		Priorité:
		1. GPS (Haversine) si coordonnées disponibles
		2. Table CityDistance
		3. Valeur par défaut selon intra/inter-ville
		"""
		try:
			# Essayer GPS d'abord
			if (store.latitude and store.longitude and 
				hasattr(order, 'delivery') and order.delivery and
				order.delivery.delivery_lat and order.delivery.delivery_lng):
				
				from delivery.utils import haversine_distance
				
				distance = haversine_distance(
					float(store.latitude),
					float(store.longitude),
					float(order.delivery.delivery_lat),
					float(order.delivery.delivery_lng)
				)
				
				if distance:
					return Decimal(str(distance))
			
			# Essayer table CityDistance
			store_city = store.city or 'Libreville'
			order_city = order.city or 'Libreville'
			
			if store_city != order_city:
				# Inter-ville
				try:
					city_distance = CityDistance.objects.get(
						from_city=store_city,
						to_city=order_city
					)
					return city_distance.distance_km
				except CityDistance.DoesNotExist:
					# Essayer dans l'autre sens
					try:
						city_distance = CityDistance.objects.get(
							from_city=order_city,
							to_city=store_city
						)
						return city_distance.distance_km
					except CityDistance.DoesNotExist:
						pass
			
			# Valeur par défaut
			from delivery.services.delivery_rules import DeliveryRulesService
			is_intercity = DeliveryRulesService.is_intercity_delivery(order)
			
			if is_intercity:
				return DeliveryPricingService.DEFAULT_INTER_CITY_DISTANCE
			else:
				return DeliveryPricingService.DEFAULT_INTRA_CITY_DISTANCE
				
		except Exception as e:
			logger.error(f"Erreur estimation distance: {e}")
			# Retourner valeur par défaut
			from delivery.services.delivery_rules import DeliveryRulesService
			is_intercity = DeliveryRulesService.is_intercity_delivery(order)
			return (
				DeliveryPricingService.DEFAULT_INTER_CITY_DISTANCE if is_intercity
				else DeliveryPricingService.DEFAULT_INTRA_CITY_DISTANCE
			)
	
	@staticmethod
	def calculate_delivery_price(order, vehicle_type, distance_km=None):
		"""
		Calcule le prix de livraison pour une commande
		
		Args:
			order: Order instance
			vehicle_type: VehicleType instance
			distance_km: Decimal ou None (sera calculé si None)
		
		Returns:
			Decimal: Prix de livraison en FCFA
		"""
		try:
			if not vehicle_type:
				raise ValueError("Type de véhicule requis")
			
			# Calculer distance si non fournie
			if distance_km is None:
				distance_km = DeliveryPricingService.estimate_distance(order.store, order)
			
			# Déterminer si intra ou inter-ville
			from delivery.services.delivery_rules import DeliveryRulesService
			is_intercity = DeliveryRulesService.is_intercity_delivery(order)
			
			# Sélectionner les tarifs appropriés
			if is_intercity:
				base_price = vehicle_type.base_price_inter_city
				price_per_km = vehicle_type.price_per_km_inter_city
			else:
				base_price = vehicle_type.base_price_intra_city
				price_per_km = vehicle_type.price_per_km_intra_city
			
			# Calculer le prix
			price = base_price + (distance_km * price_per_km)
			
			# Arrondir à 2 décimales
			price = price.quantize(Decimal('0.01'))
			
			logger.info(
				f"Prix livraison calculé pour commande {order.order_number}: "
				f"{price} FCFA ({vehicle_type.get_name_display()}, "
				f"{'inter' if is_intercity else 'intra'}-ville, {distance_km} km)"
			)
			
			return price
			
		except Exception as e:
			logger.error(f"Erreur calcul prix livraison: {e}")
			raise


