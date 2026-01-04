"""
URLs pour le module B2B
"""
from django.urls import path
from b2b.api.views import (
    # Endpoints pour les store managers
    WholesalerListView,
    WholesalerDetailView,
    WholesalerProductsView,
    WholesalerCategoriesView,
    WholesalerCatalogView,
    B2BOrderCreateView,
    MyB2BOrdersView,
    
    # Endpoints admin pour la gestion des profils B2B
    B2BProfileDetailView,
    B2BProfileCreateView,
    B2BProfileUpdateView,
    B2BProfileActivateView,
    B2BProfileDeactivateView,
    
    # Endpoints admin pour la gestion des prix B2B
    B2BProductPricingListView,
    B2BProductPricingCreateView,
    B2BProductPricingUpdateView,
    B2BProductPricingDeleteView,
    B2BProductPricingBulkCreateView,
)

app_name = 'b2b'

urlpatterns = [
    # ==================== STORE MANAGER ENDPOINTS ====================
    # Grossistes (wholesalers)
    path('wholesalers/', WholesalerListView.as_view(), name='wholesalers-list'),
    path('wholesalers/<int:id>/', WholesalerDetailView.as_view(), name='wholesaler-detail'),
    path('wholesalers/<int:id>/products/', WholesalerProductsView.as_view(), name='wholesaler-products'),
    path('wholesalers/<int:id>/categories/', WholesalerCategoriesView.as_view(), name='wholesaler-categories'),
    path('wholesalers/<int:id>/catalog/', WholesalerCatalogView.as_view(), name='wholesaler-catalog'),
    
    # Commandes B2B
    path('orders/', B2BOrderCreateView.as_view(), name='b2b-order-create'),
    path('my-orders/', MyB2BOrdersView.as_view(), name='my-b2b-orders'),
    
    # ==================== ADMIN ENDPOINTS ====================
    # Gestion des profils B2B
    path('profiles/<int:store_id>/', B2BProfileDetailView.as_view(), name='b2b-profile-detail'),
    path('profiles/', B2BProfileCreateView.as_view(), name='b2b-profile-create'),
    path('profiles/<int:store_id>/update/', B2BProfileUpdateView.as_view(), name='b2b-profile-update'),
    path('profiles/<int:store_id>/activate/', B2BProfileActivateView.as_view(), name='b2b-profile-activate'),
    path('profiles/<int:store_id>/deactivate/', B2BProfileDeactivateView.as_view(), name='b2b-profile-deactivate'),
    
    # Gestion des prix B2B
    path('pricing/<int:store_id>/', B2BProductPricingListView.as_view(), name='b2b-pricing-list'),
    path('pricing/', B2BProductPricingCreateView.as_view(), name='b2b-pricing-create'),
    path('pricing/<int:pricing_id>/update/', B2BProductPricingUpdateView.as_view(), name='b2b-pricing-update'),
    path('pricing/<int:pricing_id>/delete/', B2BProductPricingDeleteView.as_view(), name='b2b-pricing-delete'),
    path('pricing/bulk/', B2BProductPricingBulkCreateView.as_view(), name='b2b-pricing-bulk'),
]

