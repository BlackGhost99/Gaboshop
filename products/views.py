from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q

from .models import Product, ProductVariant, ProductImage
from .serializers import (
    ProductSerializer, ProductDetailSerializer, ProductCreateSerializer,
    ProductUpdateSerializer, ProductImageSerializer
)
from rest_framework.permissions import IsAdminUser


class ProductViewSet(viewsets.ModelViewSet):
    """CRUD + search for products. Managers may create products for their stores."""
    queryset = Product.objects.all().order_by('-created_at')
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductSerializer
        if self.action in ['create']:
            return ProductCreateSerializer
        if self.action in ['update', 'partial_update']:
            return ProductUpdateSerializer
        return ProductDetailSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        q = self.request.query_params.get('q')
        store_id = self.request.query_params.get('store_id')
        category_id = self.request.query_params.get('category_id')
        if store_id:
            qs = qs.filter(store_id=store_id)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        return qs

    def perform_create(self, serializer):
        # Determine store: prefer provided store if manager owns it, else use first managed store
        request = self.request
        data_store = request.data.get('store')
        store = None
        if data_store:
            try:
                store_obj = request.user.managed_stores.filter(id=int(data_store)).first()
                if store_obj:
                    store = store_obj
            except Exception:
                store = None

        if not store:
            # fallback to first managed store
            store = request.user.managed_stores.first()

        if not store:
            raise Exception('Utilisateur non associé à un magasin ou non autorisé à créer des produits')

        serializer.save(store=store)

    @action(detail=True, methods=['post'], url_path='upload-image')
    def upload_image(self, request, pk=None):
        """Upload an image to the product gallery."""
        product = self.get_object()
        file_obj = request.FILES.get('image')
        alt = request.data.get('alt_text', '')
        order = request.data.get('order', 0)

        if not file_obj:
            return Response({'success': False, 'error': 'Aucun fichier fourni'}, status=status.HTTP_400_BAD_REQUEST)

        img = ProductImage.objects.create(product=product, image=file_obj, alt_text=alt, order=order)
        return Response({'success': True, 'image': ProductImageSerializer(img, context={'request': request}).data}, status=status.HTTP_201_CREATED)


# ProductCategoryTemplateViewSet removed; templates merged into ProductCategory
from django.shortcuts import render

# Create your views here.
