from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.conf import settings
from django.db import transaction as db_transaction
from decimal import Decimal
import logging

from payments.models import Payment
from payments.services import PaymentService
from payments.serializers import (
    PaymentSerializer, PaymentInitSerializer
)
from orders.models import Order
from core.models import AuditLog
from api.models import SystemSettings
from payments.utils import verify_hmac_signature
from payments.references import next_reference, order_number_from_reference
from notifications.messages import payment_failed_for_client
from notifications.service import NotificationService
from payments.online_verification import (
    check_allowed, find_order_payment, mark_order_payment_success, verify_order_payment,
)

logger = logging.getLogger(__name__)


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
            return "La demande de paiement n'a pas pu partir : le paiement en ligne de Gaboshop est mal réglé."
        if 'timeout' in lowered or 'expire' in lowered or 'prompt' in lowered:
            return "La demande de paiement a expiré avant d'être validée."
        return "L'opérateur Mobile Money n'a pas accepté la demande de paiement."
    
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
                try:
                    formatted_phone = PaymentService._format_gabon_phone(phone_number, operator)
                except ValueError as exc:
                    return Response({
                        'success': False,
                        'error': {'code': status.HTTP_400_BAD_REQUEST, 'message': str(exc)},
                    }, status=status.HTTP_400_BAD_REQUEST)
                # Un essai précédent a pu aboutir (le client a validé malgré une erreur affichée) :
                # SingPay est interrogé avant toute nouvelle demande, pour ne jamais faire payer deux fois.
                previous = Payment.objects.filter(order=order).first()
                if previous and previous.status not in ('success', 'refunded'):
                    try:
                        verify_order_payment(
                            previous, 'avant un nouvel essai', user=request.user,
                            ip_address=request.META.get('REMOTE_ADDR'),
                        )
                    except Exception:
                        logger.exception('Verification SingPay avant nouvel essai impossible (%s)', order.order_number)
                    previous.refresh_from_db()
                    if previous.status == 'success':
                        return Response({
                            'success': True,
                            'message': 'Paiement déjà confirmé.',
                            'data': {'payment': PaymentSerializer(previous).data},
                        })

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

                created = False
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
                    # Une référence neuve par essai : SingPay refuse une référence déjà utilisée.
                    reference = next_reference(payment, first_attempt=created)
                    payment.save(update_fields=['webhook_data', 'updated_at'])
                    try:
                        api_result = PaymentService._call_operator_api(
                            operator, formatted_phone, order.total_amount, order, reference=reference
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
                                'reference': reference,
                                'at': timezone.now().isoformat(),
                            },
                        }
                        payment.save(update_fields=['status', 'webhook_data', 'updated_at'])
                        failure = payment_failed_for_client(order, payment, details)
                        NotificationService.notify_payment_failed(order, payment, details)
                        return Response({
                            'success': False,
                            'error': {
                                'code': status.HTTP_502_BAD_GATEWAY,
                                'message': self._build_payment_init_failure_message(details),
                                'details': details,
                                'reason': failure['reason'],
                                'next_step': failure['next_step'],
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
        # Webhook pour recevoir les confirmations de paiement.
        # - Notification signée (HMAC, PAYMENT_WEBHOOK_SECRET) : son contenu fait foi.
        # - Notification non signée (SingPay ne signe pas) : simple signal, le statut est
        #   redemandé à SingPay par notre serveur et seule sa réponse compte.

        webhook_secret = getattr(settings, 'PAYMENT_WEBHOOK_SECRET', '')
        signature = (
            request.headers.get('X-Webhook-Signature')
            or request.headers.get('X-Signature')
            or request.headers.get('X-SingPay-Signature')
        )
        signature_required = getattr(
            settings, 'PAYMENT_WEBHOOK_SIGNATURE_REQUIRED', not settings.DEBUG
        )
        signed = bool(
            webhook_secret and signature and verify_hmac_signature(request.body, signature, webhook_secret)
        )
        # En développement sans secret, les notifications de test restent acceptées telles quelles.
        trusted = signed or (not signature_required and not webhook_secret)

        payload = request.data if isinstance(request.data, dict) else {}
        singpay_payload = payload.get('paymentResult') or payload.get('paiementResult')
        if singpay_payload:
            transaction = singpay_payload.get('transaction') or {}
            status_payload = singpay_payload.get('status') or {}
        else:
            transaction = payload.get('transaction') or {}
            raw_status_payload = payload.get('status')
            status_payload = raw_status_payload if isinstance(raw_status_payload, dict) else {}
        if not isinstance(transaction, dict):
            transaction = {}

        transaction_id = (
            payload.get('transaction_id')
            or transaction.get('airtel_money_id')
            or transaction.get('id')
            or transaction.get('_id')
            or transaction.get('transaction_id')
        )
        reference = transaction.get('reference') or payload.get('reference')

        if not trusted:
            return self._verify_with_singpay(request, payload, transaction, reference)

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

        if not transaction_id:
            order_number = order_number_from_reference(reference)
            if order_number:
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

                # Les références des essais restent notées à côté de la notification.
                payment.webhook_data = {**(payment.webhook_data or {}), 'last_webhook': payload}
                if is_success and reference:
                    payment.webhook_data['singpay_paid_reference'] = str(reference)
                payment.save(update_fields=['webhook_data', 'updated_at'])

                if is_success:
                    mark_order_payment_success(
                        payment,
                        f'Webhook confirmation: {transaction_id}',
                        ip_address=request.META.get('REMOTE_ADDR'),
                        user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    )
                    return Response({'success': True, 'message': 'Paiement confirme.'})

                if status_step in ('START', 'PARTENAIRE'):
                    payment.status = 'processing'
                    payment.save(update_fields=['status', 'updated_at'])
                    return Response({'success': True, 'message': 'Paiement en cours.'})

                newly_failed = payment.status != 'failed'
                payment.status = 'failed'
                payment.save(update_fields=['status', 'updated_at'])
                if newly_failed:
                    failed_payment = payment
                    db_transaction.on_commit(lambda: NotificationService.notify_payment_failed(
                        failed_payment.order, failed_payment, transaction or payload,
                    ))
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

    def _verify_with_singpay(self, request, payload, transaction, reference):
        """Notification non signée : on retrouve le paiement puis on interroge SingPay."""
        transaction_ids = [
            payload.get('transaction_id'),
            transaction.get('airtel_money_id'),
            transaction.get('id'),
            transaction.get('_id'),
            transaction.get('transaction_id'),
        ]
        payment = find_order_payment(transaction_ids, reference)
        if payment is None:
            # Paiement d'abonnement : même vérification auprès de SingPay.
            from payments.views import verify_singpay_notification
            return verify_singpay_notification(payload)
        if not check_allowed(f'payment:{payment.pk}'):
            return Response(
                {'success': True, 'message': 'Verification deja en cours.'},
                status=status.HTTP_202_ACCEPTED,
            )
        new_status = verify_order_payment(
            payment, 'notification', ip_address=request.META.get('REMOTE_ADDR')
        )
        return Response({'success': True, 'data': {'status': new_status}})


class PaymentVerifyView(APIView):
    """POST /orders/<order_id>/payments/verify/ : redemande à SingPay où en est le paiement en ligne.

    Utile quand la notification de SingPay tarde ou se perd : le client (ou le commerce, ou un admin)
    déclenche lui-même la vérification. Seule la réponse de SingPay peut confirmer le paiement.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        user = request.user
        order = Order.objects.select_related('store').filter(pk=order_id).first()
        allowed = order is not None and (
            order.client_id == user.id
            or user.is_staff
            or getattr(order.store, 'manager_id', None) == user.id
        )
        payment = Payment.objects.filter(order=order).first() if allowed else None
        if payment is None:
            return Response({
                'success': False,
                'error': {'code': status.HTTP_404_NOT_FOUND, 'message': 'Aucun paiement en ligne pour cette commande.'},
            }, status=status.HTTP_404_NOT_FOUND)
        if check_allowed(f'payment:{payment.pk}'):
            verify_order_payment(payment, 'verification manuelle', user=user, ip_address=request.META.get('REMOTE_ADDR'))
        payment.refresh_from_db()
        order.refresh_from_db()
        return Response({
            'success': True,
            'data': {'payment_status': payment.status, 'order_status': order.status},
        })


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

