"""API v1: orders endpoints."""

import logging
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, RetrieveAPIView

from orders.models import Order
from orders.serializers import (
	OrderSerializer, OrderCreateSerializer, 
	OrderStatusUpdateSerializer
)
from notifications.models import Notification
# Importer DeliveryService depuis le fichier services.py (pas le package services/)
# IMPORTANT: Importer le fichier AVANT le package pour éviter les conflits
import sys
import importlib.util
import os

# Chemin absolu vers le fichier services.py
delivery_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'delivery')
services_file_path = os.path.abspath(os.path.join(delivery_dir, 'services.py'))

# Charger le fichier services.py comme module séparé
spec = importlib.util.spec_from_file_location("delivery_services_file_module", services_file_path)
delivery_services_file_module = importlib.util.module_from_spec(spec)
sys.modules["delivery_services_file_module"] = delivery_services_file_module
spec.loader.exec_module(delivery_services_file_module)

# Extraire DeliveryService et auto_assign_delivery du fichier
DeliveryService = delivery_services_file_module.DeliveryService
auto_assign_delivery = delivery_services_file_module.auto_assign_delivery

# Maintenant importer les nouveaux services depuis le package
from delivery.services import DeliveryRulesService, DeliveryPricingService
from delivery.models import Delivery, VehicleType
from users.models import User
from decimal import Decimal

logger = logging.getLogger(__name__)

class OrderCreateView(APIView):
	permission_classes = [permissions.IsAuthenticated]
    
	def post(self, request):
		serializer = OrderCreateSerializer(
			data=request.data,
			context={'request': request}
		)
        
		if serializer.is_valid():
			order = serializer.save()
            
			return Response({
				'success': True,
				'message': 'Commande créée avec succès.',
				'data': OrderSerializer(order).data
			}, status=status.HTTP_201_CREATED)
        
		# Capture et journalise certaines erreurs métier (ex: magasin fermé) dans les notifications utilisateur
		try:
			store_errors = serializer.errors.get('store') if hasattr(serializer, 'errors') else None
			if store_errors:
				message = ' '.join([str(e) for e in store_errors])
				Notification.objects.create(
					user=request.user,
					title='Commande non créée',
					body=message,
					notif_type='warning',
					metadata={'context': 'order_create'}
				)
		except Exception:
			# On garde silencieux pour ne pas masquer l'erreur principale
			pass

		return Response({
			'success': False,
			'error': {
				'code': status.HTTP_400_BAD_REQUEST,
				'message': 'Impossible de créer la commande.',
				'details': serializer.errors
			}
		}, status=status.HTTP_400_BAD_REQUEST)

class OrderDetailView(RetrieveAPIView):
	permission_classes = [permissions.IsAuthenticated]
	serializer_class = OrderSerializer
    
	def get_queryset(self):
		# Un client ne peut voir que ses commandes
		# Un gérant ne peut voir que les commandes de son magasin
		user = self.request.user
        
		if user.is_client():
			return Order.objects.filter(client=user)
		elif user.is_store_manager():
			return Order.objects.filter(store__manager=user)
		elif user.is_delivery_agent():
			return Order.objects.filter(delivery__delivery_agent=user)
		else:
			return Order.objects.all()
    
	def retrieve(self, request, *args, **kwargs):
		instance = self.get_object()
		serializer = self.get_serializer(instance)
        
		return Response({
			'success': True,
			'data': serializer.data
		})

class OrderListView(ListAPIView):
	permission_classes = [permissions.IsAuthenticated]
	serializer_class = OrderSerializer
    
	def get_queryset(self):
		user = self.request.user
        
		if user.is_client():
			return Order.objects.filter(client=user).order_by('-created_at')
		elif user.is_store_manager():
			return Order.objects.filter(store__manager=user).order_by('-created_at')
		elif user.is_delivery_agent():
			return Order.objects.filter(delivery__delivery_agent=user).order_by('-created_at')
		else:
			return Order.objects.all().order_by('-created_at')
    
	def list(self, request, *args, **kwargs):
		queryset = self.filter_queryset(self.get_queryset())
		page = self.paginate_queryset(queryset)
        
		if page is not None:
			serializer = self.get_serializer(page, many=True)
			return self.get_paginated_response(serializer.data)
        
		serializer = self.get_serializer(queryset, many=True)
		return Response({
			'success': True,
			'data': serializer.data
		})

class OrderStatusUpdateView(APIView):
	permission_classes = [permissions.IsAuthenticated]
    
	def patch(self, request, order_id):
		try:
			# Vérifier les permissions
			if request.user.is_store_manager():
				order = Order.objects.get(
					id=order_id, 
					store__manager=request.user
				)
			elif request.user.is_admin():
				order = Order.objects.get(id=order_id)
			else:
				return Response({
					'success': False,
					'error': {
						'code': status.HTTP_403_FORBIDDEN,
						'message': 'Non autorisé à modifier cette commande.'
					}
				}, status=status.HTTP_403_FORBIDDEN)
            
			serializer = OrderStatusUpdateSerializer(
				order, 
				data=request.data, 
				partial=True
			)
			
			if serializer.is_valid():
				serializer.save()
				order.refresh_from_db()

				# Auto-assigner dès que le statut passe à "ready"
				if order.status == 'ready':
					try:
						auto_assign_delivery(order)
					except Exception as assign_err:
						logger.error(f"❌ Auto-assignation livreur échouée pour {order.order_number}: {assign_err}")
				
				return Response({
					'success': True,
					'message': 'Statut de commande mis à jour.',
					'data': OrderSerializer(order).data
				})
            
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_400_BAD_REQUEST,
					'message': 'Données invalides.',
					'details': serializer.errors
				}
			}, status=status.HTTP_400_BAD_REQUEST)
        
		except Order.DoesNotExist:
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_404_NOT_FOUND,
					'message': 'Commande non trouvée.'
				}
			}, status=status.HTTP_404_NOT_FOUND)


class ClientConfirmDeliveryView(APIView):
	"""
	Permet au client de confirmer qu'il a bien reçu sa commande.
	Cette confirmation client est complémentaire à la preuve de livraison uploadée par le livreur.
	
	POST /api/v1/orders/<order_id>/confirm-delivery/
	
	Body JSON:
	{
		"pin_code": "123456"  # Code PIN optionnel (si le livreur a envoyé un code)
	}
	
	Le client doit:
	- Être le propriétaire de la commande
	- La commande doit être en statut 'delivered'
	- La preuve de livraison doit déjà être uploadée par le livreur
	- Si PIN requis, fournir le code correct
	"""
	permission_classes = [permissions.IsAuthenticated]
	
	def post(self, request, order_id):
		try:
			# Vérifier que c'est bien le client de cette commande
			order = Order.objects.get(id=order_id, client=request.user)
			
			# Vérifier le statut
			if order.status != 'delivered':
				return Response({
					'success': False,
					'error': {
						'code': status.HTTP_400_BAD_REQUEST,
						'message': f'La commande doit être en statut "delivered". Statut actuel: {order.status}'
					}
				}, status=status.HTTP_400_BAD_REQUEST)
			
			# Vérifier qu'il y a bien une preuve de livraison
			if not hasattr(order, 'delivery') or not order.delivery:
				return Response({
					'success': False,
					'error': {
						'code': status.HTTP_400_BAD_REQUEST,
						'message': 'Aucune livraison associée à cette commande.'
					}
				}, status=status.HTTP_400_BAD_REQUEST)
			
			# Récupérer la preuve de livraison
			from delivery.models import DeliveryProof
			try:
				proof = DeliveryProof.objects.get(delivery=order.delivery)
			except DeliveryProof.DoesNotExist:
				return Response({
					'success': False,
					'error': {
						'code': status.HTTP_400_BAD_REQUEST,
						'message': 'Aucune preuve de livraison trouvée. Le livreur doit d\'abord uploader la preuve.'
					}
				}, status=status.HTTP_400_BAD_REQUEST)
			
			# Vérifier le PIN si fourni
			pin_code = request.data.get('pin_code', '').strip()
			if pin_code:
				expected_pin = order.delivery.delivery_code.strip()
				if pin_code != expected_pin:
					return Response({
						'success': False,
						'error': {
							'code': status.HTTP_400_BAD_REQUEST,
							'message': 'Code PIN incorrect'
						}
					}, status=status.HTTP_400_BAD_REQUEST)
				# PIN correct, marquer comme vérifié
				proof.pin_verified = True
			
			# Vérifier si déjà confirmé
			if proof.client_received_status:
				return Response({
					'success': True,
					'message': 'Réception déjà confirmée.',
					'data': {
						'order_id': order.id,
						'confirmed_at': proof.id_card_photo_uploaded_at,
						'already_confirmed': True,
						'client_received_status': True,
						'proof_fully_confirmed': proof.is_fully_confirmed
					}
				})
			
			# Confirmer la réception
			proof.client_received_status = True
			proof.save()
			proof.refresh_from_db()
			
			# Créer une notification pour le livreur
			Notification.objects.create(
				user=order.delivery.delivery_agent,
				title='Livraison confirmée par le client',
				body=f'Le client a confirmé la réception de la commande #{order.order_number}',
				notif_type='delivery',
				metadata={
					'order_id': order.id,
					'delivery_id': order.delivery.id,
					'action': 'client_confirmed_delivery'
				}
			)
			
			# Log dans l'audit trail
			from core.models import AuditLog
			AuditLog.objects.create(
				user=request.user,
				action='CLIENT_CONFIRM_DELIVERY',
				model_name='DeliveryProof',
				object_id=proof.id,
				changes={
					'client_received_status': True,
					'pin_verified': pin_code != '',
					'confirmed_by': request.user.get_full_name() or request.user.email,
					'order_number': order.order_number
				},
				ip_address=request.META.get('REMOTE_ADDR'),
				user_agent=request.META.get('HTTP_USER_AGENT', '')
			)
			
			return Response({
				'success': True,
				'message': 'Réception confirmée avec succès.',
				'data': {
					'order_id': order.id,
					'confirmed_at': proof.id_card_photo_uploaded_at,
					'proof_valid': proof.is_valid,
					'client_received_status': proof.client_received_status,
					'proof_fully_confirmed': proof.is_fully_confirmed
				}
			})
			
		except Order.DoesNotExist:
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_404_NOT_FOUND,
					'message': 'Commande non trouvée ou vous n\'êtes pas autorisé.'
				}
			}, status=status.HTTP_404_NOT_FOUND)


class OrderSelectVehicleView(APIView):
	"""Permet au client de sélectionner un type de véhicule pour sa commande"""
	permission_classes = [permissions.IsAuthenticated]
	
	def patch(self, request, order_id):
		try:
			order = Order.objects.get(id=order_id)
			
			# Vérifier que c'est le client de la commande
			if order.client != request.user:
				return Response({
					'success': False,
					'error': 'Non autorisé - Vous n\'êtes pas le client de cette commande'
				}, status=status.HTTP_403_FORBIDDEN)
			
			# Vérifier que la commande est dans un état où on peut sélectionner un véhicule
			if order.status not in ['created', 'pending_payment']:
				return Response({
					'success': False,
					'error': f'Impossible de sélectionner un véhicule. Statut actuel: {order.get_status_display()}'
				}, status=status.HTTP_400_BAD_REQUEST)
			
			vehicle_type_id = request.data.get('vehicle_type_id')
			if not vehicle_type_id:
				return Response({
					'success': False,
					'error': 'vehicle_type_id requis'
				}, status=status.HTTP_400_BAD_REQUEST)
			
			try:
				vehicle_type = VehicleType.objects.get(id=vehicle_type_id, is_active=True)
			except VehicleType.DoesNotExist:
				return Response({
					'success': False,
					'error': 'Type de véhicule introuvable ou inactif'
				}, status=status.HTTP_404_NOT_FOUND)
			
			# Valider le choix
			is_valid, error_message, minimum_required = DeliveryRulesService.validate_vehicle_selection(
				order, vehicle_type
			)
			
			if not is_valid:
				return Response({
					'success': False,
					'error': error_message or 'Véhicule non compatible avec la commande',
					'minimum_required_vehicle_type': {
						'id': minimum_required.id,
						'name': minimum_required.get_name_display()
					} if minimum_required else None
				}, status=status.HTTP_400_BAD_REQUEST)
			
			# Récupérer ou créer la livraison
			delivery, created = Delivery.objects.get_or_create(order=order)
			
			# Calculer le véhicule minimum requis si pas déjà fait
			if not delivery.minimum_required_vehicle_type:
				delivery.minimum_required_vehicle_type = DeliveryRulesService.calculate_minimum_vehicle_type(order)
			
			# Mettre à jour le véhicule sélectionné
			delivery.selected_vehicle_type = vehicle_type
			
			# Calculer la distance et déterminer si intra/inter-ville
			from delivery.services.delivery_pricing import DeliveryPricingService
			distance_km = DeliveryPricingService.estimate_distance(order.store, order)
			delivery.distance_km = distance_km
			delivery.is_intra_city = not DeliveryRulesService.is_intercity_delivery(order)
			
			# Calculer le prix de livraison
			delivery_price = DeliveryPricingService.calculate_delivery_price(
				order, vehicle_type, distance_km
			)
			
			# Mettre à jour les frais de livraison de la commande
			order.delivery_fee = delivery_price
			delivery.delivery_fee = delivery_price
			
			# Recalculer le total de la commande
			order.calculate_totals()
			
			# Sauvegarder
			delivery.save()
			order.save()
			
			return Response({
				'success': True,
				'message': 'Véhicule sélectionné avec succès',
				'data': {
					'order_id': order.id,
					'vehicle_type': {
						'id': vehicle_type.id,
						'name': vehicle_type.get_name_display()
					},
					'delivery_fee': float(delivery_price),
					'total_amount': float(order.total_amount),
					'is_intra_city': delivery.is_intra_city,
					'distance_km': float(distance_km)
				}
			})
			
		except Order.DoesNotExist:
			return Response({
				'success': False,
				'error': 'Commande introuvable'
			}, status=status.HTTP_404_NOT_FOUND)
		except Exception as e:
			logger.error(f"Erreur sélection véhicule: {e}")
			return Response({
				'success': False,
				'error': f'Erreur: {str(e)}'
			}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

