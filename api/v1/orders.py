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
from delivery.services import DeliveryService
from users.models import User

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

				# Auto-assigner dès que le statut passe à "ready": on prend simplement le premier livreur disponible
				if order.status == 'ready' and not getattr(order, 'delivery', None):
					try:
						agent = User.objects.filter(user_type='delivery_agent', is_available=True).first()
						if agent:
							DeliveryService.assign_delivery_agent(order, agent)
						else:
							logger.warning(f"⚠️ Aucun livreur disponible pour {order.order_number}")
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

