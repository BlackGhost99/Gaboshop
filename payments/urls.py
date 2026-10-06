from django.urls import include, path
from .views import (
    CreatePaymentAPIView,
    ProviderCallbackAPIView,
    CheckPaymentAPIView,
    RefundAPIView,
    SubscriptionPlansAPIView,
    SubscribeToPlanView,
    SubscriptionPaymentIntentAPIView,
)

urlpatterns = [
    path('', include('payments.direct_urls')),
    # Anciens webhooks Airtel/Moov retirés : sans signature, n'importe qui pouvait marquer un paiement comme payé.
    # Le webhook signé est /api/v1/payments/webhook/ (PaymentWebhookView).
    
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
    
    # Plans d'abonnement (Free / Pro / Business)
    path("subscription-plans/", SubscriptionPlansAPIView.as_view(), name="subscription-plans"),
    
    # Souscrire à un plan
    path("subscriptions/subscribe/", SubscribeToPlanView.as_view(), name="subscribe-to-plan"),
    # Souscription par paiement (Airtel/Moov/Cinetpay)
    path("subscriptions/intent/", SubscriptionPaymentIntentAPIView.as_view(), name="subscribe-payment-intent"),
]
