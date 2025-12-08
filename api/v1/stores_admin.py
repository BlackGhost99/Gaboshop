"""Stores Management API for admin dashboard."""

from django.db.models import Sum, Count, Q
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from stores.models import Store
from orders.models import Order
from users.models import User


class IsPlatformAdmin(permissions.BasePermission):
    """Only platform admins can access"""
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or user.user_type == 'admin'))


class StoresListView(APIView):
    """Liste des magasins avec filtrage avancé"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request):
        stores = Store.objects.all()
        
        # Filtering
        search = request.query_params.get('search', '')
        category = request.query_params.get('category', '')
        city = request.query_params.get('city', '')
        status_filter = request.query_params.get('status', 'all')
        sort = request.query_params.get('sort', 'date')
        
        if search:
            stores = stores.filter(
                Q(name__icontains=search) | 
                Q(description__icontains=search) |
                Q(manager__first_name__icontains=search) |
                Q(manager__last_name__icontains=search)
            )
        
        if category:
            stores = stores.filter(category_id=category)
        
        if city:
            stores = stores.filter(city__icontains=city)
        
        if status_filter == 'active':
            stores = stores.filter(is_active=True)
        elif status_filter == 'inactive':
            stores = stores.filter(is_active=False)
        
        # Sorting
        if sort == 'name':
            stores = stores.order_by('name')
        elif sort == 'orders':
            stores = stores.annotate(order_count=Count('orders')).order_by('-order_count')
        else:  # date
            stores = stores.order_by('-created_at')
        
        # Annotate with counts
        stores = stores.annotate(
            products_count=Count('products'),
            orders_count=Count('orders')
        )
        
        data = []
        for store in stores:
            manager = store.manager
            data.append({
                'id': store.id,
                'name': store.name,
                'description': store.description,
                'category_id': store.category_id,
                'category_name': store.category.name if store.category else None,
                'city': store.city,
                'address': store.address,
                'zone': store.zone,
                'phone': store.phone,
                'email': store.email,
                'manager_id': store.manager_id,
                'manager_name': f"{manager.first_name} {manager.last_name}" if manager else None,
                'products_count': store.products_count,
                'orders_count': store.orders_count,
                'subscription_plan': store.subscription_plan,
                'commission_rate': float(store.commission_rate),
                'delivery_fee': float(store.delivery_fee),
                'is_active': store.is_active,
                'created_at': store.created_at.isoformat(),
                'updated_at': store.updated_at.isoformat() if store.updated_at else None,
            })
        
        return Response({
            'success': True,
            'data': data,
            'count': len(data)
        })


class StoreDetailView(APIView):
    """Détails complets d'un magasin"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request, store_id):
        store = get_object_or_404(Store, id=store_id)
        
        manager = store.manager
        data = {
            'id': store.id,
            'name': store.name,
            'description': store.description,
            'category_id': store.category_id,
            'category_name': store.category.name if store.category else None,
            'city': store.city,
            'address': store.address,
            'zone': store.zone,
            'phone': store.phone,
            'email': store.email,
            'manager_id': store.manager_id,
            'manager_name': f"{manager.first_name} {manager.last_name}" if manager else None,
            'subscription_plan': store.subscription_plan,
            'commission_rate': float(store.commission_rate),
            'delivery_fee': float(store.delivery_fee),
            'is_active': store.is_active,
            'created_at': store.created_at.isoformat(),
            'updated_at': store.updated_at.isoformat() if store.updated_at else None,
            'stats': {
                'products_count': store.products.count(),
                'orders_count': store.orders.count(),
                'total_revenue': float(
                    Order.objects.filter(store_id=store_id, status='delivered')
                    .aggregate(Sum('total_amount'))['total_amount__sum'] or 0
                ),
                'average_order_value': float(
                    Order.objects.filter(store_id=store_id)
                    .aggregate(Sum('total_amount'))['total_amount__sum'] or 0
                ) / max(store.orders.count(), 1),
            }
        }
        
        return Response({
            'success': True,
            'data': data
        })


class StoreCreateView(APIView):
    """Créer un nouveau magasin"""
    permission_classes = [IsPlatformAdmin]
    
    def post(self, request):
        try:
            data = request.data
            
            # Validation
            if not data.get('name'):
                return Response({'success': False, 'error': 'Name is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not data.get('manager_id'):
                return Response({'success': False, 'error': 'Manager is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not data.get('category_id'):
                return Response({'success': False, 'error': 'Category is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check manager exists
            manager = get_object_or_404(User, id=data.get('manager_id'))
            
            # Create store
            store = Store.objects.create(
                name=data.get('name'),
                description=data.get('description', ''),
                category_id=data.get('category_id'),
                manager=manager,
                city=data.get('city', 'Libreville'),
                address=data.get('address', ''),
                zone=data.get('zone', ''),
                phone=data.get('phone', ''),
                email=data.get('email', ''),
                commission_rate=float(data.get('commission_rate', 0)),
                delivery_fee=float(data.get('delivery_fee', 0)),
                subscription_plan=data.get('subscription_plan', 'starter'),
                is_active=data.get('is_active', True),
            )
            
            return Response({
                'success': True,
                'message': 'Store created successfully',
                'data': {
                    'id': store.id,
                    'name': store.name,
                }
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StoreUpdateView(APIView):
    """Mettre à jour un magasin"""
    permission_classes = [IsPlatformAdmin]
    
    def patch(self, request, store_id):
        try:
            store = get_object_or_404(Store, id=store_id)
            data = request.data
            
            # Update fields
            if 'name' in data:
                store.name = data['name']
            if 'description' in data:
                store.description = data['description']
            if 'category_id' in data:
                store.category_id = data['category_id']
            if 'manager_id' in data:
                manager = get_object_or_404(User, id=data['manager_id'])
                store.manager = manager
            if 'city' in data:
                store.city = data['city']
            if 'address' in data:
                store.address = data['address']
            if 'zone' in data:
                store.zone = data['zone']
            if 'phone' in data:
                store.phone = data['phone']
            if 'email' in data:
                store.email = data['email']
            if 'commission_rate' in data:
                store.commission_rate = float(data['commission_rate'])
            if 'delivery_fee' in data:
                store.delivery_fee = float(data['delivery_fee'])
            if 'subscription_plan' in data:
                store.subscription_plan = data['subscription_plan']
            if 'is_active' in data:
                store.is_active = data['is_active']
            
            store.save()
            
            return Response({
                'success': True,
                'message': 'Store updated successfully',
                'data': {
                    'id': store.id,
                    'name': store.name,
                }
            })
        
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StoreDeactivateView(APIView):
    """Désactiver un magasin (soft delete)"""
    permission_classes = [IsPlatformAdmin]
    
    def post(self, request, store_id):
        try:
            store = get_object_or_404(Store, id=store_id)
            store.is_active = False
            store.save()
            
            return Response({
                'success': True,
                'message': 'Store deactivated successfully'
            })
        
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StoreActivateView(APIView):
    """Réactiver un magasin"""
    permission_classes = [IsPlatformAdmin]
    
    def post(self, request, store_id):
        try:
            store = get_object_or_404(Store, id=store_id)
            store.is_active = True
            store.save()
            
            return Response({
                'success': True,
                'message': 'Store activated successfully'
            })
        
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StoreDeleteView(APIView):
    """Supprimer un magasin (soft delete ou hard delete)"""
    permission_classes = [IsPlatformAdmin]
    
    def delete(self, request, store_id):
        try:
            store = get_object_or_404(Store, id=store_id)
            hard_delete = request.query_params.get('hard_delete', 'false').lower() == 'true'
            
            if hard_delete:
                # Hard delete - Remove from database
                store_name = store.name
                store.delete()
                return Response({
                    'success': True,
                    'message': f'Store "{store_name}" permanently deleted'
                })
            else:
                # Soft delete - Just deactivate
                store.is_active = False
                store.save()
                return Response({
                    'success': True,
                    'message': 'Store archived (soft deleted)'
                })
        
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StoreProductsView(APIView):
    """Produits d'un magasin"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request, store_id):
        store = get_object_or_404(Store, id=store_id)
        
        products = store.products.all()
        
        # Filtering
        search = request.query_params.get('search', '')
        category = request.query_params.get('category', '')
        
        if search:
            products = products.filter(Q(name__icontains=search) | Q(description__icontains=search))
        
        if category:
            products = products.filter(category_id=category)
        
        data = []
        for product in products:
            data.append({
                'id': product.id,
                'name': product.name,
                'description': product.description,
                'price': float(product.price),
                'stock': product.stock,
                'is_available': product.is_available,
                'category_id': product.category_id,
            })
        
        return Response({
            'success': True,
            'data': data,
            'count': len(data)
        })


class StoreOrdersView(APIView):
    """Commandes d'un magasin"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request, store_id):
        get_object_or_404(Store, id=store_id)  # Verify store exists
        
        orders = Order.objects.filter(store_id=store_id)
        
        # Filtering
        status_filter = request.query_params.get('status', 'all')
        date_range = request.query_params.get('date_range', 'all')
        
        if status_filter != 'all':
            orders = orders.filter(status=status_filter)
        
        today = timezone.now().date()
        if date_range == 'today':
            orders = orders.filter(created_at__date=today)
        elif date_range == 'week':
            orders = orders.filter(created_at__date__gte=today - timezone.timedelta(days=7))
        elif date_range == 'month':
            orders = orders.filter(created_at__date__gte=today.replace(day=1))
        
        orders = orders.order_by('-created_at')
        
        data = []
        for order in orders:
            data.append({
                'id': order.id,
                'order_number': order.order_number,
                'client_name': f"{order.client.first_name} {order.client.last_name}" if order.client else "Unknown",
                'total_amount': float(order.total_amount),
                'status': order.status,
                'payment_status': order.payment_status,
                'created_at': order.created_at.isoformat(),
            })
        
        return Response({
            'success': True,
            'data': data,
            'count': len(data)
        })


class StoreDeliveryAgentsView(APIView):
    """Livreurs assignés à un magasin"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request, store_id):
        get_object_or_404(Store, id=store_id)  # Verify store exists
        
        # Get unique delivery agents who have delivered orders for this store
        agents = User.objects.filter(
            delivery__order__store_id=store_id,
            user_type='DELIVERY_AGENT'
        ).distinct()
        
        data = []
        for agent in agents:
            delivery_count = agent.delivery_set.filter(order__store_id=store_id).count()
            data.append({
                'id': agent.id,
                'name': f"{agent.first_name} {agent.last_name}",
                'phone': agent.phone,
                'deliveries': delivery_count,
            })
        
        return Response({
            'success': True,
            'data': data,
            'count': len(data)
        })
