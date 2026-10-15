"""API v1: products endpoints."""

from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, RetrieveAPIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter
from django.core.exceptions import PermissionDenied

from products.models import Product, ProductCategory
from products.serializers import (
    ProductSerializer, ProductDetailSerializer,
    ProductCategorySerializer, ProductCreateSerializer,
    ProductUpdateSerializer
)
from stores.models import Store, visible_store_filter
from api.v1.admin import IsPlatformAdmin

# Photos d'un produit : la principale (image) + 5 autres au plus (galerie, et anciens image_2/image_3).
MAX_EXTRA_PHOTOS = 5
LEGACY_PHOTO_FIELDS = ('image_2', 'image_3')


def _photo_error(message):
    return Response({
        'success': False,
        'error': {'code': status.HTTP_400_BAD_REQUEST, 'message': message, 'details': {'gallery': [message]}},
    }, status=status.HTTP_400_BAD_REQUEST)


def _clean_gallery_files(request):
    """Vérifie que les fichiers « gallery » sont de vraies images. Renvoie (fichiers, message d'erreur)."""
    from django import forms
    files = request.FILES.getlist('gallery')
    field = forms.ImageField()
    for f in files:
        try:
            field.clean(f)
        except forms.ValidationError:
            return [], f"« {f.name} » n'est pas une image valide (JPG, PNG ou WEBP)."
        f.seek(0)
    return files, ''


def _removed_photos(request):
    raw = request.data.get('remove_images', '')
    values = request.data.getlist('remove_images') if hasattr(request.data, 'getlist') else [raw]
    return {v.strip() for item in values for v in str(item or '').split(',') if v.strip()}


def _extra_photo_count(product, removed=()):
    legacy = sum(1 for f in LEGACY_PHOTO_FIELDS if getattr(product, f) and f not in removed)
    gallery = product.images.exclude(id__in=[int(r) for r in removed if r.isdigit()]).count()
    return legacy + gallery


def _apply_photos(product, files, removed):
    """Retire les photos demandées (« image_2 », « image_3 » ou l'id d'une photo de galerie) puis ajoute les nouvelles."""
    from products.models import ProductImage
    for name in LEGACY_PHOTO_FIELDS:
        if name in removed and getattr(product, name):
            getattr(product, name).delete(save=False)
            setattr(product, name, None)
    product.save()
    for img in product.images.filter(id__in=[int(r) for r in removed if r.isdigit()]):
        img.image.delete(save=False)
        img.delete()
    start = (product.images.order_by('-order').values_list('order', flat=True).first() or 0) + 1
    for i, f in enumerate(files):
        ProductImage.objects.create(product=product, image=f, order=start + i, alt_text=product.name[:200])

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
        from django.db.models import OuterRef, Subquery, Value, IntegerField
        from django.db.models.functions import Coalesce
        from django.utils import timezone
        from payments.models import StoreSubscription

        today = timezone.now().date()
        priority_subquery = StoreSubscription.objects.filter(
            store=OuterRef('store_id'),
            status='active',
            end_date__gte=today
        ).order_by('-end_date').values('plan__priority_listing')[:1]

        return Product.objects.filter(
            is_available=True,
            store__is_active=True,
            store__is_verified=True,
            market_type__in=['b2c', 'both']  # BLOQUER les produits B2B purs
        ).select_related('store', 'category').prefetch_related('images').annotate(
            store_priority=Coalesce(Subquery(priority_subquery, output_field=IntegerField()), Value(0))
        ).order_by('-is_sponsored', '-store_priority', '-created_at')

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
            visible_store_filter(self.request.user, 'store__'),
            store_id=store_id, 
            is_available=True,
            store__is_active=True,
            market_type__in=['b2c', 'both']  # BLOQUER les produits B2B purs
        ).select_related('store', 'category').prefetch_related('images')

    def list(self, request, *args, **kwargs):
        # Vérifier que le magasin existe et est actif
        try:
            store = Store.objects.get(
                visible_store_filter(request.user),
                id=self.kwargs['store_id'], 
                is_active=True,
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
    def get_queryset(self):
        return Product.objects.filter(
            visible_store_filter(self.request.user, 'store__'),
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

        # Vérifier les limites du forfait (scalable - vérifie en temps réel)
        from payments.subscription_check import SubscriptionChecker
        try:
            SubscriptionChecker.check_can_add_product(store)
        except PermissionDenied as e:
            return Response({
                'success': False,
                'error': {
                    'code': status.HTTP_403_FORBIDDEN,
                    'message': str(e)
                }
            }, status=status.HTTP_403_FORBIDDEN)

        gallery, error = _clean_gallery_files(request)
        if error:
            return _photo_error(error)
        if len(gallery) > MAX_EXTRA_PHOTOS:
            return _photo_error(f"Vous pouvez ajouter {MAX_EXTRA_PHOTOS} autres photos au plus, en plus de la photo principale.")

        serializer = ProductCreateSerializer(
            data=request.data,
            context={'request': request, 'store': store}
        )

        if serializer.is_valid():
            try:
                from payments.subscription_check import SubscriptionChecker
                SubscriptionChecker.check_can_add_food_product(
                    store,
                    serializer.validated_data.get('category')
                )
            except PermissionDenied as e:
                return Response({
                    'success': False,
                    'error': {
                        'code': status.HTTP_403_FORBIDDEN,
                        'message': str(e)
                    }
                }, status=status.HTTP_403_FORBIDDEN)

            product = serializer.save(store=store)
            _apply_photos(product, gallery, set())

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

        gallery, error = _clean_gallery_files(request)
        if error:
            return _photo_error(error)
        removed = _removed_photos(request)
        if _extra_photo_count(product, removed) + len(gallery) > MAX_EXTRA_PHOTOS:
            return _photo_error(
                f"Un produit a {MAX_EXTRA_PHOTOS} autres photos au plus, en plus de la photo principale. Retirez-en une avant d'en ajouter."
            )

        serializer = ProductUpdateSerializer(
            product, 
            data=request.data, 
            partial=True
        )

        if serializer.is_valid():
            try:
                from payments.subscription_check import SubscriptionChecker
                new_category = serializer.validated_data.get('category', product.category)
                SubscriptionChecker.check_can_add_food_product(
                    product.store,
                    new_category,
                    exclude_product_id=product.id
                )
            except PermissionDenied as e:
                return Response({
                    'success': False,
                    'error': {
                        'code': status.HTTP_403_FORBIDDEN,
                        'message': str(e)
                    }
                }, status=status.HTTP_403_FORBIDDEN)

            product = serializer.save()
            _apply_photos(product, gallery, removed)

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

        # Vérifier si le produit a des commandes associées
        from orders.models import OrderItem
        from django.db.models import ProtectedError
        
        has_orders = OrderItem.objects.filter(product=product).exists()
        
        if has_orders:
            # Soft delete : désactiver le produit au lieu de le supprimer
            product.is_available = False
            product.save()
            return Response({
                'success': True,
                'message': 'Produit désactivé avec succès (le produit ne peut pas être supprimé car il a des commandes associées).'
            }, status=status.HTTP_200_OK)
        
        # Hard delete : supprimer le produit s'il n'a pas de commandes
        try:
            product.delete()
            return Response({
                'success': True,
                'message': 'Produit supprimé avec succès.'
            }, status=status.HTTP_200_OK)
        except ProtectedError as e:
            # Si une autre relation protège le produit
            return Response({
                'success': False,
                'error': {
                    'code': status.HTTP_400_BAD_REQUEST,
                    'message': 'Ce produit ne peut pas être supprimé car il est utilisé dans d\'autres enregistrements. Il a été désactivé à la place.'
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Gérer toute autre exception
            return Response({
                'success': False,
                'error': {
                    'code': status.HTTP_500_INTERNAL_SERVER_ERROR,
                    'message': f'Erreur lors de la suppression du produit : {str(e)}'
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
    RÉSERVÉ UNIQUEMENT À L'ADMIN - Les stores ne peuvent plus créer de catégories
    """
    permission_classes = [IsPlatformAdmin]

    def post(self, request, store_id):
        # Seul l'admin peut créer des catégories
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            return Response({
                'success': False, 
                'error': {
                    'code': status.HTTP_404_NOT_FOUND,
                    'message': 'Magasin non trouvé.'
                }
            }, status=status.HTTP_404_NOT_FOUND)
        
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
        return Product.objects.filter(store_id=store_id).select_related('store', 'category').prefetch_related('images').order_by('-created_at')

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


