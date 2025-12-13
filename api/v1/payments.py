from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from decimal import Decimal

from payments.models import Payment
from payments.serializers import (
    PaymentSerializer, PaymentInitSerializer
)
from orders.models import Order
from core.models import AuditLog


class PaymentInitView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, order_id):
        try:
            # Vérifier que la commande appartient au client
            order = Order.objects.get(
                id=order_id,
                client=request.user,
            )

            if order.status not in ['created', 'pending_payment', 'paid']:
                return Response({
                    'success': False,
                    'error': {
                        'code': status.HTTP_400_BAD_REQUEST,
                        'message': 'Cette commande ne peut plus être payée.'
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = PaymentInitSerializer(data=request.data)
            
            if serializer.is_valid():
                payment_method = serializer.validated_data['payment_method']
                phone_number = serializer.validated_data.get('phone_number', '')
                operator = serializer.validated_data.get('operator')
                
                # Calcul des frais Mobile Money (3%)
                # Le client paie les frais
                order.payment_fees = Decimal('0.00')
                order.calculate_totals()

                if payment_method in ['airtel_money', 'moov_money']:
                    fees_rate = Decimal('0.03')  # 3% frais MoMo
                    fees = (order.total_amount * fees_rate).quantize(Decimal('0.01'))
                    order.payment_fees = fees
                    order.calculate_totals()
                else:
                    order.payment_fees = Decimal('0.00')
                    order.calculate_totals()

                # Générer une référence transaction interne
                base_tx_id = f"PAY-{order.order_number}"
                timestamp = timezone.now().strftime('%Y%m%d%H%M%S')

                existing_payment = Payment.objects.filter(order=order).first()

                if existing_payment and existing_payment.status == 'success':
                    payment = existing_payment
                    order.status = 'confirmed'
                    order.confirmed_at = timezone.now()
                    order.save(update_fields=['status', 'updated_at', 'confirmed_at'])
                else:
                    payment, created = Payment.objects.get_or_create(
                        order=order,
                        defaults={
                            'payment_method': payment_method,
                            'amount': order.total_amount,
                            'fees_amount': order.payment_fees,
                            'status': 'pending',
                            'client_phone': phone_number,
                            'transaction_id': f"{base_tx_id}-{timestamp}",
                            'operator_reference': (operator or '').upper() if operator else ''
                        }
                    )

                    if not created:
                        payment.payment_method = payment_method
                        payment.amount = order.total_amount
                        payment.fees_amount = order.payment_fees
                        payment.status = 'pending'
                        payment.client_phone = phone_number
                        payment.operator_reference = (operator or '').upper() if operator else ''
                        if not payment.transaction_id:
                            payment.transaction_id = f"{base_tx_id}-{timestamp}"
                        payment.save()
                    
                    # Log payment initiation
                    AuditLog.log_action(
                        action_type='payment_initiated',
                        user=request.user,
                        object_type='payment',
                        object_id=payment.id,
                        old_value=None,
                        new_value=payment_method,
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        reason=f'Initialisation paiement {payment_method} pour {order.order_number}'
                    )

                # Paiement cash = succès immédiat côté client
                if payment_method == 'cash':
                    payment.status = 'success'
                    payment.completed_at = timezone.now()
                    payment.save(update_fields=['status', 'completed_at', 'updated_at'])
                    order.status = 'confirmed'
                    order.confirmed_at = timezone.now()
                    order.save(update_fields=['status', 'updated_at', 'confirmed_at'])
                    
                    # Log cash payment completion
                    AuditLog.log_action(
                        action_type='payment_completed',
                        user=request.user,
                        object_type='payment',
                        object_id=payment.id,
                        old_value='pending',
                        new_value='success',
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                        reason=f'Paiement cash pour commande {order.order_number}'
                    )
                else:
                    # Mettre la commande en attente de paiement pour les autres méthodes
                    if order.status != 'pending_payment':
                        order.status = 'pending_payment'
                        order.save(update_fields=['status', 'updated_at'])
                
                return Response({
                    'success': True,
                    'message': 'Paiement déjà confirmé.' if payment.status == 'success' else 'Paiement initialisé.',
                    'data': {
                        'payment': PaymentSerializer(payment).data,
                        'next_steps': {
                            'mobile_money': 'Un prompt de paiement sera affiché sur votre mobile.',
                            'card': 'Redirection vers la page de paiement par carte.'
                        }
                    }
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
                    'message': 'Commande non trouvée ou déjà payée.'
                }
            }, status=status.HTTP_404_NOT_FOUND)


@method_decorator(csrf_exempt, name='dispatch')
class PaymentWebhookView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        # Webhook pour recevoir les confirmations de paiement
        # des opérateurs Mobile Money ou processeurs de carte
        
        transaction_id = request.data.get('transaction_id')
        payment_status = request.data.get('status')
        amount = request.data.get('amount')
        
        if not transaction_id:
            return Response({
                'success': False,
                'error': 'transaction_id manquant'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            payment = Payment.objects.get(transaction_id=transaction_id)
            
            if payment_status == 'success':
                payment.status = 'success'
                payment.completed_at = timezone.now()
                payment.save(update_fields=['status', 'completed_at', 'updated_at'])
                
                # Mettre à jour le statut de la commande
                payment.order.status = 'confirmed'
                payment.order.confirmed_at = timezone.now()
                payment.order.save(update_fields=['status', 'updated_at', 'confirmed_at'])
                
                # Log payment completion via webhook
                AuditLog.log_action(
                    action_type='payment_completed',
                    user=payment.order.client,
                    object_type='payment',
                    object_id=payment.id,
                    old_value='pending',
                    new_value='success',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    reason=f'Webhook confirmation: {transaction_id}'
                )
                
                # Notifier le magasin
                # notification_service.notify_store_new_order(payment.order)
                
                return Response({
                    'success': True,
                    'message': 'Paiement confirmé.'
                })
            else:
                payment.status = 'failed'
                payment.save(update_fields=['status', 'updated_at'])
                
                # Log payment failure
                AuditLog.log_action(
                    action_type='payment_failed',
                    user=payment.order.client,
                    object_type='payment',
                    object_id=payment.id,
                    old_value='pending',
                    new_value='failed',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    reason=f'Webhook échec: {transaction_id}',
                    is_suspicious=True
                )
                
                return Response({
                    'success': False,
                    'message': 'Paiement échoué.'
                })
        
        except Payment.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Paiement non trouvé'
            }, status=status.HTTP_404_NOT_FOUND)


class PaymentDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, order_id):
        try:
            # Vérifier les permissions
            if request.user.is_client():
                payment = Payment.objects.get(
                    order_id=order_id,
                    order__client=request.user
                )
            elif request.user.is_store_manager():
                payment = Payment.objects.get(
                    order_id=order_id,
                    order__store__manager=request.user
                )
            else:
                payment = Payment.objects.get(order_id=order_id)
            
            serializer = PaymentSerializer(payment)
            
            return Response({
                'success': True,
                'data': serializer.data
            })
        
        except Payment.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': status.HTTP_404_NOT_FOUND,
                    'message': 'Paiement non trouvé.'
                }
            }, status=status.HTTP_404_NOT_FOUND)


# ============================================================================
# FORFAIT / SUBSCRIPTION MANAGEMENT VIEWS
# ============================================================================

from payments.models import Forfait, ClientForfait, Payout
from payments.serializers import ForfaitSerializer, ClientForfaitSerializer, PayoutSerializer


class ForfaitListView(APIView):
	"""List all available forfaits/plans"""
	permission_classes = [permissions.AllowAny]
	
	def get(self, request):
		forfaits = Forfait.objects.filter(is_active=True)
		serializer = ForfaitSerializer(forfaits, many=True)
		return Response({
			'success': True,
			'data': serializer.data
		})


class ClientForfaitListView(APIView):
	"""Get user's current active forfait"""
	permission_classes = [permissions.IsAuthenticated]
	
	def get(self, request):
		try:
			client_forfait = ClientForfait.objects.get(user=request.user, status='active')
			serializer = ClientForfaitSerializer(client_forfait)
			return Response({
				'success': True,
				'data': serializer.data,
				'is_active': client_forfait.is_active()
			})
		except ClientForfait.DoesNotExist:
			return Response({
				'success': True,
				'data': None,
				'is_active': False,
				'message': 'Aucun forfait actif'
			})


class ClientForfaitUpdateView(APIView):
	"""Update/change user's forfait"""
	permission_classes = [permissions.IsAuthenticated]
	
	def patch(self, request):
		try:
			forfait_id = request.data.get('forfait_id')
			if not forfait_id:
				return Response({
					'success': False,
					'error': 'forfait_id is required'
				}, status=status.HTTP_400_BAD_REQUEST)
			
			forfait = Forfait.objects.get(id=forfait_id, is_active=True)
			
			# Deactivate current forfait if exists
			ClientForfait.objects.filter(
				user=request.user,
				status='active'
			).update(status='cancelled')
			
			# Create new forfait subscription
			from datetime import timedelta
			client_forfait = ClientForfait.objects.create(
				user=request.user,
				forfait=forfait,
				start_date=timezone.now().date(),
				expiry_date=timezone.now().date() + timedelta(days=30),
				status='active'
			)
			
			serializer = ClientForfaitSerializer(client_forfait)
			return Response({
				'success': True,
				'data': serializer.data,
				'message': f'Forfait {forfait.name} activé avec succès'
			}, status=status.HTTP_201_CREATED)
		
		except Forfait.DoesNotExist:
			return Response({
				'success': False,
				'error': 'Forfait not found'
			}, status=status.HTTP_404_NOT_FOUND)
		except Exception as e:
			return Response({
				'success': False,
				'error': str(e)
			}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PayoutListView(APIView):
	"""Get payouts for delivery agents and merchants"""
	permission_classes = [permissions.IsAuthenticated]
	
	def get(self, request):
		try:
			# Only users can see their own payouts
			payouts = Payout.objects.filter(user=request.user).order_by('-created_at')
			
			# Optional filters
			payout_type = request.query_params.get('type')
			status_filter = request.query_params.get('status')
			
			if payout_type:
				payouts = payouts.filter(payout_type=payout_type)
			if status_filter:
				payouts = payouts.filter(status=status_filter)
			
			serializer = PayoutSerializer(payouts, many=True)
			return Response({
				'success': True,
				'count': payouts.count(),
				'data': serializer.data
			})
		
		except Exception as e:
			return Response({
				'success': False,
				'error': str(e)
			}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
