from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.conf import settings
from django.db import transaction as db_transaction
from decimal import Decimal

from payments.models import Payment
from payments.services import PaymentService
from payments.serializers import (
    PaymentSerializer, PaymentInitSerializer
)
from orders.models import Order
from core.models import AuditLog
from api.models import SystemSettings
from payments.utils import verify_hmac_signature


def _webhook_amount(payload, transaction_payload, status_payload):
    """Return the provider amount from the known SingPay payload shapes."""
    transaction_payload = transaction_payload if isinstance(transaction_payload, dict) else {}
    status_payload = status_payload if isinstance(status_payload, dict) else {}
    candidates = (
        payload.get('amount'),
        transaction_payload.get('amount'),
        status_payload.get('amount'),
    )
    return next((value for value in candidates if value is not None), None)


class PaymentInitView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @staticmethod
    def _get_mobile_money_fee_rate(payment_method):
        """
        Retourne le taux de frais mobile money (%) depuis les paramÃ¨tres systÃ¨me.
        """
        settings = SystemSettings.get_settings()
        if payment_method == 'airtel_money':
            return Decimal(str(settings.airtel_money_fee or 0))
        if payment_method == 'moov_money':
            return Decimal(str(settings.moov_money_fee or 0))
        return Decimal('0.00')

    @staticmethod
    def _build_payment_init_failure_message(details):
        lowered = str(details or '').lower()
        config_markers = (
            'config',
            'wallet not accepted',
            'wallet en pending',
            'singpay_client_id',
            'singpay_client_secret',
            'singpay_wallet_id',
        )
        if any(marker in lowered for marker in config_markers):
            return 'Echec d initialisation du paiement mobile. Verifiez la configuration SingPay puis reessayez.'
        if 'timeout' in lowered or 'expire' in lowered or 'prompt' in lowered:
            return 'Paiement mobile expire. Verifiez le telephone du client, le solde et la validation du prompt, puis relancez.'
        return 'Paiement mobile non confirme par l operateur. Consultez le detail puis reessayez.'
    
    def post(self, request, order_id):
        try:
            # VÃ©rifier que la commande appartient au client
            order = Order.objects.get(
                id=order_id,
                client=request.user,
            )

            if order.status not in ['created', 'pending_payment', 'paid']:
                return Response({
                    'success': False,
                    'error': {
                        'code': status.HTTP_400_BAD_REQUEST,
                        'message': 'Cette commande ne peut plus Ãªtre payÃ©e.'
                    }
                }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = PaymentInitSerializer(data=request.data)
            
            if serializer.is_valid():
                payment_method = serializer.validated_data['payment_method']
                phone_number = serializer.validated_data.get('phone_number', '')
                operator = serializer.validated_data.get('operator')

                if payment_method not in ['airtel_money', 'moov_money']:
                    return Response({
                        'success': False,
                        'error': {
                            'code': status.HTTP_400_BAD_REQUEST,
                            'message': 'Seuls les paiements Mobile Money (Airtel/Moov) sont autorisÃ©s.'
                        }
                    }, status=status.HTTP_400_BAD_REQUEST)

                # Normaliser le numÃ©ro payeur et appliquer les frais rÃ©els selon l'opÃ©rateur
                formatted_phone = PaymentService._format_gabon_phone(phone_number, operator)
                real_fee_rate = self._get_mobile_money_fee_rate(payment_method)
                order.payment_fees = Decimal('0.00')
                order.calculate_totals(operator=operator, payment_method='mobile_money')
                total_mobile_money_fees = (
                    (order.items_total + order.delivery_fee) * real_fee_rate / Decimal('100')
                ).quantize(Decimal('0.01'))
                order.operator_fee = total_mobile_money_fees
                order.total_amount = (
                    order.items_total + order.delivery_fee + order.operator_fee + order.tax_amount + order.payment_fees
                )
                order.save(update_fields=['payment_fees', 'operator_fee', 'total_amount', 'updated_at'])

                # GÃ©nÃ©rer une rÃ©fÃ©rence transaction interne
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
                            'fees_amount': order.operator_fee + order.payment_fees,
                            'status': 'pending',
                            'client_phone': formatted_phone,
                            'client_name': request.user.get_full_name() or request.user.username,
                            'transaction_id': f"{base_tx_id}-{timestamp}",
                            'operator_reference': (operator or '').upper() if operator else ''
                        }
                    )

                    if not created:
                        payment.payment_method = payment_method
                        payment.amount = order.total_amount
                        payment.fees_amount = order.operator_fee + order.payment_fees
                        payment.status = 'pending'
                        payment.client_phone = formatted_phone
                        payment.client_name = request.user.get_full_name() or request.user.username
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

                next_steps = {
                    'mobile_money': 'Un prompt de paiement sera affiche sur votre mobile.',
                    'card': 'Redirection vers la page de paiement par carte.'
                }

                # Init Mobile Money via SingPay
                if payment_method in ['airtel_money', 'moov_money']:
                    try:
                        api_result = PaymentService._call_operator_api(
                            operator, formatted_phone, order.total_amount, order
                        )
                        payment.transaction_id = api_result.get('transaction_id', payment.transaction_id)
                        payment.operator_reference = api_result.get('operator_reference', payment.operator_reference)
                        payment.save(update_fields=['transaction_id', 'operator_reference', 'updated_at'])
                        next_steps = api_result.get('next_steps', next_steps)
                    except Exception as e:
                        details = str(e)
                        payment.status = 'failed'
                        payment.webhook_data = {
                            **(payment.webhook_data or {}),
                            'singpay_init_error': {
                                'message': details,
                                'at': timezone.now().isoformat(),
                            },
                        }
                        payment.save(update_fields=['status', 'webhook_data', 'updated_at'])
                        return Response({
                            'success': False,
                            'error': {
                                'code': status.HTTP_502_BAD_GATEWAY,
                                'message': self._build_payment_init_failure_message(details),
                                'details': details,
                            }
                        }, status=status.HTTP_502_BAD_GATEWAY)

                # Paiement cash = succÃ¨s immÃ©diat cÃ´tÃ© client
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
                    # Mettre la commande en attente de paiement pour les autres mÃ©thodes
                    if order.status != 'pending_payment':
                        order.status = 'pending_payment'
                        order.save(update_fields=['status', 'updated_at'])
                
                return Response({
                    'success': True,
                    'message': 'Paiement dÃ©jÃ  confirmÃ©.' if payment.status == 'success' else 'Paiement initialisÃ©.',
                    'data': {
                        'payment': PaymentSerializer(payment).data,
                        'next_steps': next_steps,
                        'payer_phone': formatted_phone,
                        'applied_fee_rate_percent': str(real_fee_rate),
                        'applied_fee_amount': str(order.operator_fee + order.payment_fees)
                    }
                })
            
            return Response({
                'success': False,
                'error': {
                    'code': status.HTTP_400_BAD_REQUEST,
                    'message': 'DonnÃ©es invalides.',
                    'details': serializer.errors
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Order.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': status.HTTP_404_NOT_FOUND,
                    'message': 'Commande non trouvÃ©e ou dÃ©jÃ  payÃ©e.'
                }
            }, status=status.HTTP_404_NOT_FOUND)


@method_decorator(csrf_exempt, name='dispatch')
class PaymentWebhookView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        # Webhook pour recevoir les confirmations de paiement
        # des operateurs Mobile Money ou processeurs de carte

        webhook_secret = getattr(settings, 'PAYMENT_WEBHOOK_SECRET', '')
        signature = (
            request.headers.get('X-Webhook-Signature')
            or request.headers.get('X-Signature')
            or request.headers.get('X-SingPay-Signature')
        )
        signature_required = getattr(
            settings, 'PAYMENT_WEBHOOK_SIGNATURE_REQUIRED', not settings.DEBUG
        )
        if signature_required and not webhook_secret:
            return Response(
                {'success': False, 'error': 'Webhook de paiement non configure'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if webhook_secret and (
            not signature or not verify_hmac_signature(request.body, signature, webhook_secret)
        ):
            return Response(
                {'success': False, 'error': 'Signature webhook invalide'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        payload = request.data
        singpay_payload = payload.get('paymentResult') or payload.get('paiementResult')
        if singpay_payload:
            transaction = singpay_payload.get('transaction') or {}
            status_payload = singpay_payload.get('status') or {}
        else:
            transaction = payload.get('transaction') or {}
            raw_status_payload = payload.get('status')
            status_payload = raw_status_payload if isinstance(raw_status_payload, dict) else {}

        transaction_id = (
            payload.get('transaction_id')
            or transaction.get('airtel_money_id')
            or transaction.get('id')
            or transaction.get('_id')
            or transaction.get('transaction_id')
        )
        payment_status = (
            payload.get('status')
            or status_payload.get('code')
            or status_payload.get('result_code')
            or status_payload.get('message')
            or transaction.get('result')
        )
        amount = _webhook_amount(payload, transaction, status_payload)
        status_payload = status_payload or payload.get('status_payload') or {}
        if not isinstance(status_payload, dict):
            status_payload = {}
        reference = transaction.get('reference') or payload.get('reference')

        if not transaction_id:
            if reference and str(reference).startswith("GABOSHOP_"):
                order_number = str(reference).replace("GABOSHOP_", "").strip()
                order = Order.objects.filter(order_number=order_number).first()
                if order and hasattr(order, "payment"):
                    transaction_id = order.payment.transaction_id
            if not transaction_id:
                return Response({
                    'success': False,
                    'error': 'transaction_id manquant'
                }, status=status.HTTP_400_BAD_REQUEST)

        try:
            with db_transaction.atomic():
                payment = Payment.objects.select_for_update().select_related('order').get(
                    transaction_id=transaction_id
                )

                if amount is None:
                    return Response(
                        {'success': False, 'error': 'Montant webhook manquant'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                try:
                    received_amount = Decimal(str(amount)).quantize(Decimal('0.01'))
                    expected_amount = payment.amount.quantize(Decimal('0.01'))
                except Exception:
                    return Response(
                        {'success': False, 'error': 'Montant webhook invalide'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if received_amount != expected_amount:
                    return Response(
                        {'success': False, 'error': 'Montant webhook incorrect'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                normalized_status = str(payment_status).upper()
                normalized_result = str(transaction.get('result') or '').upper()
                status_step = str(transaction.get('status') or '').upper()
                is_success = (
                    normalized_status in ('SUCCESS', 'OK', 'APPROVED', 'COMPLETED', 'TS', '00')
                    or status_payload.get('success') is True
                    or normalized_result == 'SUCCESS'
                    or str(status_payload.get('code') or status_payload.get('result_code') or '').upper() in ('00', '201', 'SUCCESS', 'OK')
                )

                if payment.status == 'success':
                    return Response({'success': True, 'message': 'Paiement deja confirme.'})

                payment.webhook_data = payload
                payment.save(update_fields=['webhook_data', 'updated_at'])

                if is_success:
                    payment.status = 'success'
                    payment.completed_at = timezone.now()
                    payment.save(update_fields=['status', 'completed_at', 'updated_at'])

                    payment.order.status = 'confirmed'
                    payment.order.confirmed_at = timezone.now()
                    payment.order.save(update_fields=['status', 'updated_at', 'confirmed_at'])

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
                    return Response({'success': True, 'message': 'Paiement confirme.'})

                if status_step in ('START', 'PARTENAIRE'):
                    payment.status = 'processing'
                    payment.save(update_fields=['status', 'updated_at'])
                    return Response({'success': True, 'message': 'Paiement en cours.'})

                payment.status = 'failed'
                payment.save(update_fields=['status', 'updated_at'])
                AuditLog.log_action(
                    action_type='payment_failed',
                    user=payment.order.client,
                    object_type='payment',
                    object_id=payment.id,
                    old_value='pending',
                    new_value='failed',
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    reason=f'Webhook echec: {transaction_id}',
                    is_suspicious=True
                )
                return Response({'success': False, 'message': 'Paiement echoue.'})

        except Payment.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Paiement non trouve'
            }, status=status.HTTP_404_NOT_FOUND)
class PaymentDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, order_id):
        try:
            # VÃ©rifier les permissions
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
            elif request.user.is_superuser or getattr(request.user, 'user_type', '') == 'admin':
                payment = Payment.objects.get(order_id=order_id)
            else:
                payment = Payment.objects.get(order_id=order_id, order__delivery__delivery_agent=request.user)
            
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
                    'message': 'Paiement non trouvÃ©.'
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
				'message': f'Forfait {forfait.name} activÃ© avec succÃ¨s'
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

