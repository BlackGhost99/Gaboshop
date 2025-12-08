"""Services métier pour la gestion des magasins"""
import logging
from django.db import transaction
from django.utils import timezone
from django.db import models
from stores.models import Store
from products.models import Product

logger = logging.getLogger(__name__)


class StoreService:
    """Services métier pour la gestion des magasins"""
    
    @staticmethod
    def create_store(manager, store_data):
        """
        Créer un nouveau magasin avec validation métier
        """
        try:
            with transaction.atomic():
                # Validation: vérifier que le manager n'a pas déjà un magasin actif
                existing_store = Store.objects.filter(
                    manager=manager, 
                    is_active=True
                ).first()
                
                if existing_store:
                    raise ValueError("Vous avez déjà un magasin actif.")
                
                # Créer le magasin
                store = Store.objects.create(
                    manager=manager,
                    **store_data
                )
                
                logger.info(f"🏪 Magasin créé: {store.name} par {manager.phone}")
                return store
                
        except Exception as e:
            logger.error(f"❌ Erreur création magasin: {e}")
            raise
    
    @staticmethod
    def update_store_metrics(store_id):
        """
        Mettre à jour les métriques d'un magasin (produits, commandes, etc.)
        """
        try:
            store = Store.objects.get(id=store_id)
            
            # Compter les produits actifs
            active_products = store.products.filter(is_available=True).count()
            
            # Calculer le revenu total (simplifié)
            # En production, on utiliserait les données de paiement
            total_revenue = store.orders.filter(
                status='delivered'
            ).aggregate(total=models.Sum('total_amount'))['total'] or 0
            
            # Mettre à jour le cache des métriques
            store._metrics_cache = {
                'active_products': active_products,
                'total_revenue': total_revenue,
                'last_updated': timezone.now()
            }
            
            store.save()
            return store._metrics_cache
            
        except Store.DoesNotExist:
            logger.error(f"❌ Magasin {store_id} non trouvé")
            return None
    
    @staticmethod
    def get_store_performance(store_id, period_days=30):
        """
        Analyser la performance d'un magasin sur une période
        """
        try:
            store = Store.objects.get(id=store_id)
            start_date = timezone.now() - timezone.timedelta(days=period_days)
            
            # Statistiques des commandes
            orders_stats = store.orders.filter(
                created_at__gte=start_date
            ).aggregate(
                total_orders=models.Count('id'),
                completed_orders=models.Count('id', filter=models.Q(status='delivered')),
                total_revenue=models.Sum('total_amount', filter=models.Q(status='delivered')),
                avg_order_value=models.Avg('total_amount', filter=models.Q(status='delivered'))
            )
            
            # Produits les plus vendus
            from django.db.models import Sum
            from orders.models import OrderItem
            
            top_products = OrderItem.objects.filter(
                order__store=store,
                order__created_at__gte=start_date
            ).values(
                'product__name', 'product__id'
            ).annotate(
                total_quantity=Sum('quantity'),
                total_revenue=Sum('unit_price')
            ).order_by('-total_quantity')[:10]
            
            return {
                'period': f"{period_days} jours",
                'orders': orders_stats,
                'top_products': list(top_products),
                'store_info': {
                    'name': store.name,
                    'zone': store.zone,
                    'commission_rate': store.commission_rate
                }
            }
            
        except Store.DoesNotExist:
            logger.error(f"❌ Magasin {store_id} non trouvé")
            return None
