"""API v1: orders endpoints."""

import logging
from django.db import transaction
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, RetrieveAPIView

from orders.models import Order
from orders.serializers import (
	with_order_display_relations,
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
		# Même panier renvoyé (réponse perdue, connexion coupée) : on rend la commande déjà créée.
		request_id = str(request.headers.get('Idempotency-Key') or '').strip()[:64]
		if request_id:
			existing = Order.objects.filter(client=request.user, client_request_id=request_id).first()
			if existing:
				return Response({
					'success': True,
					'message': 'Commande déjà créée.',
					'data': OrderSerializer(existing).data
				}, status=status.HTTP_200_OK)

		serializer = OrderCreateSerializer(
			data=request.data,
			context={'request': request}
		)
        
		if serializer.is_valid():
			from django.db import IntegrityError
			try:
				with transaction.atomic():
					order = serializer.save()
					if request_id:
						order.client_request_id = request_id
						order.save(update_fields=['client_request_id'])
			except IntegrityError:
				existing = Order.objects.filter(client=request.user, client_request_id=request_id).first() if request_id else None
				if existing is None:
					raise
				return Response({
					'success': True,
					'message': 'Commande déjà créée.',
					'data': OrderSerializer(existing).data
				}, status=status.HTTP_200_OK)
            
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
			queryset = Order.objects.filter(client=user)
		elif user.is_store_manager():
			queryset = Order.objects.filter(store__manager=user)
		elif user.is_delivery_agent():
			queryset = Order.objects.filter(delivery__delivery_agent=user)
		else:
			queryset = Order.objects.all()
		return with_order_display_relations(queryset)
    
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
			queryset = Order.objects.filter(client=user)
		elif user.is_store_manager():
			queryset = Order.objects.filter(store__manager=user)
		elif user.is_delivery_agent():
			queryset = Order.objects.filter(delivery__delivery_agent=user)
		else:
			queryset = Order.objects.all()
		return with_order_display_relations(queryset.order_by('-created_at'))
    
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
				partial=True,
				context={'request': request},
			)
			
			if serializer.is_valid():
				from payments.direct_service import store_delivers
				refusal = store_status_refusal(request.user, order, request.data.get('status'), request.data.get('pin_code'))
				if refusal:
					http_status = refusal.pop('http', status.HTTP_409_CONFLICT)
					return Response({'success': False, 'error': refusal}, status=http_status)
				if request.data.get('status') == 'in_transit' and order.status == 'ready' and not store_delivers(order):
					return Response({'success': False, 'error': {
						'code': 409,
						'message': 'Un livreur Gaboshop doit d’abord prendre cette commande.',
						'reason': 'Cette commande est livrée par un livreur Gaboshop, pas par le commerce.',
						'next_step': 'Attendez qu’un livreur accepte la course : il passera la chercher.',
					}}, status=status.HTTP_409_CONFLICT)
				if request.data.get('status') == 'ready':
					from payments.direct_service import can_dispatch
					if not can_dispatch(order):
						return Response({'success': False, 'error': {'code': 409, 'message': 'Le paiement requis avant expédition n’est pas confirmé.'}}, status=status.HTTP_409_CONFLICT)
				serializer.save()
				order.refresh_from_db()

				# Auto-assigner dès que le statut passe à "ready" (sauf si le commerce livre lui-même)
				if order.status == 'ready' and not getattr(getattr(order, 'payment_arrangement', None), 'delivery_method', '') == 'store':
					try:
						auto_assign_delivery(order)
					except Exception as assign_err:
						logger.error(f"? Auto-assignation livreur échouée pour {order.order_number}: {assign_err}")
				
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


def _client_has_paid(order):
	"""Le client a payé : paiement en ligne réussi, ou paiement des articles confirmé (Mobile Money au commerce).
	Lit les relations déjà chargées par la liste des commandes (pas de requête par commande)."""
	from django.core.exceptions import ObjectDoesNotExist
	try:
		if order.payment.status in ('success', 'completed'):
			return True
	except ObjectDoesNotExist:
		pass
	arrangement = getattr(order, 'payment_arrangement', None)
	if arrangement is None:
		return False
	from payments.direct_service import _refresh_status
	products = next((o for o in arrangement.obligations.all() if o.kind == 'products'), None)
	return bool(products and _refresh_status(products) == 'paid')


def _store_payout_started(order):
	"""La part du commerce est déjà partie (ou en cours d'envoi) : annuler ferait payer Gaboshop deux fois."""
	payout = getattr(order, 'store_payout', None)
	try:
		return bool(payout and payout.status in ('processing', 'paid'))
	except Exception:
		return False


def store_can_cancel(order):
	"""Le commerce peut-il annuler ? Non dès que le client a payé ou que le commerce a été payé :
	seul l'administrateur annule alors, et rembourse le client."""
	if order.status in ('delivered', 'cancelled', 'refunded'):
		return False
	return not (_client_has_paid(order) or _store_payout_started(order))


def store_status_refusal(user, order, new_status, pin_code=None):
	"""Règles du commerce sur sa commande, communes à l'écran « Commandes » et à l'assistant IA.
	Renvoie None si le changement est permis, sinon le message d'erreur (avec raison et solution)."""
	if not user.is_store_manager():
		return None
	from payments.direct_service import store_delivers
	# La course d'un livreur Gaboshop (assignée, en route, livrée) avance par le livreur, pas par le commerce :
	# sinon une commande pourrait être « livrée » sans livreur, sans code PIN ni preuve.
	if new_status in ('assigned', 'in_transit', 'delivered') and not store_delivers(order):
		return {
			'code': 409,
			'message': 'Cette étape est faite par le livreur Gaboshop.',
			'reason': 'La commande est livrée par un livreur Gaboshop : c’est lui qui la prend, la transporte et la remet au client.',
			'next_step': 'Passez la commande à « Prête » : un livreur viendra la chercher.',
		}
	if new_status == 'cancelled' and not store_can_cancel(order):
		return {
			'code': 409,
			'message': 'Cette commande est déjà payée : vous ne pouvez plus l’annuler vous-même.',
			'reason': 'Le client a payé (ou votre part vous a été versée). Annuler sans remboursement serait une fraude.',
			'next_step': 'En cas de problème, contactez Gaboshop : seul l’administrateur peut annuler et rembourser le client.',
		}
	if new_status == 'delivered':
		# Le commerce qui livre lui-même prouve la remise avec le code PIN du client (comme un livreur).
		delivery = getattr(order, 'delivery', None)
		if delivery is None or not delivery.delivery_code:
			return {'code': 409, 'message': 'Le client confirme lui-même la réception dans son application.'}
		from delivery import pin_guard
		if pin_guard.is_locked(delivery):
			return {'code': 429, 'http': status.HTTP_429_TOO_MANY_REQUESTS, 'message': pin_guard.locked_message()}
		if not pin_code or str(pin_code).strip() != delivery.delivery_code.strip():
			if pin_code:
				pin_guard.record_failure(delivery)
			return {
				'code': 400, 'http': status.HTTP_400_BAD_REQUEST,
				'message': 'Code PIN du client manquant ou incorrect.',
				'reason': 'Une commande n’est « livrée » qu’avec le code PIN que le client reçoit.',
				'next_step': 'Demandez le code au client, ou laissez-le confirmer la réception dans son application.',
			}
		pin_guard.reset(delivery)
		delivery.code_verified = True
		delivery.save(update_fields=['code_verified'])
	return None


def _pay_store_after_confirmation(order):
	"""Réception confirmée : la part du commerce (non « de confiance ») peut maintenant lui être versée."""
	from payments.store_payout_service import payout_moment_reached, schedule_store_payment
	if payout_moment_reached(order, 'client_confirmed'):
		schedule_store_payment(order.pk)


def _rate_delivery_agent(delivery, rating, comment):
	"""Enregistre la note du client et met à jour la note moyenne du livreur."""
	from django.db.models import Avg
	from delivery.models import Delivery, DeliveryProfile
	from users.models import LivreurProfile
	delivery.rating = rating
	delivery.customer_feedback = comment
	delivery.save(update_fields=['rating', 'customer_feedback'])
	average = Delivery.objects.filter(delivery_agent_id=delivery.delivery_agent_id, rating__isnull=False).aggregate(v=Avg('rating'))['v'] or 0
	average = round(average, 2)
	DeliveryProfile.objects.filter(user_id=delivery.delivery_agent_id).update(average_rating=average)
	LivreurProfile.objects.filter(user_id=delivery.delivery_agent_id).update(note_moyenne=average)


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
			
			# Option « tout au commerce » : le commerce livre lui-même, sans livreur ni preuve Gaboshop.
			# Le client confirme simplement la réception.
			arrangement = getattr(order, 'payment_arrangement', None)
			if arrangement is not None and arrangement.delivery_method == 'store' and order.status in ('ready', 'in_transit', 'delivered'):
				if order.status != 'delivered':
					order.status = 'delivered'
					order.delivered_at = timezone.now()
					order.save(update_fields=['status', 'delivered_at', 'updated_at'])
				_pay_store_after_confirmation(order)
				return Response({
					'success': True,
					'message': 'Réception confirmée. Merci !',
					'data': {'order_id': order.id, 'client_received_status': True, 'already_confirmed': False},
				})

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
				# Ancienne preuve marquée « reçue » par le livreur : on s'assure que les versements sont partis (idempotent).
				_pay_store_after_confirmation(order)
				from payments.direct_service import is_manual_order
				if not is_manual_order(order) and order.delivery.delivery_agent_id:
					from payments.services import PaymentService
					PaymentService.payout_delivery_agent(order.delivery)
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
			_pay_store_after_confirmation(order)

			# Note du livreur (facultative) donnée par le client à la confirmation.
			try:
				rating = int(request.data.get('rating') or 0)
			except (TypeError, ValueError):
				rating = 0
			if 1 <= rating <= 5 and order.delivery.delivery_agent_id:
				_rate_delivery_agent(order.delivery, rating, str(request.data.get('comment') or '')[:500])

			# Le client confirme : le livreur reçoit sa part du paiement en ligne.
			from payments.direct_service import is_manual_order
			if not is_manual_order(order) and order.delivery.delivery_agent_id:
				from payments.services import PaymentService
				PaymentService.payout_delivery_agent(order.delivery)
			
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
			AuditLog.log_action(
				'delivery_status_change', request.user, 'delivery', order.delivery.id,
				new_value='client_confirmed',
				ip_address=request.META.get('REMOTE_ADDR'),
				user_agent=request.META.get('HTTP_USER_AGENT', ''),
				reason=f'Réception confirmée par le client (commande {order.order_number}, PIN {"vérifié" if pin_code else "non saisi"})',
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


class ClientReportProblemView(APIView):
	"""POST /api/v1/orders/<id>/report-problem/ : le client signale un problème sur une commande livrée.

	Le versement automatique (48 h sans confirmation) est suspendu et l'admin est prévenu.
	"""
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request, order_id):
		order = Order.objects.filter(id=order_id, client=request.user).first()
		if order is None:
			return Response({'success': False, 'error': {'code': 404, 'message': 'Commande non trouvée.'}}, status=status.HTTP_404_NOT_FOUND)
		problem = str(request.data.get('problem') or '').strip()[:1000]
		if not problem:
			return Response({'success': False, 'error': {'code': 400, 'message': 'Décrivez le problème en quelques mots.'}}, status=status.HTTP_400_BAD_REQUEST)
		if order.status not in ('in_transit', 'delivered'):
			return Response({'success': False, 'error': {
				'code': 400, 'message': 'Un problème se signale une fois la commande livrée.',
				'next_step': 'Avant la livraison, contactez le commerce ou demandez à l’assistant.',
			}}, status=status.HTTP_400_BAD_REQUEST)
		order.client_problem = problem
		order.client_problem_reported_at = timezone.now()
		order.save(update_fields=['client_problem', 'client_problem_reported_at', 'updated_at'])
		for admin in User.objects.filter(is_active=True).filter(user_type='admin'):
			Notification.objects.create(
				user=admin, title=f'Problème signalé : commande {order.order_number}',
				body=f'{order.store.name} — {problem}', notif_type='warning',
				metadata={'order_id': order.id, 'action': 'client_problem'},
			)
		from core.models import AuditLog
		AuditLog.log_action(
			'order_status_change', request.user, 'order', order.id, new_value='client_problem',
			ip_address=request.META.get('REMOTE_ADDR'), user_agent=request.META.get('HTTP_USER_AGENT', ''),
			reason=f'Problème signalé par le client : {problem}',
		)
		return Response({'success': True, 'message': 'Problème transmis à Gaboshop. Le paiement du commerce est suspendu le temps de vérifier.'})


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
