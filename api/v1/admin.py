"""Admin API views for platform-wide management and KPIs."""

from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import timedelta
from django.db import IntegrityError
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from users.models import User
from stores.models import Store, StoreCategory
from products.models import Product, ProductCategory
from orders.models import Order, OrderItem
from delivery.models import Delivery
from payments.models import Payment
from api.models import SystemSettings


class IsPlatformAdmin(permissions.BasePermission):
    """Allow access to staff or explicit admin user_type."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or user.user_type == 'admin'))


class AdminSummaryView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        now = timezone.now()
        today = now.date()
        month_start = today.replace(day=1)
        
        # --- KPIs ---
        orders_qs = Order.objects.all()
        
        # Orders
        orders_today = orders_qs.filter(created_at__date=today).count()
        orders_month = orders_qs.filter(created_at__date__gte=month_start).count()
        orders_pending = orders_qs.filter(status__in=['created', 'pending_payment', 'paid', 'confirmed', 'preparing']).count()
        orders_delivered = orders_qs.filter(status='delivered').count()

        # Finance
        sales_today = orders_qs.filter(created_at__date=today).exclude(status__in=['cancelled', 'refunded']).aggregate(s=Sum('total_amount'))['s'] or 0
        sales_month = orders_qs.filter(created_at__date__gte=month_start).exclude(status__in=['cancelled', 'refunded']).aggregate(s=Sum('total_amount'))['s'] or 0
        commissions_total = orders_qs.aggregate(s=Sum('commission_amount'))['s'] or 0
        
        # Stores
        stores_qs = Store.objects.all()
        stores_total = stores_qs.count()
        stores_new_month = stores_qs.filter(created_at__date__gte=month_start).count()
        
        # Users
        users_qs = User.objects.all()
        clients_active = users_qs.filter(user_type='client', is_active=True).count()
        active_agents_today = Delivery.objects.filter(updated_at__date=today).values('delivery_agent').distinct().count()
        
        # Detailed counts for Users tab
        users_counts = {
            "total": users_qs.count(),
            "clients": users_qs.filter(user_type='client').count(),
            "store_managers": users_qs.filter(user_type='store_manager').count(),
            "delivery_agents": users_qs.filter(user_type='delivery_agent').count(),
        }

        # --- Charts ---
        # Sales Curve (Last 30 days)
        sales_curve = []
        for i in range(30):
            d = today - timedelta(days=i)
            day_orders = orders_qs.filter(created_at__date=d).exclude(status__in=['cancelled', 'refunded'])
            sales_curve.append({
                "date": d.strftime("%Y-%m-%d"),
                "sales": day_orders.aggregate(s=Sum('total_amount'))['s'] or 0,
                "commissions": day_orders.aggregate(s=Sum('commission_amount'))['s'] or 0,
                "count": day_orders.count()
            })
        sales_curve.reverse()

        # Category Distribution
        category_dist = OrderItem.objects.values('product__category__name').annotate(count=Count('id')).order_by('-count')[:5]
        categories_chart = [{"name": c['product__category__name'], "value": c['count']} for c in category_dist if c['product__category__name']]

        # --- Alerts ---
        low_stock_products = Product.objects.filter(stock__lt=10, is_available=True).values('id', 'name', 'store__name', 'stock')[:5]
        deactivated_stores = stores_qs.filter(is_active=False).values('id', 'name')[:5]
        unvalidated_agents = users_qs.filter(user_type='delivery_agent', is_verified=False).values('id', 'first_name', 'last_name', 'phone')[:5]

        # --- Recent Orders ---
        recent_orders = orders_qs.select_related('client', 'store').order_by('-created_at')[:10].values(
            'id', 'order_number', 'client__first_name', 'client__last_name', 'store__name', 'total_amount', 'status', 'created_at'
        )

        # --- Top Lists ---
        top_products = OrderItem.objects.values('product__name', 'product__store__name').annotate(total_sold=Sum('quantity')).order_by('-total_sold')[:5]
        top_stores = stores_qs.annotate(revenue=Sum('orders__total_amount'), order_count=Count('orders')).order_by('-revenue')[:5].values('name', 'revenue', 'order_count')

        data = {
            "kpis": {
                "orders": {"today": orders_today, "month": orders_month, "pending": orders_pending, "delivered": orders_delivered},
                "finance": {"sales_today": sales_today, "sales_month": sales_month, "commissions_total": commissions_total},
                "stores": {"total": stores_total, "new_month": stores_new_month},
                "users": {"clients_active": clients_active, "agents_active_today": active_agents_today}
            },
            "user_counts": users_counts,
            "charts": {
                "sales_curve": sales_curve,
                "categories": categories_chart
            },
            "alerts": {
                "low_stock": list(low_stock_products),
                "deactivated_stores": list(deactivated_stores),
                "unvalidated_agents": list(unvalidated_agents)
            },
            "recent_orders": list(recent_orders),
            "top_lists": {
                "products": list(top_products),
                "stores": list(top_stores)
            },
            "system_status": {
                "api_errors": 0,
                "notifications": 0,
                "last_sync": "OK",
                "api_health": "OK"
            }
        }

        return Response({"success": True, "data": data})


class AdminUsersView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        user_type = request.query_params.get('type')
        qs = User.objects.all().order_by('-date_joined')
        if user_type:
            qs = qs.filter(user_type=user_type)
        
        # For delivery agents, also prefetch delivery_profile
        if user_type == 'delivery_agent':
            qs = qs.select_related('delivery_profile')
        
        data = []
        for u in qs[:200]:
            user_data = {
                "id": u.id,
                "phone": u.phone,
                "user_type": u.user_type,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "email": u.email,
                "city": getattr(u, 'city', ''),
                "is_active": u.is_active,
                "is_staff": u.is_staff,
                "is_verified": getattr(u, 'is_verified', False),
                "is_available": getattr(u, 'is_available', False),
                "created_at": u.date_joined,
            }
            
            # Add delivery profile for delivery agents
            if u.user_type == 'delivery_agent' and hasattr(u, 'delivery_profile'):
                profile = u.delivery_profile
                user_data['profile'] = {
                    'vehicle_type': profile.vehicle_type,
                    'vehicle_plate': profile.vehicle_plate,
                    'cin_number': profile.cin_number,
                    'status': profile.status,
                    'average_rating': str(profile.average_rating),
                    'total_deliveries': profile.total_deliveries,
                    'success_rate': str(profile.success_rate)
                }
            
            data.append(user_data)
        
        return Response({"success": True, "data": data})

    def post(self, request):
        phone = request.data.get('phone')
        user_type = request.data.get('user_type') or 'client'
        email = request.data.get('email', '')
        username = request.data.get('username') or phone
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        city = request.data.get('city', 'Libreville')
        is_verified = bool(request.data.get('is_verified', False))
        is_available = bool(request.data.get('is_available', True))
        raw_password = request.data.get('password')
        if not phone:
            return Response({"success": False, "message": "phone requis"}, status=status.HTTP_400_BAD_REQUEST)
        if user_type not in dict(User.USER_TYPE_CHOICES):
            return Response({"success": False, "message": "user_type invalide"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            is_staff = user_type == 'admin'
            user = User.objects.create_user(
                phone=phone,
                password=raw_password or phone,
                user_type=user_type,
                email=email,
                username=username,
                is_staff=is_staff,
                first_name=first_name,
                last_name=last_name,
                city=city,
                is_verified=is_verified,
                is_available=is_available,
            )
        except IntegrityError:
            return Response({"success": False, "message": "Téléphone déjà utilisé"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:  # pragma: no cover
            return Response({"success": False, "message": str(exc)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "success": True,
            "data": {
                "id": user.id,
                "phone": user.phone,
                "user_type": user.user_type,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "city": getattr(user, 'city', ''),
                "is_active": user.is_active,
                "is_staff": user.is_staff,
                "is_verified": getattr(user, 'is_verified', False),
                "is_available": getattr(user, 'is_available', False),
                "created_at": user.date_joined,
            }
        }, status=status.HTTP_201_CREATED)

    def patch(self, request):
        user_id = request.data.get('id')
        if not user_id:
            return Response({"success": False, "message": "id requis"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"success": False, "message": "Utilisateur introuvable"}, status=status.HTTP_404_NOT_FOUND)

        phone = request.data.get('phone')
        user_type = request.data.get('user_type')
        is_active = request.data.get('is_active')
        first_name = request.data.get('first_name')
        last_name = request.data.get('last_name')
        email = request.data.get('email')
        city = request.data.get('city')
        is_verified = request.data.get('is_verified')
        delivery_profile_data = request.data.get('delivery_profile')
        is_available = request.data.get('is_available')
        raw_password = request.data.get('password')

        if user_type and user_type not in dict(User.USER_TYPE_CHOICES):
            return Response({"success": False, "message": "user_type invalide"}, status=status.HTTP_400_BAD_REQUEST)

        if phone:
            user.phone = phone
        if user_type:
            user.user_type = user_type
            user.is_staff = user_type == 'admin'
        if is_active is not None:
            user.is_active = bool(is_active)
        if first_name is not None:
            user.first_name = first_name
        if last_name is not None:
            user.last_name = last_name
        if email is not None:
            user.email = email
        if city is not None:
            user.city = city
        if is_verified is not None:
            user.is_verified = bool(is_verified)
        if is_available is not None:
            user.is_available = bool(is_available)
        if raw_password:
            user.set_password(raw_password)

        try:
            user.save()
        except IntegrityError:
            return Response({"success": False, "message": "Téléphone déjà utilisé"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update delivery profile if data provided
        if delivery_profile_data and user.user_type == 'delivery_agent':
            from delivery.models import DeliveryProfile
            DeliveryProfile.objects.update_or_create(
                user=user,
                defaults={
                    'vehicle_type': delivery_profile_data.get('vehicle_type', ''),
                    'vehicle_plate': delivery_profile_data.get('vehicle_plate', ''),
                    'cin_number': delivery_profile_data.get('cin_number', ''),
                }
            )

        return Response({
            "success": True,
            "data": {
                "id": user.id,
                "phone": user.phone,
                "user_type": user.user_type,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "city": getattr(user, 'city', ''),
                "is_active": user.is_active,
                "is_staff": user.is_staff,
                "is_verified": getattr(user, 'is_verified', False),
                "is_available": getattr(user, 'is_available', False),
                "created_at": user.date_joined,
            }
        })

    def delete(self, request):
        user_id = request.data.get('id') or request.query_params.get('id')
        if not user_id:
            return Response({"success": False, "message": "id requis"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            return Response({"success": False, "message": "Utilisateur introuvable"}, status=status.HTTP_404_NOT_FOUND)

        user.delete()
        return Response({"success": True})


class AdminOrdersView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        status_filter = request.query_params.get('status')
        qs = Order.objects.select_related('store', 'client').order_by('-created_at')
        if status_filter:
            qs = qs.filter(status=status_filter)
        orders = []
        for o in qs[:200]:
            orders.append({
                "id": o.id,
                "order_number": o.order_number,
                "status": o.status,
                "total_amount": o.total_amount,
                "store": o.store.name,
                "client": o.client.phone,
                "created_at": o.created_at,
            })
        return Response({"success": True, "data": orders})


class AdminFinancialsView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        orders_qs = Order.objects.exclude(status__in=['cancelled', 'refunded'])
        payments_qs = Payment.objects.all()
        deliveries_qs = Delivery.objects.filter(status='delivered')

        data = {
            "revenue_total": orders_qs.aggregate(sum=Sum('total_amount'))['sum'] or 0,
            "commissions_total": orders_qs.aggregate(sum=Sum('commission_amount'))['sum'] or 0,
            "delivery_fees_total": orders_qs.aggregate(sum=Sum('delivery_fee'))['sum'] or 0,
            "agent_commissions_total": deliveries_qs.aggregate(sum=Sum('agent_commission'))['sum'] or 0,
            "payments": {
                "success": payments_qs.filter(status='success').count(),
                "failed": payments_qs.filter(status='failed').count(),
                "pending": payments_qs.filter(status='pending').count(),
            },
        }
        return Response({"success": True, "data": data})


class AdminStoreCategoriesView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        qs = StoreCategory.objects.all().order_by('name')
        data = [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description,
                "icon": c.icon,
                "is_active": c.is_active,
            }
            for c in qs
        ]
        return Response({"success": True, "data": data})

    def post(self, request):
        name = request.data.get('name')
        if not name:
            return Response({"success": False, "message": "Nom requis"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cat = StoreCategory.objects.create(
                name=name,
                description=request.data.get('description', ''),
                icon=request.data.get('icon', ''),
                is_active=request.data.get('is_active', True)
            )
        except IntegrityError:
            return Response({"success": False, "message": "Cette catégorie existe déjà"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "success": True,
            "data": {
                "id": cat.id,
                "name": cat.name,
                "description": cat.description,
                "icon": cat.icon,
                "is_active": cat.is_active,
            }
        }, status=status.HTTP_201_CREATED)

    def patch(self, request):
        cat_id = request.data.get('id')
        if not cat_id:
            return Response({"success": False, "message": "ID requis"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cat = StoreCategory.objects.get(id=cat_id)
        except StoreCategory.DoesNotExist:
            return Response({"success": False, "message": "Catégorie introuvable"}, status=status.HTTP_404_NOT_FOUND)

        if 'name' in request.data:
            cat.name = request.data['name']
        if 'description' in request.data:
            cat.description = request.data['description']
        if 'icon' in request.data:
            cat.icon = request.data['icon']
        if 'is_active' in request.data:
            cat.is_active = bool(request.data['is_active'])
        
        try:
            cat.save()
        except IntegrityError:
            return Response({"success": False, "message": "Nom déjà utilisé"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"success": True, "data": {
            "id": cat.id,
            "name": cat.name,
            "description": cat.description,
            "icon": cat.icon,
            "is_active": cat.is_active,
        }})

    def delete(self, request):
        cat_id = request.query_params.get('id') or request.data.get('id')
        if not cat_id:
            return Response({"success": False, "message": "ID requis"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cat = StoreCategory.objects.get(id=cat_id)
            cat.delete()
        except StoreCategory.DoesNotExist:
            return Response({"success": False, "message": "Catégorie introuvable"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({"success": True})


class AdminProductCategoriesView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        # List all product categories with store info
        search = request.query_params.get('search', '')
        store_id = request.query_params.get('store_id', '')
        
        qs = ProductCategory.objects.select_related('store', 'store_category').all()
        
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(description__icontains=search))
        if store_id:
            qs = qs.filter(store_id=store_id)
        
        qs = qs.order_by('store__name', 'order', 'name')[:300]  # Limit to avoid huge payload
        
        data = [
            {
                "id": c.id,
                "name": c.name,
                "description": c.description or '',
                "store_id": c.store.id if c.store else None,
                "store_name": c.store.name if c.store else (c.store_category.name if getattr(c, 'store_category', None) else ''),
                "order": c.order or 0,
            }
            for c in qs
        ]
        return Response({"success": True, "data": data})
    
    def post(self, request):
        """Create a new product category"""
        from products.models import ProductCategory
        from stores.models import Store
        
        name = request.data.get('name')
        if not name:
            return Response({"success": False, "error": "Nom requis"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            store_id = request.data.get('store_id')
            store = Store.objects.get(id=store_id) if store_id else None
            
            category = ProductCategory.objects.create(
                name=name,
                description=request.data.get('description', ''),
                store=store,
                order=request.data.get('order', 0)
            )
            
            return Response({
                "success": True,
                "data": {
                    "id": category.id,
                    "name": category.name,
                    "description": category.description or '',
                    "store_id": category.store.id if category.store else None,
                    "store_name": category.store.name if category.store else '',
                    "order": category.order or 0,
                }
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def patch(self, request):
        """Update a product category"""
        from products.models import ProductCategory
        
        category_id = request.data.get('id')
        if not category_id:
            return Response({"success": False, "error": "ID requis"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            category = ProductCategory.objects.get(id=category_id)
            
            if 'name' in request.data:
                category.name = request.data['name']
            if 'description' in request.data:
                category.description = request.data['description']
            if 'order' in request.data:
                category.order = request.data['order']
            if 'store_id' in request.data:
                from stores.models import Store
                store_id = request.data['store_id']
                category.store = Store.objects.get(id=store_id) if store_id else None
            
            category.save()
            
            return Response({
                "success": True,
                "data": {
                    "id": category.id,
                    "name": category.name,
                    "description": category.description or '',
                    "store_id": category.store.id if category.store else None,
                    "store_name": category.store.name if category.store else '',
                    "order": category.order or 0,
                }
            })
        except ProductCategory.DoesNotExist:
            return Response({"success": False, "error": "Catégorie introuvable"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request):
        """Delete a product category"""
        from products.models import ProductCategory
        
        category_id = request.query_params.get('id') or request.data.get('id')
        if not category_id:
            return Response({"success": False, "error": "ID requis"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            category = ProductCategory.objects.get(id=category_id)
            category.delete()
            return Response({"success": True})
        except ProductCategory.DoesNotExist:
            return Response({"success": False, "error": "Catégorie introuvable"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"success": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminStoresView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        qs = Store.objects.select_related('category', 'manager').all().order_by('name')
        data = [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "category_id": s.category.id,
                "category_name": s.category.name,
                "manager_id": s.manager.id,
                "manager_name": f"{s.manager.first_name} {s.manager.last_name}".strip() or s.manager.phone,
                "phone": s.phone,
                "email": s.email,
                "address": s.address,
                "city": s.city,
                "zone": s.zone,
                "is_active": s.is_active,
                "created_at": s.created_at,
            }
            for s in qs
        ]
        return Response({"success": True, "data": data})

    def post(self, request):
        # Strict validation
        name = request.data.get('name', '').strip()
        phone = request.data.get('phone', '').strip()
        address = request.data.get('address', '').strip()
        category_id = request.data.get('category_id')
        manager_id = request.data.get('manager_id')
        
        # Required fields validation
        if not name:
            return Response({"success": False, "message": "Le nom du magasin est requis"}, status=status.HTTP_400_BAD_REQUEST)
        if not phone:
            return Response({"success": False, "message": "Le numéro de téléphone est requis"}, status=status.HTTP_400_BAD_REQUEST)
        if not address:
            return Response({"success": False, "message": "L'adresse est requise"}, status=status.HTTP_400_BAD_REQUEST)
        if not category_id:
            return Response({"success": False, "message": "La catégorie est requise"}, status=status.HTTP_400_BAD_REQUEST)
        if not manager_id:
            return Response({"success": False, "message": "Le gérant est requis"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check uniqueness
        if Store.objects.filter(phone=phone).exists():
            return Response({"success": False, "message": f"Un magasin avec le numéro {phone} existe déjà"}, status=status.HTTP_400_BAD_REQUEST)
        if Store.objects.filter(name__iexact=name).exists():
            return Response({"success": False, "message": f"Un magasin nommé '{name}' existe déjà"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            category = StoreCategory.objects.get(id=category_id)
        except StoreCategory.DoesNotExist:
            return Response({"success": False, "message": "Catégorie invalide ou introuvable"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            manager = User.objects.get(id=manager_id)
            if manager.user_type != 'store_manager':
                return Response({"success": False, "message": "L'utilisateur sélectionné n'est pas un gérant de magasin"}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            return Response({"success": False, "message": "Gérant introuvable"}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if manager already manages another store
        if Store.objects.filter(manager=manager).exists():
            return Response({"success": False, "message": f"{manager.get_full_name() or manager.phone} gère déjà un autre magasin"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            store = Store.objects.create(
                name=name,
                description=request.data.get('description', ''),
                category=category,
                manager=manager,
                phone=phone,
                email=request.data.get('email', '').strip(),
                address=address,
                city=request.data.get('city', 'Libreville'),
                zone=request.data.get('zone', ''),
                commission_rate=request.data.get('commission_rate', 8.00),
                delivery_fee=request.data.get('delivery_fee', 2000.00),
            )
        except IntegrityError as e:
            return Response({"success": False, "message": f"Erreur d'intégrité: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"success": False, "message": f"Erreur inattendue: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"success": True, "data": {"id": store.id, "name": store.name}}, status=status.HTTP_201_CREATED)

    def patch(self, request):
        store_id = request.data.get('id')
        if not store_id:
            return Response({"success": False, "message": "ID requis"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            return Response({"success": False, "message": "Magasin introuvable"}, status=status.HTTP_404_NOT_FOUND)
        
        # Validate name uniqueness if changing
        if 'name' in request.data:
            new_name = request.data['name'].strip()
            if not new_name:
                return Response({"success": False, "message": "Le nom ne peut pas être vide"}, status=status.HTTP_400_BAD_REQUEST)
            if Store.objects.filter(name__iexact=new_name).exclude(id=store_id).exists():
                return Response({"success": False, "message": f"Un autre magasin nommé '{new_name}' existe déjà"}, status=status.HTTP_400_BAD_REQUEST)
            store.name = new_name
        
        # Validate phone uniqueness if changing
        if 'phone' in request.data:
            new_phone = request.data['phone'].strip()
            if not new_phone:
                return Response({"success": False, "message": "Le téléphone ne peut pas être vide"}, status=status.HTTP_400_BAD_REQUEST)
            if Store.objects.filter(phone=new_phone).exclude(id=store_id).exists():
                return Response({"success": False, "message": f"Un autre magasin avec le numéro {new_phone} existe déjà"}, status=status.HTTP_400_BAD_REQUEST)
            store.phone = new_phone

        if 'description' in request.data:
            store.description = request.data['description']
        if 'email' in request.data:
            store.email = request.data['email'].strip()
        if 'address' in request.data:
            store.address = request.data['address'].strip()
        if 'city' in request.data:
            store.city = request.data['city']
        if 'zone' in request.data:
            store.zone = request.data['zone']
        if 'is_active' in request.data:
            store.is_active = bool(request.data['is_active'])
        
        if 'category_id' in request.data:
            try:
                store.category = StoreCategory.objects.get(id=request.data['category_id'])
            except StoreCategory.DoesNotExist:
                return Response({"success": False, "message": "Catégorie invalide"}, status=status.HTTP_400_BAD_REQUEST)
        
        if 'manager_id' in request.data:
            try:
                manager = User.objects.get(id=request.data['manager_id'])
                if manager.user_type != 'store_manager':
                    return Response({"success": False, "message": "L'utilisateur sélectionné n'est pas un gérant"}, status=status.HTTP_400_BAD_REQUEST)
                # Check if manager already manages another store
                if Store.objects.filter(manager=manager).exclude(id=store_id).exists():
                    return Response({"success": False, "message": f"{manager.get_full_name() or manager.phone} gère déjà un autre magasin"}, status=status.HTTP_400_BAD_REQUEST)
                store.manager = manager
            except User.DoesNotExist:
                return Response({"success": False, "message": "Gérant introuvable"}, status=status.HTTP_404_NOT_FOUND)

        try:
            store.save()
        except IntegrityError as e:
            return Response({"success": False, "message": f"Erreur d'intégrité: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"success": False, "message": f"Erreur inattendue: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"success": True})

    def delete(self, request):
        store_id = request.query_params.get('id') or request.data.get('id')
        if not store_id:
            return Response({"success": False, "message": "ID requis"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            Store.objects.get(id=store_id).delete()
        except Store.DoesNotExist:
            return Response({"success": False, "message": "Magasin introuvable"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"success": True})


class AdminProductsView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        qs = Product.objects.select_related('store', 'category').all().order_by('store__name', 'name')
        data = [
            {
                "id": p.id,
                "name": p.name,
                "description": p.description,
                "price": p.price,
                "stock": p.stock,
                "is_available": p.is_available,
                "store_id": p.store.id,
                "store_name": p.store.name,
                "category_id": p.category.id if p.category else None,
                "category_name": p.category.name if p.category else "",
            }
            for p in qs[:500]
        ]
        return Response({"success": True, "data": data})

    def post(self, request):
        try:
            store = Store.objects.get(id=request.data.get('store_id'))
        except Store.DoesNotExist:
            return Response({"success": False, "message": "Magasin invalide"}, status=status.HTTP_400_BAD_REQUEST)
        
        category = None
        if request.data.get('category_id'):
            try:
                category = ProductCategory.objects.get(id=request.data.get('category_id'))
            except ProductCategory.DoesNotExist:
                pass

        try:
            product = Product.objects.create(
                store=store,
                category=category,
                name=request.data.get('name'),
                description=request.data.get('description', ''),
                price=request.data.get('price', 0),
                stock=request.data.get('stock', 0),
                is_available=request.data.get('is_available', True)
            )
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"success": True, "data": {"id": product.id}}, status=status.HTTP_201_CREATED)

    def patch(self, request):
        prod_id = request.data.get('id')
        if not prod_id:
            return Response({"success": False, "message": "ID requis"}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            product = Product.objects.get(id=prod_id)
        except Product.DoesNotExist:
            return Response({"success": False, "message": "Produit introuvable"}, status=status.HTTP_404_NOT_FOUND)

        if 'name' in request.data: product.name = request.data['name']
        if 'description' in request.data: product.description = request.data['description']
        if 'price' in request.data: product.price = request.data['price']
        if 'stock' in request.data: product.stock = request.data['stock']
        if 'is_available' in request.data: product.is_available = bool(request.data['is_available'])
        
        if 'category_id' in request.data:
            if request.data['category_id']:
                try:
                    product.category = ProductCategory.objects.get(id=request.data['category_id'])
                except ProductCategory.DoesNotExist:
                    pass
            else:
                product.category = None

        product.save()
        return Response({"success": True})

    def delete(self, request):
        prod_id = request.query_params.get('id') or request.data.get('id')
        if not prod_id:
            return Response({"success": False, "message": "ID requis"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            Product.objects.get(id=prod_id).delete()
        except Product.DoesNotExist:
            return Response({"success": False, "message": "Produit introuvable"}, status=status.HTTP_404_NOT_FOUND)
        return Response({"success": True})


class AdminPaymentsView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        qs = Payment.objects.select_related('order').all().order_by('-created_at')
        data = [
            {
                "id": p.id,
                "order_number": p.order.order_number,
                "payment_method": p.get_payment_method_display(),
                "status": p.get_status_display(),
                "amount": p.amount,
                "fees_amount": p.fees_amount,
                "client_phone": p.client_phone,
                "transaction_id": p.transaction_id,
                "created_at": p.created_at,
            }
            for p in qs[:100]
        ]
        return Response({"success": True, "data": data})


class AdminDeliveriesView(APIView):
    permission_classes = [IsPlatformAdmin]

    def get(self, request):
        qs = Delivery.objects.select_related('order', 'delivery_agent').all().order_by('-order__created_at')
        data = [
            {
                "id": d.id,
                "order_number": d.order.order_number,
                "agent_name": d.delivery_agent.username if d.delivery_agent else "Non assigné",
                "status": d.get_status_display(),
                "tracking_number": d.tracking_number,
                "pickup_address": d.pickup_address,
                "city": d.city,
                "distance_km": d.distance_to_store,
            }
            for d in qs[:100]
        ]
        return Response({"success": True, "data": data})


class SystemSettingsView(APIView):
    """
    API pour récupérer et mettre à jour les paramètres système.
    GET: Retourne tous les paramètres système actifs.
    PATCH: Met à jour les paramètres système (admin uniquement).
    """
    
    def get_permissions(self):
        if self.request.method == 'PATCH':
            return [IsPlatformAdmin()]
        return [permissions.AllowAny()]
    
    def get(self, request):
        settings = SystemSettings.get_settings()
        
        data = {
            # Commissions
            "commission_global": float(settings.commission_global),
            "commission_event": float(settings.commission_event),
            
            # Paiements
            "moov_money_fee": float(settings.moov_money_fee),
            "airtel_money_fee": float(settings.airtel_money_fee),
            "payment_before_order": settings.payment_before_order,
            "unpaid_order_expiry_minutes": settings.unpaid_order_expiry_minutes,
            
            # Villes & Géolocalisation
            "auto_detect_cities": settings.auto_detect_cities,
            "default_city": settings.default_city,
            "enabled_cities": settings.get_enabled_cities_list(),
            "max_delivery_distance_km": float(settings.max_delivery_distance_km),
            
            # Livraison
            "price_per_km": float(settings.price_per_km),
            "auto_assign_delivery": settings.auto_assign_delivery,
            "max_orders_per_delivery": settings.max_orders_per_delivery,
            
            # Commandes
            "cart_validity_hours": settings.cart_validity_hours,
            "order_opening_time": settings.order_opening_time.strftime('%H:%M:%S'),
            "order_closing_time": settings.order_closing_time.strftime('%H:%M:%S'),
            
            # Magasins
            "default_store_opening": settings.default_store_opening.strftime('%H:%M:%S'),
            "default_store_closing": settings.default_store_closing.strftime('%H:%M:%S'),
            "store_verification_required": settings.store_verification_required,
            "pro_mode_monthly_fee": float(settings.pro_mode_monthly_fee),
            
            # Notifications
            "enable_sms": settings.enable_sms,
            "enable_email": settings.enable_email,
        }
        
        return Response({"success": True, "data": data})
    
    def patch(self, request):
        """Mettre à jour les paramètres système"""
        settings = SystemSettings.get_settings()
        
        # Mise à jour des champs fournis
        if 'commission_global' in request.data:
            settings.commission_global = request.data['commission_global']
        if 'commission_event' in request.data:
            settings.commission_event = request.data['commission_event']
        
        if 'moov_money_fee' in request.data:
            settings.moov_money_fee = request.data['moov_money_fee']
        if 'airtel_money_fee' in request.data:
            settings.airtel_money_fee = request.data['airtel_money_fee']
        if 'payment_before_order' in request.data:
            settings.payment_before_order = request.data['payment_before_order']
        if 'unpaid_order_expiry_minutes' in request.data:
            settings.unpaid_order_expiry_minutes = request.data['unpaid_order_expiry_minutes']
        
        if 'auto_detect_cities' in request.data:
            settings.auto_detect_cities = request.data['auto_detect_cities']
        if 'default_city' in request.data:
            settings.default_city = request.data['default_city']
        if 'enabled_cities' in request.data:
            # Gérer à la fois string et array
            cities = request.data['enabled_cities']
            if isinstance(cities, str):
                settings.enabled_cities = cities
            elif isinstance(cities, list):
                settings.enabled_cities = ','.join(cities)
        if 'max_delivery_distance_km' in request.data:
            settings.max_delivery_distance_km = request.data['max_delivery_distance_km']
        
        if 'price_per_km' in request.data:
            settings.price_per_km = request.data['price_per_km']
        if 'auto_assign_delivery' in request.data:
            settings.auto_assign_delivery = request.data['auto_assign_delivery']
        if 'max_orders_per_delivery' in request.data:
            settings.max_orders_per_delivery = request.data['max_orders_per_delivery']
        
        if 'cart_validity_hours' in request.data:
            settings.cart_validity_hours = request.data['cart_validity_hours']
        if 'order_opening_time' in request.data:
            settings.order_opening_time = request.data['order_opening_time']
        if 'order_closing_time' in request.data:
            settings.order_closing_time = request.data['order_closing_time']
        
        if 'default_store_opening' in request.data:
            settings.default_store_opening = request.data['default_store_opening']
        if 'default_store_closing' in request.data:
            settings.default_store_closing = request.data['default_store_closing']
        if 'store_verification_required' in request.data:
            settings.store_verification_required = request.data['store_verification_required']
        if 'pro_mode_monthly_fee' in request.data:
            settings.pro_mode_monthly_fee = request.data['pro_mode_monthly_fee']
        
        if 'enable_sms' in request.data:
            settings.enable_sms = request.data['enable_sms']
        if 'enable_email' in request.data:
            settings.enable_email = request.data['enable_email']
        
        settings.save()
        
        # Retourner les données mises à jour
        return self.get(request)

