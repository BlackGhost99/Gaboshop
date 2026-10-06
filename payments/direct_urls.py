from django.urls import path
from .direct_views import (
    PaymentOptionsView, StorePaymentPreferencesView, ArrangementDetailView,
    ReceiptCreateView, PendingReceiptsView, ReceiptConfirmView, ReceiptRejectView, SettlementListCreateView, SettlementConfirmView, FinancialControlView,
)

urlpatterns = [
    path('options/', PaymentOptionsView.as_view(), name='payment-options'),
    path('preferences/', StorePaymentPreferencesView.as_view(), name='payment-preferences'),
    path('arrangements/order/<int:order_id>/', ArrangementDetailView.as_view(), name='payment-arrangement-detail'),
    path('receipts/', ReceiptCreateView.as_view(), name='payment-receipt-create'),
    path('receipts/pending/', PendingReceiptsView.as_view(), name='payment-receipts-pending'),
    path('receipts/<int:receipt_id>/confirm/', ReceiptConfirmView.as_view(), name='payment-receipt-confirm'),
    path('receipts/<int:receipt_id>/reject/', ReceiptRejectView.as_view(), name='payment-receipt-reject'),
    path('settlements/', SettlementListCreateView.as_view(), name='commission-settlement-list-create'),
    path('settlements/<int:settlement_id>/confirm/', SettlementConfirmView.as_view(), name='commission-settlement-confirm'),
    path('financial-control/', FinancialControlView.as_view(), name='financial-control'),
]
