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
    ClientConfirmDeliveryView, OrderSelectVehicleView
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
    AvailableDeliveriesView, DeliveryClaimView,
    VehicleTypeListView, VehicleTypeDetailView, DeliveryCalculatePriceView,
    DeliveryValidateVehicleView, EligibleVehiclesView, DeliveryZonesListView
)
from delivery.admin_dashboard import (
    DeliveryTariffAnalyticsView, DeliveryZoneHealthCheckView
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
    DeliveryPayoutView, SubscriptionsView, SponsoredProductsView, RevenueBreakdownView,
    CategoryCommissionListCreateView, CategoryCommissionDetailView,
    ReversementListView, ReversementCreateView, ReversementUpdateView,
    CommissionListView, CommissionSettleView,
    CategoryCommissionChangeLogListView,
    DeliveryPayoutUpdateView,
    SponsoredProductCreateView, SponsoredProductUpdateView,
    ClientCreditListView, ClientCreditCreateView, ClientCreditUpdateView,
    ForfaitListView, ForfaitCreateView, ForfaitUpdateView,
    ClientForfaitListView, ClientForfaitCreateView, ClientForfaitUpdateView
)
from .subscriptions_admin import (
    SubscriptionPlanListView, SubscriptionPlanCreateView, SubscriptionPlanDetailView,
    SubscriptionPlanUpdateView, SubscriptionPlanDeleteView,
    B2BSubscriptionPlanListView, B2BSubscriptionPlanCreateView, B2BSubscriptionPlanDetailView,
    B2BSubscriptionPlanUpdateView, B2BSubscriptionPlanDeleteView,
    StoreSubscriptionListView, StoreSubscriptionCreateView, StoreSubscriptionUpdateView,
    B2BStoreSubscriptionListView, B2BStoreSubscriptionCreateView, B2BStoreSubscriptionUpdateView
)
from .b2b_admin import (
    B2BCategoryListView, B2BCategoryCreateView, B2BCategoryUpdateView, B2BCategoryDeleteView,
    B2BOrderListView, B2BOrderDetailView, B2BOrderStatusUpdateView
)
from .payments_admin import (
    PaymentCallbackLogListView, PaymentCallbackLogDetailView,
    PayoutListView as AdminPayoutListView, PayoutCreateView, PayoutUpdateView
)
from b2b.api.views import (
    WholesalerListView, WholesalerDetailView, WholesalerProductsView,
    WholesalerCategoriesView, WholesalerCatalogView, B2BOrderCreateView,
    MyB2BOrdersView, B2BProfileDetailView, B2BProfileCreateView,
    B2BProfileUpdateView, B2BProfileActivateView, B2BProfileDeactivateView,
    B2BProductPricingListView, B2BProductPricingCreateView,
    B2BProductPricingUpdateView, B2BProductPricingDeleteView,
    B2BProductPricingBulkCreateView
)
from .b2c_admin import B2CProductPricingListView
from .orders_admin import (
    OrderStatsView, OrdersListView, OrderDetailView as AdminOrderDetailView,
    DeliveryAssignmentView, OrderStatusUpdateView as AdminOrderStatusUpdateView,
    OrdersCancelView, OrdersByStoreView, DeliveryAgentStatsView
)
from .stores_admin import (
    StoresListView, StoreDetailView as AdminStoreDetailView, StoreCreateView as AdminStoreCreateView,
    StoreUpdateView as AdminStoreUpdateView, StoreB2BSettingsUpdateView, StoreB2CSettingsUpdateView, StoreDeactivateView, StoreActivateView,
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
    
    # Vehicle types endpoints
    path('delivery/vehicle-types/', VehicleTypeListView.as_view(), name='vehicle-types-list'),
    path('delivery/vehicle-types/<int:vehicle_type_id>/', VehicleTypeDetailView.as_view(), name='vehicle-type-detail'),
    path('delivery/zones/', DeliveryZonesListView.as_view(), name='delivery-zones-list'),
    path('delivery/calculate-price/', DeliveryCalculatePriceView.as_view(), name='delivery-calculate-price'),
    path('delivery/validate-vehicle/', DeliveryValidateVehicleView.as_view(), name='delivery-validate-vehicle'),
    path('delivery/eligible-vehicles/<int:order_id>/', EligibleVehiclesView.as_view(), name='eligible-vehicles'),
    
    # Subscription / Forfaits (Dashboard)
    path('dashboard/subscription/status/', get_subscription_status, name='subscription-status'),
    path('dashboard/subscription/plans/', get_available_plans, name='subscription-plans'),
    path('dashboard/subscription/check-permission/', check_permission, name='subscription-check-permission'),
    path('dashboard/subscription/purchase/', purchase_plan, name='subscription-purchase'),

    # Admin (plateforme)
    path('admin/summary/', AdminSummaryView.as_view(), name='admin-summary'),
    path('admin/users/', AdminUsersView.as_view(), name='admin-users'),
    path('admin/orders/', AdminOrdersView.as_view(), name='admin-orders'),
    path('admin/delivery/tariff-analytics/', DeliveryTariffAnalyticsView.as_view(), name='delivery-tariff-analytics'),
    path('admin/delivery/zone-health/', DeliveryZoneHealthCheckView.as_view(), name='delivery-zone-health'),
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
    
    # Finance Admin Extended
    path('admin/finance/reversements/', ReversementListView.as_view(), name='admin-finance-reversements'),
    path('admin/finance/reversements/create/', ReversementCreateView.as_view(), name='admin-finance-reversements-create'),
    path('admin/finance/reversements/<int:reversement_id>/', ReversementUpdateView.as_view(), name='admin-finance-reversements-update'),
    path('admin/finance/commissions/', CommissionListView.as_view(), name='admin-finance-commissions'),
    path('admin/finance/commissions/<int:commission_id>/settle/', CommissionSettleView.as_view(), name='admin-finance-commissions-settle'),
    path('admin/finance/category-commission-logs/', CategoryCommissionChangeLogListView.as_view(), name='admin-finance-category-commission-logs'),
    path('admin/finance/delivery-payouts/<int:payout_id>/', DeliveryPayoutUpdateView.as_view(), name='admin-finance-delivery-payouts-update'),
    path('admin/finance/sponsored-products/create/', SponsoredProductCreateView.as_view(), name='admin-finance-sponsored-products-create'),
    path('admin/finance/sponsored-products/<int:sponsored_id>/', SponsoredProductUpdateView.as_view(), name='admin-finance-sponsored-products-update'),
    path('admin/finance/client-credits/', ClientCreditListView.as_view(), name='admin-finance-client-credits'),
    path('admin/finance/client-credits/create/', ClientCreditCreateView.as_view(), name='admin-finance-client-credits-create'),
    path('admin/finance/client-credits/<int:credit_id>/', ClientCreditUpdateView.as_view(), name='admin-finance-client-credits-update'),
    path('admin/finance/forfaits/', ForfaitListView.as_view(), name='admin-finance-forfaits'),
    path('admin/finance/forfaits/create/', ForfaitCreateView.as_view(), name='admin-finance-forfaits-create'),
    path('admin/finance/forfaits/<int:forfait_id>/', ForfaitUpdateView.as_view(), name='admin-finance-forfaits-update'),
    path('admin/finance/client-forfaits/', ClientForfaitListView.as_view(), name='admin-finance-client-forfaits'),
    path('admin/finance/client-forfaits/create/', ClientForfaitCreateView.as_view(), name='admin-finance-client-forfaits-create'),
    path('admin/finance/client-forfaits/<int:client_forfait_id>/', ClientForfaitUpdateView.as_view(), name='admin-finance-client-forfaits-update'),
    
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
    path('admin/stores/<int:store_id>/b2b-settings/', StoreB2BSettingsUpdateView.as_view(), name='admin-stores-b2b-settings'),
    path('admin/stores/<int:store_id>/b2c-settings/', StoreB2CSettingsUpdateView.as_view(), name='admin-stores-b2c-settings'),
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
    
    # Subscription Plans Admin
    path('admin/subscription-plans/', SubscriptionPlanListView.as_view(), name='admin-subscription-plans'),
    path('admin/subscription-plans/create/', SubscriptionPlanCreateView.as_view(), name='admin-subscription-plans-create'),
    path('admin/subscription-plans/<int:plan_id>/', SubscriptionPlanDetailView.as_view(), name='admin-subscription-plans-detail'),
    path('admin/subscription-plans/<int:plan_id>/update/', SubscriptionPlanUpdateView.as_view(), name='admin-subscription-plans-update'),
    path('admin/subscription-plans/<int:plan_id>/delete/', SubscriptionPlanDeleteView.as_view(), name='admin-subscription-plans-delete'),
    path('admin/b2b-subscription-plans/', B2BSubscriptionPlanListView.as_view(), name='admin-b2b-subscription-plans'),
    path('admin/b2b-subscription-plans/create/', B2BSubscriptionPlanCreateView.as_view(), name='admin-b2b-subscription-plans-create'),
    path('admin/b2b-subscription-plans/<int:plan_id>/', B2BSubscriptionPlanDetailView.as_view(), name='admin-b2b-subscription-plans-detail'),
    path('admin/b2b-subscription-plans/<int:plan_id>/update/', B2BSubscriptionPlanUpdateView.as_view(), name='admin-b2b-subscription-plans-update'),
    path('admin/b2b-subscription-plans/<int:plan_id>/delete/', B2BSubscriptionPlanDeleteView.as_view(), name='admin-b2b-subscription-plans-delete'),
    path('admin/store-subscriptions/', StoreSubscriptionListView.as_view(), name='admin-store-subscriptions'),
    path('admin/store-subscriptions/create/', StoreSubscriptionCreateView.as_view(), name='admin-store-subscriptions-create'),
    path('admin/store-subscriptions/<int:subscription_id>/', StoreSubscriptionUpdateView.as_view(), name='admin-store-subscriptions-update'),
    path('admin/b2b-store-subscriptions/', B2BStoreSubscriptionListView.as_view(), name='admin-b2b-store-subscriptions'),
    path('admin/b2b-store-subscriptions/create/', B2BStoreSubscriptionCreateView.as_view(), name='admin-b2b-store-subscriptions-create'),
    path('admin/b2b-store-subscriptions/<int:subscription_id>/', B2BStoreSubscriptionUpdateView.as_view(), name='admin-b2b-store-subscriptions-update'),
    
    # B2B Admin
    path('admin/b2b/categories/', B2BCategoryListView.as_view(), name='admin-b2b-categories'),
    path('admin/b2b/categories/create/', B2BCategoryCreateView.as_view(), name='admin-b2b-categories-create'),
    path('admin/b2b/categories/<int:category_id>/', B2BCategoryUpdateView.as_view(), name='admin-b2b-categories-update'),
    path('admin/b2b/categories/<int:category_id>/delete/', B2BCategoryDeleteView.as_view(), name='admin-b2b-categories-delete'),
    path('admin/b2b/orders/', B2BOrderListView.as_view(), name='admin-b2b-orders'),
    path('admin/b2b/orders/<int:order_id>/', B2BOrderDetailView.as_view(), name='admin-b2b-orders-detail'),
    path('admin/b2b/orders/<int:order_id>/status/', B2BOrderStatusUpdateView.as_view(), name='admin-b2b-orders-status'),
    
    # Payments Admin
    path('admin/payment-callbacks/', PaymentCallbackLogListView.as_view(), name='admin-payment-callbacks'),
    path('admin/payment-callbacks/<int:log_id>/', PaymentCallbackLogDetailView.as_view(), name='admin-payment-callbacks-detail'),
    path('admin/payouts/', AdminPayoutListView.as_view(), name='admin-payouts'),
    path('admin/payouts/create/', PayoutCreateView.as_view(), name='admin-payouts-create'),
    path('admin/payouts/<int:payout_id>/', PayoutUpdateView.as_view(), name='admin-payouts-update'),

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
    path('orders/<int:order_id>/select-vehicle/', OrderSelectVehicleView.as_view(), name='order-select-vehicle'),

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

    # B2B Endpoints
    path('b2b/wholesalers/', WholesalerListView.as_view(), name='b2b-wholesalers'),
    path('b2b/wholesalers/<int:pk>/', WholesalerDetailView.as_view(), name='b2b-wholesaler-detail'),
    path('b2b/wholesalers/<int:id>/products/', WholesalerProductsView.as_view(), name='b2b-wholesaler-products'),
    path('b2b/wholesalers/<int:id>/categories/', WholesalerCategoriesView.as_view(), name='b2b-wholesaler-categories'),
    path('b2b/wholesalers/<int:id>/catalog/', WholesalerCatalogView.as_view(), name='b2b-wholesaler-catalog'),
    path('b2b/orders/', B2BOrderCreateView.as_view(), name='b2b-order-create'),
    path('b2b/my-orders/', MyB2BOrdersView.as_view(), name='b2b-my-orders'),
    path('b2b/profiles/', B2BProfileCreateView.as_view(), name='b2b-profile-create'),
    path('b2b/profiles/<int:store_id>/', B2BProfileDetailView.as_view(), name='b2b-profile-detail'),
    path('b2b/profiles/<int:store_id>/update/', B2BProfileUpdateView.as_view(), name='b2b-profile-update'),
    path('b2b/profiles/<int:store_id>/activate/', B2BProfileActivateView.as_view(), name='b2b-profile-activate'),
    path('b2b/profiles/<int:store_id>/deactivate/', B2BProfileDeactivateView.as_view(), name='b2b-profile-deactivate'),
    path('b2b/pricing/<int:store_id>/', B2BProductPricingListView.as_view(), name='b2b-pricings'),
    path('b2b/pricing/', B2BProductPricingCreateView.as_view(), name='b2b-pricing-create'),
    path('b2b/pricing/bulk/', B2BProductPricingBulkCreateView.as_view(), name='b2b-pricing-bulk-create'),
    path('b2b/pricing/<int:pricing_id>/', B2BProductPricingUpdateView.as_view(), name='b2b-pricing-update'),
    path('b2b/pricing/<int:pricing_id>/delete/', B2BProductPricingDeleteView.as_view(), name='b2b-pricing-delete'),
    
    # B2C Endpoints
    path('admin/b2c/pricing/<int:store_id>/', B2CProductPricingListView.as_view(), name='b2c-pricings'),

    path('', include(router.urls)),
    # Webhooks
    path('webhooks/whatsapp/', WhatsAppWebhookView.as_view(), name='whatsapp-webhook'),
    
    # B2B
    path('b2b/', include('b2b.urls')),
    
    # Store Finance Module (Store-level financial management)
    path('store/finance/', include('finance.urls')),
    
    # AI Module
    path('ai/', include('api.v1.ai.urls')),
]
