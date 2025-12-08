import logging
import requests
import json
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from django.conf import settings
from payments.models import Payment, Commission, Reversement
from orders.models import Order
# Persisted notifications service (DB + multi-canal)
from notifications.service import NotificationService

logger = logging.getLogger(__name__)


class PaymentService:
    """Services métier pour la gestion des paiements Mobile Money Gabon"""
    
    # Configuration des opérateurs Gabon
    OPERATOR_CONFIG = {
        'airtel': {
            'name': 'Airtel Money',
            'currency': 'XAF',
            'country_code': 'GA',
            'api_timeout': 30
        },
        'moov': {
            'name': 'Moov Money', 
            'currency': 'XAF',
            'country_code': 'GA',
            'api_timeout': 30
        }
    }

    @staticmethod
    def init_mobile_money_payment(order, phone_number, operator):
        """
        Initialiser un paiement Mobile Money pour le Gabon
        """
        try:
            # Validation de base
            if order.status != 'pending':
                raise ValueError("La commande n'est pas en attente de paiement.")
            
            if operator not in ['airtel', 'moov']:
                raise ValueError("Opérateur non supporté. Choisir 'airtel' ou 'moov'.")
            
            # Formater le numéro pour le Gabon
            formatted_phone = PaymentService._format_gabon_phone(phone_number, operator)
            
            # Créer l'enregistrement de paiement
            payment = Payment.objects.create(
                order=order,
                payment_method='mobile_money',
                amount=order.total_amount,
                status='pending',
                operator_reference=f"{operator.upper()}_INIT"
            )
            
            # Appeler l'API de l'opérateur
            api_result = PaymentService._call_operator_api(
                operator, formatted_phone, order.total_amount, order
            )
            
            # Mettre à jour le paiement avec la réponse
            payment.transaction_id = api_result['transaction_id']
            payment.operator_reference = api_result['operator_reference']
            payment.save()
            
            logger.info(
                f"💳 Paiement {operator.upper()} initié: {payment.transaction_id} "
                f"| {formatted_phone} | {order.total_amount}F CFA"
            )
            
            return {
                'payment': payment,
                'next_steps': api_result.get('next_steps', {}),
                'operator_response': api_result
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur initiation paiement {operator}: {e}")
            raise

    @staticmethod
    def _call_operator_api(operator, phone, amount, order):
        """
        Appeler l'API de l'opérateur Mobile Money
        """
        try:
            if operator == 'airtel':
                return PaymentService._call_airtel_money_api(phone, amount, order)
            elif operator == 'moov':
                return PaymentService._call_moov_money_api(phone, amount, order)
                
        except Exception as e:
            logger.error(f"❌ Erreur API {operator}: {e}")
            # Retourner une réponse simulée en cas d'échec
            return PaymentService._get_fallback_response(operator, phone, amount, order)

    @staticmethod
    def _call_airtel_money_api(phone, amount, order):
        """
        Intégration avec Airtel Money API
        """
        try:
            # === EN PRODUCTION: Décommenter et configurer ===
            """
            headers = {
                'Authorization': f'Bearer {settings.AIRTEL_API_KEY}',
                'Content-Type': 'application/json',
                'X-Country': 'GA',
                'X-Currency': 'XAF'
            }
            
            payload = {
                'reference': f"GABOSHOP_{order.order_number}",
                'subscriber': {
                    'msisdn': phone
                },
                'transaction': {
                    'amount': str(amount),
                    'id': f"CMD{order.id}",
                    'description': f"Paiement GABOSHOP #{order.order_number}"
                }
            }
            
            response = requests.post(
                'https://openapi.airtel.africa/merchant/v1/payments/',
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'transaction_id': data['data']['transaction']['id'],
                    'operator_reference': data['data']['transaction']['airtel_money_id'],
                    'status': 'pending',
                    'next_steps': {
                        'message': 'Un prompt de paiement apparaîtra sur votre mobile Airtel',
                        'action': 'Vérifiez votre téléphone et entrez votre PIN'
                    }
                }
            else:
                raise Exception(f"Airtel API error: {response.status_code} - {response.text}")
            """
            
            # === SIMULATION POUR MVP ===
            transaction_id = f"AIRTEL_{order.id}_{int(timezone.now().timestamp())}"
            
            logger.info(
                f"📱 Appel Airtel Money simulé: "
                f"{phone} | {amount}F | {transaction_id}"
            )
            
            return {
                'transaction_id': transaction_id,
                'operator_reference': f"AIRTEL_REF_{order.order_number}",
                'status': 'pending',
                'next_steps': {
                    'message': '✅ Simulation: Un prompt de paiement apparaîtra sur votre mobile Airtel',
                    'action': '📱 Vérifiez votre téléphone et entrez votre PIN',
                    'test_instruction': 'Pour tester, simulez le paiement dans l\'interface admin'
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur Airtel Money API: {e}")
            raise

    @staticmethod
    def _call_moov_money_api(phone, amount, order):
        """
        Intégration avec Moov Money API
        """
        try:
            # === EN PRODUCTION: Décommenter et configurer ===
            """
            headers = {
                'Authorization': f'Bearer {settings.MOOV_API_KEY}',
                'Content-Type': 'application/json',
                'X-API-Key': settings.MOOV_API_SECRET
            }
            
            payload = {
                'merchantId': settings.MOOV_MERCHANT_ID,
                'amount': str(amount),
                'currency': 'XAF',
                'customerMsidn': phone,
                'orderId': order.order_number,
                'description': f"GABOSHOP Commande #{order.order_number}",
                'callbackUrl': f"{settings.BASE_URL}/api/v1/payments/webhook/"
            }
            
            response = requests.post(
                'https://api.moov.africa/payments/request',
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'transaction_id': data['transactionId'],
                    'operator_reference': data['paymentReference'],
                    'status': 'pending',
                    'next_steps': {
                        'message': 'Un prompt de paiement apparaîtra sur votre mobile Moov',
                        'action': 'Vérifiez votre téléphone et entrez votre PIN'
                    }
                }
            else:
                raise Exception(f"Moov API error: {response.status_code} - {response.text}")
            """
            
            # === SIMULATION POUR MVP ===
            transaction_id = f"MOOV_{order.id}_{int(timezone.now().timestamp())}"
            
            logger.info(
                f"📱 Appel Moov Money simulé: "
                f"{phone} | {amount}F | {transaction_id}"
            )
            
            return {
                'transaction_id': transaction_id,
                'operator_reference': f"MOOV_REF_{order.order_number}",
                'status': 'pending',
                'next_steps': {
                    'message': '✅ Simulation: Un prompt de paiement apparaîtra sur votre mobile Moov',
                    'action': '📱 Vérifiez votre téléphone et entrez votre PIN',
                    'test_instruction': 'Pour tester, simulez le paiement dans l\'interface admin'
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur Moov Money API: {e}")
            raise

    @staticmethod
    def _get_fallback_response(operator, phone, amount, order):
        """
        Réponse de fallback si les APIs sont indisponibles
        """
        transaction_id = f"{operator.upper()}_FALLBACK_{order.id}_{int(timezone.now().timestamp())}"
        
        return {
            'transaction_id': transaction_id,
            'operator_reference': f"{operator.upper()}_FALLBACK_REF",
            'status': 'pending',
            'next_steps': {
                'message': f'Paiement {operator} initialisé (mode simulation)',
                'action': 'Le service de paiement sera confirmé manuellement',
                'note': 'Fallback activé - APIs temporairement indisponibles'
            }
        }

    @staticmethod
    def _format_gabon_phone(phone, operator):
        """
        Formater le numéro de téléphone pour les APIs Gabon
        """
        # Nettoyer le numéro
        clean_phone = phone.replace(' ', '').replace('-', '').replace('.', '')
        
        # Format standard: +241XXXXXXXX
        if clean_phone.startswith('0'):
            clean_phone = '+241' + clean_phone[1:]
        elif clean_phone.startswith('241'):
            clean_phone = '+' + clean_phone
        elif not clean_phone.startswith('+'):
            clean_phone = '+241' + clean_phone
        
        # Validation pour le Gabon
        if not clean_phone.startswith('+241'):
            raise ValueError("Numéro de téléphone Gabon invalide. Format: +241XXXXXXXX")
        
        if len(clean_phone) != 13:  # +241 + 8 chiffres
            raise ValueError("Numéro de téléphone Gabon invalide. Doit avoir 8 chiffres après +241")
        
        return clean_phone

    @staticmethod
    @transaction.atomic
    def confirm_payment(transaction_id, external_status, operator_data=None):
        """
        Confirmer un paiement via webhook/callback des opérateurs
        """
        try:
            payment = Payment.objects.select_for_update().get(
                transaction_id=transaction_id
            )
            
            if payment.status != 'pending':
                logger.warning(f"⚠️ Paiement déjà traité: {transaction_id}")
                return payment
            
            if external_status.upper() in ['SUCCESS', 'COMPLETED', 'APPROVED']:
                # Paiement réussi
                payment.status = 'completed'
                payment.completed_at = timezone.now()
                
                if operator_data:
                    payment.operator_reference = operator_data.get('operator_reference', '')
                
                payment.save()
                
                # Mettre à jour la commande
                payment.order.status = 'confirmed'
                payment.order.save()
                
                # Créer la commission
                PaymentService._create_commission(payment.order)
                
                # Notifier le magasin
                NotificationService.notify_new_order(payment.order)
                
                logger.info(f"✅ Paiement confirmé: {transaction_id}")
                
                # Retourner les détails de confirmation
                return {
                    'payment': payment,
                    'order_updated': True,
                    'commission_created': True,
                    'notifications_sent': True
                }
                
            else:
                # Paiement échoué
                payment.status = 'failed'
                payment.save()
                
                logger.warning(f"❌ Paiement échoué: {transaction_id} - Statut: {external_status}")
                
                return {
                    'payment': payment,
                    'order_updated': False,
                    'error': f"Paiement refusé: {external_status}"
                }
                
        except Payment.DoesNotExist:
            logger.error(f"❌ Paiement non trouvé: {transaction_id}")
            raise ValueError("Paiement non trouvé")

    @staticmethod
    def _create_commission(order):
        """
        Créer un enregistrement de commission pour une commande payée
        """
        try:
            from orders.services import OrderService
            
            # Calculer la commission
            commission_calc = OrderService.calculate_order_commission(order)
            
            if commission_calc:
                commission = Commission.objects.create(
                    order=order,
                    store=order.store,
                    order_amount=order.items_total,
                    commission_rate=order.store.commission_rate,
                    commission_amount=commission_calc['commission_amount'],
                    delivery_fee_share=commission_calc['delivery_fee_share']
                )
                
                logger.info(
                    f"💰 Commission créée: {commission.commission_amount}F "
                    f"pour #{order.order_number} | Taux: {commission.commission_rate}%"
                )
                
                return commission
                
        except Exception as e:
            logger.error(f"❌ Erreur création commission: {e}")
            raise

    @staticmethod
    def check_payment_status(transaction_id):
        """
        Vérifier le statut d'un paiement auprès de l'opérateur
        """
        try:
            payment = Payment.objects.get(transaction_id=transaction_id)
            
            # En production: appeler l'API de l'opérateur pour le statut réel
            # Pour le MVP, retourner le statut local
            
            return {
                'transaction_id': payment.transaction_id,
                'status': payment.status,
                'amount': payment.amount,
                'order_number': payment.order.order_number,
                'created_at': payment.created_at,
                'completed_at': payment.completed_at
            }
            
        except Payment.DoesNotExist:
            return {'error': 'Paiement non trouvé'}

    @staticmethod
    @transaction.atomic
    def payout_delivery_agent(delivery):
        """
        Payer le livreur via Airtel Money après confirmation de livraison
        
        Args:
            delivery: Objet Delivery avec agent_commission et delivery_agent
            
        Returns:
            dict avec succès et détails du payout
        """
        try:
            # Validation
            if not delivery.agent_commission or delivery.agent_commission <= 0:
                logger.warning(f"⚠️ Pas de commission pour livraison {delivery.id}")
                return {
                    'success': False,
                    'error': 'Aucune commission à payer'
                }
            
            agent = delivery.delivery_agent
            if not agent.phone_number:
                logger.error(f"❌ Livreur {agent.id} n'a pas de numéro de téléphone")
                return {
                    'success': False,
                    'error': 'Livreur: numéro de téléphone manquant'
                }
            
            # Déterminer l'opérateur (pour l'instant Airtel par défaut)
            operator = 'airtel'
            formatted_phone = PaymentService._format_gabon_phone(agent.phone_number, operator)
            
            # Créer le paiement pour le livreur
            payment = Payment.objects.create(
                order=delivery.order,
                payment_method='mobile_money',
                amount=delivery.agent_commission,
                status='pending',
                operator_reference=f"PAYOUT_DELIVERY_{delivery.id}",
                transaction_id=f"PAYOUT_DLV_{delivery.id}_{int(timezone.now().timestamp())}",
                client_phone=formatted_phone,  # Utiliser pour le numéro du livreur
                client_name=agent.get_full_name() or agent.username  # Utiliser pour le nom du livreur
            )
            
            # Appeler l'API Airtel Money pour le payout
            try:
                api_result = PaymentService._call_airtel_payout_api(
                    formatted_phone,
                    float(delivery.agent_commission),
                    delivery,
                    agent
                )
                
                payment.transaction_id = api_result['transaction_id']
                payment.operator_reference = api_result['operator_reference']
                payment.status = api_result.get('status', 'pending')
                
                if api_result.get('completed'):
                    payment.completed_at = timezone.now()
                
                payment.save()
                
                logger.info(
                    f"💳 Payout Airtel initié pour livreur {agent.username}: "
                    f"{delivery.agent_commission}F CFA | {formatted_phone} | "
                    f"Livraison #{delivery.id}"
                )
                
                # Notifier le livreur
                NotificationService.notify_delivery_agent_payment(
                    agent, delivery, payment, api_result.get('message', '')
                )
                
                return {
                    'success': True,
                    'payment': payment,
                    'amount': delivery.agent_commission,
                    'phone': formatted_phone,
                    'transaction_id': payment.transaction_id,
                    'message': api_result.get('message', 'Payout Airtel Money initié')
                }
                
            except Exception as api_error:
                logger.error(f"❌ Erreur API Airtel payout: {api_error}")
                payment.status = 'failed'
                payment.save()
                
                return {
                    'success': False,
                    'error': f'Erreur service Airtel: {str(api_error)}',
                    'payment': payment
                }
            
        except Exception as e:
            logger.error(f"❌ Erreur payout livreur: {e}")
            return {
                'success': False,
                'error': f'Erreur payout: {str(e)}'
            }

    @staticmethod
    def _call_airtel_payout_api(phone, amount, delivery, agent):
        """
        Appeler l'API Airtel Money pour un payout (paiement au livreur)
        """
        try:
            # En production: appeler l'API réelle d'Airtel
            # Pour le MVP: simulation
            
            logger.info(
                f"📱 Payout Airtel simulé: {phone} | {amount}F CFA | "
                f"Livreur: {agent.username} | Livraison: {delivery.id}"
            )
            
            transaction_id = f"AIRTEL_PAYOUT_{delivery.id}_{int(timezone.now().timestamp())}"
            
            return {
                'transaction_id': transaction_id,
                'operator_reference': f"AIRTEL_PAYOUT_{delivery.order.order_number}",
                'status': 'completed',  # En simulation, considérer comme réussi immédiatement
                'completed': True,
                'message': f'✅ Payout {amount}F CFA envoyé à {phone}',
                'amount': amount,
                'recipient': agent.get_full_name() or agent.username
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur API Airtel payout: {e}")
            raise

    @staticmethod
    def process_store_payout(store_id, period_start, period_end):
        """
        Traiter le reversement pour un magasin sur une période
        """
        try:
            with transaction.atomic():
                from stores.models import Store
                from django.db.models import Sum, Count
                
                store = Store.objects.get(id=store_id)
                
                # Récupérer les commissions non réglées pour la période
                unsettled_commissions = Commission.objects.filter(
                    store=store,
                    is_settled=False,
                    order__status='delivered',
                    order__delivered_at__range=[period_start, period_end]
                )
                
                if not unsettled_commissions.exists():
                    return {
                        'success': True,
                        'message': 'Aucune commission à reverser pour cette période',
                        'reversement': None
                    }
                
                # Calculer les totaux
                aggregates = unsettled_commissions.aggregate(
                    total_orders=Count('id'),
                    total_sales=Sum('order_amount'),
                    total_commissions=Sum('commission_amount')
                )
                
                total_orders = aggregates['total_orders'] or 0
                total_sales = aggregates['total_sales'] or Decimal('0.00')
                total_commissions = aggregates['total_commissions'] or Decimal('0.00')
                net_amount = total_sales - total_commissions
                
                # Créer le reversement
                reversement = Reversement.objects.create(
                    store=store,
                    period_start=period_start,
                    period_end=period_end,
                    total_orders=total_orders,
                    total_sales=total_sales,
                    total_commissions=total_commissions,
                    net_amount=net_amount,
                    status='pending'
                )
                
                # Marquer les commissions comme réglées
                unsettled_commissions.update(is_settled=True)
                
                logger.info(
                    f"💰 Reversement créé: {net_amount}F CFA "
                    f"pour {store.name} | Période: {period_start} à {period_end}"
                )
                
                return {
                    'success': True,
                    'message': f'Reversement de {net_amount}F CFA créé avec succès',
                    'reversement': reversement
                }
                
        except Exception as e:
            logger.error(f"❌ Erreur traitement reversement: {e}")
            return {
                'success': False,
                'error': str(e)
            }
