"""Quel niveau de support donne le forfait du commerce de la personne ? (la règle vient de payments/plan_features.py)"""
from payments.plan_features import has

from .models import PRIORITY_DEDICATED, PRIORITY_PRIORITY, PRIORITY_RANKS, PRIORITY_STANDARD


def plan_priority(plan):
    if has(plan, 'dedicated_support'):
        return PRIORITY_DEDICATED
    if has(plan, 'priority_support'):
        return PRIORITY_PRIORITY
    return PRIORITY_STANDARD


def support_context(user):
    """(commerce, forfait, priorité) retenus pour cette personne.

    Seuls les gérants de commerce ont un forfait de support. S'ils gèrent plusieurs commerces, on retient celui
    dont le forfait donne le meilleur niveau : la demande est traitée selon le plus haut niveau qu'ils ont payé.
    """
    if getattr(user, 'user_type', '') != 'store_manager':
        return None, None, PRIORITY_STANDARD
    best = (None, None, PRIORITY_STANDARD)
    for store in user.managed_stores.all().order_by('id'):
        plan = store.get_current_plan()
        level = plan_priority(plan)
        if best[0] is None or PRIORITY_RANKS[level] < PRIORITY_RANKS[best[2]]:
            best = (store, plan, level)
    return best
