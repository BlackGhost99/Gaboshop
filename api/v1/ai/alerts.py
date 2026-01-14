"""
Service de surveillance et alertes IA
"""
from django.utils import timezone
from django.db.models import Q, Count, Sum
from datetime import timedelta
from typing import List, Dict, Any
from products.models import Product
from orders.models import Order
from payments.models import PaymentIntent
from stores.models import Store


class AlertMonitor:
    """
    Surveille les signaux critiques et génère des alertes
    """
    
    @staticmethod
    def check_stock_alerts(store: Store = None) -> List[Dict[str, Any]]:
        """
        Vérifie les alertes de stock
        """
        alerts = []
        
        queryset = Product.objects.filter(is_available=True)
        if store:
            queryset = queryset.filter(store=store)
        
        # Stock critique (< 10 unités)
        critical_stock = queryset.filter(stock__gt=0, stock__lte=10).count()
        if critical_stock > 0:
            alerts.append({
                "type": "LOW_STOCK",
                "severity": "warning",
                "message": f"{critical_stock} produit(s) avec stock critique (< 10 unités)",
                "count": critical_stock,
            })
        
        # Stock épuisé
        out_of_stock = queryset.filter(stock=0).count()
        if out_of_stock > 0:
            alerts.append({
                "type": "OUT_OF_STOCK",
                "severity": "error",
                "message": f"{out_of_stock} produit(s) en rupture de stock",
                "count": out_of_stock,
            })
        
        return alerts
    
    @staticmethod
    def check_payment_alerts(store: Store = None) -> List[Dict[str, Any]]:
        """
        Vérifie les alertes de paiement
        """
        alerts = []
        
        # Paiements échoués récents (24h)
        recent_failed = PaymentIntent.objects.filter(
            status='FAILED',
            created_at__gte=timezone.now() - timedelta(hours=24)
        )
        
        if store:
            recent_failed = recent_failed.filter(user__managed_stores=store)
        
        failed_count = recent_failed.count()
        if failed_count > 5:
            alerts.append({
                "type": "HIGH_PAYMENT_FAILURES",
                "severity": "warning",
                "message": f"{failed_count} paiements échoués dans les dernières 24h",
                "count": failed_count,
            })
        
        return alerts
    
    @staticmethod
    def check_order_alerts(store: Store = None) -> List[Dict[str, Any]]:
        """
        Vérifie les alertes de commandes
        """
        alerts = []
        
        # Commandes simultanées (risque de surcharge)
        if store:
            pending_orders = Order.objects.filter(
                store=store,
                status__in=['created', 'pending_payment', 'paid', 'confirmed']
            ).count()
            
            if pending_orders > 20:
                alerts.append({
                    "type": "HIGH_PENDING_ORDERS",
                    "severity": "warning",
                    "message": f"{pending_orders} commandes en attente. Risque de surcharge.",
                    "count": pending_orders,
                })
        
        return alerts
    
    @staticmethod
    def check_popular_products(store: Store = None) -> List[Dict[str, Any]]:
        """
        Détecte les produits populaires avec stock faible
        """
        alerts = []
        
        # Produits commandés récemment (7 jours) avec stock faible
        recent_orders = Order.objects.filter(
            created_at__gte=timezone.now() - timedelta(days=7),
            status__in=['paid', 'confirmed', 'preparing', 'ready']
        )
        
        if store:
            recent_orders = recent_orders.filter(store=store)
        
        # Compter les produits les plus commandés
        from orders.models import OrderItem
        popular_items = OrderItem.objects.filter(
            order__in=recent_orders
        ).values('product').annotate(
            total_ordered=Sum('quantity')
        ).order_by('-total_ordered')[:10]
        
        for item in popular_items:
            product_id = item['product']
            total_ordered = item['total_ordered']
            
            try:
                product = Product.objects.get(id=product_id)
                if product.stock < total_ordered * 2:  # Stock < 2x la demande récente
                    alerts.append({
                        "type": "POPULAR_LOW_STOCK",
                        "severity": "warning",
                        "message": f"Produit populaire '{product.name}' avec stock faible ({product.stock} unités)",
                        "product_id": product.id,
                        "product_name": product.name,
                        "stock": product.stock,
                        "recent_demand": total_ordered,
                    })
            except Product.DoesNotExist:
                continue
        
        return alerts
    
    @staticmethod
    def get_all_alerts(store: Store = None, user_role: str = None) -> List[Dict[str, Any]]:
        """
        Récupère toutes les alertes pertinentes
        """
        all_alerts = []
        
        # Alertes selon le rôle
        if user_role in ['store_manager', 'admin']:
            all_alerts.extend(AlertMonitor.check_stock_alerts(store))
            all_alerts.extend(AlertMonitor.check_payment_alerts(store))
            all_alerts.extend(AlertMonitor.check_order_alerts(store))
            all_alerts.extend(AlertMonitor.check_popular_products(store))
        
        return all_alerts

