"""
Admin dashboard views for delivery zone analytics and tariff management.
Shows statistics about configured zones, vehicle types, and pricing strategies.
"""

import logging
from decimal import Decimal
from django.db import models
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response

logger = logging.getLogger(__name__)

from delivery.models import DeliveryZone, VehicleType, ZoneVehicleRate


class DeliveryTariffAnalyticsView(APIView):
	"""
	Admin endpoint to analyze delivery tariffs across zones.
	GET /api/v1/admin/delivery/tariff-analytics/
	
	Returns:
	{
		"success": true,
		"data": {
			"zones_count": 7,
			"vehicle_types_count": 3,
			"total_rate_configs": 21,
			"zones": [
				{
					"id": 1,
					"name": "Centre-Ville",
					"city": "Libreville",
					"inter_city_surcharge": "1500.00",
					"rate_count": 3,
					"rates": [...]
				}
			],
			"price_statistics": {
				"avg_base_price_by_vehicle": {...},
				"min_max_per_km": {...}
			}
		}
	}
	"""
	permission_classes = [permissions.IsAdminUser]
	
	def get(self, request):
		"""Retrieve tariff analytics"""
		try:
			# Get zone statistics
			zones = DeliveryZone.objects.filter(is_active=True).prefetch_related('zonevehiclerate_set')
			zones_count = zones.count()
			
			# Get vehicle types
			vehicles = VehicleType.objects.filter(is_active=True)
			vehicle_types_count = vehicles.count()
			
			# Get rate configurations
			total_rates = ZoneVehicleRate.objects.filter(is_active=True)
			total_rate_configs = total_rates.count()
			
			# Build zones data with rates
			zones_data = []
			for zone in zones:
				rates = zone.zonevehiclerate_set.filter(is_active=True)
				zone_data = {
					'id': zone.id,
					'name': zone.name,
					'city': zone.city,
					'description': zone.description,
					'inter_city_surcharge': str(zone.inter_city_surcharge),
					'rate_count': rates.count(),
					'rates': [
						{
							'vehicle': rate.vehicle.get_name_display(),
							'vehicle_type': rate.vehicle.name,
							'base_price': str(rate.base_price),
							'price_per_km': str(rate.price_per_km),
						}
						for rate in rates.order_by('vehicle__name')
					]
				}
				zones_data.append(zone_data)
			
			# Calculate price statistics
			price_stats = {
				'avg_base_price_by_vehicle': {},
				'min_max_per_km': {},
			}
			
			for vehicle in vehicles:
				vehicle_rates = total_rates.filter(vehicle=vehicle)
				if vehicle_rates.exists():
					avg_base = vehicle_rates.aggregate(avg=models.Avg('base_price'))['avg'] or 0
					price_stats['avg_base_price_by_vehicle'][vehicle.name] = {
						'name': vehicle.get_name_display(),
						'avg_base_price': f"{avg_base:.2f}",
						'count': vehicle_rates.count(),
					}
					
					min_km = vehicle_rates.aggregate(min=models.Min('price_per_km'))['min'] or 0
					max_km = vehicle_rates.aggregate(max=models.Max('price_per_km'))['max'] or 0
					price_stats['min_max_per_km'][vehicle.name] = {
						'name': vehicle.get_name_display(),
						'min_per_km': f"{min_km:.2f}",
						'max_per_km': f"{max_km:.2f}",
					}
			
			response_data = {
				'zones_count': zones_count,
				'vehicle_types_count': vehicle_types_count,
				'total_rate_configs': total_rate_configs,
				'zones': zones_data,
				'price_statistics': price_stats,
			}
			
			return Response({
				'success': True,
				'data': response_data
			}, status=status.HTTP_200_OK)
			
		except Exception as e:
			logger.error(f"Erreur analytics tarifs: {e}")
			return Response({
				'success': False,
				'error': str(e)
			}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DeliveryZoneHealthCheckView(APIView):
	"""
	Admin endpoint to verify delivery zone configuration health.
	Ensures all zones have rates for all vehicle types.
	GET /api/v1/admin/delivery/zone-health/
	
	Returns:
	{
		"success": true,
		"data": {
			"healthy": true,
			"issues": [],
			"coverage": {
				"complete_zones": 5,
				"incomplete_zones": 2,
				"zones_missing_rates": [...]
			}
		}
	}
	"""
	permission_classes = [permissions.IsAdminUser]
	
	def get(self, request):
		"""Check zone configuration health"""
		try:
			zones = DeliveryZone.objects.filter(is_active=True)
			vehicles = VehicleType.objects.filter(is_active=True)
			
			issues = []
			zones_missing_rates = []
			complete_zones = 0
			incomplete_zones = 0
			
			for zone in zones:
				zone_rates = zone.zonevehiclerate_set.filter(is_active=True)
				if zone_rates.count() == vehicles.count():
					complete_zones += 1
				else:
					incomplete_zones += 1
					missing_vehicles = []
					for vehicle in vehicles:
						if not zone_rates.filter(vehicle=vehicle).exists():
							missing_vehicles.append(vehicle.get_name_display())
					
					zones_missing_rates.append({
						'zone_id': zone.id,
						'zone_name': f"{zone.name} ({zone.city})",
						'missing_vehicles': missing_vehicles,
						'configured_count': zone_rates.count(),
						'total_expected': vehicles.count(),
					})
					issues.append(f"Zone '{zone.name}' manquent tarifs pour: {', '.join(missing_vehicles)}")
			
			# Check for zones without any rates at all
			empty_zones = []
			for zone in zones:
				if zone.zonevehiclerate_set.filter(is_active=True).count() == 0:
					empty_zones.append(zone.name)
					issues.append(f"Zone '{zone.name}' n'a aucun tarif configuré")
			
			is_healthy = len(issues) == 0
			
			response_data = {
				'healthy': is_healthy,
				'issues': issues,
				'coverage': {
					'total_zones': zones.count(),
					'complete_zones': complete_zones,
					'incomplete_zones': incomplete_zones,
					'empty_zones': empty_zones,
					'zones_missing_rates': zones_missing_rates,
				},
			}
			
			return Response({
				'success': True,
				'data': response_data
			}, status=status.HTTP_200_OK)
			
		except Exception as e:
			logger.error(f"Erreur health check zones: {e}")
			return Response({
				'success': False,
				'error': str(e)
			}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
