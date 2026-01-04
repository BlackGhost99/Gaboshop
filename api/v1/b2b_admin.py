"""
Admin API views for B2B management (categories, orders)
"""
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta

from b2b.models import B2BCategory
from b2b.api.serializers import B2BCategorySerializer, B2BOrderSerializer
from orders.models import Order
from stores.models import Store


class IsPlatformAdmin(permissions.BasePermission):
    """Allow access to staff or explicit admin user_type."""
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or user.user_type == 'admin'))


# ============================================================================
# B2B CATEGORY ENDPOINTS
# ============================================================================

class B2BCategoryListView(APIView):
    """GET /admin/b2b/categories/ - Liste des catégories B2B"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request):
        is_active = request.query_params.get('is_active')
        search = request.query_params.get('search')
        
        categories = B2BCategory.objects.all()
        
        if is_active is not None:
            categories = categories.filter(is_active=is_active.lower() == 'true')
        if search:
            categories = categories.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )
        
        categories = categories.order_by('name')
        serializer = B2BCategorySerializer(categories, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': categories.count()
        })


class B2BCategoryCreateView(APIView):
    """POST /admin/b2b/categories/ - Créer une catégorie B2B"""
    permission_classes = [IsPlatformAdmin]
    
    def post(self, request):
        serializer = B2BCategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'data': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class B2BCategoryUpdateView(APIView):
    """PATCH /admin/b2b/categories/<id>/ - Modifier une catégorie B2B"""
    permission_classes = [IsPlatformAdmin]
    
    def patch(self, request, category_id):
        try:
            category = B2BCategory.objects.get(id=category_id)
            serializer = B2BCategorySerializer(category, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'success': True,
                    'data': serializer.data
                })
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        except B2BCategory.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Catégorie introuvable'
            }, status=status.HTTP_404_NOT_FOUND)


class B2BCategoryDeleteView(APIView):
    """DELETE /admin/b2b/categories/<id>/ - Supprimer une catégorie B2B"""
    permission_classes = [IsPlatformAdmin]
    
    def delete(self, request, category_id):
        try:
            category = B2BCategory.objects.get(id=category_id)
            # Vérifier qu'aucun produit n'utilise cette catégorie
            from products.models import Product
            products_count = Product.objects.filter(b2b_category=category).count()
            if products_count > 0:
                return Response({
                    'success': False,
                    'error': f'Impossible de supprimer: {products_count} produit(s) utilisent cette catégorie'
                }, status=status.HTTP_400_BAD_REQUEST)
            category.delete()
            return Response({
                'success': True,
                'message': 'Catégorie supprimée avec succès'
            })
        except B2BCategory.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Catégorie introuvable'
            }, status=status.HTTP_404_NOT_FOUND)


# ============================================================================
# B2B ORDERS ENDPOINTS
# ============================================================================

class B2BOrderListView(APIView):
    """GET /admin/b2b/orders/ - Liste des commandes B2B avec filtres avancés"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request):
        # Filtres
        store_id = request.query_params.get('store_id')  # Grossiste (seller)
        source_store_id = request.query_params.get('source_store_id')  # Buyer
        status_filter = request.query_params.get('status')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        search = request.query_params.get('search')
        
        orders = Order.objects.filter(is_b2b=True).select_related(
            'store', 'source_store', 'client'
        ).prefetch_related('items')
        
        if store_id:
            orders = orders.filter(store_id=store_id)
        if source_store_id:
            orders = orders.filter(source_store_id=source_store_id)
        if status_filter:
            orders = orders.filter(status=status_filter)
        if date_from:
            orders = orders.filter(created_at__gte=date_from)
        if date_to:
            orders = orders.filter(created_at__lte=date_to)
        if search:
            orders = orders.filter(
                Q(order_number__icontains=search) |
                Q(store__name__icontains=search) |
                Q(source_store__name__icontains=search)
            )
        
        orders = orders.order_by('-created_at')
        serializer = B2BOrderSerializer(orders, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': orders.count()
        })


class B2BOrderDetailView(APIView):
    """GET /admin/b2b/orders/<id>/ - Détail d'une commande B2B"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request, order_id):
        try:
            order = Order.objects.filter(is_b2b=True, id=order_id).select_related(
                'store', 'source_store', 'client'
            ).prefetch_related('items').first()
            
            if not order:
                return Response({
                    'success': False,
                    'error': 'Commande B2B introuvable'
                }, status=status.HTTP_404_NOT_FOUND)
            
            serializer = B2BOrderSerializer(order)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class B2BOrderStatusUpdateView(APIView):
    """PATCH /admin/b2b/orders/<id>/status/ - Modifier le statut d'une commande B2B"""
    permission_classes = [IsPlatformAdmin]
    
    def patch(self, request, order_id):
        try:
            order = Order.objects.filter(is_b2b=True, id=order_id).first()
            if not order:
                return Response({
                    'success': False,
                    'error': 'Commande B2B introuvable'
                }, status=status.HTTP_404_NOT_FOUND)
            
            new_status = request.data.get('status')
            if not new_status:
                return Response({
                    'success': False,
                    'error': 'Statut requis'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Valider le statut
            valid_statuses = ['created', 'confirmed', 'preparing', 'ready', 'assigned', 'in_transit', 'delivered', 'cancelled']
            if new_status not in valid_statuses:
                return Response({
                    'success': False,
                    'error': f'Statut invalide. Statuts valides: {", ".join(valid_statuses)}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Mettre à jour le statut
            old_status = order.status
            order.status = new_status
            
            # Mettre à jour les timestamps si nécessaire
            if new_status == 'confirmed' and not order.confirmed_at:
                order.confirmed_at = timezone.now()
            elif new_status == 'delivered' and not order.delivered_at:
                order.delivered_at = timezone.now()
            
            order.save()
            
            serializer = B2BOrderSerializer(order)
            return Response({
                'success': True,
                'data': serializer.data,
                'message': f'Statut changé de {old_status} à {new_status}'
            })
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

