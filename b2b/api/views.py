"""
Vues API pour le module B2B
"""

from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListAPIView, RetrieveAPIView
from django.shortcuts import get_object_or_404
from django.db import transaction

from django.db.models import Q
from stores.models import Store
from orders.models import Order, OrderItem
from b2b.models import B2BProfile, B2BCategory, B2BProductPricing
from b2b.services.permissions import (
	can_access_b2b, 
	can_purchase_from_wholesaler,
	can_purchase_from_self,
	must_be_b2c_store
)
from b2b.services.supply import (
	get_available_wholesalers,
	get_b2b_products,
	get_b2b_categories,
	validate_b2b_order
)
from b2b.api.serializers import (
	WholesalerSerializer,
	B2BProfileSerializer,
	B2BCategorySerializer,
	B2BProductSerializer,
	B2BOrderCreateSerializer,
	B2BOrderSerializer,
	B2BCatalogProductSerializer,
	B2BCatalogCategorySerializer,
)


class IsPlatformAdmin(permissions.BasePermission):
	"""Only platform admins can access"""
	def has_permission(self, request, view):
		user = request.user
		return bool(user and user.is_authenticated and (user.is_staff or getattr(user, 'user_type', '') == 'admin'))


class IsStoreManager(permissions.BasePermission):
	"""Seuls les store_managers peuvent accéder"""
	def has_permission(self, request, view):
		return bool(
			request.user and 
			request.user.is_authenticated and 
			request.user.user_type == 'store_manager'
		)


class WholesalerListView(ListAPIView):
	"""
	GET /api/b2b/wholesalers/
	Liste des grossistes disponibles
	"""
	permission_classes = [IsAuthenticated, IsStoreManager]
	serializer_class = WholesalerSerializer
	
	def get_queryset(self):
		"""Retourne les grossistes disponibles pour le magasin connecté"""
		user = self.request.user
		
		# Vérifier les permissions
		if not can_access_b2b(user):
			return Store.objects.none()
		
		# Récupérer le magasin du gérant connecté
		buyer_store = Store.objects.filter(
			manager=user,
			is_b2c=True,
			is_active=True
		).first()
		
		return get_available_wholesalers(buyer_store)
	
	def list(self, request, *args, **kwargs):
		"""Liste des grossistes avec vérification des permissions"""
		if not can_access_b2b(request.user):
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_403_FORBIDDEN,
					'message': 'Vous n\'êtes pas autorisé à accéder au B2B'
				}
			}, status=status.HTTP_403_FORBIDDEN)
		
		queryset = self.get_queryset()
		serializer = self.get_serializer(queryset, many=True)
		
		return Response({
			'success': True,
			'data': serializer.data
		})


class WholesalerDetailView(RetrieveAPIView):
	"""
	GET /api/b2b/wholesalers/{id}/
	Détails d'un grossiste
	"""
	permission_classes = [IsAuthenticated, IsStoreManager]
	serializer_class = WholesalerSerializer
	
	def get_object(self):
		"""Récupère le grossiste avec vérification des permissions"""
		wholesaler_id = self.kwargs['id']
		user = self.request.user
		
		# Vérifier les permissions
		if not can_access_b2b(user):
			from rest_framework.exceptions import PermissionDenied
			raise PermissionDenied("Vous n'êtes pas autorisé à accéder au B2B")
		
		# Récupérer le magasin du gérant connecté
		buyer_store = Store.objects.filter(
			manager=user,
			is_b2c=True,
			is_active=True
		).first()
		
		wholesaler = get_object_or_404(Store, id=wholesaler_id, is_b2b=True, is_active=True)
		
		# Vérifier que le magasin peut acheter de ce grossiste
		can_purchase, error_msg = can_purchase_from_wholesaler(buyer_store, wholesaler)
		if not can_purchase:
			from rest_framework.exceptions import PermissionDenied
			raise PermissionDenied(error_msg)
		
		return wholesaler
	
	def retrieve(self, request, *args, **kwargs):
		"""Détails du grossiste"""
		instance = self.get_object()
		serializer = self.get_serializer(instance)
		
		return Response({
			'success': True,
			'data': serializer.data
		})


class WholesalerProductsView(ListAPIView):
	"""
	GET /api/b2b/wholesalers/{id}/products/
	Produits B2B d'un grossiste
	"""
	permission_classes = [IsAuthenticated, IsStoreManager]
	serializer_class = B2BProductSerializer
	
	def get_queryset(self):
		"""Retourne les produits B2B du grossiste"""
		wholesaler_id = self.kwargs['id']
		category_id = self.request.query_params.get('category_id')
		search = self.request.query_params.get('search')
		
		return get_b2b_products(wholesaler_id, category_id, search)
	
	def list(self, request, *args, **kwargs):
		"""Liste des produits B2B"""
		wholesaler_id = self.kwargs['id']
		user = request.user
		
		# Vérifier les permissions
		if not can_access_b2b(user):
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_403_FORBIDDEN,
					'message': 'Vous n\'êtes pas autorisé à accéder au B2B'
				}
			}, status=status.HTTP_403_FORBIDDEN)
		
		# Récupérer le magasin du gérant connecté
		buyer_store = Store.objects.filter(
			manager=user,
			is_b2c=True,
			is_active=True
		).first()
		
		# Vérifier que le grossiste existe et est accessible
		try:
			wholesaler = Store.objects.get(id=wholesaler_id, is_b2b=True, is_active=True)
			can_purchase, error_msg = can_purchase_from_wholesaler(buyer_store, wholesaler)
			if not can_purchase:
				return Response({
					'success': False,
					'error': {
						'code': status.HTTP_403_FORBIDDEN,
						'message': error_msg
					}
				}, status=status.HTTP_403_FORBIDDEN)
		except Store.DoesNotExist:
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_404_NOT_FOUND,
					'message': 'Grossiste non trouvé'
				}
			}, status=status.HTTP_404_NOT_FOUND)
		
		queryset = self.get_queryset()
		
		# Passer le contexte pour le serializer
		serializer = self.get_serializer(
			queryset,
			many=True,
			context={
				'request': request,
				'wholesaler_id': wholesaler_id,
				'quantity': request.query_params.get('quantity', 1)
			}
		)
		
		return Response({
			'success': True,
			'data': {
				'wholesaler': {
					'id': wholesaler.id,
					'name': wholesaler.name
				},
				'products': serializer.data
			}
		})


class WholesalerCategoriesView(ListAPIView):
	"""
	GET /api/b2b/wholesalers/{id}/categories/
	Catégories B2B d'un grossiste
	"""
	permission_classes = [IsAuthenticated, IsStoreManager]
	serializer_class = B2BCategorySerializer
	
	def list(self, request, *args, **kwargs):
		"""Liste des catégories B2B du grossiste"""
		wholesaler_id = self.kwargs['id']
		user = request.user
		
		# Vérifier les permissions
		if not can_access_b2b(user):
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_403_FORBIDDEN,
					'message': 'Vous n\'êtes pas autorisé à accéder au B2B'
				}
			}, status=status.HTTP_403_FORBIDDEN)
		
		categories = get_b2b_categories(wholesaler_id)
		serializer = self.get_serializer(categories, many=True)
		
		return Response({
			'success': True,
			'data': serializer.data
		})


class WholesalerCatalogView(APIView):
	"""
	GET /api/b2b/wholesalers/{id}/catalog/
	Catalogue complet d'un grossiste : infos + catégories + produits
	
	Query params:
		- category_id: int (optionnel) - Filtrer par catégorie B2B
		- search: str (optionnel) - Recherche textuelle
		- page: int (optionnel) - Numéro de page (défaut 1)
		- page_size: int (optionnel) - Taille de page (défaut 20, max 100)
	"""
	permission_classes = [IsAuthenticated, IsStoreManager]
	
	def get(self, request, id):
		user = request.user
		wholesaler_id = id
		
		# Vérifier les permissions
		if not can_access_b2b(user):
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_403_FORBIDDEN,
					'message': 'Vous n\'êtes pas autorisé à accéder au B2B'
				}
			}, status=status.HTTP_403_FORBIDDEN)
		
		# Récupérer le magasin du gérant connecté
		buyer_store = Store.objects.filter(
			manager=user,
			is_b2c=True,
			is_active=True
		).first()
		
		# Récupérer le grossiste
		try:
			wholesaler = Store.objects.select_related('b2b_profile', 'category').get(
				id=wholesaler_id,
				is_b2b=True,
				is_active=True
			)
		except Store.DoesNotExist:
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_404_NOT_FOUND,
					'message': 'Grossiste non trouvé'
				}
			}, status=status.HTTP_404_NOT_FOUND)
		
		# Vérifier permissions d'achat
		can_purchase, error_msg = can_purchase_from_wholesaler(buyer_store, wholesaler)
		if not can_purchase:
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_403_FORBIDDEN,
					'message': error_msg
				}
			}, status=status.HTTP_403_FORBIDDEN)
		
		# Query params
		category_id = request.query_params.get('category_id')
		search = request.query_params.get('search')
		page = int(request.query_params.get('page', 1))
		page_size = min(int(request.query_params.get('page_size', 20)), 100)
		
		# Récupérer les catégories avec compte de produits
		from django.db.models import Count
		categories = get_b2b_categories(wholesaler_id)
		categories_with_count = categories.annotate(
			product_count=Count('products', filter=Q(
				products__store=wholesaler,
				products__is_available=True,
				products__b2b_pricings__is_active=True
			))
		).filter(product_count__gt=0)
		
		# Récupérer les produits
		products = get_b2b_products(wholesaler_id, category_id, search)
		
		# Pagination
		total_products = products.count()
		start = (page - 1) * page_size
		end = start + page_size
		paginated_products = products[start:end]
		
		# Serializer contexte
		context = {'request': request, 'wholesaler_id': wholesaler_id}
		
		# Construire la réponse
		b2b_profile = wholesaler.b2b_profile if hasattr(wholesaler, 'b2b_profile') else None
		
		return Response({
			'success': True,
			'data': {
				'wholesaler': {
					'id': wholesaler.id,
					'name': wholesaler.name,
					'description': wholesaler.description,
					'logo': request.build_absolute_uri(wholesaler.logo.url) if wholesaler.logo else None,
					'banner_image': request.build_absolute_uri(wholesaler.banner_image.url) if wholesaler.banner_image else None,
					'city': wholesaler.city,
					'zone': wholesaler.zone,
					'phone': wholesaler.phone,
					'email': wholesaler.email,
					'minimum_order_amount': float(b2b_profile.minimum_order_amount) if b2b_profile else 0,
					'delivery_delay_hours': wholesaler.b2b_delivery_delay if hasattr(wholesaler, 'b2b_delivery_delay') else 24,
				},
				'categories': B2BCatalogCategorySerializer(categories_with_count, many=True).data,
				'products': B2BCatalogProductSerializer(paginated_products, many=True, context=context).data,
				'pagination': {
					'page': page,
					'page_size': page_size,
					'total_products': total_products,
					'total_pages': (total_products + page_size - 1) // page_size,
				}
			}
		})


class B2BOrderCreateView(APIView):
	"""
	POST /api/b2b/orders/
	Créer une commande B2B
	"""
	permission_classes = [IsAuthenticated, IsStoreManager]
	
	def post(self, request):
		"""Créer une commande B2B"""
		user = request.user
		
		# Vérifier les permissions
		if not can_access_b2b(user):
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_403_FORBIDDEN,
					'message': 'Vous n\'êtes pas autorisé à accéder au B2B'
				}
			}, status=status.HTTP_403_FORBIDDEN)
		
		# Récupérer le magasin du gérant connecté
		buyer_store = Store.objects.filter(
			manager=user,
			is_b2c=True,
			is_active=True
		).first()
		
		if not buyer_store:
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_404_NOT_FOUND,
					'message': 'Aucun magasin B2C trouvé pour votre compte'
				}
			}, status=status.HTTP_404_NOT_FOUND)
		
		# Valider les données
		serializer = B2BOrderCreateSerializer(data=request.data)
		if not serializer.is_valid():
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_400_BAD_REQUEST,
					'message': 'Données invalides',
					'errors': serializer.errors
				}
			}, status=status.HTTP_400_BAD_REQUEST)
		
		validated_data = serializer.validated_data
		wholesaler_id = validated_data['wholesaler_id']
		
		# Récupérer le grossiste
		try:
			wholesaler = Store.objects.get(id=wholesaler_id, is_b2b=True, is_active=True)
		except Store.DoesNotExist:
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_404_NOT_FOUND,
					'message': 'Grossiste non trouvé'
				}
			}, status=status.HTTP_404_NOT_FOUND)
		
		# Vérifier que c'est un store B2C
		can_order, error_msg = must_be_b2c_store(buyer_store)
		if not can_order:
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_403_FORBIDDEN,
					'message': error_msg
				}
			}, status=status.HTTP_403_FORBIDDEN)
		
		# Vérifier qu'il n'achète pas chez lui-même
		can_purchase, error_msg = can_purchase_from_self(buyer_store, wholesaler)
		if not can_purchase:
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_400_BAD_REQUEST,
					'message': error_msg
				}
			}, status=status.HTTP_400_BAD_REQUEST)
		
		# Valider la commande
		order_items = validated_data['items']
		is_valid, error_msg, totals = validate_b2b_order(order_items, wholesaler, buyer_store)
		
		if not is_valid:
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_400_BAD_REQUEST,
					'message': error_msg
				}
			}, status=status.HTTP_400_BAD_REQUEST)
		
		# Créer la commande
		with transaction.atomic():
			# Créer l'ordre
			order = Order.objects.create(
				client=user,
				store=wholesaler,
				source_store=buyer_store,
				is_b2b=True,
				delivery_type=validated_data.get('delivery_type', 'standard'),
				notes=validated_data.get('notes', ''),
				delivery_address=validated_data['delivery_address'],
				delivery_phone=validated_data['delivery_phone'],
				delivery_zone=validated_data['delivery_zone'],
				city=validated_data.get('city', 'Libreville'),
				items_total=totals['items_total'],
				delivery_fee=totals['delivery_fee'],
				service_fee=totals['service_fee'],
				total_amount=totals['total_amount'],
				status='created'
			)
			
			# Créer les items de commande
			for item in totals['items']:
				OrderItem.objects.create(
					order=order,
					product=item['product'],
					quantity=item['quantity'],
					unit_price=item['unit_price']
				)
				
				# Réduire le stock
				item['product'].reduce_stock(item['quantity'])
			
			# Calculer la commission
			order.calculate_commission()
			order.save()
		
		# Serializer la commande créée
		order_serializer = B2BOrderSerializer(order)
		
		return Response({
			'success': True,
			'data': order_serializer.data,
			'message': 'Commande B2B créée avec succès'
		}, status=status.HTTP_201_CREATED)


class MyB2BOrdersView(ListAPIView):
	"""
	GET /api/b2b/my-orders/
	Commandes B2B du magasin connecté
	"""
	permission_classes = [IsAuthenticated, IsStoreManager]
	serializer_class = B2BOrderSerializer
	
	def get_queryset(self):
		"""Retourne les commandes B2B du magasin connecté"""
		user = self.request.user
		
		# Vérifier les permissions
		if not can_access_b2b(user):
			return Order.objects.none()
		
		# Récupérer le magasin du gérant connecté
		buyer_store = Store.objects.filter(
			manager=user,
			is_b2c=True,
			is_active=True
		).first()
		
		if not buyer_store:
			return Order.objects.none()
		
		# Récupérer les commandes B2B où ce magasin est le source_store
		return Order.objects.filter(
			is_b2b=True,
			source_store=buyer_store
		).select_related('store', 'source_store', 'client').prefetch_related('items').order_by('-created_at')
	
	def list(self, request, *args, **kwargs):
		"""Liste des commandes B2B"""
		if not can_access_b2b(request.user):
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_403_FORBIDDEN,
					'message': 'Vous n\'êtes pas autorisé à accéder au B2B'
				}
			}, status=status.HTTP_403_FORBIDDEN)
		
		queryset = self.get_queryset()
		serializer = self.get_serializer(queryset, many=True)
		
		return Response({
			'success': True,
			'data': serializer.data
		})


# ==================== ADMIN ENDPOINTS ====================

class B2BProfileDetailView(APIView):
	"""
	GET /api/b2b/profiles/{store_id}/
	- Si profil existe : retourne le profil
	- Sinon : 200 avec exists: False
	"""
	permission_classes = [IsPlatformAdmin]
	
	def get(self, request, store_id):
		try:
			store = Store.objects.get(id=store_id)
		except Store.DoesNotExist:
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_404_NOT_FOUND,
					'message': 'Magasin non trouvé'
				}
			}, status=status.HTTP_404_NOT_FOUND)
		
		if hasattr(store, 'b2b_profile'):
			serializer = B2BProfileSerializer(store.b2b_profile)
			return Response({'success': True, 'exists': True, 'data': serializer.data})
		
		return Response({'success': True, 'exists': False, 'data': None})


class B2BProfileCreateView(APIView):
	"""
	POST /api/b2b/profiles/
	Créer un profil B2B pour un store
	"""
	permission_classes = [IsPlatformAdmin]
	
	def post(self, request):
		store_id = request.data.get('store_id')
		if not store_id:
			return Response({'success': False, 'error': {'code': status.HTTP_400_BAD_REQUEST, 'message': 'store_id est requis'}}, status=status.HTTP_400_BAD_REQUEST)
		
		try:
			store = Store.objects.get(id=store_id)
		except Store.DoesNotExist:
			return Response({'success': False, 'error': {'code': status.HTTP_404_NOT_FOUND, 'message': 'Magasin non trouvé'}}, status=status.HTTP_404_NOT_FOUND)
		
		if hasattr(store, 'b2b_profile'):
			return Response({'success': False, 'error': {'code': status.HTTP_400_BAD_REQUEST, 'message': 'Un profil B2B existe déjà'}}, status=status.HTTP_400_BAD_REQUEST)
		
		b2b_profile = B2BProfile.objects.create(
			store=store,
			minimum_order_amount=request.data.get('minimum_order_amount', 0),
			visible_to_all=request.data.get('visible_to_all', True),
			is_active=request.data.get('is_active', True),
		)
		
		store.is_b2b = True
		store.save()
		
		serializer = B2BProfileSerializer(b2b_profile)
		return Response({'success': True, 'exists': True, 'data': serializer.data}, status=status.HTTP_201_CREATED)


class B2BProfileUpdateView(APIView):
	"""
	PUT /api/b2b/profiles/{store_id}/update/
	Mettre à jour un profil B2B
	"""
	permission_classes = [IsPlatformAdmin]
	
	def put(self, request, store_id):
		try:
			store = Store.objects.get(id=store_id)
		except Store.DoesNotExist:
			return Response({'success': False, 'error': {'code': status.HTTP_404_NOT_FOUND, 'message': 'Magasin non trouvé'}}, status=status.HTTP_404_NOT_FOUND)
		
		if not hasattr(store, 'b2b_profile'):
			return Response({'success': False, 'error': {'code': status.HTTP_404_NOT_FOUND, 'message': 'Aucun profil B2B pour ce magasin'}}, status=status.HTTP_404_NOT_FOUND)
		
		profile = store.b2b_profile
		if 'minimum_order_amount' in request.data:
			profile.minimum_order_amount = request.data['minimum_order_amount']
		if 'visible_to_all' in request.data:
			profile.visible_to_all = request.data['visible_to_all']
		if 'is_active' in request.data:
			profile.is_active = request.data['is_active']
		profile.save()
		
		serializer = B2BProfileSerializer(profile)
		return Response({'success': True, 'data': serializer.data, 'exists': True})


class B2BProfileActivateView(APIView):
	"""
	PATCH /api/b2b/profiles/{store_id}/activate/
	Active le profil B2B, le crée si absent
	"""
	permission_classes = [IsPlatformAdmin]
	
	def patch(self, request, store_id):
		try:
			store = Store.objects.get(id=store_id)
		except Store.DoesNotExist:
			return Response({'success': False, 'error': {'code': status.HTTP_404_NOT_FOUND, 'message': 'Magasin non trouvé'}}, status=status.HTTP_404_NOT_FOUND)
		
		profile, created = B2BProfile.objects.get_or_create(
			store=store,
			defaults={
				'minimum_order_amount': request.data.get('minimum_order_amount', 0),
				'visible_to_all': request.data.get('visible_to_all', True),
				'is_active': True,
			}
		)
		if not created:
			profile.is_active = True
			if 'minimum_order_amount' in request.data:
				profile.minimum_order_amount = request.data['minimum_order_amount']
			if 'visible_to_all' in request.data:
				profile.visible_to_all = request.data['visible_to_all']
			profile.save()
		
		store.is_b2b = True
		store.save()
		
		serializer = B2BProfileSerializer(profile)
		return Response({'success': True, 'data': serializer.data, 'exists': True})


class B2BProfileDeactivateView(APIView):
	"""
	PATCH /api/b2b/profiles/{store_id}/deactivate/
	Désactive le profil B2B si existant
	"""
	permission_classes = [IsPlatformAdmin]
	
	def patch(self, request, store_id):
		try:
			store = Store.objects.get(id=store_id)
		except Store.DoesNotExist:
			return Response({'success': False, 'error': {'code': status.HTTP_404_NOT_FOUND, 'message': 'Magasin non trouvé'}}, status=status.HTTP_404_NOT_FOUND)
		
		if not hasattr(store, 'b2b_profile'):
			return Response({'success': False, 'error': {'code': status.HTTP_404_NOT_FOUND, 'message': 'Aucun profil B2B pour ce magasin'}}, status=status.HTTP_404_NOT_FOUND)
		
		profile = store.b2b_profile
		profile.is_active = False
		profile.save()
		
		serializer = B2BProfileSerializer(profile)
		return Response({'success': True, 'data': serializer.data, 'exists': True})


# ==================== B2B PRODUCT PRICING MANAGEMENT ====================

from b2b.api.serializers import B2BProductPricingSerializer
from products.models import Product


class B2BProductPricingListView(APIView):
	"""
	GET /api/b2b/pricing/{store_id}/
	Liste des prix B2B pour un store (grossiste)
	"""
	permission_classes = [IsPlatformAdmin]
	
	def get(self, request, store_id):
		try:
			store = Store.objects.get(id=store_id)
		except Store.DoesNotExist:
			return Response({'success': False, 'error': {'code': status.HTTP_404_NOT_FOUND, 'message': 'Magasin non trouvé'}}, status=status.HTTP_404_NOT_FOUND)
		
		pricings = B2BProductPricing.objects.filter(b2b_store=store).select_related('product')
		serializer = B2BProductPricingSerializer(pricings, many=True)
		
		# Récupérer aussi les produits sans prix B2B
		products_with_pricing = pricings.values_list('product_id', flat=True)
		products_without_pricing = Product.objects.filter(
			store=store,
			is_available=True
		).exclude(id__in=products_with_pricing).values('id', 'name', 'price', 'stock')
		
		return Response({
			'success': True,
			'data': {
				'pricings': serializer.data,
				'products_without_pricing': list(products_without_pricing),
			}
		})


class B2BProductPricingCreateView(APIView):
	"""
	POST /api/b2b/pricing/
	Créer un prix B2B pour un produit
	"""
	permission_classes = [IsPlatformAdmin]
	
	def post(self, request):
		product_id = request.data.get('product_id')
		store_id = request.data.get('store_id')
		b2b_price = request.data.get('b2b_price')
		min_quantity = request.data.get('min_quantity', 1)
		max_quantity = request.data.get('max_quantity')
		
		if not all([product_id, store_id, b2b_price]):
			return Response({
				'success': False,
				'error': {'code': status.HTTP_400_BAD_REQUEST, 'message': 'product_id, store_id et b2b_price sont requis'}
			}, status=status.HTTP_400_BAD_REQUEST)
		
		try:
			product = Product.objects.get(id=product_id)
			store = Store.objects.get(id=store_id)
		except Product.DoesNotExist:
			return Response({'success': False, 'error': {'code': status.HTTP_404_NOT_FOUND, 'message': 'Produit non trouvé'}}, status=status.HTTP_404_NOT_FOUND)
		except Store.DoesNotExist:
			return Response({'success': False, 'error': {'code': status.HTTP_404_NOT_FOUND, 'message': 'Magasin non trouvé'}}, status=status.HTTP_404_NOT_FOUND)
		
		# Vérifier que le produit appartient au store
		if product.store_id != store.id:
			return Response({
				'success': False,
				'error': {'code': status.HTTP_400_BAD_REQUEST, 'message': 'Le produit n\'appartient pas à ce magasin'}
			}, status=status.HTTP_400_BAD_REQUEST)
		
		# Créer ou mettre à jour le pricing
		pricing, created = B2BProductPricing.objects.update_or_create(
			product=product,
			b2b_store=store,
			min_quantity=min_quantity,
			defaults={
				'b2b_price': b2b_price,
				'max_quantity': max_quantity,
				'is_active': True,
			}
		)
		
		serializer = B2BProductPricingSerializer(pricing)
		return Response({
			'success': True,
			'data': serializer.data,
			'message': 'Prix B2B créé' if created else 'Prix B2B mis à jour'
		}, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class B2BProductPricingUpdateView(APIView):
	"""
	PUT /api/b2b/pricing/{pricing_id}/
	Mettre à jour un prix B2B
	"""
	permission_classes = [IsPlatformAdmin]
	
	def put(self, request, pricing_id):
		try:
			pricing = B2BProductPricing.objects.get(id=pricing_id)
		except B2BProductPricing.DoesNotExist:
			return Response({'success': False, 'error': {'code': status.HTTP_404_NOT_FOUND, 'message': 'Prix B2B non trouvé'}}, status=status.HTTP_404_NOT_FOUND)
		
		if 'b2b_price' in request.data:
			pricing.b2b_price = request.data['b2b_price']
		if 'min_quantity' in request.data:
			pricing.min_quantity = request.data['min_quantity']
		if 'max_quantity' in request.data:
			pricing.max_quantity = request.data['max_quantity']
		if 'is_active' in request.data:
			pricing.is_active = request.data['is_active']
		
		pricing.save()
		serializer = B2BProductPricingSerializer(pricing)
		return Response({'success': True, 'data': serializer.data})


class B2BProductPricingDeleteView(APIView):
	"""
	DELETE /api/b2b/pricing/{pricing_id}/
	Supprimer un prix B2B
	"""
	permission_classes = [IsPlatformAdmin]
	
	def delete(self, request, pricing_id):
		try:
			pricing = B2BProductPricing.objects.get(id=pricing_id)
		except B2BProductPricing.DoesNotExist:
			return Response({'success': False, 'error': {'code': status.HTTP_404_NOT_FOUND, 'message': 'Prix B2B non trouvé'}}, status=status.HTTP_404_NOT_FOUND)
		
		pricing.delete()
		return Response({'success': True, 'message': 'Prix B2B supprimé'})


class B2BProductPricingBulkCreateView(APIView):
	"""
	POST /api/b2b/pricing/bulk/
	Créer des prix B2B en masse (tous les produits d'un store)
	
	Body: {
		"store_id": int,
		"discount_percent": float (ex: 10 pour -10%)
	}
	"""
	permission_classes = [IsPlatformAdmin]
	
	def post(self, request):
		store_id = request.data.get('store_id')
		discount_percent = request.data.get('discount_percent', 10)
		
		if not store_id:
			return Response({
				'success': False,
				'error': {'code': status.HTTP_400_BAD_REQUEST, 'message': 'store_id est requis'}
			}, status=status.HTTP_400_BAD_REQUEST)
		
		try:
			store = Store.objects.get(id=store_id)
		except Store.DoesNotExist:
			return Response({'success': False, 'error': {'code': status.HTTP_404_NOT_FOUND, 'message': 'Magasin non trouvé'}}, status=status.HTTP_404_NOT_FOUND)
		
		# Récupérer les produits sans prix B2B
		existing_product_ids = B2BProductPricing.objects.filter(b2b_store=store).values_list('product_id', flat=True)
		products = Product.objects.filter(store=store, is_available=True).exclude(id__in=existing_product_ids)
		
		created_count = 0
		from decimal import Decimal
		discount_factor = Decimal(str(1 - discount_percent / 100))
		
		for product in products:
			b2b_price = product.price * discount_factor
			B2BProductPricing.objects.create(
				product=product,
				b2b_store=store,
				b2b_price=b2b_price,
				min_quantity=1,
				is_active=True
			)
			created_count += 1
		
		return Response({
			'success': True,
			'message': f'{created_count} prix B2B créés avec {discount_percent}% de remise',
			'created_count': created_count
		})

