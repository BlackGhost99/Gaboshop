"""Finance & Revenue API views for platform analytics and reporting."""

from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from payments.models import (
    Payment, Commission, DeliveryPayout, StoreSubscription, SponsoredProduct,
    Reversement, CategoryCommission, CategoryCommissionChangeLog,
    ClientCredit, Forfait, ClientForfait
)
from orders.models import Order
from stores.models import Store
from products.models import Product
from users.models import User
from payments.serializers_category_commission import CategoryCommissionSerializer
from rest_framework import generics, permissions as rf_permissions, serializers
from django.db.models import Q, Sum, Count
from decimal import Decimal


class IsPlatformAdmin(permissions.BasePermission):
	def has_permission(self, request, view):
		user = request.user
		return bool(user and user.is_authenticated and (user.is_staff or user.user_type == 'admin'))


class FinanceDashboardView(APIView):
	"""Dashboard financier avec KPIs"""
	permission_classes = [IsPlatformAdmin]

	def get(self, request):
		today = timezone.now().date()
		month_start = today.replace(day=1)

		# Statistiques d'aujourd'hui
		today_payments = Payment.objects.filter(
			status='success',
			completed_at__date=today
		).aggregate(total=Sum('amount'))['total'] or 0

		today_commissions = Commission.objects.filter(
			created_at__date=today
		).aggregate(total=Sum('commission_amount'))['total'] or 0

		# Statistiques du mois
		month_payments = Payment.objects.filter(
			status='success',
			completed_at__date__gte=month_start
		).aggregate(total=Sum('amount'))['total'] or 0

		month_orders = Order.objects.filter(
			created_at__date__gte=month_start
		).count()

		month_commissions = Commission.objects.filter(
			created_at__date__gte=month_start
		).aggregate(total=Sum('commission_amount'))['total'] or 0

		# Paiements livreurs
		month_delivery_payouts = DeliveryPayout.objects.filter(
			created_at__date__gte=month_start,
			status='completed'
		).aggregate(total=Sum('calculated_payout'))['total'] or 0

		# Abonnements actifs
		active_subscriptions = StoreSubscription.objects.filter(
			status='active',
			end_date__gte=today
		).aggregate(total=Sum('monthly_fee'))['total'] or 0

		# Revenus sponsoring
		sponsoring_revenue = SponsoredProduct.objects.filter(
			status='active',
			end_date__gte=timezone.now()
		).aggregate(total=Sum('price_paid'))['total'] or 0

		# Calcul du bénéfice réel
		month_platform_profit = (
			month_commissions +
			active_subscriptions +
			sponsoring_revenue -
			month_delivery_payouts
		)

		data = {
			"today": {
				"revenue": float(today_payments),
				"commissions": float(today_commissions),
				"orders_count": Order.objects.filter(created_at__date=today).count(),
			},
			"month": {
				"revenue": float(month_payments),
				"orders_count": month_orders,
				"commissions": float(month_commissions),
				"delivery_payouts": float(month_delivery_payouts),
				"subscriptions_revenue": float(active_subscriptions),
				"sponsoring_revenue": float(sponsoring_revenue),
				"platform_profit": float(month_platform_profit),
			},
			"metrics": {
				"paid_orders": Payment.objects.filter(status='success').count(),
				"pending_payments": Payment.objects.filter(status='pending').count(),
				"failed_payments": Payment.objects.filter(status='failed').count(),
			}
		}

		return Response({"success": True, "data": data})


class TransactionsListView(APIView):
	"""Liste des transactions clients"""
	permission_classes = [IsPlatformAdmin]

	def get(self, request):
		payments = Payment.objects.select_related('order').all()[:100]

		data = [
			{
				"id": p.id,
				"date": p.created_at.isoformat(),
				"transaction_id": p.transaction_id,
				"order_number": p.order.order_number if p.order else "N/A",
				"client_name": p.client_name,
				"client_phone": p.client_phone,
				"amount": float(p.amount),
				"method": p.get_payment_method_display(),
				"status": p.get_status_display(),
				"proof": p.operator_reference or "Paiement manuel confirmé",
			}
			for p in payments
		]

		return Response({"success": True, "data": data})


class CommissionsByStoreView(APIView):
	"""Commissions par magasin"""
	permission_classes = [IsPlatformAdmin]

	def get(self, request):
		stores = Store.objects.all()

		data = []
		for store in stores:
			commissions = Commission.objects.filter(store=store).aggregate(
				total_sales=Sum('order_amount'),
				total_commission=Sum('commission_amount')
			)

			data.append({
				"store_id": store.id,
				"store_name": store.name,
				"total_sales": float(commissions['total_sales'] or 0),
				"commission_rate": 5.0,  # À mettre à jour depuis SystemSettings
				"commission_amount": float(commissions['total_commission'] or 0),
				"status": "pending",
			})

		return Response({"success": True, "data": data})


class DeliveryPayoutView(APIView):
	"""Coûts de livraison et paiements livreurs"""
	permission_classes = [IsPlatformAdmin]

	def get(self, request):
		payouts = DeliveryPayout.objects.select_related('delivery_agent', 'order').all()[:100]

		data = [
			{
				"id": p.id,
				"order_number": p.order.order_number,
				"livreur_name": p.delivery_agent.username,
				"distance_km": float(p.distance_km),
				"fee_from_client": float(p.delivery_fee_from_client),
				"livreur_salary": float(p.calculated_payout),
				"platform_profit": float(p.platform_profit),
				"status": p.get_status_display(),
			}
			for p in payouts
		]

		return Response({"success": True, "data": data})


class SubscriptionsView(APIView):
	"""Abonnements Mode Pro des magasins"""
	permission_classes = [IsPlatformAdmin]

	def get(self, request):
		subscriptions = StoreSubscription.objects.select_related('store').all()

		data = [
			{
				"id": s.id,
				"store_name": s.store.name,
				"plan": s.plan_name,
				"price": float(s.monthly_fee),
				"start_date": s.start_date.isoformat(),
				"end_date": s.end_date.isoformat(),
				"status": s.get_status_display(),
				"auto_renew": s.auto_renew,
			}
			for s in subscriptions
		]

		return Response({"success": True, "data": data})


class IsStaffOrStoreManager(rf_permissions.BasePermission):
	"""Allow access to staff/admin or store managers (read-only for others)."""

	def has_permission(self, request, view):
		user = request.user
		return bool(
			user
			and user.is_authenticated
			and (user.is_staff or user.user_type == 'admin' or user.user_type == 'store_manager')
		)


class CategoryCommissionListCreateView(generics.ListCreateAPIView):
	"""List all category commissions or create/update (staff only)."""
	queryset = CategoryCommission.objects.select_related('store_category').all()
	serializer_class = CategoryCommissionSerializer
	permission_classes = [IsStaffOrStoreManager]

	def get_queryset(self):
		user = self.request.user
		if user and (user.is_staff or user.user_type == 'admin'):
			return super().get_queryset()
		# store managers: only show commissions for their store category
		try:
			store = getattr(user, 'store', None)
			if store and store.category:
				return CategoryCommission.objects.filter(store_category=store.category)
		except Exception:
			pass
		return CategoryCommission.objects.none()

	def perform_create(self, serializer):
		instance = serializer.save()
		# Create audit entry
		try:
			from payments.models import CategoryCommissionChangeLog
			user = getattr(self.request, 'user', None)
			CategoryCommissionChangeLog.objects.create(
				category_commission=instance,
				old_rate=None,
				new_rate=instance.base_rate,
				changed_by=user if getattr(user, 'is_authenticated', False) else None,
				note='Created via API',
			)
		except Exception:
			pass


class CategoryCommissionDetailView(generics.RetrieveUpdateAPIView):
	queryset = CategoryCommission.objects.select_related('store_category').all()
	serializer_class = CategoryCommissionSerializer
	permission_classes = [IsStaffOrStoreManager]

	def perform_update(self, serializer):
		# capture old value
		instance = self.get_object()
		old_rate = instance.base_rate
		updated = serializer.save()
		new_rate = updated.base_rate
		if old_rate != new_rate:
			try:
				from payments.models import CategoryCommissionChangeLog
				user = getattr(self.request, 'user', None)
				CategoryCommissionChangeLog.objects.create(
					category_commission=updated,
					old_rate=old_rate,
					new_rate=new_rate,
					changed_by=user if getattr(user, 'is_authenticated', False) else None,
					note='Updated via API',
				)
			except Exception:
				pass


class SponsoredProductsView(APIView):
	"""Produits sponsorisés / mises en avant payantes"""
	permission_classes = [IsPlatformAdmin]

	def get(self, request):
		sponsored = SponsoredProduct.objects.select_related('product', 'store').all()

		data = [
			{
				"id": s.id,
				"store_name": s.store.name,
				"product_name": s.product.name,
				"duration": f"{(s.end_date - s.start_date).days} jours",
				"price_paid": float(s.price_paid),
				"status": s.get_status_display(),
				"impressions": s.impressions,
				"clicks": s.clicks,
				"ctr": f"{(s.clicks / max(s.impressions, 1) * 100):.2f}%",
			}
			for s in sponsored
		]

		return Response({"success": True, "data": data})


class RevenueBreakdownView(APIView):
	"""Répartition des revenus par catégorie"""
	permission_classes = [IsPlatformAdmin]

	def get(self, request):
		today = timezone.now().date()
		month_start = today.replace(day=1)

		# Commissions
		commissions_revenue = Commission.objects.filter(
			created_at__date__gte=month_start
		).aggregate(total=Sum('commission_amount'))['total'] or 0

		# Livraison
		delivery_revenue = DeliveryPayout.objects.filter(
			created_at__date__gte=month_start
		).aggregate(total=Sum('platform_profit'))['total'] or 0

		# Abonnements
		subscriptions_revenue = StoreSubscription.objects.filter(
			start_date__gte=month_start
		).aggregate(total=Sum('monthly_fee'))['total'] or 0

		# Sponsoring
		sponsoring_revenue = SponsoredProduct.objects.filter(
			start_date__gte=timezone.now() - timedelta(days=30)
		).aggregate(total=Sum('price_paid'))['total'] or 0

		# Frais de service
		service_fees = Payment.objects.filter(
			status='success',
			created_at__date__gte=month_start
		).aggregate(total=Sum('fees_amount'))['total'] or 0

		total_revenue = (
			float(commissions_revenue) +
			float(delivery_revenue) +
			float(subscriptions_revenue) +
			float(sponsoring_revenue) +
			float(service_fees)
		)

		data = {
			"commissions": {
				"amount": float(commissions_revenue),
				"percentage": (float(commissions_revenue) / max(total_revenue, 1)) * 100,
			},
			"delivery": {
				"amount": float(delivery_revenue),
				"percentage": (float(delivery_revenue) / max(total_revenue, 1)) * 100,
			},
			"subscriptions": {
				"amount": float(subscriptions_revenue),
				"percentage": (float(subscriptions_revenue) / max(total_revenue, 1)) * 100,
			},
			"sponsoring": {
				"amount": float(sponsoring_revenue),
				"percentage": (float(sponsoring_revenue) / max(total_revenue, 1)) * 100,
			},
			"service_fees": {
				"amount": float(service_fees),
				"percentage": (float(service_fees) / max(total_revenue, 1)) * 100,
			},
			"total_revenue": total_revenue,
		}

		return Response({"success": True, "data": data})


# ============================================================================
# SERIALIZERS
# ============================================================================

class ReversementSerializer(serializers.ModelSerializer):
    """Serializer for Reversement"""
    store_name = serializers.CharField(source='store.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Reversement
        fields = '__all__'
        read_only_fields = ('created_at', 'processed_at', 'completed_at')


class CommissionDetailSerializer(serializers.ModelSerializer):
    """Serializer détaillé pour Commission"""
    store_name = serializers.CharField(source='store.name', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    is_settled_display = serializers.SerializerMethodField()
    
    class Meta:
        model = Commission
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
    
    def get_is_settled_display(self, obj):
        return 'Réglé' if obj.is_settled else 'En attente'


class CategoryCommissionChangeLogSerializer(serializers.ModelSerializer):
    """Serializer pour CategoryCommissionChangeLog (read-only)"""
    category_name = serializers.CharField(source='category_commission.store_category.name', read_only=True)
    changed_by_name = serializers.SerializerMethodField()
    
    class Meta:
        model = CategoryCommissionChangeLog
        fields = '__all__'
        read_only_fields = '__all__'
    
    def get_changed_by_name(self, obj):
        if obj.changed_by:
            return obj.changed_by.get_full_name() or obj.changed_by.username
        return 'Système'


class DeliveryPayoutSerializer(serializers.ModelSerializer):
    """Serializer pour DeliveryPayout"""
    delivery_agent_name = serializers.CharField(source='delivery_agent.get_full_name', read_only=True)
    order_number = serializers.CharField(source='order.order_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = DeliveryPayout
        fields = '__all__'
        read_only_fields = ('created_at', 'paid_at')


class SponsoredProductSerializer(serializers.ModelSerializer):
    """Serializer pour SponsoredProduct"""
    store_name = serializers.CharField(source='store.name', read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = SponsoredProduct
        fields = '__all__'
        read_only_fields = ('created_at', 'impressions', 'clicks')


class ClientCreditSerializer(serializers.ModelSerializer):
    """Serializer pour ClientCredit"""
    client_name = serializers.CharField(source='client.get_full_name', read_only=True)
    client_phone = serializers.CharField(source='client.phone', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ClientCredit
        fields = '__all__'
        read_only_fields = ('created_at', 'used_at')


class ForfaitSerializer(serializers.ModelSerializer):
    """Serializer pour Forfait"""
    class Meta:
        model = Forfait
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class ClientForfaitSerializer(serializers.ModelSerializer):
    """Serializer pour ClientForfait"""
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_phone = serializers.CharField(source='user.phone', read_only=True)
    forfait_name = serializers.CharField(source='forfait.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_active_display = serializers.SerializerMethodField()
    
    class Meta:
        model = ClientForfait
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at', 'start_date')
    
    def get_is_active_display(self, obj):
        return obj.is_active()


# ============================================================================
# REVERSEMENT ENDPOINTS
# ============================================================================

class ReversementListView(APIView):
    """GET /admin/finance/reversements/ - Liste des reversements"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request):
        from django.db.models import Q
        store_id = request.query_params.get('store_id')
        status_filter = request.query_params.get('status')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        reversements = Reversement.objects.select_related('store').all()
        
        if store_id:
            reversements = reversements.filter(store_id=store_id)
        if status_filter:
            reversements = reversements.filter(status=status_filter)
        if date_from:
            reversements = reversements.filter(period_start__gte=date_from)
        if date_to:
            reversements = reversements.filter(period_end__lte=date_to)
        
        reversements = reversements.order_by('-period_end')
        serializer = ReversementSerializer(reversements, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': reversements.count()
        })


class ReversementCreateView(APIView):
    """POST /admin/finance/reversements/ - Créer un reversement"""
    permission_classes = [IsPlatformAdmin]
    
    def post(self, request):
        from decimal import Decimal
        store_id = request.data.get('store_id')
        period_start = request.data.get('period_start')
        period_end = request.data.get('period_end')
        
        if not store_id or not period_start or not period_end:
            return Response({
                'success': False,
                'error': 'store_id, period_start et period_end requis'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            store = Store.objects.get(id=store_id)
        except Store.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Magasin introuvable'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Calculer les totaux pour la période
        orders = Order.objects.filter(
            store=store,
            status='delivered',
            delivered_at__date__gte=period_start,
            delivered_at__date__lte=period_end
        )
        
        total_orders = orders.count()
        total_sales = orders.aggregate(total=Sum('items_total'))['total'] or Decimal('0')
        total_commissions = orders.aggregate(total=Sum('commission_amount'))['total'] or Decimal('0')
        net_amount = total_sales - total_commissions
        
        reversement_data = {
            'store': store.id,
            'period_start': period_start,
            'period_end': period_end,
            'total_orders': total_orders,
            'total_sales': total_sales,
            'total_commissions': total_commissions,
            'net_amount': net_amount,
            'status': 'pending'
        }
        
        serializer = ReversementSerializer(data=reversement_data)
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


class ReversementUpdateView(APIView):
    """PATCH /admin/finance/reversements/<id>/ - Modifier le statut d'un reversement"""
    permission_classes = [IsPlatformAdmin]
    
    def patch(self, request, reversement_id):
        try:
            reversement = Reversement.objects.get(id=reversement_id)
            new_status = request.data.get('status')
            transaction_reference = request.data.get('transaction_reference')
            
            if new_status:
                valid_statuses = ['pending', 'processing', 'completed', 'failed']
                if new_status not in valid_statuses:
                    return Response({
                        'success': False,
                        'error': f'Statut invalide. Statuts valides: {", ".join(valid_statuses)}'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                reversement.status = new_status
                if new_status == 'processing' and not reversement.processed_at:
                    reversement.processed_at = timezone.now()
                elif new_status == 'completed' and not reversement.completed_at:
                    reversement.completed_at = timezone.now()
            
            if transaction_reference:
                reversement.transaction_reference = transaction_reference
            
            reversement.save()
            serializer = ReversementSerializer(reversement)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except Reversement.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Reversement introuvable'
            }, status=status.HTTP_404_NOT_FOUND)


# ============================================================================
# COMMISSION DETAILED ENDPOINTS
# ============================================================================

class CommissionListView(APIView):
    """GET /admin/finance/commissions/ - Liste des commissions détaillée"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request):
        from django.db.models import Q
        store_id = request.query_params.get('store_id')
        is_settled = request.query_params.get('is_settled')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        commissions = Commission.objects.select_related('store', 'order').all()
        
        if store_id:
            commissions = commissions.filter(store_id=store_id)
        if is_settled is not None:
            commissions = commissions.filter(is_settled=is_settled.lower() == 'true')
        if date_from:
            commissions = commissions.filter(created_at__gte=date_from)
        if date_to:
            commissions = commissions.filter(created_at__lte=date_to)
        
        commissions = commissions.order_by('-created_at')
        serializer = CommissionDetailSerializer(commissions, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': commissions.count()
        })


class CommissionSettleView(APIView):
    """PATCH /admin/finance/commissions/<id>/settle/ - Marquer commission comme réglée"""
    permission_classes = [IsPlatformAdmin]
    
    def patch(self, request, commission_id):
        try:
            commission = Commission.objects.get(id=commission_id)
            commission.is_settled = True
            commission.save()
            serializer = CommissionDetailSerializer(commission)
            return Response({
                'success': True,
                'data': serializer.data,
                'message': 'Commission marquée comme réglée'
            })
        except Commission.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Commission introuvable'
            }, status=status.HTTP_404_NOT_FOUND)


# ============================================================================
# CATEGORY COMMISSION CHANGE LOG ENDPOINTS
# ============================================================================

class CategoryCommissionChangeLogListView(APIView):
    """GET /admin/finance/category-commission-logs/ - Historique des changements"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request):
        category_id = request.query_params.get('category_id')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        logs = CategoryCommissionChangeLog.objects.select_related(
            'category_commission__store_category', 'changed_by'
        ).all()
        
        if category_id:
            logs = logs.filter(category_commission__store_category_id=category_id)
        if date_from:
            logs = logs.filter(created_at__gte=date_from)
        if date_to:
            logs = logs.filter(created_at__lte=date_to)
        
        logs = logs.order_by('-created_at')
        serializer = CategoryCommissionChangeLogSerializer(logs, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': logs.count()
        })


# ============================================================================
# DELIVERY PAYOUT MANAGEMENT ENDPOINTS
# ============================================================================

class DeliveryPayoutUpdateView(APIView):
    """PATCH /admin/finance/delivery-payouts/<id>/ - Modifier le statut d'un payout"""
    permission_classes = [IsPlatformAdmin]
    
    def patch(self, request, payout_id):
        try:
            payout = DeliveryPayout.objects.get(id=payout_id)
            new_status = request.data.get('status')
            
            if new_status:
                valid_statuses = ['pending', 'processing', 'completed', 'failed']
                if new_status not in valid_statuses:
                    return Response({
                        'success': False,
                        'error': f'Statut invalide. Statuts valides: {", ".join(valid_statuses)}'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                payout.status = new_status
                if new_status == 'completed' and not payout.paid_at:
                    payout.paid_at = timezone.now()
                payout.save()
            
            serializer = DeliveryPayoutSerializer(payout)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except DeliveryPayout.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Payout introuvable'
            }, status=status.HTTP_404_NOT_FOUND)


# ============================================================================
# SPONSORED PRODUCT CRUD ENDPOINTS
# ============================================================================

class SponsoredProductCreateView(APIView):
    """POST /admin/finance/sponsored-products/ - Créer un sponsoring"""
    permission_classes = [IsPlatformAdmin]
    
    def post(self, request):
        serializer = SponsoredProductSerializer(data=request.data)
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


class SponsoredProductUpdateView(APIView):
    """PATCH /admin/finance/sponsored-products/<id>/ - Modifier un sponsoring"""
    permission_classes = [IsPlatformAdmin]
    
    def patch(self, request, sponsored_id):
        try:
            sponsored = SponsoredProduct.objects.get(id=sponsored_id)
            serializer = SponsoredProductSerializer(sponsored, data=request.data, partial=True)
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
        except SponsoredProduct.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Sponsoring introuvable'
            }, status=status.HTTP_404_NOT_FOUND)


# ============================================================================
# CLIENT CREDIT CRUD ENDPOINTS
# ============================================================================

class ClientCreditListView(APIView):
    """GET /admin/finance/client-credits/ - Liste des crédits clients"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request):
        from django.db.models import Q
        client_id = request.query_params.get('client_id')
        status_filter = request.query_params.get('status')
        credit_type = request.query_params.get('credit_type')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        
        credits = ClientCredit.objects.select_related('client').all()
        
        if client_id:
            credits = credits.filter(client_id=client_id)
        if status_filter:
            credits = credits.filter(status=status_filter)
        if credit_type:
            credits = credits.filter(credit_type=credit_type)
        if date_from:
            credits = credits.filter(created_at__gte=date_from)
        if date_to:
            credits = credits.filter(created_at__lte=date_to)
        
        credits = credits.order_by('-created_at')
        serializer = ClientCreditSerializer(credits, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': credits.count()
        })


class ClientCreditCreateView(APIView):
    """POST /admin/finance/client-credits/ - Créer un crédit client"""
    permission_classes = [IsPlatformAdmin]
    
    def post(self, request):
        serializer = ClientCreditSerializer(data=request.data)
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


class ClientCreditUpdateView(APIView):
    """PATCH /admin/finance/client-credits/<id>/ - Modifier un crédit"""
    permission_classes = [IsPlatformAdmin]
    
    def patch(self, request, credit_id):
        try:
            credit = ClientCredit.objects.get(id=credit_id)
            # Ne pas permettre de modifier le montant si déjà utilisé
            if credit.status == 'used' and 'amount' in request.data:
                return Response({
                    'success': False,
                    'error': 'Impossible de modifier le montant d\'un crédit déjà utilisé'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            serializer = ClientCreditSerializer(credit, data=request.data, partial=True)
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
        except ClientCredit.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Crédit introuvable'
            }, status=status.HTTP_404_NOT_FOUND)


# ============================================================================
# FORFAIT CRUD ENDPOINTS
# ============================================================================

class ForfaitListView(APIView):
    """GET /admin/finance/forfaits/ - Liste des forfaits"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request):
        is_active = request.query_params.get('is_active')
        forfaits = Forfait.objects.all()
        
        if is_active is not None:
            forfaits = forfaits.filter(is_active=is_active.lower() == 'true')
        
        forfaits = forfaits.order_by('monthly_price')
        serializer = ForfaitSerializer(forfaits, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': forfaits.count()
        })


class ForfaitCreateView(APIView):
    """POST /admin/finance/forfaits/ - Créer un forfait"""
    permission_classes = [IsPlatformAdmin]
    
    def post(self, request):
        serializer = ForfaitSerializer(data=request.data)
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


class ForfaitUpdateView(APIView):
    """PATCH /admin/finance/forfaits/<id>/ - Modifier un forfait"""
    permission_classes = [IsPlatformAdmin]
    
    def patch(self, request, forfait_id):
        try:
            forfait = Forfait.objects.get(id=forfait_id)
            serializer = ForfaitSerializer(forfait, data=request.data, partial=True)
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
        except Forfait.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Forfait introuvable'
            }, status=status.HTTP_404_NOT_FOUND)


# ============================================================================
# CLIENT FORFAIT CRUD ENDPOINTS
# ============================================================================

class ClientForfaitListView(APIView):
    """GET /admin/finance/client-forfaits/ - Liste des abonnements clients"""
    permission_classes = [IsPlatformAdmin]
    
    def get(self, request):
        user_id = request.query_params.get('user_id')
        forfait_id = request.query_params.get('forfait_id')
        status_filter = request.query_params.get('status')
        
        client_forfaits = ClientForfait.objects.select_related('user', 'forfait').all()
        
        if user_id:
            client_forfaits = client_forfaits.filter(user_id=user_id)
        if forfait_id:
            client_forfaits = client_forfaits.filter(forfait_id=forfait_id)
        if status_filter:
            client_forfaits = client_forfaits.filter(status=status_filter)
        
        client_forfaits = client_forfaits.order_by('-expiration_date')
        serializer = ClientForfaitSerializer(client_forfaits, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': client_forfaits.count()
        })


class ClientForfaitCreateView(APIView):
    """POST /admin/finance/client-forfaits/ - Créer un abonnement client"""
    permission_classes = [IsPlatformAdmin]
    
    def post(self, request):
        serializer = ClientForfaitSerializer(data=request.data)
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


class ClientForfaitUpdateView(APIView):
    """PATCH /admin/finance/client-forfaits/<id>/ - Modifier un abonnement client"""
    permission_classes = [IsPlatformAdmin]
    
    def patch(self, request, client_forfait_id):
        try:
            client_forfait = ClientForfait.objects.get(id=client_forfait_id)
            serializer = ClientForfaitSerializer(client_forfait, data=request.data, partial=True)
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
        except ClientForfait.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Abonnement client introuvable'
            }, status=status.HTTP_404_NOT_FOUND)
