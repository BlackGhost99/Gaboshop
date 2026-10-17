"""Gamme des forfaits commerces : Gratuit (porte d'entrée), Pro (à vendre), Business (visible, grisé).

Règle du propriétaire (15 oct. 2026) : un commerce sans abonnement est au forfait Gratuit, jamais bloqué
par « Aucun forfait trouvé ». Le forfait Gratuit n'expire pas : c'est le plan de repli, pas une ligne
d'abonnement. Les fonctions acceptent le modèle en paramètre pour servir aussi dans les migrations.
"""
from decimal import Decimal

FREE_FEATURES = ['Commandes', 'Paiement', 'Livraison', 'Support standard']
# Les outils du Pro (statistiques, import, alertes de stock, promotions) viennent de ses cases : voir plan_features.py.
PRO_FEATURES = []
# Business n'est pas en vente : ces lignes décrivent ce qui reste à construire avant de l'ouvrir.
BUSINESS_FEATURES = ['Multi-boutiques', 'API', 'Synchronisation stock', 'Support prioritaire', 'Tarifs négociés']
# Ce que le forfait Pro (et Business, quand il ouvrira) donne vraiment ; la migration 0028 l'applique aux forfaits existants.
PRO_TOOLS = {'has_statistics': True, 'can_view_detailed_reports': True, 'can_export_excel': True, 'can_export_pdf': True,
             'can_import_products': True, 'has_stock_alerts': True, 'can_create_promotions': True,
             # 17 oct. 2026 : les options marketing deviennent réelles (support, page, express, suivi, finance détaillée).
             'has_priority_support': True, 'support_level': 'prioritaire', 'has_custom_page': True,
             'can_offer_express_delivery': True, 'has_advanced_delivery_tracking': True, 'can_view_finance_detailed': True}
B2B_PRO_TOOLS = {'can_view_detailed_reports': True, 'can_export_finance_csv': True, 'can_export_finance_pdf': True,
                 'can_import_products': True, 'has_stock_alerts': True,
                 'can_offer_bulk_discounts': True, 'can_create_promotions': True, 'has_priority_support': True,
                 'has_api_access': True, 'can_view_finance_detailed': True}
BUSINESS_DESCRIPTION = ('Business — réservé aux commerces à fort volume et partenaires professionnels. '
                        'Disponible prochainement.')

B2C_DEFAULTS = {
    'free': {'names': ('Gratuit', 'Free'), 'price': Decimal('0'), 'max_products': 20,
             'can_offer_express_delivery': False, 'has_advanced_delivery_tracking': False,
             'features_json': FREE_FEATURES, 'description': 'Pour démarrer et vendre sans payer.'},
    'pro': {'names': ('Pro',), 'price': Decimal('10000'), 'max_products': 200, **PRO_TOOLS,
            'features_json': PRO_FEATURES, 'description': 'Pour les commerces qui veulent vendre plus.'},
    'business': {'names': ('Business',), 'price': Decimal('50000'), 'max_products': None, **PRO_TOOLS,
                 'support_level': 'dedie', 'is_available': False,
                 'features_json': BUSINESS_FEATURES, 'description': BUSINESS_DESCRIPTION},
}
B2B_DEFAULTS = {
    'free': {'names': ('B2B Gratuit', 'B2B Free'), 'price': Decimal('0'), 'max_b2b_products': 20,
             'can_offer_bulk_discounts': False, 'description': 'Pour démarrer et vendre sans payer.', 'display_order': 1},
    'pro': {'names': ('B2B Pro',), 'price': Decimal('10000'), 'max_b2b_products': 200, **B2B_PRO_TOOLS,
            'is_popular': True,
            'description': 'Pour les grossistes qui veulent vendre plus.', 'display_order': 2},
    'business': {'names': ('B2B Business',), 'price': Decimal('80000'), 'max_b2b_products': None, **B2B_PRO_TOOLS,
                 'is_available': False, 'description': BUSINESS_DESCRIPTION, 'display_order': 3},
}


def _free_name(model, names):
    for name in names:
        if not model.objects.filter(name=name).exists():
            return name
    return f"{names[0]} {model.objects.count() + 1}"


def _slug(model, name):
    from django.utils.text import slugify
    base = slugify(name) or 'plan'
    slug, n = base, 2
    while model.objects.filter(slug=slug).exists():
        slug, n = f"{base}-{n}", n + 1
    return slug


def ensure_plan(model, plan_type, defaults_table):
    """Le plan de ce type ; créé avec les valeurs par défaut s'il manque. Un plan existant n'est pas modifié."""
    plan = model.objects.filter(plan_type=plan_type).first()
    if plan is not None:
        return plan
    values = dict(defaults_table[plan_type])
    name = _free_name(model, values.pop('names'))
    field_names = {f.name for f in model._meta.get_fields()}
    values = {k: v for k, v in values.items() if k in field_names}
    return model.objects.create(name=name, slug=_slug(model, name), plan_type=plan_type, is_active=True, **values)


def ensure_free_plan(model=None):
    if model is None:
        from payments.models import SubscriptionPlan as model
    plan = ensure_plan(model, 'free', B2C_DEFAULTS)
    if not plan.is_active:  # le plan de repli doit toujours rester utilisable
        plan.is_active = True
        plan.save(update_fields=['is_active'])
    return plan


def ensure_free_b2b_plan(model=None):
    if model is None:
        from b2b.models import B2BSubscriptionPlan as model
    plan = ensure_plan(model, 'free', B2B_DEFAULTS)
    if not plan.is_active:
        plan.is_active = True
        plan.save(update_fields=['is_active'])
    return plan


def ensure_range(b2c_model, b2b_model=None):
    """Créer seulement les forfaits manquants, sans effacer les décisions de l'admin.

    Les valeurs initiales de Business le rendent non achetable à sa création ;
    une fois modifié depuis l'administration, ses états et son prix sont conservés.
    """
    for model, table in ((b2c_model, B2C_DEFAULTS), (b2b_model, B2B_DEFAULTS)):
        if model is None:
            continue
        for plan_type in ('free', 'pro', 'business'):
            ensure_plan(model, plan_type, table)
        model.objects.filter(plan_type='free', is_active=False).update(is_active=True)


def unavailable_message(plan):
    return f"Le forfait {plan.name} n'est pas encore disponible. Il ouvrira prochainement."
