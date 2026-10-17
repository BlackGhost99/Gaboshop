"""
Finance services - Plan gating and business logic
"""
from payments.models import SubscriptionPlan
from django.core.exceptions import PermissionDenied
from datetime import timedelta
from django.utils import timezone


def get_plan_features(store):
    """Retourne les features du plan actuel du store"""
    return plan_feature_map(store.get_current_plan())


def plan_feature_map(plan):
    """Ce qu'un forfait permet côté finance (forfait commerce ou grossiste)."""
    if not plan:
        # Plan Free par défaut
        return {
            'can_view_basic_reports': True,
            'can_view_detailed_reports': False,
            'can_export_excel': False,
            'can_export_pdf': False,
            'history_limit_days': 30,
            # Finance B2B - Free par défaut
            'can_view_finance_basic': False,
            'can_view_finance_detailed': False,
            'can_export_finance_csv': False,
            'can_export_finance_pdf': False,
            'finance_history_limit_days': None,
            'plan_name': 'Free'
        }
    
    # Vérifier si c'est un plan B2B ou B2C
    from b2b.models import B2BSubscriptionPlan
    is_b2b_plan = isinstance(plan, B2BSubscriptionPlan)
    
    if is_b2b_plan:
        # Plan B2B (B2BSubscriptionPlan)
        return {
            # Finance B2C - Non applicable pour stores B2B purs
            'can_view_basic_reports': getattr(plan, 'can_view_detailed_reports', False),  # Utiliser can_view_detailed_reports comme proxy
            'can_view_detailed_reports': getattr(plan, 'can_view_detailed_reports', False),
            'can_export_excel': getattr(plan, 'can_export_finance_csv', False),  # Utiliser CSV comme proxy
            'can_export_pdf': getattr(plan, 'can_export_finance_pdf', False),
            'history_limit_days': getattr(plan, 'finance_history_limit_days', 30),
            # Finance B2B - Utiliser les champs du plan B2B
            'can_view_finance_basic': getattr(plan, 'can_view_finance_basic', True),
            'can_view_finance_detailed': getattr(plan, 'can_view_finance_detailed', False),
            'can_export_finance_csv': getattr(plan, 'can_export_finance_csv', False),
            'can_export_finance_pdf': getattr(plan, 'can_export_finance_pdf', False),
            'finance_history_limit_days': getattr(plan, 'finance_history_limit_days', None),
            'plan_name': plan.name
        }
    else:
        # Plan B2C (SubscriptionPlan)
        return {
            # Finance B2C
            'can_view_basic_reports': plan.can_view_basic_reports,
            'can_view_detailed_reports': plan.can_view_detailed_reports,
            'can_export_excel': plan.can_export_excel,
            'can_export_pdf': plan.can_export_pdf,
            'history_limit_days': plan.history_limit_days,
            # Finance B2B (si applicable)
            'can_view_finance_basic': getattr(plan, 'can_view_finance_basic', False),
            'can_view_finance_detailed': getattr(plan, 'can_view_finance_detailed', False),
            'can_export_finance_csv': getattr(plan, 'can_export_finance_csv', False),
            'can_export_finance_pdf': getattr(plan, 'can_export_finance_pdf', False),
            'finance_history_limit_days': getattr(plan, 'finance_history_limit_days', None),
            'plan_name': plan.name
        }


def enforce_feature(store, feature_key, messages=None):
    """Enforce une feature ou lève PermissionDenied"""
    features = get_plan_features(store)
    
    if not features.get(feature_key, False):
        labels = {
            'can_export_excel': "L'export Excel/CSV",
            'can_export_pdf': "L'export PDF",
            'can_view_detailed_reports': "Les rapports détaillés",
            'can_export_finance_csv': "L'export CSV",
            'can_export_finance_pdf': "L'export PDF",
            'can_view_finance_detailed': "Les rapports détaillés",
        }
        message = (messages or {}).get(feature_key)
        if not message:
            # Conseiller seulement un forfait en vente qui donne vraiment cet outil.
            from payments.plan_features import plan_for_sale
            target = plan_for_sale(store.get_current_plan(), lambda plan: plan_feature_map(plan).get(feature_key, False))
            label = labels.get(feature_key, "Cet outil")
            plural = label.startswith('Les ')
            if target is None:
                verb = 'ne sont inclus' if plural else "n'est inclus"
                message = f"{label} {verb} dans aucun forfait en vente pour le moment."
            else:
                verb = 'font' if plural else 'fait'
                message = f"{label} {verb} partie du forfait {target.name}. Passez à {target.name} dans « Mon forfait »."
        raise PermissionDenied(message)


def apply_history_limit(queryset, store, date_field='created_at'):
    """Applique la limite d'historique selon le plan"""
    features = get_plan_features(store)
    limit_days = features.get('history_limit_days')
    
    if limit_days is not None:
        cutoff_date = timezone.now() - timedelta(days=limit_days)
        filter_kwargs = {f'{date_field}__gte': cutoff_date}
        queryset = queryset.filter(**filter_kwargs)
    
    return queryset
