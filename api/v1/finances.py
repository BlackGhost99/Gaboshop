"""Finance & Revenue API views for platform analytics and reporting."""

from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from payments.models import Payment, Commission, DeliveryPayout, StoreSubscription, SponsoredProduct
from orders.models import Order
from stores.models import Store


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
