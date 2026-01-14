"""API v1 URL router.

Register explicit views for users, stores, products and orders.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .users import (
    RegisterView, LoginView, ProfileView, RefreshTokenView
)
from .stores import (
    StoreCategoryListView, StoreListView, StoreDetailView, StoreCreateView,
    StoreUpdateView
)
from .products import (
    StoreProductsView, ProductDetailView, ProductCreateView, ProductListView,
    ProductUpdateView, ProductDeleteView, StoreProductCategoryListView, 
    StoreProductCategoryCreateView, StoreManagerProductsView
)
from .products import AllProductCategoryListView
from products.views import ProductViewSet
from .orders import (
    OrderCreateView, OrderListView, OrderDetailView, OrderStatusUpdateView,
    ClientConfirmDeliveryView
)
from .payments import (
    PaymentInitView, PaymentDetailView, PaymentWebhookView,
    ClientForfaitListView, ClientForfaitUpdateView, ForfaitListView,
    PayoutListView
)
from .webhooks import WhatsAppWebhookView
from .dashboards import (
    ClientDashboardView, StoreDashboardView, DeliveryDashboardView, DeliveryAssignedOrdersView
)
from .notifications import (
    NotificationListView, NotificationMarkAllReadView, NotificationMarkReadView,
    NotificationDeleteView
)
from .delivery import (
    DeliveryProfileUpdateView, DeliveryAcceptAssignmentView, 
    DeliveryRejectAssignmentView, DeliveryStartView, DeliveryCompleteView,
    DeliveryProofUploadView, DeliveryVerifyPINView,
    AvailableDeliveriesView, DeliveryClaimView
)
from .subscription import (
    get_subscription_status, get_available_plans, check_permission, purchase_plan
)
from .admin import (
    AdminSummaryView, AdminUsersView, AdminOrdersView, AdminFinancialsView,
    AdminStoreCategoriesView, AdminProductCategoriesView, AdminPaymentsView, AdminDeliveriesView,
    AdminStoresView, AdminProductsView, SystemSettingsView
)
from .finances import (
    FinanceDashboardView, TransactionsListView, CommissionsByStoreView,
    DeliveryPayoutView, SubscriptionsView, SponsoredProductsView, RevenueBreakdownView
    , CategoryCommissionListCreateView, CategoryCommissionDetailView
)
from .orders_admin import (
    OrderStatsView, OrdersListView, OrderDetailView as AdminOrderDetailView,
    DeliveryAssignmentView, OrderStatusUpdateView as AdminOrderStatusUpdateView,
    OrdersCancelView, OrdersByStoreView, DeliveryAgentStatsView
)
from .stores_admin import (
    StoresListView, StoreDetailView as AdminStoreDetailView, StoreCreateView as AdminStoreCreateView,
    StoreUpdateView as AdminStoreUpdateView, StoreDeactivateView, StoreActivateView,
    StoreDeleteView, StoreProductsView as AdminStoreProductsView,
    StoreOrdersView as AdminStoreOrdersView, StoreDeliveryAgentsView
)
from .products_admin import (
    ProductsListView, ProductDetailView as AdminProductDetailView,
    ProductCreateView as AdminProductCreateView, ProductUpdateView as AdminProductUpdateView,
    ProductActivateView, ProductDeactivateView, ProductDeleteView as AdminProductDeleteView,
    ProductBulkActionsView, ProductStatsView
)

router = DefaultRouter()
router.register(r'products-api', ProductViewSet, basename='product')

urlpatterns = [
    # Users / Auth
    path('auth/register/', RegisterView.as_view(), name='auth-register'),
    path('auth/login/', LoginView.as_view(), name='auth-login'),
    path('auth/profile/', ProfileView.as_view(), name='auth-profile'),
    path('auth/token/refresh/', RefreshTokenView.as_view(), name='token-refresh'),

    # Notifications
    path('notifications/', NotificationListView.as_view(), name='notifications'),
    path('notifications/mark-all-read/', NotificationMarkAllReadView.as_view(), name='notifications-mark-all'),
    path('notifications/<int:pk>/read/', NotificationMarkReadView.as_view(), name='notifications-read'),
    path('notifications/<int:pk>/', NotificationDeleteView.as_view(), name='notifications-delete'),

    # Dashboards
    path('dashboard/client/', ClientDashboardView.as_view(), name='dashboard-client'),
    path('dashboard/store/', StoreDashboardView.as_view(), name='dashboard-store'),
    path('dashboard/delivery/', DeliveryDashboardView.as_view(), name='dashboard-delivery'),
    path('dashboard/delivery/assigned-orders/', DeliveryAssignedOrdersView.as_view(), name='dashboard-delivery-assigned'),
    path('dashboard/delivery/available/', AvailableDeliveriesView.as_view(), name='dashboard-delivery-available'),
    path('dashboard/delivery/profile/update/', DeliveryProfileUpdateView.as_view(), name='delivery-profile-update'),
    path('dashboard/delivery/<int:delivery_id>/claim/', DeliveryClaimView.as_view(), name='delivery-claim'),
    path('dashboard/delivery/<int:delivery_id>/accept/', DeliveryAcceptAssignmentView.as_view(), name='delivery-accept'),
    path('dashboard/delivery/<int:delivery_id>/reject/', DeliveryRejectAssignmentView.as_view(), name='delivery-reject'),
    path('dashboard/delivery/<int:delivery_id>/start/', DeliveryStartView.as_view(), name='delivery-start'),
    path('dashboard/delivery/<int:delivery_id>/upload-proof/', DeliveryProofUploadView.as_view(), name='delivery-proof-upload'),
    path('dashboard/delivery/<int:delivery_id>/verify-pin/', DeliveryVerifyPINView.as_view(), name='delivery-verify-pin'),
    path('dashboard/delivery/<int:delivery_id>/complete/', DeliveryCompleteView.as_view(), name='delivery-complete'),
    
    # Subscription / Forfaits (Dashboard)
    path('dashboard/subscription/status/', get_subscription_status, name='subscription-status'),
    path('dashboard/subscription/plans/', get_available_plans, name='subscription-plans'),
    path('dashboard/subscription/check-permission/', check_permission, name='subscription-check-permission'),
    path('dashboard/subscription/purchase/', purchase_plan, name='subscription-purchase'),

    # Admin (plateforme)
    path('admin/summary/', AdminSummaryView.as_view(), name='admin-summary'),
    path('admin/users/', AdminUsersView.as_view(), name='admin-users'),
    path('admin/orders/', AdminOrdersView.as_view(), name='admin-orders'),
    path('admin/financials/', AdminFinancialsView.as_view(), name='admin-financials'),
    path('admin/store-categories/', AdminStoreCategoriesView.as_view(), name='admin-store-categories'),
    path('admin/stores/', AdminStoresView.as_view(), name='admin-stores'),
    path('admin/product-categories/', AdminProductCategoriesView.as_view(), name='admin-product-categories'),
    path('admin/products/', AdminProductsView.as_view(), name='admin-products'),
    path('admin/payments/', AdminPaymentsView.as_view(), name='admin-payments'),
    path('admin/deliveries/', AdminDeliveriesView.as_view(), name='admin-deliveries'),
    
    # Finance Module
    path('finance/dashboard/', FinanceDashboardView.as_view(), name='finance-dashboard'),
    path('finance/transactions/', TransactionsListView.as_view(), name='finance-transactions'),
    path('finance/commissions/', CommissionsByStoreView.as_view(), name='finance-commissions'),
    path('finance/delivery-payouts/', DeliveryPayoutView.as_view(), name='finance-delivery-payouts'),
    path('finance/subscriptions/', SubscriptionsView.as_view(), name='finance-subscriptions'),
    path('finance/sponsored-products/', SponsoredProductsView.as_view(), name='finance-sponsored'),
    path('finance/revenue-breakdown/', RevenueBreakdownView.as_view(), name='finance-breakdown'),
    path('finance/category-commissions/', CategoryCommissionListCreateView.as_view(), name='finance-category-commissions'),
    path('finance/category-commissions/<int:pk>/', CategoryCommissionDetailView.as_view(), name='finance-category-commission-detail'),
    
    # Orders Admin Management
    path('admin/orders/stats/', OrderStatsView.as_view(), name='orders-stats'),
    path('admin/orders/list/', OrdersListView.as_view(), name='orders-list-admin'),
    path('admin/orders/<int:order_id>/', AdminOrderDetailView.as_view(), name='orders-detail-admin'),
    path('admin/orders/<int:order_id>/assign-delivery/', DeliveryAssignmentView.as_view(), name='orders-assign-delivery'),
    path('admin/orders/<int:order_id>/cancel/', OrdersCancelView.as_view(), name='orders-cancel'),
    path('admin/orders/by-store/', OrdersByStoreView.as_view(), name='orders-by-store'),
    path('admin/delivery-agents/stats/', DeliveryAgentStatsView.as_view(), name='delivery-agents-stats'),
    
    # Stores Admin Management
    path('admin/stores/list/', StoresListView.as_view(), name='admin-stores-list'),
    path('admin/stores/create/', AdminStoreCreateView.as_view(), name='admin-stores-create'),
    path('admin/stores/<int:store_id>/detail/', AdminStoreDetailView.as_view(), name='admin-stores-detail'),
    path('admin/stores/<int:store_id>/update/', AdminStoreUpdateView.as_view(), name='admin-stores-update'),
    path('admin/stores/<int:store_id>/deactivate/', StoreDeactivateView.as_view(), name='admin-stores-deactivate'),
    path('admin/stores/<int:store_id>/activate/', StoreActivateView.as_view(), name='admin-stores-activate'),
    path('admin/stores/<int:store_id>/', StoreDeleteView.as_view(), name='admin-stores-delete'),
    path('admin/stores/<int:store_id>/products/', AdminStoreProductsView.as_view(), name='admin-stores-products'),
    path('admin/stores/<int:store_id>/orders/', AdminStoreOrdersView.as_view(), name='admin-stores-orders'),
    path('admin/stores/<int:store_id>/delivery-agents/', StoreDeliveryAgentsView.as_view(), name='admin-stores-delivery-agents'),
    
    # Products Admin Management
    path('admin/products/stats/', ProductStatsView.as_view(), name='admin-products-stats'),
    path('admin/products/list/', ProductsListView.as_view(), name='admin-products-list'),
    path('admin/products/create/', AdminProductCreateView.as_view(), name='admin-products-create'),
    path('admin/products/bulk-actions/', ProductBulkActionsView.as_view(), name='admin-products-bulk'),
    path('admin/products/<int:product_id>/detail/', AdminProductDetailView.as_view(), name='admin-products-detail'),
    path('admin/products/<int:product_id>/update/', AdminProductUpdateView.as_view(), name='admin-products-update'),
    path('admin/products/<int:product_id>/activate/', ProductActivateView.as_view(), name='admin-products-activate'),
    path('admin/products/<int:product_id>/deactivate/', ProductDeactivateView.as_view(), name='admin-products-deactivate'),
    path('admin/products/<int:product_id>/', AdminProductDeleteView.as_view(), name='admin-products-delete'),
    
    # System Settings (public)
    path('settings/', SystemSettingsView.as_view(), name='system-settings'),

    # Stores
    path('stores/categories/', StoreCategoryListView.as_view(), name='store-categories'),
    path('stores/', StoreListView.as_view(), name='store-list'),
    path('stores/create/', StoreCreateView.as_view(), name='store-create'),
    path('stores/<int:pk>/', StoreDetailView.as_view(), name='store-detail'),
    path('stores/<int:pk>/update/', StoreUpdateView.as_view(), name='store-update'),

    # Products
    path('products/', ProductListView.as_view(), name='product-list-all'),
    path('stores/<int:store_id>/products/', StoreProductsView.as_view(), name='store-products'),
    path('stores/<int:store_id>/products/manager/', StoreManagerProductsView.as_view(), name='store-manager-products'),
    path('stores/<int:store_id>/products/create/', ProductCreateView.as_view(), name='product-create'),
    path('stores/<int:store_id>/categories/', StoreProductCategoryListView.as_view(), name='store-product-categories'),
    path('stores/<int:store_id>/categories/create/', StoreProductCategoryCreateView.as_view(), name='store-product-category-create'),
    path('products/categories/', AllProductCategoryListView.as_view(), name='product-categories'),
    path('products/<int:pk>/', ProductDetailView.as_view(), name='product-detail'),
    path('products/<int:pk>/update/', ProductUpdateView.as_view(), name='product-update'),
    path('products/<int:pk>/delete/', ProductDeleteView.as_view(), name='product-delete'),

    # Orders
    path('orders/', OrderListView.as_view(), name='order-list'),
    path('orders/create/', OrderCreateView.as_view(), name='order-create'),
    path('orders/<int:pk>/', OrderDetailView.as_view(), name='order-detail'),
    path('orders/<int:order_id>/status/', OrderStatusUpdateView.as_view(), name='order-status-update'),
    path('orders/<int:order_id>/confirm-delivery/', ClientConfirmDeliveryView.as_view(), name='client-confirm-delivery'),

    # Payments
    path('orders/<int:order_id>/payments/init/', PaymentInitView.as_view(), name='payment-init'),
    path('orders/<int:order_id>/payments/', PaymentDetailView.as_view(), name='payment-detail'),
    path('payments/webhook/', PaymentWebhookView.as_view(), name='payment-webhook'),
    
    # Forfaits Clients (Plans/Subscriptions)
    path('forfaits/', ForfaitListView.as_view(), name='forfaits-list'),
    path('my-forfait/', ClientForfaitListView.as_view(), name='my-forfait'),
    path('my-forfait/update/', ClientForfaitUpdateView.as_view(), name='update-forfait'),
    
    # Payouts (Paiements automatiques aux livreurs et commerçants)
    path('payouts/', PayoutListView.as_view(), name='payouts-list'),

    path('', include(router.urls)),
    # Webhooks
    path('webhooks/whatsapp/', WhatsAppWebhookView.as_view(), name='whatsapp-webhook'),
    
    # B2B
    path('b2b/', include('b2b.urls')),
]
