"""
Services pour l'IA Gaboshop
"""
from django.utils import timezone
from django.db.models import Q, Count, Sum
from decimal import Decimal
from typing import Dict, Any, Optional, List
from payments.subscription_check import SubscriptionChecker
from stores.models import Store
from orders.models import Order
from products.models import Product
from users.models import User


class AIContextService:
    """
    Service pour construire le contexte complet de l'utilisateur
    """
    
    @staticmethod
    def get_user_context(user: User) -> Dict[str, Any]:
        """
        Construit le contexte utilisateur complet
        """
        context = {
            "user": {
                "id": user.id,
                "role": user.user_type,
                "phone": user.phone,
                "email": user.email if hasattr(user, 'email') else None,
                "is_verified": user.is_verified if hasattr(user, 'is_verified') else False,
            }
        }
        
        # Contexte magasin si store_manager
        if user.user_type == 'store_manager':
            try:
                store = user.managed_stores.filter(is_active=True).first()
                if store:
                    subscription = SubscriptionChecker.get_active_subscription(store)
                    plan = SubscriptionChecker.get_current_plan(store)
                    
                    # Calculer métriques
                    orders_7d = Order.objects.filter(
                        store=store,
                        created_at__gte=timezone.now() - timezone.timedelta(days=7)
                    ).count()
                    
                    # Vérifier stock critique
                    low_stock_products = Product.objects.filter(
                        store=store,
                        is_available=True,
                        stock__gt=0,
                        stock__lte=10
                    ).count()
                    
                    context["store"] = {
                        "id": store.id,
                        "name": store.name,
                        "verified": store.is_verified,
                        "b2b_plan": plan.plan_type if plan else "free",
                        "b2c_plan": plan.plan_type if plan else "free",
                    }
                    
                    context["subscription"] = {
                        "b2b": plan.plan_type if plan and plan.can_access_b2b else "free",
                        "b2c": plan.plan_type if plan else "free",
                    }
                    
                    # Alertes
                    alerts = []
                    if not store.products.filter(is_available=True).exists():
                        alerts.append("NO_ACTIVE_PRODUCTS")
                    if plan and plan.plan_type == 'starter' and store.commission_rate > Decimal('8.00'):
                        alerts.append("HIGH_COMMISSION_PLAN")
                    if low_stock_products > 0:
                        alerts.append("LOW_STOCK_PRODUCTS")
                    
                    context["alerts"] = alerts
                    
                    context["metrics"] = {
                        "orders_7d": orders_7d,
                        "stock_critical": low_stock_products > 0,
                        "low_stock_count": low_stock_products,
                    }
            except Exception:
                pass
        
        # Contexte client
        elif user.user_type == 'client':
            orders_7d = Order.objects.filter(
                client=user,
                created_at__gte=timezone.now() - timezone.timedelta(days=7)
            ).count()
            
            context["metrics"] = {
                "orders_7d": orders_7d,
            }
        
        return context
    
    @staticmethod
    def get_full_context(user: User, frontend_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Construit le contexte complet en combinant backend et frontend
        """
        backend_context = AIContextService.get_user_context(user)
        
        if frontend_context:
            backend_context["frontend"] = frontend_context
        
        return backend_context


class ErrorAnalyzer:
    """
    Analyse les erreurs API pour fournir des explications intelligentes
    """
    
    ERROR_EXPLANATIONS = {
        401: "Votre session a expiré. Veuillez vous reconnecter.",
        403: "Vous n'avez pas les permissions nécessaires pour effectuer cette action. Vérifiez votre forfait d'abonnement.",
        404: "La ressource demandée n'existe pas ou n'est plus disponible.",
        500: "Une erreur serveur s'est produite. Notre équipe a été notifiée.",
    }
    
    @staticmethod
    def analyze_error(status_code: int, endpoint: str, error_details: Optional[Dict] = None) -> str:
        """
        Analyse une erreur et retourne une explication humaine
        """
        base_explanation = ErrorAnalyzer.ERROR_EXPLANATIONS.get(
            status_code,
            f"Une erreur (code {status_code}) s'est produite."
        )
        
        # Explications spécifiques selon l'endpoint
        if status_code == 403:
            if 'subscription' in endpoint or 'permission' in endpoint:
                return f"{base_explanation} Votre forfait actuel ne permet pas cette action. Considérez une mise à niveau."
            elif 'b2b' in endpoint:
                return f"{base_explanation} L'accès B2B nécessite un forfait Business."
        
        if status_code == 404:
            if 'product' in endpoint:
                return f"{base_explanation} Ce produit n'est peut-être plus disponible ou a été retiré."
            elif 'order' in endpoint:
                return f"{base_explanation} Cette commande n'existe pas ou vous n'y avez pas accès."
        
        return base_explanation


class AIGatewayService:
    """
    Service pour communiquer avec Anthropic Claude API
    """
    
    @staticmethod
    def build_system_prompt(context: Dict[str, Any]) -> str:
        """
        Construit le prompt système pour Claude
        """
        role = context.get("user", {}).get("role", "client")
        
        base_prompt = """Tu es l'assistant IA de Gaboshop, une plateforme e-commerce au Gabon.
Tu dois être utile, humain, et orienter les utilisateurs sans jamais remplacer la logique métier.
Tu expliques les erreurs, guides les utilisateurs, et prépares des actions sous contrôle utilisateur.

Règles importantes:
- Ne jamais modifier directement la base de données
- Toujours demander confirmation avant d'exécuter des actions
- Expliquer les erreurs de manière claire et actionnable
- Adapter ton langage selon le rôle de l'utilisateur
"""
        
        if role == "store_manager":
            store_info = context.get("store", {})
            alerts = context.get("alerts", [])
            
            base_prompt += f"""
Contexte magasin:
- Magasin: {store_info.get('name', 'N/A')}
- Plan: {context.get('subscription', {}).get('b2c', 'free')}
- Alertes: {', '.join(alerts) if alerts else 'Aucune'}
"""
        
        return base_prompt
    
    @staticmethod
    def build_user_message(user_message: str, context: Dict[str, Any], last_error: Optional[Dict] = None) -> str:
        """
        Construit le message utilisateur enrichi avec contexte
        """
        message = user_message
        
        # Ajouter contexte d'erreur si présent
        if last_error:
            error_explanation = ErrorAnalyzer.analyze_error(
                last_error.get("status"),
                last_error.get("endpoint", ""),
                last_error.get("details")
            )
            message += f"\n\n[Contexte erreur: {error_explanation}]"
        
        return message

