"""
Admin API views for B2C management (pricing)
"""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db.models import Q

from products.models import Product
from stores.models import Store


class IsPlatformAdmin(permissions.BasePermission):
    """Allow access to staff or explicit admin user_type."""
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or user.user_type == 'admin'))


# ============================================================================
# B2C PRICING ENDPOINTS
# ============================================================================

class B2CProductPricingListView(APIView):
    """GET /admin/b2c/pricing/<store_id>/ - Liste des produits B2C avec prix"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request, store_id):
        try:
            store = get_object_or_404(Store, id=store_id)
            
            # Get products with market_type='b2c' or 'both'
            products = Product.objects.filter(
                store=store
            ).filter(
                Q(market_type='b2c') | Q(market_type='both')
            ).select_related('category', 'store').order_by('name')
            
            products_data = []
            for product in products:
                products_data.append({
                    'id': product.id,
                    'name': product.name,
                    'description': product.description or '',
                    'price': float(product.price),
                    'compare_price': float(product.compare_price) if product.compare_price else None,
                    'stock': product.stock,
                    'category_id': product.category.id if product.category else None,
                    'category_name': product.category.name if product.category else '—',
                    'is_available': product.is_available,
                    'market_type': product.market_type,
                    'sku': product.sku or '',
                    'image': product.image.url if product.image else None,
                })
            
            # Get products without B2C pricing (market_type='b2b' only)
            products_without_b2c = Product.objects.filter(
                store=store,
                market_type='b2b'
            ).select_related('category').order_by('name')
            
            products_without_data = []
            for product in products_without_b2c:
                products_without_data.append({
                    'id': product.id,
                    'name': product.name,
                    'description': product.description or '',
                    'category_id': product.category.id if product.category else None,
                    'category_name': product.category.name if product.category else '—',
                    'market_type': product.market_type,
                })
            
            return Response({
                'success': True,
                'data': {
                    'products': products_data,
                    'products_without_b2c': products_without_data,
                    'store': {
                        'id': store.id,
                        'name': store.name,
                    }
                }
            })
        
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
