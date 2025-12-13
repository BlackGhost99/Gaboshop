"""
Vues pour l'intégration CinetPay / Airtel Money / Moov Money
- Création de PaymentIntent
- Callbacks des providers
- Vérification et refund
"""

import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.utils import timezone
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
            payload.get("transaction_id") or
            (payload.get("data") or {}).get("transaction_id") or
            payload.get("transaction")
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
            payload.get("api_response_id") or
            (payload.get("data") or {}).get("api_response_id") or
            f"{provider}-{reference}"
        )
        amount = int(float((
            payload.get("amount") or
            (payload.get("data") or {}).get("amount") or 0
        )))
        status_str = (
            (payload.get("status") or (payload.get("data") or {}).get("status") or "")
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
        accepted_statuses = ("ACCEPTED", "APPROVED", "SUCCESS", "OK", "00")
        is_success = (
            status_str in accepted_statuses or
            payload.get("code") in ("00", "201") or
            (payload.get("message") and "CREATED" in str(payload.get("message")).upper())
        )

        if is_success:
            logger.info(f"✅ Paiement confirmé: {intent.reference}")
            intent.status = "SUCCESS"
            intent.save()
            tx.status = "SUCCESS"
            tx.processed = True
            tx.raw_response = payload
            tx.save()

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
        amount = int(request.data.get("amount", 0))
        
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

        logger.info(f"💰 Refund initié: {reference} | Montant: {amount}")

        # Appeler le provider
        if intent.provider == "cinetpay":
            res = call_cinetpay_refund(reference, amount)
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

        intent.status = "REFUNDED"
        intent.save()

        # Mettre à jour la commande
        if intent.order and hasattr(intent.order, 'mark_as_refunded'):
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
        plans_qs = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
        plans_data = SubscriptionPlanSerializer(plans_qs, many=True).data

        current_plan = None
        store = Store.objects.filter(manager=request.user).first()
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
                    'price': float(plan_obj.price) if plan_obj else float(active_sub.monthly_fee),
                    'commission_rate': float(plan_obj.commission_rate) if plan_obj and plan_obj.commission_rate is not None else None,
                    'end_date': active_sub.end_date,
                    'status': active_sub.status,
                    'auto_renew': active_sub.auto_renew,
                    'features': active_sub.get_plan_features(),
                    'max_products': plan_obj.max_products if plan_obj else None,
                    'priority_listing': plan_obj.priority_listing if plan_obj else 0,
                    'can_sponsor_products': plan_obj.can_sponsor_products if plan_obj else False,
                }

        return Response({
            'plans': plans_data,
            'current_plan': current_plan
        })


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
