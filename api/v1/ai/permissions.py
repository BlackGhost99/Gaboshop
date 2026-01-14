"""
Système de permissions pour l'IA
Définit ce que l'IA peut faire selon le rôle et le plan de l'utilisateur
"""
from typing import Dict, Any, Optional
from payments.subscription_check import SubscriptionChecker
from stores.models import Store
from users.models import User


class AIPermissionChecker:
    """
    Vérifie les permissions de l'IA selon le rôle et le plan
    """
    
    @staticmethod
    def get_permissions(user: User, store: Optional[Store] = None) -> Dict[str, bool]:
        """
        Retourne les permissions IA pour un utilisateur
        
        Returns:
            Dict avec les permissions (can_search, can_compare_prices, etc.)
        """
        role = user.user_type
        
        # Permissions de base selon le rôle
        permissions = {
            "can_search": True,  # Tous peuvent rechercher
            "can_compare_prices": True,  # Tous peuvent comparer
            "can_prepare_order": role in ["client", "store_manager"],
            "can_execute_order": False,  # JAMAIS automatique, toujours confirmation
            "can_read_stock": role in ["store_manager", "admin"],
            "can_trigger_alerts": role in ["store_manager", "admin"],
            "can_read_orders": role in ["client", "store_manager", "delivery_agent", "admin"],
            "can_read_analytics": role in ["store_manager", "admin"],
        }
        
        # Permissions spécifiques selon le plan (si store_manager)
        if role == "store_manager" and store:
            plan = SubscriptionChecker.get_current_plan(store)
            
            if plan:
                # Permissions B2B selon plan
                permissions["can_access_b2b"] = plan.can_access_b2b if hasattr(plan, 'can_access_b2b') else False
                permissions["can_read_statistics"] = plan.has_statistics if hasattr(plan, 'has_statistics') else False
            else:
                permissions["can_access_b2b"] = False
                permissions["can_read_statistics"] = False
        
        return permissions
    
    @staticmethod
    def can_execute_action(action: str, user: User, store: Optional[Store] = None) -> tuple[bool, Optional[str]]:
        """
        Vérifie si une action peut être exécutée
        
        Args:
            action: Type d'action (prepare_order, search_products, etc.)
            user: Utilisateur
            store: Magasin (si applicable)
        
        Returns:
            Tuple (allowed: bool, reason: Optional[str])
        """
        permissions = AIPermissionChecker.get_permissions(user, store)
        
        action_permissions = {
            "search_products": "can_search",
            "compare_prices": "can_compare_prices",
            "prepare_order": "can_prepare_order",
            "execute_order": "can_execute_order",
            "read_stock": "can_read_stock",
            "trigger_alerts": "can_trigger_alerts",
            "read_orders": "can_read_orders",
            "read_analytics": "can_read_analytics",
            "access_b2b": "can_access_b2b",
        }
        
        permission_key = action_permissions.get(action)
        if not permission_key:
            return False, f"Action inconnue: {action}"
        
        if permission_key not in permissions:
            return False, "Permission non définie"
        
        allowed = permissions[permission_key]
        
        if not allowed:
            reason = f"L'action '{action}' n'est pas autorisée pour votre rôle/plan."
            if user.user_type == "store_manager" and store:
                plan = SubscriptionChecker.get_current_plan(store)
                if plan and action == "access_b2b":
                    reason += " Un forfait Business est requis pour accéder au B2B."
            return False, reason
        
        return True, None

