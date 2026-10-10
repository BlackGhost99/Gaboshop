"""
Service de vérification en temps réel des forfaits d'abonnement
Applique automatiquement les limites selon le plan actif du magasin
"""

from django.utils import timezone
from django.core.exceptions import PermissionDenied
from decimal import Decimal
import re
import unicodedata
from .models import StoreSubscription, SubscriptionPlan


class SubscriptionChecker:
    """
    Vérifie les permissions d'un magasin selon son forfait en temps réel
    Utilisé par les API et les vues pour appliquer les restrictions automatiquement
    """
    
    @staticmethod
    def _get_monthly_order_limit(plan):
        """Compat B2C/B2B: max_orders_per_month or max_monthly_orders."""
        if not plan:
            return None
        if hasattr(plan, 'max_orders_per_month'):
            return getattr(plan, 'max_orders_per_month')
        if hasattr(plan, 'max_monthly_orders'):
            return getattr(plan, 'max_monthly_orders')
        return None

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
        Gère à la fois les plans B2C (SubscriptionPlan) et B2B (B2BSubscriptionPlan)
        
        Returns:
            SubscriptionPlan, B2BSubscriptionPlan ou le plan par défaut (Free)
        """
        # Utiliser la méthode du modèle Store qui gère correctement B2B et B2C
        return store.get_current_plan()
    
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
        
        # Vérifier si c'est un plan B2B ou B2C
        from b2b.models import B2BSubscriptionPlan
        is_b2b_plan = isinstance(plan, B2BSubscriptionPlan)
        
        if is_b2b_plan:
            # Pour les stores B2B, vérifier max_b2b_products
            # IMPORTANT: Compter TOUS les produits du store B2B, pas seulement ceux avec prix B2B
            # Car un store B2B peut créer des produits sans prix B2B, et ils comptent dans la limite
            max_products = getattr(plan, 'max_b2b_products', None)
            if max_products is not None:
                # Compter TOUS les produits du store (scalable et logique)
                total_product_count = store.products.count()
                
                if total_product_count >= max_products:
                    raise PermissionDenied(
                        f"Votre forfait {plan.name} ne permet que {max_products} produit{'s' if max_products > 1 else ''} B2B. "
                        f"Vous en avez déjà {total_product_count}. "
                        f"Passez à un forfait supérieur pour ajouter plus de produits."
                    )
        else:
            # Pour les stores B2C, vérifier max_products
            if plan.max_products is not None:
                product_count = store.products.count()
                if product_count >= plan.max_products:
                    raise PermissionDenied(
                        f"Votre forfait {plan.name} ne permet que {plan.max_products} produits. "
                        f"Vous en avez déjà {product_count}. "
                        f"Passez à un forfait supérieur pour ajouter plus de produits."
                    )
    
    @staticmethod
    def _normalize_text(value):
        text = (value or '').strip().lower()
        text = unicodedata.normalize('NFD', text)
        text = re.sub(r'[\u0300-\u036f]', '', text)
        return text

    @staticmethod
    def _food_keywords():
        """Mots « alimentaire » réglés dans l'admin (mêmes que pour les commissions)."""
        from api.models import SystemSettings
        try:
            raw = SystemSettings.current('food_category_keywords', 'ALIMENTATION,BOISSONS')
        except Exception:
            raw = 'ALIMENTATION,BOISSONS'
        return [
            SubscriptionChecker._normalize_text(k) for k in (raw or '').split(',') if k.strip()
        ]

    @staticmethod
    def _is_food_category(category, keywords=None):
        """
        Un produit est alimentaire quand la catégorie de commerce de sa catégorie
        contient un des mots réglés dans l'admin. Même règle que la commission.
        """
        store_category = getattr(category, 'store_category', None) if category else None
        if not store_category:
            return False
        if keywords is None:
            keywords = SubscriptionChecker._food_keywords()
        name = SubscriptionChecker._normalize_text(getattr(store_category, 'name', ''))
        return any(k and k in name for k in keywords)

    @staticmethod
    def check_can_add_food_product(store, category=None, exclude_product_id=None):
        """
        Limite le nombre de produits alimentaires selon le forfait (max_products_food).
        Le non alimentaire n'est jamais bloqué ici : seul max_products le limite.
        Un commerce déjà au-dessus garde ses produits mais ne peut plus en ajouter.
        """
        plan = SubscriptionChecker.get_current_plan(store)
        if not plan:
            raise PermissionDenied("Aucun forfait trouvé. Veuillez vous abonner.")

        max_food = getattr(plan, 'max_products_food', None)
        if max_food is None:
            return

        keywords = SubscriptionChecker._food_keywords()
        if not SubscriptionChecker._is_food_category(category, keywords):
            return

        products_qs = store.products.select_related('category__store_category')
        if exclude_product_id:
            products_qs = products_qs.exclude(id=exclude_product_id)
        food_count = sum(
            1 for product in products_qs
            if SubscriptionChecker._is_food_category(product.category, keywords)
        )

        if food_count >= max_food:
            raise PermissionDenied(
                f"Votre forfait {plan.name} permet {max_food} produits alimentaires. "
                f"Vous en avez déjà {food_count}. "
                f"Les produits non alimentaires restent possibles, "
                f"ou passez à un forfait supérieur pour ajouter plus d'alimentaire."
            )

    # Ancien nom, gardé pour les appels existants.
    check_can_add_non_food_product = check_can_add_food_product

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
        monthly_limit = SubscriptionChecker._get_monthly_order_limit(plan)
        if plan and monthly_limit:
            # Compter commandes ce mois
            from django.utils import timezone
            from orders.models import Order
            month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            order_count = Order.objects.filter(
                store=store,
                created_at__gte=month_start
            ).count()
            if order_count >= monthly_limit:
                raise PermissionDenied(
                    f"Vous avez atteint la limite de {monthly_limit} commandes/mois "
                    f"de votre plan {plan.name}. Passez au plan Pro ou Business pour des commandes illimitées."
                )
    
    @staticmethod
    def check_can_access_b2b(store):
        """
        🏭 Vérifie si le store B2C peut accéder au B2B (approvisionnement)
        """
        plan = SubscriptionChecker.get_current_plan(store)
        if not plan or not plan.can_access_b2b:
            raise PermissionDenied(
                f"L'acc?s au catalogue B2B (approvisionnement) est r?serv? aux plans Pro ou Business. "
                f"Passez au plan Pro ou Business pour commander chez les grossistes."
            )
    
    @staticmethod
    def check_can_offer_express_delivery(store):
        """
        VÇ¸rifie si le magasin peut proposer la livraison express.
        """
        plan = SubscriptionChecker.get_current_plan(store)
        if not plan or not getattr(plan, 'can_offer_express_delivery', False):
            raise PermissionDenied(
                "La livraison express n'est pas disponible avec votre forfait actuel. "
                "Passez au plan Pro ou Business pour l'activer."
            )

    @staticmethod
    def get_service_fee_b2b(store):
        """Retourne 0 (frais desactives)."""
        return Decimal('0.00')
    
    @staticmethod
    def get_subscription_price(store):
        """
        💵 Retourne le prix de la souscription selon le type de store
        Business: 50 000 F (B2C) ou 80 000 F (B2B)
        Pro: 20 000 F
        Free: 0 F
        """
        plan = SubscriptionChecker.get_current_plan(store)
        if not plan:
            return Decimal('0.00')
        
        # Plan Business a un prix différent selon le type de store
        if plan.plan_type == 'business':
            if store.is_b2b:
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

