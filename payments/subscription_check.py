"""
Service de vérification en temps réel des forfaits d'abonnement
Applique automatiquement les limites selon le plan actif du magasin
"""

from django.utils import timezone
from django.core.exceptions import PermissionDenied
from decimal import Decimal
from .models import StoreSubscription, SubscriptionPlan


class SubscriptionChecker:
    """
    Vérifie les permissions d'un magasin selon son forfait en temps réel
    Utilisé par les API et les vues pour appliquer les restrictions automatiquement
    """
    
    @staticmethod
    def get_active_subscription(store):
        """
        Récupère l'abonnement ACTIF du magasin
        
        Returns:
            StoreSubscription ou None
        """
        try:
            # Chercher un abonnement actif et non expiré
            subscription = StoreSubscription.objects.filter(
                store=store,
                status='active',
                end_date__gte=timezone.now().date()
            ).latest('end_date')
            return subscription
        except StoreSubscription.DoesNotExist:
            return None
    
    @staticmethod
    def get_current_plan(store):
        """
        Récupère le plan ACTUEL du magasin
        
        Returns:
            SubscriptionPlan ou le plan par défaut (Starter)
        """
        subscription = SubscriptionChecker.get_active_subscription(store)
        
        if subscription and subscription.plan:
            return subscription.plan
        
        # Plan par défaut: Starter
        try:
            return SubscriptionPlan.objects.get(plan_type='starter')
        except SubscriptionPlan.DoesNotExist:
            return None
    
    @staticmethod
    def is_subscription_active(store):
        """
        Vérifie si le magasin a un forfait ACTIF
        """
        subscription = SubscriptionChecker.get_active_subscription(store)
        return subscription is not None
    
    @staticmethod
    def is_subscription_expired(store):
        """
        Vérifie si le forfait du magasin a EXPIRÉ
        """
        subscription = SubscriptionChecker.get_active_subscription(store)
        if not subscription:
            return False
        return subscription.end_date < timezone.now().date()
    
    @staticmethod
    def get_plan_features(store):
        """
        Retourne les fonctionnalités disponibles pour ce magasin
        """
        plan = SubscriptionChecker.get_current_plan(store)
        if plan:
            return plan.get_features_list()
        return []
    
    @staticmethod
    def get_days_until_expiry(store):
        """
        Retourne le nombre de jours avant expiration du forfait
        """
        subscription = SubscriptionChecker.get_active_subscription(store)
        if not subscription:
            return 0
        delta = (subscription.end_date - timezone.now().date()).days
        return max(0, delta)
    
    # ========================================================================
    # VÉRIFICATIONS DE PERMISSIONS (celles-ci lèvent PermissionDenied)
    # ========================================================================
    
    @staticmethod
    def check_can_add_product(store):
        """
        ✔️ Vérifiez si le magasin peut ajouter un produit selon son forfait
        """
        plan = SubscriptionChecker.get_current_plan(store)
        
        if not plan:
            raise PermissionDenied("Aucun forfait trouvé. Veuillez vous abonner.")
        
        # Si max_products est None → illimité
        if plan.max_products is not None:
            product_count = store.products.count()
            if product_count >= plan.max_products:
                raise PermissionDenied(
                    f"Votre forfait {plan.name} ne permet que {plan.max_products} produits. "
                    f"Vous en avez déjà {product_count}. "
                    f"Passez à un forfait supérieur pour ajouter plus de produits."
                )
    
    @staticmethod
    def check_can_access_statistics(store):
        """
        📊 Vérifiez si le magasin peut accéder aux statistiques
        """
        plan = SubscriptionChecker.get_current_plan(store)
        
        if not plan or not plan.has_statistics:
            raise PermissionDenied(
                f"Les statistiques ne sont pas disponibles avec votre forfait actuel. "
                f"Passez à un forfait supérieur pour accéder aux statistiques avancées."
            )
    
    @staticmethod
    def check_can_customize_store(store):
        """
        🎨 Vérifiez si le magasin peut personnaliser sa boutique
        """
        plan = SubscriptionChecker.get_current_plan(store)
        
        if not plan or not plan.has_custom_page:
            raise PermissionDenied(
                f"La personnalisation de boutique n'est pas disponible avec votre forfait actuel. "
                f"Passez à un forfait supérieur pour personnaliser votre boutique."
            )
    
    @staticmethod
    def check_can_sponsor_products(store):
        """
        ⭐ Vérifiez si le magasin peut sponsoriser des produits
        """
        plan = SubscriptionChecker.get_current_plan(store)
        
        if not plan or not plan.can_sponsor_products:
            raise PermissionDenied(
                f"La sponsorisation de produits n'est pas disponible avec votre forfait actuel. "
                f"Passez à un forfait supérieur pour sponsoriser vos produits."
            )
    
    @staticmethod
    def check_can_access_priority_support(store):
        """
        📞 Vérifiez si le magasin a accès au support prioritaire
        """
        plan = SubscriptionChecker.get_current_plan(store)
        
        if not plan or not plan.has_priority_support:
            raise PermissionDenied(
                f"Le support prioritaire n'est pas disponible avec votre forfait actuel. "
                f"Passez à un forfait supérieur pour accéder au support VIP."
            )
    
    @staticmethod
    def check_can_create_order(store):
        """
        🛒 Vérifie si le store peut créer une commande ce mois
        """
        plan = SubscriptionChecker.get_current_plan(store)
        if plan and plan.max_orders_per_month:
            # Compter commandes ce mois
            from django.utils import timezone
            from orders.models import Order
            month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            order_count = Order.objects.filter(
                store=store,
                created_at__gte=month_start
            ).count()
            if order_count >= plan.max_orders_per_month:
                raise PermissionDenied(
                    f"Vous avez atteint la limite de {plan.max_orders_per_month} commandes/mois "
                    f"de votre plan {plan.name}. Passez au plan Business pour des commandes illimitées."
                )
    
    @staticmethod
    def check_can_access_b2b(store):
        """
        🏭 Vérifie si le store B2C peut accéder au B2B (approvisionnement)
        """
        plan = SubscriptionChecker.get_current_plan(store)
        if not plan or not plan.can_access_b2b:
            raise PermissionDenied(
                f"L'accès au catalogue B2B (approvisionnement) est réservé au plan Business. "
                f"Passez au plan Business pour commander chez les grossistes."
            )
    
    @staticmethod
    def get_service_fee_b2b(store):
        """
        💰 Retourne les frais de service B2B selon le plan
        """
        plan = SubscriptionChecker.get_current_plan(store)
        
        if plan and hasattr(plan, 'service_fee_to_wholesaler_amount'):
            return Decimal(str(plan.service_fee_to_wholesaler_amount))
        else:
            # Fallback pour compatibilité
            return Decimal('1000.00')
    
    @staticmethod
    def get_subscription_price(store):
        """
        💵 Retourne le prix de la souscription selon le type de store
        Business: 50 000 F (B2C) ou 80 000 F (B2B)
        Pro: 30 000 F
        Free: 0 F
        """
        plan = SubscriptionChecker.get_current_plan(store)
        if not plan:
            return Decimal('0.00')
        
        # Plan Business a un prix différent selon le type de store
        if plan.plan_type == 'business':
            if store.is_b2b or store.store_type in ['wholesaler', 'industry']:
                return Decimal('80000.00')  # B2B
            else:
                return Decimal('50000.00')  # B2C
        
        return plan.price


def check_subscription_permission(permission_type):
    """
    Décorateur pour vérifier les permissions de forfait sur une vue/API
    
    Usage:
        @check_subscription_permission('add_product')
        def create_product(request):
            ...
    """
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            store = request.user.store  # Suppose que l'utilisateur a une relation avec un magasin
            
            if permission_type == 'add_product':
                SubscriptionChecker.check_can_add_product(store)
            elif permission_type == 'statistics':
                SubscriptionChecker.check_can_access_statistics(store)
            elif permission_type == 'customize':
                SubscriptionChecker.check_can_customize_store(store)
            elif permission_type == 'sponsor':
                SubscriptionChecker.check_can_sponsor_products(store)
            elif permission_type == 'priority_support':
                SubscriptionChecker.check_can_access_priority_support(store)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
