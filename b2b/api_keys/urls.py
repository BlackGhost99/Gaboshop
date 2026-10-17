"""Routes de l'accès API des grossistes, montées sous /api/v1/b2b/."""
from django.urls import path

from b2b.api_keys import views

urlpatterns = [
    path('api-keys/', views.ApiKeyListCreateView.as_view(), name='b2b-api-keys'),
    path('api-keys/<int:key_id>/revoke/', views.ApiKeyRevokeView.as_view(), name='b2b-api-key-revoke'),
    path('integration/products/', views.IntegrationProductListView.as_view(), name='b2b-integration-products'),
    path('integration/products/<int:product_id>/', views.IntegrationProductDetailView.as_view(),
         name='b2b-integration-product'),
    path('integration/orders/', views.IntegrationOrderListView.as_view(), name='b2b-integration-orders'),
    path('integration/orders/<int:order_id>/', views.IntegrationOrderDetailView.as_view(),
         name='b2b-integration-order'),
]
