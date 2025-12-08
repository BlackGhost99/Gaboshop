from django.urls import path
from . import webhooks
from .views import (
    CreatePaymentAPIView,
    ProviderCallbackAPIView,
    CheckPaymentAPIView,
    RefundAPIView,
    SubscriptionPlansAPIView,
)

urlpatterns = [
    # Anciens webhooks (conservés pour compatibilité)
    path('webhooks/airtel/', webhooks.airtel_money_webhook, name='webhook_airtel'),
    path('webhooks/moov/', webhooks.moov_money_webhook, name='webhook_moov'),
    
    # ============================================================================
    # NOUVEAUX ENDPOINTS CINETPAY / AIRTEL / MOOV
    # ============================================================================
    
    # Créer un paiement
    path("create/", CreatePaymentAPIView.as_view(), name="payment-create"),
    
    # Callbacks des providers
    path(
        "provider/<str:provider>/notify/",
        ProviderCallbackAPIView.as_view(),
        name="provider-callback"
    ),
    
    # Test de notification (GET + POST)
    path(
        "provider/<str:provider>/test-notification/",
        ProviderCallbackAPIView.as_view(),
        name="provider-test-notification"
    ),
    
    # Vérifier le statut
    path("check/", CheckPaymentAPIView.as_view(), name="payment-check"),
    
    # Rembourser
    path("refund/", RefundAPIView.as_view(), name="payment-refund"),
    
    # Plans d'abonnement (Starter / Pro / Business)
    path("subscription-plans/", SubscriptionPlansAPIView.as_view(), name="subscription-plans"),
]
