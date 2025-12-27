"""API v1: delivery endpoints."""

import logging
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from django.utils import timezone

logger = logging.getLogger(__name__)

from delivery.models import Delivery
from delivery.serializers import (
	DeliverySerializer, DeliveryAssignSerializer,
	DeliveryStatusUpdateSerializer, DeliveryConfirmSerializer
)
from orders.models import Order
from core.validators import (
	is_valid_delivery_transition, 
	can_user_change_delivery_status,
	validate_delivery_proof,
	can_mark_as_delivered
)
from core.models import AuditLog
from django.db import transaction
from notifications.service import NotificationService
from delivery.services import auto_assign_delivery

class DeliveryProfileUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.is_delivery_agent():
            return Response({'error': 'Accès réservé aux livreurs'}, status=status.HTTP_403_FORBIDDEN)

        # Update User fields
        if 'first_name' in request.data:
            user.first_name = request.data['first_name']
        if 'last_name' in request.data:
            user.last_name = request.data['last_name']
        if 'email' in request.data:
            user.email = request.data['email']
        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']
        
        user.save()

        return Response({
            'success': True,
            'message': 'Profil mis à jour avec succès',
            'data': {
                'first_name': user.first_name,
                'last_name': user.last_name,
                'email': user.email,
                'phone': user.phone,
                'profile_picture': request.build_absolute_uri(user.profile_picture.url) if user.profile_picture else None,
            }
        })

class DeliveryAssignView(APIView):
	permission_classes = [permissions.IsAuthenticated]
    
	def post(self, request, order_id):
		try:
			# Vérifier que l'utilisateur est admin ou gérant du magasin
			order = Order.objects.get(id=order_id)
            
			if not (request.user.is_admin() or 
				   (request.user.is_store_manager() and order.store.manager == request.user)):
				return Response({
					'success': False,
					'error': {
						'code': status.HTTP_403_FORBIDDEN,
						'message': 'Non autorisé à assigner des livraisons pour cette commande.'
					}
				}, status=status.HTTP_403_FORBIDDEN)
            
			# Vérifier que la commande est prête pour livraison
			if order.status != 'ready':
				return Response({
					'success': False,
					'error': {
						'code': status.HTTP_400_BAD_REQUEST,
						'message': 'La commande doit être prête pour livraison.'
					}
				}, status=status.HTTP_400_BAD_REQUEST)
            
			# Récupérer ou créer la livraison
			delivery, created = Delivery.objects.get_or_create(order=order)
            
			serializer = DeliveryAssignSerializer(
				delivery, 
				data=request.data
			)
            
			if serializer.is_valid():
				delivery = serializer.save()
				delivery.status = 'assigned'
				delivery.save()
                
				# Mettre à jour le statut de la commande
				order.status = 'assigned'
				order.save()
                
				return Response({
					'success': True,
					'message': 'Livreur assigné avec succès.',
					'data': DeliverySerializer(delivery).data
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

class DeliveryStatusUpdateView(APIView):
	permission_classes = [permissions.IsAuthenticated]
    
	def patch(self, request, delivery_id):
		try:
			# Vérifier que l'utilisateur est le livreur assigné ou admin
			delivery = Delivery.objects.get(id=delivery_id)
            
			if not (request.user.is_admin() or 
				   delivery.delivery_agent == request.user):
				return Response({
					'success': False,
					'error': {
						'code': status.HTTP_403_FORBIDDEN,
						'message': 'Non autorisé à modifier cette livraison.'
					}
				}, status=status.HTTP_403_FORBIDDEN)
            
			serializer = DeliveryStatusUpdateSerializer(
				delivery,
				data=request.data,
				partial=True
			)
            
			if serializer.is_valid():
				delivery = serializer.save()
                
				# Mettre à jour le statut de la commande si nécessaire
				if delivery.status == 'delivered':
					delivery.order.status = 'delivered'
					delivery.order.save()
                
				return Response({
					'success': True,
					'message': 'Statut de livraison mis à jour.',
					'data': DeliverySerializer(delivery).data
				})
            
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_400_BAD_REQUEST,
					'message': 'Données invalides.',
					'details': serializer.errors
				}
			}, status=status.HTTP_400_BAD_REQUEST)
        
		except Delivery.DoesNotExist:
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_404_NOT_FOUND,
					'message': 'Livraison non trouvée.'
				}
			}, status=status.HTTP_404_NOT_FOUND)

class DeliveryConfirmView(APIView):
	permission_classes = [permissions.IsAuthenticated]
    
	def post(self, request, delivery_id):
		try:
			delivery = Delivery.objects.get(
				id=delivery_id,
				delivery_agent=request.user
			)
            
			serializer = DeliveryConfirmSerializer(
				delivery,
				data=request.data,
				partial=True
			)
            
			if serializer.is_valid():
				delivery = serializer.save()
                
				return Response({
					'success': True,
					'message': 'Livraison confirmée avec succès.',
					'data': DeliverySerializer(delivery).data
				})
            
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_400_BAD_REQUEST,
					'message': 'Données invalides.',
					'details': serializer.errors
				}
			}, status=status.HTTP_400_BAD_REQUEST)
        
		except Delivery.DoesNotExist:
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_404_NOT_FOUND,
					'message': 'Livraison non trouvée.'
				}
			}, status=status.HTTP_404_NOT_FOUND)

class DeliveryListView(ListAPIView):
	permission_classes = [permissions.IsAuthenticated]
	serializer_class = DeliverySerializer
    
	def get_queryset(self):
		user = self.request.user
        
		if user.is_delivery_agent():
			return Delivery.objects.filter(delivery_agent=user)
		elif user.is_store_manager():
			return Delivery.objects.filter(order__store__manager=user)
		else:
			return Delivery.objects.all()
    
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


class AvailableDeliveriesView(ListAPIView):
	"""Liste des livraisons non assignées que les livreurs peuvent voir/claim"""
	permission_classes = [permissions.IsAuthenticated]
	serializer_class = DeliverySerializer

	def get_queryset(self):
		user = self.request.user
		# Log who requested available deliveries to help debug client visibility issues
		try:
			logger.info(f"AvailableDeliveries requested by user_id={getattr(user,'id',None)} phone={getattr(user,'phone',None)} city={getattr(user,'city',None)}")
		except Exception:
			pass
		# Only delivery agents can see available deliveries
		if not user.is_delivery_agent():
			return Delivery.objects.none()

		# Filter waiting deliveries in the same city and that are ready
		qs = Delivery.objects.filter(status='waiting')
		# Optionally restrict by city
		if hasattr(user, 'city') and user.city:
			qs = qs.filter(city=user.city)

		# Only include deliveries whose order status indicates ready for delivery
		qs = qs.filter(order__status__in=['ready', 'paid', 'confirmed'])
		return qs.order_by('created_at')


class DeliveryClaimView(APIView):
	"""Permet à un livreur de réclamer (claim) une livraison libre.
	Utilise une transaction pour éviter les courses concurrentes.
	"""
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request, delivery_id):
		user = request.user
		if not user.is_delivery_agent():
			return Response({'success': False, 'error': 'Accès réservé aux livreurs'}, status=status.HTTP_403_FORBIDDEN)

		try:
			with transaction.atomic():
				# Lock the delivery row to avoid race conditions
				delivery = Delivery.objects.select_for_update().get(id=delivery_id)

				# Must be unassigned and in waiting state
				if delivery.delivery_agent is not None or delivery.status != 'waiting':
					return Response({'success': False, 'error': 'Livraison déjà prise ou non disponible'}, status=status.HTTP_400_BAD_REQUEST)

				# Assign to current user (manual claim)
				delivery.delivery_agent = user
				delivery.status = 'assigned'
				delivery.assigned_at = timezone.now()
				delivery.is_auto_assigned = False
				# Compute agent commission if not set
				try:
					if delivery.order and delivery.order.delivery_fee:
						delivery.agent_commission = delivery.order.delivery_fee * Decimal('0.8')
				except Exception:
					pass
				delivery.save()

				# Update order status
				delivery.order.status = 'assigned'
				delivery.order.save()

				# Notify agent (local notification) and client
				try:
					NotificationService.notify_delivery_assigned(delivery)
				except Exception:
					pass

			return Response({'success': True, 'message': 'Livraison réclamée avec succès', 'data': DeliverySerializer(delivery).data})

		except Delivery.DoesNotExist:
			return Response({'success': False, 'error': 'Livraison non trouvée'}, status=status.HTTP_404_NOT_FOUND)
		except Exception as e:
			return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


def get_client_ip(request):
	"""Récupère l'IP du client pour l'audit"""
	x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
	if x_forwarded_for:
		ip = x_forwarded_for.split(',')[0]
	else:
		ip = request.META.get('REMOTE_ADDR')
	return ip


class DeliveryAcceptAssignmentView(APIView):
	"""Le livreur accepte une commande qui lui a été assignée"""
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request, delivery_id):
		try:
			delivery = Delivery.objects.get(id=delivery_id)
			
			# Vérifier que le livreur accepte sa propre livraison
			if delivery.delivery_agent != request.user:
				AuditLog.log_action(
					action_type='delivery_status_change_rejected',
					user=request.user,
					user_role=request.user.get_user_type_display() if hasattr(request.user, 'get_user_type_display') else 'unknown',
					object_type='delivery',
					object_id=delivery_id,
					old_value=delivery.status,
					new_value='accepted',
					ip_address=get_client_ip(request),
					user_agent=request.META.get('HTTP_USER_AGENT', ''),
					reason='Unauthorized user attempted to accept delivery',
					is_suspicious=True
				)
				return Response({
					'success': False,
					'error': 'Vous ne pouvez accepter que vos propres commandes'
				}, status=status.HTTP_403_FORBIDDEN)
			
			# Vérifier que la transition de statut est valide
			is_valid, error_msg = can_user_change_delivery_status(request.user, delivery.status, 'accepted')
			if not is_valid:
				AuditLog.log_action(
					action_type='delivery_status_change_rejected',
					user=request.user,
					user_role=request.user.get_user_type_display() if hasattr(request.user, 'get_user_type_display') else 'unknown',
					object_type='delivery',
					object_id=delivery_id,
					old_value=delivery.status,
					new_value='accepted',
					ip_address=get_client_ip(request),
					user_agent=request.META.get('HTTP_USER_AGENT', ''),
					reason=error_msg,
					is_suspicious=True
				)
				return Response({
					'success': False,
					'error': error_msg
				}, status=status.HTTP_400_BAD_REQUEST)
			
			old_status = delivery.status
			old_order_status = delivery.order.status
			
			# Accepter la livraison
			delivery.status = 'accepted'
			delivery.save()
			
			# Mettre à jour la commande
			delivery.order.status = 'in_transit'
			delivery.order.save()
			
			# Enregistrer l'action dans l'audit
			AuditLog.log_action(
				action_type='delivery_status_change',
				user=request.user,
				user_role=request.user.get_user_type_display() if hasattr(request.user, 'get_user_type_display') else 'unknown',
				object_type='delivery',
				object_id=delivery_id,
				old_value=old_status,
				new_value=delivery.status,
				ip_address=get_client_ip(request),
				user_agent=request.META.get('HTTP_USER_AGENT', ''),
				reason='Delivery agent accepted delivery assignment'
			)
			
			# Enregistrer aussi la mise à jour de la commande
			AuditLog.log_action(
				action_type='order_status_change',
				user=request.user,
				user_role=request.user.get_user_type_display() if hasattr(request.user, 'get_user_type_display') else 'unknown',
				object_type='order',
				object_id=delivery.order.id,
				old_value=old_order_status,
				new_value=delivery.order.status,
				ip_address=get_client_ip(request),
				user_agent=request.META.get('HTTP_USER_AGENT', ''),
				reason='Order status updated when delivery accepted'
			)
			
			# Envoyer le PIN au client via notification
			try:
				from notifications.models import Notification
				client = delivery.order.client
				pin_code = delivery.delivery_code
				message = f'Votre livreur a accepté la livraison de la commande #{delivery.order.order_number}. Code PIN de livraison: {pin_code}'
				
				# Enregistrer la notification en base de données
				Notification.objects.create(
					user=client,
					title='Livraison acceptée - Veuillez confirmer',
					body=message,
					notif_type='delivery',
					metadata={
						'order_id': delivery.order.id,
						'delivery_id': delivery.id,
						'delivery_code': pin_code,
						'action': 'delivery_accepted'
					}
				)
				
				# Envoyer SMS/WhatsApp au client
				from notifications.service import NotificationService
				sms_message = f'Code PIN livraison: {pin_code}. Commande #{delivery.order.order_number}'
				template = {
					'sms': sms_message,
					'whatsapp': {
						'template_name': 'delivery_pin',
						'parameters': [pin_code, str(delivery.order.order_number)]
					}
				}
				NotificationService._send_to_client(client.phone, client.email, template, message)
				logger.info(f'✓ PIN envoyé au client {client.phone} pour livraison {delivery.id}')
			except Exception as e:
				logger.error(f'Erreur lors de l\'envoi du PIN au client: {str(e)}')
			
			return Response({
				'success': True,
				'message': 'Commande acceptée avec succès',
				'data': {
					'delivery_id': delivery.id,
					'order_id': delivery.order.id,
					'status': delivery.status,
					'status_display': delivery.get_status_display()
				}
			})
		
		except Delivery.DoesNotExist:
			return Response({
				'success': False,
				'error': 'Livraison non trouvée'
			}, status=status.HTTP_404_NOT_FOUND)
		except Exception as e:
			AuditLog.log_action(
				action_type='delivery_error',
				user=request.user,
				user_role=request.user.get_user_type_display() if hasattr(request.user, 'get_user_type_display') else 'unknown',
				object_type='delivery',
				object_id=delivery_id,
				old_value='unknown',
				new_value='error',
				ip_address=get_client_ip(request),
				user_agent=request.META.get('HTTP_USER_AGENT', ''),
				reason=f'Error during delivery acceptance: {str(e)}',
				is_suspicious=True,
				notes=str(e)
			)
			return Response({
				'success': False,
				'error': str(e)
			}, status=status.HTTP_400_BAD_REQUEST)


class DeliveryRejectAssignmentView(APIView):
	"""Le livreur refuse une commande qui lui a été assignée"""
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request, delivery_id):
		try:
			delivery = Delivery.objects.get(id=delivery_id)
			
			# Vérifier que le livreur refuse sa propre livraison
			if delivery.delivery_agent != request.user:
				AuditLog.log_action(
					action_type='delivery_status_change_rejected',
					user=request.user,
					user_role=request.user.get_user_type_display() if hasattr(request.user, 'get_user_type_display') else 'unknown',
					object_type='delivery',
					object_id=delivery_id,
					old_value=delivery.status,
					new_value='waiting',
					ip_address=get_client_ip(request),
					user_agent=request.META.get('HTTP_USER_AGENT', ''),
					reason='Unauthorized user attempted to reject delivery',
					is_suspicious=True
				)
				return Response({
					'success': False,
					'error': 'Vous ne pouvez refuser que vos propres commandes'
				}, status=status.HTTP_403_FORBIDDEN)
			
			# Vérifier que la transition de statut est valide
			is_valid, error_msg = can_user_change_delivery_status(request.user, delivery.status, 'waiting')
			if not is_valid:
				AuditLog.log_action(
					action_type='delivery_status_change_rejected',
					user=request.user,
					user_role=request.user.get_user_type_display() if hasattr(request.user, 'get_user_type_display') else 'unknown',
					object_type='delivery',
					object_id=delivery_id,
					old_value=delivery.status,
					new_value='waiting',
					ip_address=get_client_ip(request),
					user_agent=request.META.get('HTTP_USER_AGENT', ''),
					reason=error_msg,
					is_suspicious=True
				)
				return Response({
					'success': False,
					'error': error_msg
				}, status=status.HTTP_400_BAD_REQUEST)
			
			old_status = delivery.status
			old_order_status = delivery.order.status
			
			# Refuser la livraison
			delivery.delivery_agent = None
			delivery.status = 'waiting'
			delivery.save()
			
			# Remettre la commande en attente
			delivery.order.status = 'ready'
			delivery.order.save()

			# Tenter une réassignation automatique immédiatement
			try:
				auto_assign_delivery(delivery.order)
			except Exception:
				logger.exception('Erreur lors de l\'auto-assignation après refus de livraison')
			
			# Enregistrer l'action dans l'audit
			AuditLog.log_action(
				action_type='delivery_status_change',
				user=request.user,
				user_role=request.user.get_user_type_display() if hasattr(request.user, 'get_user_type_display') else 'unknown',
				object_type='delivery',
				object_id=delivery_id,
				old_value=old_status,
				new_value=delivery.status,
				ip_address=get_client_ip(request),
				user_agent=request.META.get('HTTP_USER_AGENT', ''),
				reason='Delivery agent rejected delivery assignment'
			)
			
			# Enregistrer aussi la mise à jour de la commande
			AuditLog.log_action(
				action_type='order_status_change',
				user=request.user,
				user_role=request.user.get_user_type_display() if hasattr(request.user, 'get_user_type_display') else 'unknown',
				object_type='order',
				object_id=delivery.order.id,
				old_value=old_order_status,
				new_value=delivery.order.status,
				ip_address=get_client_ip(request),
				user_agent=request.META.get('HTTP_USER_AGENT', ''),
				reason='Order status updated when delivery rejected'
			)
			
			return Response({
				'success': True,
				'message': 'Commande refusée avec succès',
				'data': {
					'delivery_id': delivery.id,
					'order_id': delivery.order.id,
					'status': delivery.status,
					'status_display': delivery.get_status_display()
				}
			})
		
		except Delivery.DoesNotExist:
			return Response({
				'success': False,
				'error': 'Livraison non trouvée'
			}, status=status.HTTP_404_NOT_FOUND)
		except Exception as e:
			AuditLog.log_action(
				action_type='delivery_error',
				user=request.user,
				user_role=request.user.get_user_type_display() if hasattr(request.user, 'get_user_type_display') else 'unknown',
				object_type='delivery',
				object_id=delivery_id,
				old_value='unknown',
				new_value='error',
				ip_address=get_client_ip(request),
				user_agent=request.META.get('HTTP_USER_AGENT', ''),
				reason=f'Error during delivery completion: {str(e)}',
				is_suspicious=True,
				notes=str(e)
			)
			return Response({
				'success': False,
				'error': str(e)
			}, status=status.HTTP_400_BAD_REQUEST)


class DeliveryProofUploadView(APIView):
	"""
	Upload de la preuve de livraison (photo pièce d'identité + GPS + signature/PIN)
	IMPORTANT: Photo pièce d'identité OBLIGATOIRE, photo colis OPTIONNELLE
	Car le client peut venir chercher le colis (toutes les routes ne sont pas accessibles)
	"""
	permission_classes = [permissions.IsAuthenticated]
	
	def post(self, request, delivery_id):
		try:
			delivery = Delivery.objects.get(id=delivery_id)
			
			# Vérifier que c'est le livreur assigné
			if delivery.delivery_agent != request.user:
				return Response({
					'success': False,
					'error': 'Non autorisé - Vous n\'êtes pas le livreur de cette livraison'
				}, status=status.HTTP_403_FORBIDDEN)
			
			# Vérifier le statut (doit être in_transit ou picked_up)
			# Tolérance: accepter aussi 'accepted' pour éviter blocage avant démarrage.
			if delivery.status not in ['in_transit', 'picked_up', 'accepted']:
				return Response({
					'success': False,
					'error': f"Impossible d'uploader la preuve. Statut actuel: {delivery.get_status_display()}"
				}, status=status.HTTP_400_BAD_REQUEST)
			
			# Extraire les données
			id_card_photo = request.FILES.get('id_card_photo')  # OBLIGATOIRE
			package_photo = request.FILES.get('package_photo')   # OPTIONNELLE
			signature = request.FILES.get('signature')
			latitude = request.data.get('latitude')
			longitude = request.data.get('longitude')
			pin_code = request.data.get('pin_code')
			recipient_name = request.data.get('recipient_name', '')
			gps_accuracy = request.data.get('gps_accuracy')
			notes = request.data.get('notes', '')
			client_received_status_raw = request.data.get('client_received_status')
			client_received_status = str(client_received_status_raw).lower() in ['true', '1', 'yes', 'on'] if client_received_status_raw is not None else False
			
			# Préparer les données pour validation
			proof_data = {
				'id_card_photo': id_card_photo,  # OBLIGATOIRE
				'package_photo': package_photo,   # OPTIONNELLE
				'latitude': latitude,
				'longitude': longitude,
				'signature': signature,
				'pin_code': pin_code,
				'pin_verified': False,
				'client_received_status': client_received_status
			}
			
			# Valider la preuve
			is_valid, errors = validate_delivery_proof(delivery, proof_data)
			
			if not is_valid:
				return Response({
					'success': False,
					'error': {
						'code': 'invalid_proof',
						'message': 'Preuve de livraison invalide',
						'details': errors
					}
				}, status=status.HTTP_400_BAD_REQUEST)
			
			# Vérifier le PIN si fourni
			if pin_code:
				if pin_code.strip() == delivery.delivery_code.strip():
					delivery.code_verified = True
					proof_data['pin_verified'] = True
				else:
					return Response({
						'success': False,
						'error': {
							'code': 'invalid_pin',
							'message': 'Code PIN incorrect'
						}
					}, status=status.HTTP_400_BAD_REQUEST)
			
			# Enregistrer sur le modèle Delivery (rétrocompatibilité)
			delivery.proof_latitude = latitude
			delivery.proof_longitude = longitude
			
			if signature:
				delivery.client_signature = signature
			
			if recipient_name:
				delivery.client_name_confirmed = recipient_name
			
			delivery.save()
			
			# Créer ou mettre à jour DeliveryProof
			from delivery.models import DeliveryProof
			from core.validators import calculate_gps_distance
			import django.utils.timezone
			
			# Calculer la distance entre GPS de livraison et adresse client
			distance_from_address = None
			if delivery.delivery_lat and delivery.delivery_lng:
				distance_from_address = calculate_gps_distance(
					latitude, longitude,
					delivery.delivery_lat, delivery.delivery_lng
				)
			
			defaults_data = {
				'id_card_photo': id_card_photo,  # OBLIGATOIRE
				'latitude': latitude,
				'longitude': longitude,
				'gps_accuracy': gps_accuracy,
				'signature': signature,
				'pin_code': pin_code if pin_code else '',
				'pin_verified': delivery.code_verified,
				'recipient_name': recipient_name,
				'notes': notes,
				'distance_from_address': distance_from_address,
				'client_received_status': client_received_status,
				'status': 'verified' if (signature or delivery.code_verified) else 'pending'
			}
			
			# Photo colis optionnelle
			if package_photo:
				defaults_data['package_photo'] = package_photo
				defaults_data['package_photo_uploaded_at'] = django.utils.timezone.now()
			
			proof, created = DeliveryProof.objects.update_or_create(
				delivery=delivery,
				defaults=defaults_data
			)
			
			# Log audit
			AuditLog.log_action(
				action_type='delivery_proof_uploaded',
				user=request.user,
				object_type='delivery',
				object_id=delivery.id,
				old_value=None,
				new_value='proof_added',
				ip_address=get_client_ip(request),
				user_agent=request.META.get('HTTP_USER_AGENT', ''),
				reason=f'Proof uploaded: ID card photo, GPS({latitude},{longitude}), Distance: {distance_from_address}m, Client received: {client_received_status}'
			)
			
			return Response({
				'success': True,
				'message': 'Preuve de livraison enregistrée avec succès',
				'data': {
					'delivery_id': delivery.id,
					'proof_id': proof.id,
					'proof_status': proof.status,
					'has_photo': bool(proof.id_card_photo),
					'has_gps': bool(proof.latitude and proof.longitude),
					'has_signature': bool(proof.signature),
					'pin_verified': proof.pin_verified,
					'is_valid': proof.is_valid,
					'is_fully_confirmed': proof.is_fully_confirmed,
					'client_received_status': proof.client_received_status,
					'client_confirmation_pending': proof.client_confirmation_pending,
					'distance_from_address': float(distance_from_address) if distance_from_address else None,
					'location_valid': proof.is_location_valid,
					'can_complete_delivery': proof.is_valid
				}
			})
			
		except Delivery.DoesNotExist:
			return Response({
				'success': False,
				'error': 'Livraison non trouvée'
			}, status=status.HTTP_404_NOT_FOUND)
		except Exception as e:
			return Response({
				'success': False,
				'error': {
					'code': 'upload_error',
					'message': str(e)
				}
			}, status=status.HTTP_400_BAD_REQUEST)


class DeliveryVerifyPINView(APIView):
	"""
	Vérifier le code PIN de livraison
	Endpoint séparé pour permettre la vérification du PIN client
	"""
	permission_classes = [permissions.IsAuthenticated]
	
	def post(self, request, delivery_id):
		try:
			delivery = Delivery.objects.get(id=delivery_id)
			
			# Vérifier que c'est le livreur assigné
			if delivery.delivery_agent != request.user:
				return Response({
					'success': False,
					'error': 'Non autorisé'
				}, status=status.HTTP_403_FORBIDDEN)
			
			pin_code = request.data.get('pin_code', '').strip()
			
			if not pin_code:
				return Response({
					'success': False,
					'error': 'Code PIN requis'
				}, status=status.HTTP_400_BAD_REQUEST)
			
			# Vérifier le PIN
			if pin_code == delivery.delivery_code.strip():
				delivery.code_verified = True
				delivery.save()
				
				# Mettre à jour DeliveryProof si existe
				from delivery.models import DeliveryProof
				try:
					proof = DeliveryProof.objects.get(delivery=delivery)
					proof.pin_code = pin_code
					proof.pin_verified = True
					if proof.signature or proof.pin_verified:
						proof.status = 'verified'
					proof.save()
				except DeliveryProof.DoesNotExist:
					pass
				
				# Log audit
				AuditLog.log_action(
					action_type='delivery_pin_verified',
					user=request.user,
					object_type='delivery',
					object_id=delivery.id,
					old_value='unverified',
					new_value='verified',
					ip_address=get_client_ip(request),
					user_agent=request.META.get('HTTP_USER_AGENT', ''),
					reason='PIN code verified successfully'
				)
				
				return Response({
					'success': True,
					'message': 'Code PIN vérifié avec succès',
					'data': {
						'delivery_id': delivery.id,
						'pin_verified': True,
						'delivery_code': delivery.delivery_code
					}
				})
			else:
				# Log tentative échouée
				AuditLog.log_action(
					action_type='delivery_pin_failed',
					user=request.user,
					object_type='delivery',
					object_id=delivery.id,
					old_value='unverified',
					new_value='failed_attempt',
					ip_address=get_client_ip(request),
					user_agent=request.META.get('HTTP_USER_AGENT', ''),
					reason=f'Incorrect PIN attempt: {pin_code}',
					is_suspicious=True
				)
				
				return Response({
					'success': False,
					'error': {
						'code': 'invalid_pin',
						'message': 'Code PIN incorrect'
					}
				}, status=status.HTTP_400_BAD_REQUEST)
		
		except Delivery.DoesNotExist:
			return Response({
				'success': False,
				'error': 'Livraison non trouvée'
			}, status=status.HTTP_404_NOT_FOUND)


class DeliveryStartView(APIView):
	"""Le livreur démarre une livraison acceptée"""
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request, delivery_id):
		try:
			delivery = Delivery.objects.get(id=delivery_id)
			
			# Vérifier que le livreur démarre sa propre livraison
			if delivery.delivery_agent != request.user:
				AuditLog.log_action(
					action_type='delivery_status_change_rejected',
					user=request.user,
					user_role=request.user.get_user_type_display() if hasattr(request.user, 'get_user_type_display') else 'unknown',
					object_type='delivery',
					object_id=delivery_id,
					old_value=delivery.status,
					new_value='in_transit',
					ip_address=get_client_ip(request),
					user_agent=request.META.get('HTTP_USER_AGENT', ''),
					reason='Unauthorized user attempted to start delivery',
					is_suspicious=True
				)
				return Response({
					'success': False,
					'error': 'Vous ne pouvez démarrer que vos propres livraisons'
				}, status=status.HTTP_403_FORBIDDEN)
			
			# Vérifier que la transition de statut est valide
			# Le livreur doit d'abord passer par 'picked_up' avant 'in_transit'
			next_status = 'picked_up' if delivery.status == 'accepted' else 'in_transit'
			
			is_valid, error_msg = can_user_change_delivery_status(request.user, delivery.status, next_status)
			if not is_valid:
				AuditLog.log_action(
					action_type='delivery_status_change_rejected',
					user=request.user,
					user_role=request.user.get_user_type_display() if hasattr(request.user, 'get_user_type_display') else 'unknown',
					object_type='delivery',
					object_id=delivery_id,
					old_value=delivery.status,
					new_value=next_status,
					ip_address=get_client_ip(request),
					user_agent=request.META.get('HTTP_USER_AGENT', ''),
					reason=error_msg,
					is_suspicious=True
				)
				return Response({
					'success': False,
					'error': error_msg
				}, status=status.HTTP_400_BAD_REQUEST)
			
			old_status = delivery.status
			old_order_status = delivery.order.status
			
			# Démarrer la livraison avec le bon statut
			if delivery.status == 'accepted':
				# Première étape: récupérer le colis
				delivery.status = 'picked_up'
				delivery.picked_up_at = timezone.now()
			else:
				# Étapes suivantes: en transit
				delivery.status = 'in_transit'
				if not delivery.picked_up_at:
					delivery.picked_up_at = timezone.now()
			
			delivery.save()
			
			# Mettre à jour la commande en conséquence
			if delivery.status == 'picked_up':
				delivery.order.status = 'preparing'  # Le colis est récupéré mais pas encore en route
			else:
				delivery.order.status = 'in_transit'
			delivery.order.save()
			
			# Message adapté selon le statut
			if delivery.status == 'picked_up':
				message = 'Colis récupéré avec succès. Cliquez à nouveau pour démarrer la livraison.'
			else:
				message = 'Livraison en cours'
			
			# Enregistrer l'action dans l'audit
			AuditLog.log_action(
				action_type='delivery_status_change',
				user=request.user,
				user_role=request.user.get_user_type_display() if hasattr(request.user, 'get_user_type_display') else 'unknown',
				object_type='delivery',
				object_id=delivery_id,
				old_value=old_status,
				new_value=delivery.status,
				ip_address=get_client_ip(request),
				user_agent=request.META.get('HTTP_USER_AGENT', ''),
				reason='Delivery agent updated delivery status'
			)
			
			return Response({
				'success': True,
				'message': message,
				'data': {
					'delivery_id': delivery.id,
					'order_id': delivery.order.id,
					'status': delivery.status,
					'status_display': delivery.get_status_display()
				}
			})
		
		except Delivery.DoesNotExist:
			return Response({
				'success': False,
				'error': 'Livraison non trouvée'
			}, status=status.HTTP_404_NOT_FOUND)
		except Exception as e:
			AuditLog.log_action(
				action_type='delivery_error',
				user=request.user,
				user_role=request.user.get_user_type_display() if hasattr(request.user, 'get_user_type_display') else 'unknown',
				object_type='delivery',
				object_id=delivery_id,
				old_value='unknown',
				new_value='error',
				ip_address=get_client_ip(request),
				user_agent=request.META.get('HTTP_USER_AGENT', ''),
				reason=f'Error during delivery start: {str(e)}',
				is_suspicious=True,
				notes=str(e)
			)
			return Response({
				'success': False,
				'error': str(e)
			}, status=status.HTTP_400_BAD_REQUEST)


class DeliveryCompleteView(APIView):
	"""
	Le livreur confirme la livraison avec preuve obligatoire
	Requiert: photo + GPS + signature/PIN
	"""
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request, delivery_id):
		try:
			delivery = Delivery.objects.get(id=delivery_id)
			
			# Vérifier que le livreur confirme sa propre livraison
			if delivery.delivery_agent != request.user:
				AuditLog.log_action(
					action_type='delivery_status_change_rejected',
					user=request.user,
					user_role=request.user.get_user_type_display() if hasattr(request.user, 'get_user_type_display') else 'unknown',
					object_type='delivery',
					object_id=delivery_id,
					old_value=delivery.status,
					new_value='delivered',
					ip_address=get_client_ip(request),
					user_agent=request.META.get('HTTP_USER_AGENT', ''),
					reason='Unauthorized user attempted to complete delivery',
					is_suspicious=True
				)
				return Response({
					'success': False,
					'error': 'Vous ne pouvez confirmer que vos propres livraisons'
				}, status=status.HTTP_403_FORBIDDEN)
			
			# Vérifier la preuve de livraison (OBLIGATOIRE)
			can_deliver, reason = can_mark_as_delivered(delivery)
			if not can_deliver:
				return Response({
					'success': False,
					'error': {
						'code': 'proof_required',
						'message': reason,
						'details': {
							'photo_required': not bool(delivery.delivery_proof_photo),
							'gps_required': not bool(delivery.proof_latitude and delivery.proof_longitude),
							'signature_or_pin_required': not bool(delivery.client_signature or delivery.code_verified)
						}
					}
				}, status=status.HTTP_400_BAD_REQUEST)
			
			# Vérifier que la transition de statut est valide
			is_valid, error_msg = can_user_change_delivery_status(request.user, delivery.status, 'delivered')
			if not is_valid:
				AuditLog.log_action(
					action_type='delivery_status_change_rejected',
					user=request.user,
					user_role=request.user.get_user_type_display() if hasattr(request.user, 'get_user_type_display') else 'unknown',
					object_type='delivery',
					object_id=delivery_id,
					old_value=delivery.status,
					new_value='delivered',
					ip_address=get_client_ip(request),
					user_agent=request.META.get('HTTP_USER_AGENT', ''),
					reason=error_msg,
					is_suspicious=True
				)
				return Response({
					'success': False,
					'error': error_msg
				}, status=status.HTTP_400_BAD_REQUEST)
			
			old_status = delivery.status
			old_order_status = delivery.order.status
			
			# Confirmer la livraison
			delivery.status = 'delivered'
			delivery.delivered_at = timezone.now()
			delivery.save()
			
			# Mettre à jour la commande
			delivery.order.status = 'delivered'
			delivery.order.save()
			
			# Enregistrer l'action dans l'audit
			AuditLog.log_action(
				action_type='delivery_status_change',
				user=request.user,
				user_role=request.user.get_user_type_display() if hasattr(request.user, 'get_user_type_display') else 'unknown',
				object_type='delivery',
				object_id=delivery_id,
				old_value=old_status,
				new_value=delivery.status,
				ip_address=get_client_ip(request),
				user_agent=request.META.get('HTTP_USER_AGENT', ''),
				reason=f'Delivery completed with proof: GPS({delivery.proof_latitude},{delivery.proof_longitude})'
			)
			
			# Enregistrer aussi la mise à jour de la commande
			AuditLog.log_action(
				action_type='order_status_change',
				user=request.user,
				user_role=request.user.get_user_type_display() if hasattr(request.user, 'get_user_type_display') else 'unknown',
				object_type='order',
				object_id=delivery.order.id,
				old_value=old_order_status,
				new_value=delivery.order.status,
				ip_address=get_client_ip(request),
				user_agent=request.META.get('HTTP_USER_AGENT', ''),
				reason='Order status updated when delivery completed'
			)
			
			# 🎉 PAYER LE LIVREUR VIA AIRTEL MONEY
			from payments.services import PaymentService
			payout_result = PaymentService.payout_delivery_agent(delivery)
			
			payment_status = 'success' if payout_result.get('success') else 'pending'
			payment_message = payout_result.get('message', payout_result.get('error', ''))
			
			return Response({
				'success': True,
				'message': 'Livraison confirmée avec succès',
				'data': {
					'delivery_id': delivery.id,
					'order_id': delivery.order.id,
					'status': delivery.status,
					'status_display': delivery.get_status_display(),
					'proof_verified': True,
					'delivered_at': delivery.delivered_at.isoformat() if delivery.delivered_at else None,
					'client_received_status': getattr(getattr(delivery, 'proof', None), 'client_received_status', False),
					'client_confirmation_pending': getattr(getattr(delivery, 'proof', None), 'client_confirmation_pending', False),
					'payout': {
						'status': payment_status,
						'amount': float(delivery.agent_commission),
						'message': payment_message,
						'transaction_id': payout_result.get('transaction_id')
					}
				}
			})
		
		except Delivery.DoesNotExist:
			return Response({
				'success': False,
				'error': 'Livraison non trouvée'
			}, status=status.HTTP_404_NOT_FOUND)
		except Exception as e:
			AuditLog.log_action(
				action_type='delivery_error',
				user=request.user,
				user_role=request.user.get_user_type_display() if hasattr(request.user, 'get_user_type_display') else 'unknown',
				object_type='delivery',
				object_id=delivery_id,
				old_value='unknown',
				new_value='error',
				ip_address=get_client_ip(request),
				user_agent=request.META.get('HTTP_USER_AGENT', ''),
				reason=f'Error during delivery completion: {str(e)}',
				is_suspicious=True,
				notes=str(e)
			)
			return Response({
				'success': False,
				'error': str(e)
			}, status=status.HTTP_400_BAD_REQUEST)