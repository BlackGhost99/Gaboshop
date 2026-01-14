"""
URLs pour l'API B2B
"""

from django.urls import path
from b2b.api.views import (
	WholesalerListView,
	WholesalerDetailView,
	WholesalerProductsView,
	WholesalerCategoriesView,
	B2BOrderCreateView,
	MyB2BOrdersView,
	B2BProfileCreateView,
	B2BProfileDetailView,
	B2BProfileUpdateView,
	B2BProfileActivateView,
	B2BProfileDeactivateView,
)

app_name = 'b2b'

urlpatterns = [
	# Liste des grossistes
	path('wholesalers/', WholesalerListView.as_view(), name='wholesalers-list'),
	
	# Détails d'un grossiste
	path('wholesalers/<int:id>/', WholesalerDetailView.as_view(), name='wholesaler-detail'),
	
	# Produits B2B d'un grossiste
	path('wholesalers/<int:id>/products/', WholesalerProductsView.as_view(), name='wholesaler-products'),
	
	# Catégories B2B d'un grossiste
	path('wholesalers/<int:id>/categories/', WholesalerCategoriesView.as_view(), name='wholesaler-categories'),
	
	# Créer une commande B2B
	path('orders/', B2BOrderCreateView.as_view(), name='order-create'),
	
	# Mes commandes B2B
	path('my-orders/', MyB2BOrdersView.as_view(), name='my-orders'),
	
	# Admin - Gestion des profils B2B (routes spécifiques avant la route générique)
	path('profiles/<int:store_id>/update/', B2BProfileUpdateView.as_view(), name='profile-update'),
	path('profiles/<int:store_id>/activate/', B2BProfileActivateView.as_view(), name='profile-activate'),
	path('profiles/<int:store_id>/deactivate/', B2BProfileDeactivateView.as_view(), name='profile-deactivate'),
	path('profiles/<int:store_id>/', B2BProfileDetailView.as_view(), name='profile-detail'),
	path('profiles/', B2BProfileCreateView.as_view(), name='profile-create'),
]




