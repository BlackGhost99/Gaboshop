"""Droits équipe B2C dérivés exclusivement du forfait effectivement actif en base.

Cette fonction ne crée pas d'accès employé. Les futurs endpoints d'équipe devront
l'appeler à chaque demande (et vérifier les permissions au niveau des commandes).
"""


def get_b2c_staff_policy(store):
    if store is None or getattr(store, 'is_b2b', False):
        return {
            'can_manage_staff': False, 'max_staff_accounts': 0,
            'plan_type': None, 'plan_name': None,
        }

    plan = store.get_current_plan()
    enabled = bool(getattr(plan, 'can_manage_staff', False))
    limit = max(0, int(getattr(plan, 'max_staff_accounts', 0) or 0))
    return {
        'can_manage_staff': bool(enabled and limit > 0),
        'max_staff_accounts': limit if enabled else 0,
        'plan_type': getattr(plan, 'plan_type', None),
        'plan_name': getattr(plan, 'name', None),
    }
