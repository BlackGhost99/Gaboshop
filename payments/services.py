import logging
import requests
import json
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from django.conf import settings
from payments.models import Payment, Commission, Reversement, DeliveryPayout
from orders.models import Order
# Persisted notifications service (DB + multi-canal)
from notifications.service import NotificationService
from payments.utils import call_singpay_payment, call_singpay_transfer

logger = logging.getLogger(__name__)


def _build_singpay_error_message(response):
    """Build a user-facing SingPay error with actionable context."""
    if not isinstance(response, dict):
        return "Erreur SingPay"

    details = response.get("response") if isinstance(response.get("response"), dict) else {}
    status_payload = response.get("status") if isinstance(response.get("status"), dict) else {}
    transaction_payload = response.get("transaction") if isinstance(response.get("transaction"), dict) else {}
    payment_result = response.get("paymentResult") or response.get("paiementResult")
    if isinstance(payment_result, dict):
        status_payload = status_payload or (
            payment_result.get("status") if isinstance(payment_result.get("status"), dict) else {}
        )
        transaction_payload = transaction_payload or (
            payment_result.get("transaction") if isinstance(payment_result.get("transaction"), dict) else {}
        )

    message_parts = [
        response.get("error"),
        response.get("result"),
        response.get("status") if not isinstance(response.get("status"), dict) else None,
        status_payload.get("message"),
        status_payload.get("code"),
        details.get("message"),
        details.get("error"),
        details.get("raw"),
        transaction_payload.get("result"),
        transaction_payload.get("status"),
    ]
    message = " - ".join(str(part) for part in message_parts if part not in (None, "", {}))
    if not message:
        message = "SingPay error"

    lowered = message.lower()
    if "timeouterror" in lowered or "timeout" in lowered:
        return (
            "Paiement Mobile Money expire: le client n'a pas valide le prompt a temps, "
            "le telephone etait indisponible, ou l'operateur n'a pas confirme le debit."
        )
    if "insufficient" in lowered or "solde" in lowered or "fund" in lowered:
        return "Paiement refuse: le solde du client semble insuffisant."
    if "wallet not accepted" in lowered or "status: pending" in lowered:
        return (
            message
            + " | "
            "Action requise: activer/valider le wallet chez SingPay "
            "(wallet en Pending) puis reutiliser le meme CLIENT_ID/SECRET/WALLET_ID."
        )
    if "something went wrong" in lowered:
        return (
            "SingPay a retourne une erreur generique. Verifiez dans le tableau SingPay "
            "le champ result; si result=TimeOutError, le client doit relancer et valider "
            "le prompt Mobile Money."
        )
    return message


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
            logger.error(f"Erreur API {operator}: {e}")
            if getattr(settings, 'PAYMENT_SIMULATION_MODE', False):
                # Mode simulation explicite uniquement (dev/tests)
                return PaymentService._get_fallback_response(operator, phone, amount, order)
            raise
    @staticmethod
    def _call_airtel_money_api(phone, amount, order):
        """
        Integration avec SingPay (Airtel Money)
        """
        try:
            response = call_singpay_payment(
                "airtel",
                amount=amount,
                reference=f"GABOSHOP_{order.order_number}",
                phone=phone,
                portefeuille=getattr(settings, "SINGPAY_WALLET_ID", ""),
                disbursement=getattr(settings, "SINGPAY_DISBURSEMENT_ID", ""),
                is_transfer=getattr(settings, 'SINGPAY_ENABLE_TRANSFER', False),
            )

            if response.get("error"):
                raise Exception(_build_singpay_error_message(response))

            tx = response.get("transaction") if isinstance(response.get("transaction"), dict) else {}
            status_payload = response.get("status") if isinstance(response.get("status"), dict) else {}
            result_payload = str(response.get("result") or tx.get("result") or "").lower()
            if result_payload in ("timeouterror", "failed", "error", "ko"):
                raise Exception(_build_singpay_error_message(response))
            if status_payload.get("success") is False:
                raise Exception(_build_singpay_error_message(response))
            transaction_id = (
                tx.get("airtel_money_id")
                or tx.get("id")
                or tx.get("_id")
                or response.get("airtel_money_id")
                or response.get("id")
                or response.get("_id")
                or response.get("transaction_id")
                or f"AIRTEL_{order.id}_{int(timezone.now().timestamp())}"
            )
            operator_reference = (
                tx.get("airtel_money_id")
                or tx.get("id")
                or tx.get("_id")
                or response.get("airtel_money_id")
                or response.get("id")
                or response.get("_id")
                or ""
            )

            return {
                "transaction_id": transaction_id,
                "operator_reference": operator_reference,
                "status": "pending",
                "next_steps": {
                    "message": "Un prompt de paiement apparaitra sur votre mobile Airtel",
                    "action": "Verifiez votre telephone et entrez votre PIN",
                    "singpay_status": status_payload,
                },
                "raw": response,
            }

        except Exception as e:
            logger.error(f"Erreur Airtel Money API: {e}")
            raise


    @staticmethod
    def _call_moov_money_api(phone, amount, order):
        """
        Integration avec SingPay (Moov Money)
        """
        try:
            response = call_singpay_payment(
                "moov",
                amount=amount,
                reference=f"GABOSHOP_{order.order_number}",
                phone=phone,
                portefeuille=getattr(settings, "SINGPAY_WALLET_ID", ""),
                disbursement=getattr(settings, "SINGPAY_DISBURSEMENT_ID", ""),
                is_transfer=getattr(settings, 'SINGPAY_ENABLE_TRANSFER', False),
            )

            if response.get("error"):
                raise Exception(_build_singpay_error_message(response))

            tx = response.get("transaction") if isinstance(response.get("transaction"), dict) else {}
            status_payload = response.get("status") if isinstance(response.get("status"), dict) else {}
            result_payload = str(response.get("result") or tx.get("result") or "").lower()
            if result_payload in ("timeouterror", "failed", "error", "ko"):
                raise Exception(_build_singpay_error_message(response))
            if status_payload.get("success") is False:
                raise Exception(_build_singpay_error_message(response))
            transaction_id = (
                tx.get("moov_money_id")
                or tx.get("airtel_money_id")
                or tx.get("id")
                or tx.get("_id")
                or response.get("moov_money_id")
                or response.get("airtel_money_id")
                or response.get("id")
                or response.get("_id")
                or response.get("transaction_id")
                or f"MOOV_{order.id}_{int(timezone.now().timestamp())}"
            )
            operator_reference = (
                tx.get("moov_money_id")
                or tx.get("airtel_money_id")
                or tx.get("id")
                or tx.get("_id")
                or response.get("moov_money_id")
                or response.get("airtel_money_id")
                or response.get("id")
                or response.get("_id")
                or ""
            )

            return {
                "transaction_id": transaction_id,
                "operator_reference": operator_reference,
                "status": "pending",
                "next_steps": {
                    "message": "Un prompt de paiement apparaitra sur votre mobile Moov",
                    "action": "Verifiez votre telephone et entrez votre PIN",
                    "singpay_status": status_payload,
                },
                "raw": response,
            }

        except Exception as e:
            logger.error(f"Erreur Moov Money API: {e}")
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
        import re

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

        # Format attendu: +241 suivi de 8 chiffres (Gabon)
        if not re.match(r'^\+241\d{8}$', clean_phone):
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
                payment.status = 'success'
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
                        commission_rate=commission_calc.get('commission_rate', order.store.commission_rate),
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
        Payer le livreur via SingPay /transfer apres confirmation de livraison.
        """
        try:
            if delivery.status != 'delivered' or delivery.order.status in ('cancelled', 'refunded'):
                return {'success': False, 'error': 'La livraison doit être livrée et non annulée'}
            if delivery.order.store.offers_delivery:
                # Le commerce gère sa livraison : la part livraison est incluse dans son versement.
                return {
                    'success': True,
                    'skipped': True,
                    'message': 'Livraison assurée par le commerce : rémunération incluse dans son versement',
                    'transaction_id': None,
                }
            if not hasattr(delivery, 'proof'):
                return {'success': False, 'error': 'Preuve de livraison requise'}
            if not delivery.agent_commission or delivery.agent_commission <= 0:
                logger.warning("Pas de commission pour livraison %s", delivery.id)
                return {'success': False, 'error': 'Aucune commission a payer'}

            agent = delivery.delivery_agent
            if not agent:
                return {'success': False, 'error': 'Livreur non assigne'}
            if not agent.phone:
                return {'success': False, 'error': 'Livreur: numero de telephone manquant'}

            disbursement_id = (agent.singpay_disbursement_id or '').strip()
            if not disbursement_id:
                return {'success': False, 'error': 'Livreur: disbursement SingPay manquant'}

            existing = DeliveryPayout.objects.select_for_update().filter(
                order=delivery.order, delivery_agent=agent
            ).first()
            if existing and existing.status in ('completed', 'processing'):
                return {
                    'success': True,
                    'payment': existing,
                    'amount': existing.calculated_payout,
                    'phone': agent.phone,
                    'transaction_id': None,
                    'message': 'Paiement livreur déjà initié ou terminé',
                    'already_processed': True,
                }

            payout, _ = DeliveryPayout.objects.get_or_create(
                order=delivery.order,
                delivery_agent=agent,
                defaults={
                    'delivery_fee_from_client': delivery.delivery_fee,
                    'distance_km': Decimal('0.00'),
                    'price_per_km': Decimal('0.00'),
                    'calculated_payout': delivery.agent_commission,
                    'platform_profit': Decimal('0.00'),
                    'status': 'pending',
                }
            )

            api_result = PaymentService._call_airtel_payout_api(
                amount=float(delivery.agent_commission),
                delivery=delivery,
                agent=agent,
                disbursement_id=disbursement_id,
            )

            payout.status = 'completed' if api_result.get('completed') else 'processing'
            if payout.status == 'completed':
                payout.paid_at = timezone.now()
            payout.save(update_fields=['status', 'paid_at'])
            # Expose transaction id to notification layer (non persisted here).
            payout.transaction_id = api_result.get('transaction_id')

            NotificationService.notify_delivery_agent_payment(
                agent, delivery, payout, api_result.get('message', '')
            )

            return {
                'success': True,
                'payment': payout,
                'amount': delivery.agent_commission,
                'phone': agent.phone,
                'transaction_id': api_result.get('transaction_id'),
                'message': api_result.get('message', 'Payout SingPay initie')
            }
        except Exception as e:
            logger.error("Erreur payout livreur: %s", e)
            return {'success': False, 'error': f'Erreur payout: {str(e)}'}

    @staticmethod
    def _call_airtel_payout_api(amount, delivery, agent, disbursement_id):
        """
        Appeler l'API SingPay pour un payout (paiement au livreur)
        """
        try:
            reference = None
            if delivery and getattr(delivery, 'order', None) and getattr(delivery.order, 'payment', None):
                reference = delivery.order.payment.transaction_id or None
            if not reference:
                reference = f"PAYOUT_DLV_{delivery.id}_{int(timezone.now().timestamp())}"

            response = call_singpay_transfer(
                reference=reference,
                disbursement=disbursement_id,
                amount=amount,
                portefeuille=getattr(settings, "SINGPAY_WALLET_ID", ""),
            )

            if response.get("error"):
                raise Exception(response["error"])

            return {
                'transaction_id': response.get('transaction_id') or reference,
                'operator_reference': reference,
                'status': 'success',
                'completed': True,
                'message': f'Payout {amount}F CFA envoye au livreur',
                'amount': amount,
                'recipient': agent.get_full_name() or agent.username
            }

        except Exception as e:
            logger.error(f"Erreur API SingPay payout: {e}")
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
                ).exclude(
                    # Déjà versé commande par commande à la confirmation du commerce
                    order__store_payout__status__in=['processing', 'paid']
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

