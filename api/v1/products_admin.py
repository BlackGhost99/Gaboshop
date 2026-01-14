"""Products Management API for admin dashboard."""

from django.db.models import Sum, Count, Q, F
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from decimal import Decimal

from products.models import Product
from stores.models import Store
from orders.models import OrderItem


class IsPlatformAdmin(permissions.BasePermission):
    """Only platform admins can access"""
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or user.user_type == 'admin'))


class ProductsListView(APIView):
    """Liste des produits avec filtrage avancé"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request):
        products = Product.objects.select_related('store', 'category').all()
        
        # Filtering
        search = request.query_params.get('search', '')
        category = request.query_params.get('category', '')
        store_id = request.query_params.get('store_id', '')
        status_filter = request.query_params.get('status', 'all')
        stock_filter = request.query_params.get('stock', 'all')
        promo_filter = request.query_params.get('promo', 'all')
        price_min = request.query_params.get('price_min', '')
        price_max = request.query_params.get('price_max', '')
        sort = request.query_params.get('sort', 'date')
        
        if search:
            products = products.filter(
                Q(name__icontains=search) | 
                Q(description__icontains=search) |
                Q(sku__icontains=search) |
                Q(store__name__icontains=search)
            )
        
        if category:
            products = products.filter(category_id=category)
        
        if store_id:
            products = products.filter(store_id=store_id)
        
        if status_filter == 'active':
            products = products.filter(is_available=True)
        elif status_filter == 'inactive':
            products = products.filter(is_available=False)
        
        if stock_filter == 'in_stock':
            products = products.filter(stock__gt=0)
        elif stock_filter == 'low_stock':
            products = products.filter(stock__gt=0, stock__lte=10)
        elif stock_filter == 'out_of_stock':
            products = products.filter(stock=0)
        
        if promo_filter == 'promo':
            products = products.filter(compare_price__gt=F('price'))
        elif promo_filter == 'no_promo':
            products = products.filter(Q(compare_price__isnull=True) | Q(compare_price__lte=F('price')))
        
        if price_min:
            products = products.filter(price__gte=Decimal(price_min))
        if price_max:
            products = products.filter(price__lte=Decimal(price_max))
        
        # Sorting
        if sort == 'name':
            products = products.order_by('name')
        elif sort == 'price_asc':
            products = products.order_by('price')
        elif sort == 'price_desc':
            products = products.order_by('-price')
        elif sort == 'stock':
            products = products.order_by('-stock')
        elif sort == 'popularity':
            products = products.annotate(
                order_count=Count('orderitem')
            ).order_by('-order_count')
        else:  # date
            products = products.order_by('-created_at')
        
        data = []
        for product in products:
            # Calculate stock status
            stock_status = 'out_of_stock'
            if product.stock > 10:
                stock_status = 'in_stock'
            elif product.stock > 0:
                stock_status = 'low_stock'
            
            # Calculate if on promo
            on_promo = product.compare_price and product.compare_price > product.price
            
            # Determine display prices
            # price: Regular/Original price
            # promo_price: Discounted/Selling price (if on promo)
            display_price = product.compare_price if on_promo else product.price
            display_promo_price = product.price if on_promo else None
            
            data.append({
                'id': product.id,
                'name': product.name,
                'description': product.description,
                'sku': getattr(product, 'sku', None),
                'category_id': product.category_id,
                'category_name': product.category.name if product.category else None,
                'store_id': product.store_id,
                'store_name': product.store.name if product.store else None,
                'price': float(display_price),
                'promo_price': float(display_promo_price) if display_promo_price else None,
                'on_promo': on_promo,
                'stock': product.stock,
                'stock_status': stock_status,
                'is_available': product.is_available,
                'image': product.image.url if product.image else None,
                'created_at': product.created_at.isoformat(),
                'updated_at': product.updated_at.isoformat() if hasattr(product, 'updated_at') and product.updated_at else None,
            })
        
        return Response({
            'success': True,
            'data': data,
            'count': len(data)
        })


class ProductDetailView(APIView):
    """Détails complets d'un produit avec statistiques"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request, product_id):
        product = get_object_or_404(
            Product.objects.select_related('store', 'category'),
            id=product_id
        )
        
        # Calculate stats
        order_items = OrderItem.objects.filter(product_id=product_id)
        total_orders = order_items.count()
        total_revenue = float(
            order_items.aggregate(Sum('total_price'))['total_price__sum'] or 0
        )
        
        # Stock status
        stock_status = 'out_of_stock'
        if product.stock > 10:
            stock_status = 'in_stock'
        elif product.stock > 0:
            stock_status = 'low_stock'
        
        # Check if on promo
        on_promo = False
        if product.promo_price and product.promo_price < product.price:
            on_promo = True
        
        data = {
            'id': product.id,
            'name': product.name,
            'description': product.description,
            'sku': getattr(product, 'sku', None),
            'category_id': product.category_id,
            'category_name': product.category.name if product.category else None,
            'store_id': product.store_id,
            'store_name': product.store.name if product.store else None,
            'price': float(product.price),
            'promo_price': float(product.promo_price) if product.promo_price else None,
            'on_promo': on_promo,
            'stock': product.stock,
            'stock_status': stock_status,
            'is_available': product.is_available,
            'image': product.image.url if product.image else None,
            'created_at': product.created_at.isoformat(),
            'updated_at': product.updated_at.isoformat() if hasattr(product, 'updated_at') and product.updated_at else None,
            'stats': {
                'total_orders': total_orders,
                'total_revenue': total_revenue,
                'average_order_value': total_revenue / max(total_orders, 1),
            }
        }
        
        return Response({
            'success': True,
            'data': data
        })


class ProductCreateView(APIView):
    """Créer un nouveau produit"""
    permission_classes = [IsPlatformAdmin]
    
    def post(self, request):
        try:
            data = request.data
            
            # Validation
            if not data.get('name'):
                return Response({'success': False, 'error': 'Name is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not data.get('store_id'):
                return Response({'success': False, 'error': 'Store is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not data.get('price'):
                return Response({'success': False, 'error': 'Price is required'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate price is not negative
            price = Decimal(str(data.get('price')))
            if price < 0:
                return Response({'success': False, 'error': 'Price cannot be negative'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Validate stock is not negative
            stock = int(data.get('stock', 0))
            if stock < 0:
                return Response({'success': False, 'error': 'Stock cannot be negative'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check store exists
            store = get_object_or_404(Store, id=data.get('store_id'))
            
            # Create product
            product = Product.objects.create(
                name=data.get('name'),
                description=data.get('description', ''),
                store=store,
                category_id=data.get('category_id') if data.get('category_id') else None,
                price=price,
                promo_price=Decimal(str(data.get('promo_price'))) if data.get('promo_price') else None,
                stock=stock,
                is_available=data.get('is_available', True),
            )
            
            # Handle image upload if provided
            if request.FILES.get('image'):
                product.image = request.FILES['image']
                product.save()
            
            return Response({
                'success': True,
                'message': 'Product created successfully',
                'data': {
                    'id': product.id,
                    'name': product.name,
                }
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProductUpdateView(APIView):
    """Mettre à jour un produit"""
    permission_classes = [IsPlatformAdmin]
    
    def patch(self, request, product_id):
        try:
            product = get_object_or_404(Product, id=product_id)
            data = request.data
            
            # Update fields
            if 'name' in data:
                product.name = data['name']
            if 'description' in data:
                product.description = data['description']
            if 'category_id' in data:
                product.category_id = data['category_id'] if data['category_id'] else None
            if 'price' in data:
                price = Decimal(str(data['price']))
                if price < 0:
                    return Response({'success': False, 'error': 'Price cannot be negative'}, status=status.HTTP_400_BAD_REQUEST)
                product.price = price
            if 'promo_price' in data:
                product.promo_price = Decimal(str(data['promo_price'])) if data['promo_price'] else None
            if 'compare_price' in data:
                product.compare_price = Decimal(str(data['compare_price'])) if data['compare_price'] else None
            if 'stock' in data:
                stock = int(data['stock'])
                if stock < 0:
                    return Response({'success': False, 'error': 'Stock cannot be negative'}, status=status.HTTP_400_BAD_REQUEST)
                product.stock = stock
            if 'is_available' in data:
                product.is_available = data['is_available']
            
            # Handle image upload if provided
            if request.FILES.get('image'):
                product.image = request.FILES['image']
            
            product.save()
            
            return Response({
                'success': True,
                'message': 'Product updated successfully',
                'data': {
                    'id': product.id,
                    'name': product.name,
                }
            })
        
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProductActivateView(APIView):
    """Activer un produit"""
    permission_classes = [IsPlatformAdmin]
    
    def post(self, request, product_id):
        try:
            product = get_object_or_404(Product, id=product_id)
            product.is_available = True
            product.save()
            
            return Response({
                'success': True,
                'message': 'Product activated successfully'
            })
        
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProductDeactivateView(APIView):
    """Désactiver un produit"""
    permission_classes = [IsPlatformAdmin]
    
    def post(self, request, product_id):
        try:
            product = get_object_or_404(Product, id=product_id)
            product.is_available = False
            product.save()
            
            return Response({
                'success': True,
                'message': 'Product deactivated successfully'
            })
        
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProductDeleteView(APIView):
    """Supprimer un produit (soft delete ou hard delete)"""
    permission_classes = [IsPlatformAdmin]
    
    def delete(self, request, product_id):
        try:
            product = get_object_or_404(Product, id=product_id)
            hard_delete = request.query_params.get('hard_delete', 'false').lower() == 'true'
            
            # Check if product has been ordered
            has_orders = OrderItem.objects.filter(product_id=product_id).exists()
            
            if has_orders and hard_delete:
                return Response({
                    'success': False,
                    'error': 'Cannot permanently delete product with existing orders. Use soft delete instead.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            if hard_delete and not has_orders:
                # Hard delete - Remove from database
                product_name = product.name
                product.delete()
                return Response({
                    'success': True,
                    'message': f'Product "{product_name}" permanently deleted'
                })
            else:
                # Soft delete - Just deactivate
                product.is_available = False
                product.save()
                return Response({
                    'success': True,
                    'message': 'Product archived (soft deleted)'
                })
        
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProductBulkActionsView(APIView):
    """Actions en masse sur plusieurs produits"""
    permission_classes = [IsPlatformAdmin]
    
    def post(self, request):
        try:
            action = request.data.get('action')
            product_ids = request.data.get('product_ids', [])
            
            if not product_ids:
                return Response({'success': False, 'error': 'No products selected'}, status=status.HTTP_400_BAD_REQUEST)
            
            products = Product.objects.filter(id__in=product_ids)
            
            if action == 'activate':
                products.update(is_available=True)
                message = f'{products.count()} products activated'
            elif action == 'deactivate':
                products.update(is_available=False)
                message = f'{products.count()} products deactivated'
            elif action == 'delete':
                # Check if any have orders
                has_orders = OrderItem.objects.filter(product_id__in=product_ids).exists()
                if has_orders:
                    products.update(is_available=False)
                    message = f'{products.count()} products archived (have existing orders)'
                else:
                    count = products.count()
                    products.delete()
                    message = f'{count} products permanently deleted'
            elif action == 'update_stock':
                stock_value = request.data.get('stock_value', 0)
                products.update(stock=stock_value)
                message = f'{products.count()} products stock updated to {stock_value}'
            else:
                return Response({'success': False, 'error': 'Invalid action'}, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({
                'success': True,
                'message': message
            })
        
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProductStatsView(APIView):
    """Statistiques globales des produits"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request):
        total_products = Product.objects.count()
        active_products = Product.objects.filter(is_available=True).count()
        inactive_products = Product.objects.filter(is_available=False).count()
        out_of_stock = Product.objects.filter(stock=0).count()
        low_stock = Product.objects.filter(stock__gt=0, stock__lte=10).count()
        on_promo = Product.objects.filter(
            compare_price__gt=F('price')
        ).count()
        
        stats = {
            'total_products': total_products,
            'active_products': active_products,
            'inactive_products': inactive_products,
            'out_of_stock': out_of_stock,
            'low_stock': low_stock,
            'on_promo': on_promo,
        }
        
        return Response({
            'success': True,
            'data': stats
        })
