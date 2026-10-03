"""
Vues pour l'intégration CinetPay / Airtel Money / Moov Money
- Création de PaymentIntent
- Callbacks des providers
- Vérification et refund
"""

import logging
from decimal import Decimal
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.utils import timezone
from django.db import connection
from django.db.utils import OperationalError
from datetime import timedelta

from .models import PaymentIntent, PaymentTransaction, SubscriptionPlan, StoreSubscription
from .serializers import CreatePaymentSerializer, PaymentIntentSerializer, SubscriptionPlanSerializer
from .utils import (
    call_cinetpay_init, call_cinetpay_check, call_cinetpay_refund,
    call_airtel_money_init, call_airtel_money_check,
    call_moov_money_init, call_moov_money_check,
    verify_hmac_signature,
    build_cinetpay_payload, build_airtel_payload, build_moov_payload
)
from stores.models import Store
from orders.models import Order

logger = logging.getLogger(__name__)


def _b2b_subscription_tables_ready():
    try:
        tables = connection.introspection.table_names()
        return 'b2b_b2bsubscriptionplan' in tables and 'b2b_b2bstoresubscription' in tables
    except OperationalError:
        return False
    except Exception:
        return False


def _get_subscription_price(store, plan):
    if isinstance(plan, SubscriptionPlan) and plan.plan_type == 'business':
        if store.is_b2b:
            return int(Decimal('80000.00'))
        return int(Decimal('50000.00'))
    return int(Decimal(plan.price))


def _activate_subscription_from_intent(intent):
    meta = intent.metadata or {}
    if meta.get('purpose') != 'store_subscription':
        return None
    if meta.get('subscription_activated'):
        return None

    store_id = meta.get('store_id')
    plan_id = meta.get('plan_id')
    subscription_kind = meta.get('subscription_kind')
    if not store_id or not plan_id or not subscription_kind:
        logger.warning("Subscription intent missing metadata: %s", intent.reference)
        return None

    store = Store.objects.filter(id=store_id).first()
    if not store or store.manager_id != intent.user_id:
        logger.warning("Subscription intent store mismatch: %s", intent.reference)
        return None

    start_date = timezone.now().date()
    end_date = start_date + timedelta(days=30)

    if subscription_kind == 'b2b':
        from b2b.models import B2BSubscriptionPlan, B2BStoreSubscription

        if not _b2b_subscription_tables_ready():
            logger.warning("B2B subscription tables missing for intent %s", intent.reference)
            return None

        if not store.is_b2b:
            logger.warning("Store is not B2B for intent %s", intent.reference)
            return None

        plan = B2BSubscriptionPlan.objects.filter(id=plan_id, is_active=True).first()
        if not plan or plan.plan_type == 'free':
            logger.warning("Invalid B2B plan for intent %s", intent.reference)
            return None

        subscription = getattr(store, 'b2b_subscription', None)
        if subscription:
            subscription.plan = plan
            subscription.plan_name = plan.name
            subscription.monthly_fee = plan.price
            subscription.status = 'active'
            subscription.start_date = start_date
            subscription.end_date = end_date
            subscription.auto_renew = True
            subscription.save()
        else:
            subscription = B2BStoreSubscription.objects.create(
                store=store,
                plan=plan,
                plan_name=plan.name,
                monthly_fee=plan.price,
                status='active',
                start_date=start_date,
                end_date=end_date,
                auto_renew=True
            )

        store.subscription_plan = plan.plan_type
        store.save(update_fields=['subscription_plan'])
    else:
        plan = SubscriptionPlan.objects.filter(id=plan_id, is_active=True).first()
        if not plan or plan.plan_type == 'free':
            logger.warning("Invalid B2C plan for intent %s", intent.reference)
            return None

        StoreSubscription.objects.filter(store=store, status='active').update(status='expired')
        subscription = StoreSubscription.objects.create(
            store=store,
            plan=plan,
            plan_name=plan.name,
            monthly_fee=_get_subscription_price(store, plan),
            status='active',
            start_date=start_date,
            end_date=end_date,
            auto_renew=True
        )

        store.subscription_plan = plan.plan_type
        store.save(update_fields=['subscription_plan'])

    meta['subscription_activated'] = True
    meta['subscription_id'] = subscription.id
    intent.metadata = meta
    intent.save(update_fields=['metadata'])
    return subscription


class CreatePaymentAPIView(APIView):
    """
    Créer un PaymentIntent et initialiser un paiement provider
    POST /api/v1/payments/create/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CreatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        order_id = serializer.validated_data["order_id"]
        provider = serializer.validated_data.get("provider", "cinetpay")
        channels = serializer.validated_data.get("channels", "ALL")
        lang = serializer.validated_data.get("lang", "FR")
        metadata = serializer.validated_data.get("metadata", {})

        # Vérifier la commande
        try:
            order = Order.objects.get(id=order_id, user=request.user)
        except Order.DoesNotExist:
            return Response(
                {"detail": "Commande non trouvée"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Vérifier le statut de la commande
        if order.status not in ("CREATED", "PENDING"):
            return Response(
                {"detail": "Cette commande ne peut pas être payée"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Créer le PaymentIntent AVANT l'appel externe (sécurité)
        intent = PaymentIntent.objects.create(
            user=request.user,
            order=order,
            amount=int(order.total_amount),
            currency="XAF",
            provider=provider,
            expires_at=timezone.now() + timedelta(minutes=30),
            metadata=metadata
        )

        logger.info(f"✅ PaymentIntent créé: {intent.reference} | Montant: {intent.amount} XAF")

        # Dispatcher selon le provider
        if provider == "cinetpay":
            return self._handle_cinetpay(intent, request, channels, lang)
        elif provider == "airtel":
            return self._handle_airtel(intent, request)
        elif provider == "moov":
            return self._handle_moov(intent, request)
        else:
            return Response(
                {"detail": "Provider non supporté"},
                status=status.HTTP_400_BAD_REQUEST
            )

    def _handle_cinetpay(self, intent, request, channels, lang):
        """Initialiser un paiement CinetPay"""
        payload = build_cinetpay_payload(intent, channels, lang)
        response = call_cinetpay_init(payload)
        
        # Sauvegarder la réponse
        intent.raw_response = response
        
        if isinstance(response, dict) and response.get("data"):
            data = response["data"]
            intent.payment_token = data.get("payment_token", "")
            intent.payment_url = data.get("payment_url", "")
            intent.status = "PENDING"
            logger.info(f"✅ CinetPay init: {intent.reference} | token: {intent.payment_token}")
        else:
            intent.status = "FAILED"
            logger.error(f"❌ CinetPay init failed: {response}")
        
        intent.save()
        PaymentTransaction.objects.create(
            intent=intent,
            status="PENDING",
            raw_response=response
        )

        return Response({
            "reference": intent.reference,
            "payment_token": intent.payment_token,
            "payment_url": intent.payment_url,
            "status": intent.status,
            "provider": intent.provider,
            "amount": intent.amount,
            "currency": intent.currency
        }, status=status.HTTP_201_CREATED)

    def _handle_airtel(self, intent, request):
        """Initialiser un paiement Airtel Money"""
        phone = request.data.get("phone_number")
        if not phone:
            return Response(
                {"detail": "phone_number requis pour Airtel"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payload = build_airtel_payload(intent, phone)
        response = call_airtel_money_init(
            phone=phone,
            amount=intent.amount,
            reference=intent.reference,
            metadata=intent.metadata
        )
        
        intent.raw_response = response
        if isinstance(response, dict) and not response.get("error"):
            intent.payment_url = response.get("payment_url", "")
            intent.status = "PENDING"
            logger.info(f"✅ Airtel init: {intent.reference}")
        else:
            intent.status = "FAILED"
            logger.error(f"❌ Airtel init failed: {response}")
        
        intent.save()
        PaymentTransaction.objects.create(
            intent=intent,
            status="PENDING",
            raw_response=response
        )

        return Response({
            "reference": intent.reference,
            "payment_url": intent.payment_url,
            "status": intent.status,
            "provider": intent.provider
        }, status=status.HTTP_201_CREATED)


class SubscriptionPaymentIntentAPIView(APIView):
    """
    Creer un PaymentIntent pour une souscription (B2C/B2B)
    POST /api/v1/payments/subscriptions/intent/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if not request.user.is_store_manager():
            return Response(
                {"detail": "Seuls les gerants peuvent souscrire"},
                status=status.HTTP_403_FORBIDDEN
            )

        store = Store.objects.filter(manager=request.user).first()
        if not store:
            return Response(
                {"detail": "Aucun magasin trouve"},
                status=status.HTTP_404_NOT_FOUND
            )

        plan_id = request.data.get("plan_id")
        provider = request.data.get("provider", "cinetpay")
        operator = request.data.get("operator")
        phone = request.data.get("phone_number")
        channels = request.data.get("channels", "ALL")
        lang = request.data.get("lang", "FR")

        if not plan_id:
            return Response({"detail": "plan_id requis"}, status=status.HTTP_400_BAD_REQUEST)

        if provider in ("card", "credit_card"):
            provider = "cinetpay"

        # Compat legacy: provider=airtel|moov -> provider=singpay + operator
        if provider in ("airtel", "moov"):
            operator = provider
            provider = "singpay"

        if provider not in ("cinetpay", "singpay"):
            return Response({"detail": "Provider non supporte"}, status=status.HTTP_400_BAD_REQUEST)

        if provider == "singpay":
            if operator not in ("airtel", "moov"):
                return Response(
                    {"detail": "operator requis pour SingPay (airtel|moov)"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if not phone:
                return Response(
                    {"detail": "phone_number requis pour Mobile Money"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if phone.startswith("0"):
                phone = "+241" + phone[1:]

        subscription_kind = "b2b" if store.is_b2b else "b2c"

        if subscription_kind == "b2b":
            from b2b.models import B2BSubscriptionPlan

            if not _b2b_subscription_tables_ready():
                return Response(
                    {"detail": "Tables B2B manquantes. Lancez les migrations pour activer les plans."},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )

            plan = B2BSubscriptionPlan.objects.filter(id=plan_id, is_active=True).first()
            if not plan or plan.plan_type == "free":
                return Response(
                    {"detail": "Plan B2B introuvable ou invalide"},
                    status=status.HTTP_404_NOT_FOUND
                )
            amount = int(Decimal(plan.price))
        else:
            plan = SubscriptionPlan.objects.filter(id=plan_id, is_active=True).first()
            if not plan or plan.plan_type == "free":
                return Response(
                    {"detail": "Plan B2C introuvable ou invalide"},
                    status=status.HTTP_404_NOT_FOUND
                )
            amount = _get_subscription_price(store, plan)

        metadata = {
            "purpose": "store_subscription",
            "plan_id": int(plan.id),
            "store_id": int(store.id),
            "subscription_kind": subscription_kind,
        }
        if provider == "singpay":
            metadata["operator"] = operator

        intent = PaymentIntent.objects.create(
            user=request.user,
            amount=amount,
            currency="XAF",
            provider=provider,
            expires_at=timezone.now() + timedelta(minutes=30),
            metadata=metadata
        )

        if provider == "cinetpay":
            payload = build_cinetpay_payload(intent, channels, lang)
            response = call_cinetpay_init(payload)
            intent.raw_response = response
            if isinstance(response, dict) and response.get("data"):
                data = response["data"]
                intent.payment_token = data.get("payment_token", "")
                intent.payment_url = data.get("payment_url", "")
                intent.status = "PENDING"
            else:
                intent.status = "FAILED"
            intent.save()
            PaymentTransaction.objects.create(intent=intent, status=intent.status, raw_response=response)
        else:
            if operator == "airtel":
                response = call_airtel_money_init(
                    phone=phone,
                    amount=intent.amount,
                    reference=intent.reference,
                    metadata=intent.metadata
                )
            else:
                response = call_moov_money_init(
                    phone=phone,
                    amount=intent.amount,
                    reference=intent.reference,
                    metadata=intent.metadata
                )

            intent.raw_response = response
            if isinstance(response, dict) and not response.get("error"):
                intent.payment_url = response.get("payment_url", "")
                intent.status = "PENDING"
            else:
                intent.status = "FAILED"
            intent.save()
            PaymentTransaction.objects.create(intent=intent, status=intent.status, raw_response=response)

        if intent.status == "FAILED":
            return Response({"detail": "Impossible d'initialiser le paiement"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "success": True,
            "payment_intent": {
                "reference": intent.reference,
                "status": intent.status,
                "provider": intent.provider,
                "operator": operator if intent.provider == "singpay" else None,
                "amount": intent.amount,
                "currency": intent.currency,
                "payment_url": intent.payment_url,
            },
            "subscription": {
                "plan_id": plan.id,
                "plan_name": plan.name,
                "subscription_kind": subscription_kind,
            }
        }, status=status.HTTP_201_CREATED)

    def _handle_moov(self, intent, request):
        """Initialiser un paiement Moov Money"""
        phone = request.data.get("phone_number")
        if not phone:
            return Response(
                {"detail": "phone_number requis pour Moov"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payload = build_moov_payload(intent, phone)
        response = call_moov_money_init(
            phone=phone,
            amount=intent.amount,
            reference=intent.reference,
            metadata=intent.metadata
        )
        
        intent.raw_response = response
        if isinstance(response, dict) and not response.get("error"):
            intent.payment_url = response.get("payment_url", "")
            intent.status = "PENDING"
            logger.info(f"✅ Moov init: {intent.reference}")
        else:
            intent.status = "FAILED"
            logger.error(f"❌ Moov init failed: {response}")
        
        intent.save()
        PaymentTransaction.objects.create(
            intent=intent,
            status="PENDING",
            raw_response=response
        )

        return Response({
            "reference": intent.reference,
            "payment_url": intent.payment_url,
            "status": intent.status,
            "provider": intent.provider
        }, status=status.HTTP_201_CREATED)


class ProviderCallbackAPIView(APIView):
    """
    Endpoint de callback pour les notifications des providers
    POST/GET /api/v1/payments/<provider>/notify/
    
    Public endpoint sécurisé par signature HMAC si disponible
    """
    permission_classes = []  # Public endpoint

    def post(self, request, provider="cinetpay"):
        """Traiter la notification du provider"""
        payload = request.data
        singpay_payload = payload.get('paymentResult') or payload.get('paiementResult')
        if singpay_payload:
            transaction = singpay_payload.get('transaction') or {}
            status_payload = singpay_payload.get('status') or {}
        else:
            transaction = payload.get('transaction') or {}
            status_payload = payload.get('status') or {}

        logger.info(f"📨 Callback reçu: {provider} | Payload: {payload}")

        # Vérifier la signature si disponible
        if provider == "cinetpay":
            header_sig = request.headers.get("X-Signature") or request.headers.get("x-signature")
            if getattr(settings, "CINETPAY_SECRET", None) and header_sig:
                ok = verify_hmac_signature(settings.CINETPAY_SECRET, request.body, header_sig)
                if not ok:
                    logger.warning(f"❌ Signature invalide pour {provider}")
                    return Response(
                        {"detail": "Invalid signature"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

        # Extraire la référence
        reference = (
            payload.get('transaction_id')
            or (payload.get('data') or {}).get('transaction_id')
            or transaction.get('reference')
            or payload.get('reference')
            or transaction.get('id')
            or transaction.get('_id')
            or (payload.get('transaction') if isinstance(payload.get('transaction'), str) else None)
        )
        if not reference:
            logger.error(f"❌ Reference manquante dans callback {provider}")
            return Response(
                {"detail": "Missing reference"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Récupérer le PaymentIntent
        try:
            intent = PaymentIntent.objects.get(reference=reference)
        except PaymentIntent.DoesNotExist:
            logger.error(f"❌ PaymentIntent non trouvé: {reference}")
            return Response(
                {"detail": "Unknown reference"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Extraire les données de transaction
        provider_tx_id = (
            transaction.get('airtel_money_id')
            or transaction.get('id')
            or transaction.get('_id')
            or payload.get('api_response_id')
            or (payload.get('data') or {}).get('api_response_id')
            or f"{provider}-{reference}"
        )
        amount = int(float((
            payload.get("amount")
            or (payload.get("data") or {}).get("amount")
            or transaction.get("amount")
            or 0
        )))
        status_str = (
            (payload.get('status')
             or (payload.get('data') or {}).get('status')
             or status_payload.get('code')
             or status_payload.get('result_code')
             or status_payload.get('message')
             or transaction.get('result')
             or '')
            .upper()
        )

        # Créer ou récupérer la transaction (idempotence)
        tx, created = PaymentTransaction.objects.get_or_create(
            intent=intent,
            provider_tx_id=provider_tx_id,
            defaults={
                "status": status_str or "PENDING",
                "raw_response": payload
            }
        )

        if tx.processed:
            logger.warning(f"⚠️ Transaction déjà traitée (idempotence): {provider_tx_id}")
            return Response(
                {"detail": "Already processed"},
                status=status.HTTP_200_OK
            )

        # Vérifier le montant
        if amount and amount != intent.amount:
            logger.error(f"❌ Montant mismatch: expected {intent.amount}, got {amount}")
            tx.status = "FAILED"
            tx.raw_response = payload
            tx.processed = True
            tx.save()
            intent.status = "FAILED"
            intent.save()
            return Response(
                {"detail": "Amount mismatch"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Vérifier le statut de succès
        accepted_statuses = ("ACCEPTED", "APPROVED", "SUCCESS", "OK", "00", "TS")
        normalized_result = str(transaction.get('result') or '').upper()
        status_step = str(transaction.get('status') or '').upper()
        is_success = (
            status_str in accepted_statuses
            or normalized_result == "SUCCESS"
            or payload.get('code') in ("00", "201")
            or str(status_payload.get('code') or status_payload.get('result_code') or '').upper() in ("00", "201", "SUCCESS", "OK")
            or status_payload.get('success') is True
            or (payload.get('message') and "CREATED" in str(payload.get('message')).upper())
        )

        if is_success:
            logger.info(f"✅ Paiement confirmé: {intent.reference}")
            intent.status = "SUCCESS"
            intent.save()
            tx.status = "SUCCESS"
            tx.processed = True
            tx.raw_response = payload
            tx.save()

            _activate_subscription_from_intent(intent)

            # Business logic: marquer la commande comme payée
            order = intent.order
            if order:
                try:
                    # Réserver le stock
                    if hasattr(order, 'reserve_stock'):
                        order.reserve_stock()
                    
                    # Marquer comme payé
                    if hasattr(order, 'mark_as_paid'):
                        order.mark_as_paid(provider_tx_id, intent.amount)
                    
                    logger.info(f"✅ Commande #{order.id} marquée comme payée")
                except Exception as e:
                    logger.error(f"❌ Erreur reserve stock: {e}")
                    intent.status = "RESERVE_FAILED"
                    intent.save()
                    tx.status = "FAILED"
                    tx.processed = True
                    tx.save()
                    return Response(
                        {"detail": "Stock reserve failed"},
                        status=status.HTTP_200_OK
                    )

            return Response(
                {"detail": "Payment confirmed"},
                status=status.HTTP_200_OK
            )
        else:
            if status_step in ("START", "PARTENAIRE"):
                tx.status = "PENDING"
                tx.raw_response = payload
                tx.save()
                return Response(
                    {"detail": "Payment pending"},
                    status=status.HTTP_200_OK
                )
            logger.warning(f"❌ Paiement échoué: {intent.reference} | Status: {status_str}")
            tx.status = "FAILED"
            tx.raw_response = payload
            tx.processed = True
            tx.save()
            intent.status = "FAILED"
            intent.save()
            return Response(
                {"detail": "Payment failed"},
                status=status.HTTP_200_OK
            )

    def get(self, request, provider="cinetpay"):
        """Tester l'accessibilité du endpoint"""
        return Response(
            {"detail": f"Notification endpoint for {provider} is reachable"},
            status=status.HTTP_200_OK
        )


class CheckPaymentAPIView(APIView):
    """
    Vérifier le statut d'un paiement
    POST /api/v1/payments/check/
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        """Vérifier une transaction"""
        transaction_id = request.data.get("transaction_id")
        provider = request.data.get("provider", "cinetpay")
        
        if not transaction_id:
            return Response(
                {"detail": "transaction_id requis"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Appeler le provider approprié
        if provider == "cinetpay":
            result = call_cinetpay_check(transaction_id)
        elif provider == "airtel":
            result = call_airtel_money_check(transaction_id)
        elif provider == "moov":
            result = call_moov_money_check(transaction_id)
        elif provider == "singpay":
            # SingPay status endpoint is shared in current integration.
            result = call_airtel_money_check(transaction_id)
        else:
            return Response(
                {"detail": "Provider non supporté"},
                status=status.HTTP_400_BAD_REQUEST
            )

        logger.info(f"🔍 Check payment: tx_id={transaction_id}, provider={provider}")
        
        return Response(
            {"data": result, "provider": provider},
            status=status.HTTP_200_OK
        )


class RefundAPIView(APIView):
    """
    Rembourser un paiement
    POST /api/v1/payments/refund/
    Requiert les permissions admin
    """
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        """Initier un remboursement"""
        reference = request.data.get("reference")
        try:
            amount = Decimal(str(request.data.get("amount", 0)))
        except Exception:
            amount = Decimal('0')
        component = request.data.get('component', 'products')
        
        if not reference:
            return Response(
                {"detail": "reference requis"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if amount <= 0:
            return Response(
                {"detail": "Montant invalide"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            intent = PaymentIntent.objects.get(reference=reference)
        except PaymentIntent.DoesNotExist:
            return Response(
                {"detail": "PaymentIntent non trouvé"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Vérifier que c'est un paiement réussi
        if intent.status != "SUCCESS":
            return Response(
                {"detail": f"Ne peut pas rembourser un paiement en statut {intent.status}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if amount > Decimal(str(intent.amount)):
            return Response(
                {"detail": "Le remboursement dépasse le paiement d'origine"},
                status=status.HTTP_400_BAD_REQUEST
            )
        if intent.order and hasattr(intent.order, 'payment_arrangement'):
            from payments.direct_service import record_refund
            obligation = intent.order.payment_arrangement.obligations.filter(kind=component).first()
            if not obligation or amount > obligation.remaining_amount:
                return Response(
                    {"detail": "Le remboursement dépasse le solde remboursable du composant"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        logger.info(f"💰 Refund initié: {reference} | Montant: {amount}")

        # Appeler le provider
        if intent.provider == "cinetpay":
            res = call_cinetpay_refund(reference, int(amount))
        elif intent.provider == "airtel":
            return Response(
                {"detail": "Refund non supporté pour Airtel dans cette version"},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        elif intent.provider == "moov":
            return Response(
                {"detail": "Refund non supporté pour Moov dans cette version"},
                status=status.HTTP_501_NOT_IMPLEMENTED
            )
        else:
            return Response(
                {"detail": "Provider non supporté"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Sauvegarder la transaction de refund
        PaymentTransaction.objects.create(
            intent=intent,
            status="REFUNDED",
            raw_response=res
        )

        if amount >= Decimal(str(intent.amount)):
            intent.status = "REFUNDED"
            intent.save(update_fields=['status'])

        if intent.order and hasattr(intent.order, 'payment_arrangement'):
            record_refund(
                intent.order, component, amount, request.user,
                reference=f'{reference}-{PaymentTransaction.objects.filter(intent=intent).count()}',
                reason=request.data.get('reason', 'Remboursement fournisseur'),
            )

        # Mettre à jour la commande
        if amount >= Decimal(str(intent.amount)) and intent.order and hasattr(intent.order, 'mark_as_refunded'):
            try:
                intent.order.mark_as_refunded(amount)
                logger.info(f"✅ Commande #{intent.order.id} marquée comme remboursée")
            except Exception as e:
                logger.error(f"❌ Erreur mark_as_refunded: {e}")

        return Response({
            "detail": "Remboursement initié",
            "provider_response": res,
            "reference": reference,
            "amount": amount
        }, status=status.HTTP_200_OK)


class SubscriptionPlansAPIView(APIView):
    """Expose la liste des plans et le forfait courant du magasin de l'utilisateur."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from payments.subscription_check import SubscriptionChecker
        from b2b.models import B2BSubscriptionPlan, B2BStoreSubscription
        
        store = Store.objects.filter(manager=request.user).first()
        
        # Si le store est B2B, retourner les plans B2B
        if store and store.is_b2b:
            if not _b2b_subscription_tables_ready():
                return Response({
                    'success': False,
                    'error': 'Tables B2B manquantes. Appliquez les migrations B2B pour activer les plans.'
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            plans_qs = B2BSubscriptionPlan.objects.filter(is_active=True).order_by('display_order', 'price')
            plans_data = []
            
            for plan in plans_qs:
                # Récupérer toutes les features et les convertir en liste de strings
                all_features = plan.get_all_features()
                features_list = [f['title'] for f in all_features if f.get('enabled', True)]
                
                plans_data.append({
                    'id': plan.id,
                    'name': plan.name,
                    'slug': plan.slug,
                    'plan_type': plan.plan_type,
                    'price': float(plan.price),
                    'actual_price': float(plan.price),
                    'price_label': f"{int(plan.price)} F/mois" if plan.price > 0 else "Gratuit",
                    'description': plan.description,
                    'tagline': plan.tagline,
                    'features': features_list,  # Liste de strings pour le frontend
                    'is_popular': plan.is_popular,
                })
            
            # Récupérer le plan actuel B2B
            current_plan = None
            try:
                b2b_sub = B2BStoreSubscription.objects.get(store=store, status='active')
                if b2b_sub.is_active() and b2b_sub.plan:
                    plan_obj = b2b_sub.plan
                    all_features = plan_obj.get_all_features()
                    features_list = [f['title'] for f in all_features if f.get('enabled', True)]
                    
                    current_plan = {
                        'id': plan_obj.id,
                        'name': plan_obj.name,
                        'plan_type': plan_obj.plan_type,
                        'price': float(b2b_sub.monthly_fee),
                        'end_date': b2b_sub.end_date.isoformat() if b2b_sub.end_date else None,
                        'status': b2b_sub.status,
                        'auto_renew': b2b_sub.auto_renew,
                        'features': features_list,
                        'days_until_expiry': b2b_sub.get_remaining_days(),
                    }
            except B2BStoreSubscription.DoesNotExist:
                pass
            
            return Response({
                'success': True,
                'plans': plans_data,
                'current_plan': current_plan,
                'store_type': 'b2b' if store.is_b2b else 'b2c'
            })
        
        # Sinon, retourner les plans B2C (comportement existant)
        plans_qs = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
        plans_data = SubscriptionPlanSerializer(plans_qs, many=True).data
        
        # Ajouter le prix dynamique pour Business selon le type de store
        if store:
            for plan in plans_data:
                price_value = float(plan.get('price') or 0)
                if plan['plan_type'] == 'business':
                    # Prix dynamique: 50k B2C, 80k B2B
                    if store.is_b2b:
                        plan['actual_price'] = 80000.00
                        plan['price_label'] = '80 000 F/mois (B2B)'
                    else:
                        plan['actual_price'] = 50000.00
                        plan['price_label'] = '50 000 F/mois (B2C)'
                else:
                    plan['actual_price'] = price_value
                    plan['price_label'] = f"{int(price_value)} F/mois" if price_value > 0 else "Gratuit"

        current_plan = None
        if store:
            active_sub = (
                StoreSubscription.objects
                .filter(store=store, status='active')
                .order_by('-end_date')
                .first()
            )
            if active_sub:
                plan_obj = active_sub.plan
                current_plan = {
                    'id': plan_obj.id if plan_obj else None,
                    'name': plan_obj.name if plan_obj else active_sub.plan_name,
                    'plan_type': plan_obj.plan_type if plan_obj else active_sub.plan_name.lower(),
                    'price': float(active_sub.monthly_fee),
                    'commission_rate': float(plan_obj.commission_rate) if plan_obj and plan_obj.commission_rate is not None else None,
                    'end_date': active_sub.end_date,
                    'status': active_sub.status,
                    'auto_renew': active_sub.auto_renew,
                    'features': active_sub.get_plan_features(),
                    'max_products': plan_obj.max_products if plan_obj else None,
                    'max_orders_per_month': plan_obj.max_orders_per_month if plan_obj else None,
                    'can_access_b2b': plan_obj.can_access_b2b if plan_obj else False,
                    'priority_listing': plan_obj.priority_listing if plan_obj else 0,
                    'can_sponsor_products': plan_obj.can_sponsor_products if plan_obj else False,
                    'days_until_expiry': SubscriptionChecker.get_days_until_expiry(store),
                }

        return Response({
            'success': True,
            'plans': plans_data,
            'current_plan': current_plan,
            'store_type': store.store_type if store else None
        })


class SubscribeToPlanView(APIView):
    """
    POST /api/v1/subscriptions/subscribe/
    Souscrire à un plan (Pro ou Business)
    
    Body: {
        "plan_id": 2,
        "payment_method": "admin_validation" | "mobile_money" | "wallet" | "bank_transfer"
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        from datetime import timedelta
        from payments.subscription_check import SubscriptionChecker
        
        # Vérifier que l'utilisateur est store manager
        if not request.user.is_store_manager():
            return Response({
                'success': False,
                'error': 'Seuls les gérants de magasin peuvent souscrire'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Récupérer le store
        store = Store.objects.filter(manager=request.user).first()
        if not store:
            return Response({
                'success': False,
                'error': 'Aucun magasin trouvé'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Récupérer les paramètres
        plan_id = request.data.get('plan_id')
        payment_method = request.data.get('payment_method', 'admin_validation')
        
        if not plan_id:
            return Response({
                'success': False,
                'error': 'plan_id requis'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Récupérer le plan
        try:
            plan = SubscriptionPlan.objects.get(id=plan_id, is_active=True)
        except SubscriptionPlan.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Plan introuvable'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Vérifier que ce n'est pas le plan Free
        if plan.plan_type == 'free':
            return Response({
                'success': False,
                'error': 'Impossible de souscrire au plan Free'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Calculer le prix selon le type de store (Business uniquement)
        subscription_price = SubscriptionChecker.get_subscription_price(store) if plan.plan_type == 'business' else plan.price
        
        # Expirer les abonnements actifs existants
        StoreSubscription.objects.filter(
            store=store,
            status='active'
        ).update(status='expired')
        
        # Pour l'instant, on valide manuellement (admin)
        # TODO: Implémenter Mobile Money, Wallet, Bank Transfer
        if payment_method == 'admin_validation':
            # Créer directement la souscription (à valider par admin)
            subscription = StoreSubscription.objects.create(
                store=store,
                plan=plan,
                plan_name=plan.name,
                monthly_fee=subscription_price,
                status='pending_payment',
                start_date=timezone.now().date(),
                end_date=timezone.now().date() + timedelta(days=30),
                auto_renew=False
            )
            
            return Response({
                'success': True,
                'message': f'Demande de souscription au plan {plan.name} créée. En attente de validation admin.',
                'data': {
                    'subscription_id': subscription.id,
                    'plan': plan.name,
                    'price': float(subscription_price),
                    'status': subscription.status,
                    'payment_method': 'admin_validation'
                }
            }, status=status.HTTP_201_CREATED)
        
        else:
            return Response({
                'success': False,
                'error': f'Méthode de paiement {payment_method} non implémentée pour le moment'
            }, status=status.HTTP_400_BAD_REQUEST)


# ===============================================================================
# FORFAITS CLIENTS - ENDPOINTS
# ===============================================================================

class ClientForfaitListView(APIView):
    """
    GET /api/v1/forfaits/
    Récupère la liste de tous les forfaits clients disponibles
    """
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        from .models import Forfait
        from .serializers import ForfaitSerializer
        
        forfaits = Forfait.objects.filter(is_active=True).order_by('monthly_price')
        serializer = ForfaitSerializer(forfaits, many=True)
        
        return Response({
            'success': True,
            'count': forfaits.count(),
            'forfaits': serializer.data
        })


class MyForfaitView(APIView):
    """
    GET /api/v1/my-forfait/
    Récupère le forfait actuel de l'utilisateur connecté
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        from .models import ClientForfait
        from .serializers import ClientForfaitSerializer
        
        try:
            client_forfait = ClientForfait.objects.get(user=request.user)
            serializer = ClientForfaitSerializer(client_forfait)
            
            return Response({
                'success': True,
                'forfait': serializer.data
            })
        except ClientForfait.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Utilisateur n\'a pas de forfait',
                'message': 'Veuillez choisir un forfait'
            }, status=status.HTTP_404_NOT_FOUND)


class UpgradeForfaitView(APIView):
    """
    POST /api/v1/upgrade-forfait/
    
    Upgrade le forfait de l'utilisateur
    Body:
    {
        "forfait_id": 2,
        "auto_renew": true
    }
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        from .models import Forfait, ClientForfait
        from .serializers import ClientForfaitSerializer
        from django.utils import timezone
        from datetime import timedelta
        
        forfait_id = request.data.get('forfait_id')
        auto_renew = request.data.get('auto_renew', True)
        
        if not forfait_id:
            return Response({
                'success': False,
                'error': 'forfait_id est requis'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            forfait = Forfait.objects.get(id=forfait_id, is_active=True)
        except Forfait.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Forfait non trouvé'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # TODO: Intégrer Flutterwave pour le paiement du forfait
        # Pour l'instant, on crée juste le ClientForfait
        
        client_forfait, created = ClientForfait.objects.update_or_create(
            user=request.user,
            defaults={
                'forfait': forfait,
                'start_date': timezone.now(),
                'expiration_date': timezone.now() + timedelta(days=30),
                'status': 'active',
                'auto_renew': auto_renew
            }
        )
        
        serializer = ClientForfaitSerializer(client_forfait)
        
        return Response({
            'success': True,
            'message': f'Forfait "{forfait.name}" activé avec succès',
            'forfait': serializer.data
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


# ===============================================================================
# PAYOUTS - ENDPOINTS (Paiements automatiques)
# ===============================================================================

class PayoutListView(APIView):
    """
    GET /api/v1/payouts/
    Récupère la liste des payouts de l'utilisateur connecté
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        from .models import Payout
        from .serializers import PayoutSerializer
        
        payouts = Payout.objects.filter(user=request.user).order_by('-created_at')
        
        # Filtrer par statut si demandé
        status_filter = request.query_params.get('status')
        if status_filter:
            payouts = payouts.filter(status=status_filter)
        
        serializer = PayoutSerializer(payouts, many=True)
        
        return Response({
            'success': True,
            'count': payouts.count(),
            'payouts': serializer.data
        })


class PayoutDetailView(APIView):
    """
    GET /api/v1/payouts/<int:payout_id>/
    Récupère les détails d'un payout spécifique
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, payout_id):
        from .models import Payout
        from .serializers import PayoutSerializer
        
        try:
            payout = Payout.objects.get(id=payout_id, user=request.user)
            serializer = PayoutSerializer(payout)
            
            return Response({
                'success': True,
                'payout': serializer.data
            })
        except Payout.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Payout non trouvé'
            }, status=status.HTTP_404_NOT_FOUND)


class PayoutStatisticsView(APIView):
    """
    GET /api/v1/payouts/statistics/
    Récupère les statistiques de payouts de l'utilisateur
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        from .models import Payout
        from django.db.models import Sum, Count, Q
        
        user = request.user
        
        # Statistiques générales
        total_paid = Payout.objects.filter(
            user=user,
            status='paid'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        total_pending = Payout.objects.filter(
            user=user,
            status='pending'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        count_paid = Payout.objects.filter(user=user, status='paid').count()
        count_pending = Payout.objects.filter(user=user, status='pending').count()
        count_failed = Payout.objects.filter(user=user, status='failed').count()
        
        # Statistiques par type
        by_type = {}
        for payout_type, display in Payout.TYPES:
            by_type[payout_type] = {
                'total': Payout.objects.filter(
                    user=user,
                    payout_type=payout_type,
                    status='paid'
                ).aggregate(total=Sum('amount'))['total'] or 0,
                'count': Payout.objects.filter(
                    user=user,
                    payout_type=payout_type,
                    status='paid'
                ).count()
            }
        
        return Response({
            'success': True,
            'statistics': {
                'total_paid': float(total_paid),
                'total_pending': float(total_pending),
                'count_paid': count_paid,
                'count_pending': count_pending,
                'count_failed': count_failed,
                'by_type': by_type
            }
        })

