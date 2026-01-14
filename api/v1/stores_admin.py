"""Stores Management API for admin dashboard."""

from django.db.models import Sum, Count, Q, Exists, OuterRef
from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from stores.models import Store
from orders.models import Order
from users.models import User
from b2b.models import B2BProfile


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
        
        # Optimize queries with select_related and prefetch_related
        stores = stores.select_related('category', 'manager')
        
        # Annotate with counts and B2B profile existence
        stores = stores.annotate(
            products_count=Count('products'),
            orders_count=Count('orders'),
            has_b2b_profile=Exists(
                B2BProfile.objects.filter(store_id=OuterRef('pk'))
            )
        )
        
        data = []
        for store in stores:
            manager = store.manager
            # has_b2b_profile is now an annotation, so we can access it directly
            has_b2b_profile = store.has_b2b_profile
            data.append({
                'id': store.id,
                'name': store.name,
                'category_id': store.category_id,
                'category_name': store.category.name if store.category else None,
                'city': store.city,
                'zone': store.zone,
                'manager_id': store.manager_id,
                'manager_name': f"{manager.first_name} {manager.last_name}" if manager else None,
                'products_count': store.products_count,
                'orders_count': store.orders_count,
                'is_active': store.is_active,
                'is_b2b': store.is_b2b,
                'has_b2b_profile': has_b2b_profile,
                'created_at': store.created_at.isoformat(),
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
        # Optimiser les requêtes pour les stats
        orders_qs = store.orders.all()
        products_count = store.products.count()
        orders_count = orders_qs.count()
        
        # Calculer le revenu total et la moyenne en une seule requête
        revenue_data = orders_qs.filter(status='delivered').aggregate(
            total_revenue=Sum('total_amount')
        )
        total_revenue = float(revenue_data['total_revenue'] or 0)
        
        all_orders_revenue = orders_qs.aggregate(total=Sum('total_amount'))
        average_order_value = float(all_orders_revenue['total'] or 0) / max(orders_count, 1)
        
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
            'is_active': store.is_active,
            'is_verified': store.is_verified,
            'is_b2b': store.is_b2b,
            'b2b_min_order_amount': float(store.b2b_min_order_amount),
            'b2b_delivery_delay': store.b2b_delivery_delay,
            'created_at': store.created_at.isoformat(),
            'stats': {
                'products_count': products_count,
                'orders_count': orders_count,
                'total_revenue': total_revenue,
                'average_order_value': average_order_value,
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


class StoreB2BSettingsUpdateView(APIView):
    """Mettre à jour les paramètres B2B d'un magasin"""
    permission_classes = [IsPlatformAdmin]
    
    def patch(self, request, store_id):
        try:
            store = get_object_or_404(Store, id=store_id)
            data = request.data
            
            # Sauvegarder l'ancienne valeur de is_b2b
            old_is_b2b = store.is_b2b
            
            # Vérifier si is_b2b est activé ou désactivé
            is_b2b_activated = False
            is_b2b_deactivated = False
            if 'is_b2b' in data:
                new_is_b2b = bool(data['is_b2b'])
                # Si on active B2B et qu'il n'était pas activé avant
                if new_is_b2b and not old_is_b2b:
                    is_b2b_activated = True
                # Si on désactive B2B et qu'il était activé avant
                elif not new_is_b2b and old_is_b2b:
                    is_b2b_deactivated = True
                store.is_b2b = new_is_b2b
            
            # Update B2B fields
            if 'b2b_min_order_amount' in data:
                store.b2b_min_order_amount = float(data['b2b_min_order_amount'])
            if 'b2b_delivery_delay' in data:
                store.b2b_delivery_delay = int(data['b2b_delivery_delay'])
            
            store.save()
            
            # Si B2B est activé, créer/activer automatiquement le profil B2B
            profile_created = False
            profile_updated = False
            if is_b2b_activated:
                try:
                    # S'assurer que b2b_min_order_amount a une valeur par défaut
                    min_order = store.b2b_min_order_amount if store.b2b_min_order_amount else 0
                    
                    profile, created = B2BProfile.objects.get_or_create(
                        store=store,
                        defaults={
                            'minimum_order_amount': min_order,
                            'visible_to_all': True,
                            'is_active': True,
                        }
                    )
                    if created:
                        profile_created = True
                    else:
                        # Mettre à jour le profil existant
                        profile.is_active = True
                        profile.minimum_order_amount = min_order
                        profile.visible_to_all = True
                        profile.save()
                        profile_updated = True
                except Exception as profile_error:
                    # Si la création du profil échoue, on log l'erreur mais on continue
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Erreur lors de la création du profil B2B pour le magasin {store.id}: {str(profile_error)}")
                    # On ne bloque pas la requête, mais on retourne un warning
                    return Response({
                        'success': False,
                        'error': f'Le magasin a été mis à jour mais le profil B2B n\'a pas pu être créé: {str(profile_error)}'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Si B2B est désactivé, désactiver aussi le profil B2B
            if is_b2b_deactivated:
                if hasattr(store, 'b2b_profile'):
                    store.b2b_profile.is_active = False
                    store.b2b_profile.save()
            
            # Recharger le store depuis la DB pour avoir la relation b2b_profile à jour
            store.refresh_from_db()
            
            # Préparer la réponse avec les infos du profil B2B
            response_data = {
                'id': store.id,
                'name': store.name,
                'is_b2b': store.is_b2b,
                'b2b_min_order_amount': float(store.b2b_min_order_amount),
                'b2b_delivery_delay': store.b2b_delivery_delay,
            }
            
            # Ajouter les infos du profil B2B si disponible
            try:
                if hasattr(store, 'b2b_profile') and store.b2b_profile:
                    response_data['b2b_profile'] = {
                        'id': store.b2b_profile.id,
                        'is_active': store.b2b_profile.is_active,
                        'minimum_order_amount': float(store.b2b_profile.minimum_order_amount),
                        'visible_to_all': store.b2b_profile.visible_to_all,
                    }
            except B2BProfile.DoesNotExist:
                pass
            
            message = 'Paramètres B2B mis à jour avec succès'
            if profile_created:
                message += ' - Profil B2B créé automatiquement'
            elif profile_updated:
                message += ' - Profil B2B activé automatiquement'
            
            return Response({
                'success': True,
                'message': message,
                'data': response_data
            })
        
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class StoreB2CSettingsUpdateView(APIView):
    """Mettre à jour les paramètres B2C d'un magasin"""
    permission_classes = [IsPlatformAdmin]
    
    def patch(self, request, store_id):
        try:
            store = get_object_or_404(Store, id=store_id)
            data = request.data
            
            # Sauvegarder l'ancienne valeur de is_b2c
            old_is_b2c = store.is_b2c
            
            # Vérifier si is_b2c est activé ou désactivé
            is_b2c_activated = False
            is_b2c_deactivated = False
            if 'is_b2c' in data:
                new_is_b2c = bool(data['is_b2c'])
                # Si on active B2C et qu'il n'était pas activé avant
                if new_is_b2c and not old_is_b2c:
                    is_b2c_activated = True
                # Si on désactive B2C et qu'il était activé avant
                elif not new_is_b2c and old_is_b2c:
                    is_b2c_deactivated = True
                store.is_b2c = new_is_b2c
            
            store.save()
            
            # Préparer la réponse
            response_data = {
                'id': store.id,
                'name': store.name,
                'is_b2c': store.is_b2c,
                'is_b2b': store.is_b2b,
            }
            
            message = 'Paramètres B2C mis à jour avec succès'
            if is_b2c_activated:
                message += ' - Le magasin peut maintenant vendre au détail'
            elif is_b2c_deactivated:
                message += ' - Le magasin ne peut plus vendre au détail'
            
            return Response({
                'success': True,
                'message': message,
                'data': response_data
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
