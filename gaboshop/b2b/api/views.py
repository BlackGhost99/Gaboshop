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

from stores.models import Store
from orders.models import Order, OrderItem
from b2b.models import B2BProfile, B2BCategory
from b2b.services.permissions import can_access_b2b, can_purchase_from_wholesaler
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
	B2BOrderSerializer
)


class IsPlatformAdmin(permissions.BasePermission):
	"""Only platform admins can access"""
	def has_permission(self, request, view):
		user = request.user
		return bool(user and user.is_authenticated and (user.is_staff or user.user_type == 'admin'))


class WholesalerListView(ListAPIView):
	"""
	GET /api/b2b/wholesalers/
	Liste des grossistes disponibles
	"""
	permission_classes = [IsAuthenticated]
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
	permission_classes = [IsAuthenticated]
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
	permission_classes = [IsAuthenticated]
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
	permission_classes = [IsAuthenticated]
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


class B2BOrderCreateView(APIView):
	"""
	POST /api/b2b/orders/
	Créer une commande B2B
	"""
	permission_classes = [IsAuthenticated]
	
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
	permission_classes = [IsAuthenticated]
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

class B2BProfileCreateView(APIView):
	"""
	POST /api/b2b/profiles/
	Créer un profil B2B pour un store (Admin seulement)
	"""
	permission_classes = [IsPlatformAdmin]
	
	def post(self, request):
		"""Créer un profil B2B"""
		store_id = request.data.get('store_id')
		if not store_id:
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_400_BAD_REQUEST,
					'message': 'store_id est requis'
				}
			}, status=status.HTTP_400_BAD_REQUEST)
		
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
		
		# Vérifier si un profil existe déjà
		if hasattr(store, 'b2b_profile'):
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_400_BAD_REQUEST,
					'message': 'Un profil B2B existe déjà pour ce magasin'
				}
			}, status=status.HTTP_400_BAD_REQUEST)
		
		# Créer le profil B2B
		profile_data = {
			'store': store,
			'minimum_order_amount': request.data.get('minimum_order_amount', 0),
			'visible_to_all': request.data.get('visible_to_all', True),
			'is_active': request.data.get('is_active', True),
		}
		
		b2b_profile = B2BProfile.objects.create(**profile_data)
		
		# Activer is_b2b sur le store
		store.is_b2b = True
		store.save()
		
		serializer = B2BProfileSerializer(b2b_profile)
		return Response({
			'success': True,
			'data': serializer.data,
			'message': 'Profil B2B créé avec succès'
		}, status=status.HTTP_201_CREATED)


class B2BProfileDetailView(APIView):
	"""
	GET /api/b2b/profiles/{store_id}/
	Récupérer le profil B2B d'un store (Admin seulement)
	"""
	permission_classes = [IsPlatformAdmin]
	
	def get(self, request, store_id):
		"""Récupérer le profil B2B"""
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
		
		if not hasattr(store, 'b2b_profile'):
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_404_NOT_FOUND,
					'message': 'Aucun profil B2B trouvé pour ce magasin'
				}
			}, status=status.HTTP_404_NOT_FOUND)
		
		serializer = B2BProfileSerializer(store.b2b_profile)
		return Response({
			'success': True,
			'data': serializer.data
		})


class B2BProfileUpdateView(APIView):
	"""
	PUT /api/b2b/profiles/{store_id}/
	Mettre à jour un profil B2B (Admin seulement)
	"""
	permission_classes = [IsPlatformAdmin]
	
	def put(self, request, store_id):
		"""Mettre à jour le profil B2B"""
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
		
		if not hasattr(store, 'b2b_profile'):
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_404_NOT_FOUND,
					'message': 'Aucun profil B2B trouvé pour ce magasin'
				}
			}, status=status.HTTP_404_NOT_FOUND)
		
		b2b_profile = store.b2b_profile
		
		# Mettre à jour les champs
		if 'minimum_order_amount' in request.data:
			b2b_profile.minimum_order_amount = request.data['minimum_order_amount']
		if 'visible_to_all' in request.data:
			b2b_profile.visible_to_all = request.data['visible_to_all']
		if 'is_active' in request.data:
			b2b_profile.is_active = request.data['is_active']
		
		b2b_profile.save()
		
		serializer = B2BProfileSerializer(b2b_profile)
		return Response({
			'success': True,
			'data': serializer.data,
			'message': 'Profil B2B mis à jour avec succès'
		})


class B2BProfileActivateView(APIView):
	"""
	PATCH /api/b2b/profiles/{store_id}/activate/
	Activer le profil B2B et is_b2b du store (Admin seulement)
	"""
	permission_classes = [IsPlatformAdmin]
	
	def patch(self, request, store_id):
		"""Activer le profil B2B"""
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
		
		# Créer le profil s'il n'existe pas
		if not hasattr(store, 'b2b_profile'):
			b2b_profile = B2BProfile.objects.create(
				store=store,
				is_active=True,
				minimum_order_amount=request.data.get('minimum_order_amount', 0),
				visible_to_all=request.data.get('visible_to_all', True)
			)
		else:
			b2b_profile = store.b2b_profile
			b2b_profile.is_active = True
			b2b_profile.save()
		
		# Activer is_b2b sur le store
		store.is_b2b = True
		store.save()
		
		serializer = B2BProfileSerializer(b2b_profile)
		return Response({
			'success': True,
			'data': serializer.data,
			'message': 'Profil B2B activé avec succès'
		})


class B2BProfileDeactivateView(APIView):
	"""
	PATCH /api/b2b/profiles/{store_id}/deactivate/
	Désactiver le profil B2B (Admin seulement)
	Note: On ne désactive pas is_b2b sur le store, seulement le profil
	"""
	permission_classes = [IsPlatformAdmin]
	
	def patch(self, request, store_id):
		"""Désactiver le profil B2B"""
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
		
		if not hasattr(store, 'b2b_profile'):
			return Response({
				'success': False,
				'error': {
					'code': status.HTTP_404_NOT_FOUND,
					'message': 'Aucun profil B2B trouvé pour ce magasin'
				}
			}, status=status.HTTP_404_NOT_FOUND)
		
		b2b_profile = store.b2b_profile
		b2b_profile.is_active = False
		b2b_profile.save()
		
		serializer = B2BProfileSerializer(b2b_profile)
		return Response({
			'success': True,
			'data': serializer.data,
			'message': 'Profil B2B désactivé avec succès'
		})

