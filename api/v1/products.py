"""API v1: products endpoints."""

from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, RetrieveAPIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter

from products.models import Product, ProductCategory
from products.serializers import (
    ProductSerializer, ProductDetailSerializer,
    ProductCategorySerializer, ProductCreateSerializer,
    ProductUpdateSerializer
)
from stores.models import Store

# Default templates per StoreCategory.name used as fallback suggestions
DEFAULT_CATEGORY_TEMPLATES = {
    'Hypermarché': [
        'Alimentation', 'Électronique', 'Bricolage', 'Vêtements', 'Maison'
    ],
    'Épicerie': [
        'Frais', 'Épicerie sèche', 'Boissons', 'Produits ménagers'
    ],
    'Vêtements': [
        'Homme', 'Femme', 'Enfant', 'Accessoires'
    ]
}


def get_suggested_categories_for_store(store):
    """Return a list of suggested category dicts for a given Store.

    Each item matches the shape frontend expects: id may be None for suggestions.
    """
    cat_name = store.category.name if store and store.category else None
    names = DEFAULT_CATEGORY_TEMPLATES.get(cat_name, [])
    suggestions = []
    for i, n in enumerate(names):
        suggestions.append({
            'id': None,
            'name': n,
            'description': '',
            'order': i,
            'is_suggested': True
        })
    return suggestions

class ProductListView(ListAPIView):
    """
    Liste publique de tous les produits disponibles
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['category', 'store', 'is_featured', 'is_sponsored']
    search_fields = ['name', 'description', 'store__name']

    def get_queryset(self):
        return Product.objects.filter(
            is_available=True,
            store__is_active=True,
            market_type__in=['b2c', 'both']  # BLOQUER les produits B2B purs
        ).select_related('store', 'category').order_by('-is_sponsored', '-created_at')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response({
                'success': True,
                'data': serializer.data
            })

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })

class StoreProductsView(ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['category']
    search_fields = ['name', 'description']

    def get_queryset(self):
        store_id = self.kwargs['store_id']
        return Product.objects.filter(
            store_id=store_id, 
            is_available=True,
            store__is_active=True,
            market_type__in=['b2c', 'both']  # BLOQUER les produits B2B purs
        ).select_related('store', 'category')

    def list(self, request, *args, **kwargs):
        # Vérifier que le magasin existe et est actif
        try:
            store = Store.objects.get(
                id=self.kwargs['store_id'], 
                is_active=True
            )
        except Store.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': status.HTTP_404_NOT_FOUND,
                    'message': 'Magasin non trouvé ou inactif.'
                }
            }, status=status.HTTP_404_NOT_FOUND)

        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': {
                'store': {
                    'id': store.id,
                    'name': store.name,
                    'zone': store.zone
                },
                'products': serializer.data
            }
        })

class ProductDetailView(RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductDetailSerializer
    queryset = Product.objects.filter(
        is_available=True, 
        store__is_active=True,
        market_type__in=['b2c', 'both']  # BLOQUER les produits B2B purs
    )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)

        return Response({
            'success': True,
            'data': serializer.data
        })

class ProductCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, store_id):
        # Vérifier que l'utilisateur est le gérant de ce magasin
        try:
            store = Store.objects.get(
                id=store_id, 
                manager=request.user,
                is_active=True
            )
        except Store.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': status.HTTP_403_FORBIDDEN,
                    'message': 'Vous n\'êtes pas autorisé à ajouter des produits à ce magasin.'
                }
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = ProductCreateSerializer(
            data=request.data,
            context={'request': request}
        )

        if serializer.is_valid():
            product = serializer.save(store=store)

            return Response({
                'success': True,
                'message': 'Produit créé avec succès.',
                'data': ProductSerializer(product).data
            }, status=status.HTTP_201_CREATED)

        return Response({
            'success': False,
            'error': {
                'code': status.HTTP_400_BAD_REQUEST,
                'message': 'Données invalides.',
                'details': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)

class ProductUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request, pk):
        # Vérifier que l'utilisateur est le gérant du magasin du produit
        try:
            product = Product.objects.get(
                id=pk, 
                store__manager=request.user
            )
        except Product.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': status.HTTP_403_FORBIDDEN,
                    'message': 'Vous n\'êtes pas autorisé à modifier ce produit.'
                }
            }, status=status.HTTP_403_FORBIDDEN)

        serializer = ProductUpdateSerializer(
            product, 
            data=request.data, 
            partial=True
        )

        if serializer.is_valid():
            product = serializer.save()

            return Response({
                'success': True,
                'message': 'Produit mis à jour avec succès.',
                'data': ProductDetailSerializer(product).data
            })

        return Response({
            'success': False,
            'error': {
                'code': status.HTTP_400_BAD_REQUEST,
                'message': 'Données invalides.',
                'details': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)

class ProductDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        # Vérifier que l'utilisateur est le gérant du magasin du produit
        try:
            product = Product.objects.get(
                id=pk, 
                store__manager=request.user
            )
        except Product.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': status.HTTP_403_FORBIDDEN,
                    'message': 'Vous n\'êtes pas autorisé à supprimer ce produit.'
                }
            }, status=status.HTTP_403_FORBIDDEN)

        product.delete()

        return Response({
            'success': True,
            'message': 'Produit supprimé avec succès.'
        }, status=status.HTTP_200_OK)

class StoreProductCategoryListView(ListAPIView):
    """
    Liste des catégories de produits d'un magasin
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProductCategorySerializer

    def get_queryset(self):
        store_id = self.kwargs['store_id']
        # Return categories related to the store's StoreCategory
        try:
            store = Store.objects.get(id=store_id)
            return ProductCategory.objects.filter(store_category_id=store.category_id).order_by('order', 'name')
        except Store.DoesNotExist:
            return ProductCategory.objects.none()

    def list(self, request, *args, **kwargs):
        try:
            store = Store.objects.get(id=self.kwargs['store_id'])
            # Allow store manager or admin/staff users to view categories
            if store.manager != request.user and not (request.user.is_staff or request.user.is_superuser):
                return Response({
                    'success': False,
                    'error': {
                        'code': status.HTTP_403_FORBIDDEN,
                        'message': 'Vous n\'êtes pas autorisé à voir ces catégories.'
                    }
                }, status=status.HTTP_403_FORBIDDEN)
        except Store.DoesNotExist:
            return Response({
                'success': False,
                'error': {
                    'code': status.HTTP_404_NOT_FOUND,
                    'message': 'Magasin non trouvé.'
                }
            }, status=status.HTTP_404_NOT_FOUND)

        queryset = list(self.get_queryset())
        if not queryset:
            # No explicit categories for this store: return suggested templates
            suggestions = get_suggested_categories_for_store(store)
            return Response({'success': True, 'data': suggestions})

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })

class StoreProductCategoryCreateView(APIView):
    """
    Création d'une catégorie de produit pour un magasin
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, store_id):
        try:
            store = Store.objects.get(id=store_id, manager=request.user)
        except Store.DoesNotExist:
            return Response({
                'success': False, 
                'error': {
                    'code': status.HTTP_403_FORBIDDEN,
                    'message': 'Vous n\'êtes pas autorisé à ajouter des catégories à ce magasin.'
                }
            }, status=status.HTTP_403_FORBIDDEN)
        
        serializer = ProductCategorySerializer(data=request.data)
        if serializer.is_valid():
            # Persist with store_category inferred from store
            category = serializer.save(store_category=store.category)
            return Response({
                'success': True,
                'message': 'Catégorie créée avec succès.',
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
            
        print("Category Create Errors:", serializer.errors)
        return Response({
            'success': False,
            'error': {
                'code': status.HTTP_400_BAD_REQUEST,
                'message': 'Données invalides.',
                'details': serializer.errors
            }
        }, status=status.HTTP_400_BAD_REQUEST)

class StoreManagerProductsView(ListAPIView):
    """
    Liste des produits d'un magasin pour le gérant (inclut les non-disponibles)
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['category', 'is_available']
    search_fields = ['name', 'description']

    def get_queryset(self):
        store_id = self.kwargs['store_id']
        return Product.objects.filter(store_id=store_id).select_related('store', 'category').order_by('-created_at')

    def list(self, request, *args, **kwargs):
        try:
            store = Store.objects.get(id=self.kwargs['store_id'])
            # Allow store manager or admin/staff users to view manager product list
            if store.manager != request.user and not (request.user.is_staff or request.user.is_superuser):
                 return Response({
                     'success': False, 
                     'error': {
                         'code': status.HTTP_403_FORBIDDEN,
                         'message': 'Vous n\'êtes pas autorisé à voir ces produits.'
                     }
                 }, status=status.HTTP_403_FORBIDDEN)
        except Store.DoesNotExist:
            return Response({
                'success': False, 
                'error': {
                    'code': status.HTTP_404_NOT_FOUND,
                    'message': 'Magasin non trouvé.'
                }
            }, status=status.HTTP_404_NOT_FOUND)

        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': {
                'store': {
                    'id': store.id,
                    'name': store.name,
                    'zone': store.zone
                },
                'products': serializer.data
            }
        })


class AllProductCategoryListView(ListAPIView):
    """
    Retourne toutes les catégories de produits existantes (globales).
    Utile pour remplir une liste déroulante lors de la création d'un produit.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = ProductCategorySerializer

    def get_queryset(self):
        return ProductCategory.objects.select_related('store_category').order_by('store_category__name', 'order', 'name')

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })


