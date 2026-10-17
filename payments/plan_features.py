"""Ce qu'un forfait donne vraiment : une seule source pour le code qui applique et pour la carte qui promet.

Règle (contrôle du 16 oct. 2026) : une ligne n'apparaît sur la carte d'un forfait que si un écran ou une vérification
du serveur la rend réelle. Les cases sans effet et les textes libres qui promettent un outil inexistant ne s'affichent plus.
"""
import re
import unicodedata

from django.core.exceptions import PermissionDenied

# Libellés des outils, partagés par les cartes et par les messages de refus.
LABELS = {
    'advanced_stats': 'Statistiques avancées',
    'product_import': 'Import de produits par fichier Excel/CSV',
    'stock_alerts': 'Alertes de stock faible',
    'promotions': 'Promotions (prix barré)',
    'priority_support': 'Support prioritaire',
    'dedicated_support': 'Ligne de support dédiée',
    'custom_page': 'Page de boutique personnalisée',
    'express_delivery': 'Livraison express',
    'live_tracking': 'Suivi des livraisons en temps réel',
    'detailed_finance': 'Rapport financier détaillé par catégorie',
    'bulk_discounts': 'Prix dégressifs pour achats en gros',
    'api_access': 'Accès API pour vos logiciels',
}

# Promesses sans code derrière : jamais affichées sur la carte d'un forfait en vente, même saisies par l'admin.
UNBACKED_PATTERNS = (
    'multi boutique', 'multiboutique', 'synchronisation', 'tarifs negocies', 'tarif negocie',
    'account manager', 'gestionnaire de compte', 'formation', 'visibilite b2b', 'mis en avant',
    'mise en avant', 'sponsor', 'badge',
)
# Lignes libres remplacées par les cases du forfait (la case décide, le texte ne peut plus mentir).
SUPERSEDED_PATTERNS = (
    'statist', 'rapport', 'export', 'import', 'alerte', 'promo', 'commission', 'historique', 'approvisionnement',
    'express', 'api', 'page personnalisee', 'personnalisation', 'support prioritaire', 'support vip',
    'support dedie', 'suivi detaille', 'suivi avance', 'gps', 'remise', 'achats en gros', 'finance', 'financier',
)


def _plain(value):
    text = unicodedata.normalize('NFD', (value or '').strip().lower())
    text = re.sub(r'[̀-ͯ]', '', text)
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', text).split())


def _matches(text, patterns):
    words = f' {_plain(text)} '
    return any(f' {p} ' in words or (len(p) > 4 and p in words) for p in patterns)


def keep_free_text(text):
    """Vrai si une ligne saisie par l'admin peut rester sur la carte d'un forfait en vente."""
    return bool(_plain(text)) and not _matches(text, UNBACKED_PATTERNS) and not _matches(text, SUPERSEDED_PATTERNS)


def is_b2b_plan(plan):
    from b2b.models import B2BSubscriptionPlan
    return isinstance(plan, B2BSubscriptionPlan)


def has(plan, feature):
    """Le forfait inclut-il cet outil ?"""
    if plan is None:
        return False
    if feature == 'advanced_stats':
        if is_b2b_plan(plan):
            return bool(plan.can_view_detailed_reports or plan.has_advanced_analytics)
        return bool(plan.has_statistics or plan.can_view_detailed_reports)
    if feature == 'product_import':
        return bool(getattr(plan, 'can_import_products', False))
    if feature == 'stock_alerts':
        return bool(getattr(plan, 'has_stock_alerts', False))
    if feature == 'promotions':
        return bool(getattr(plan, 'can_create_promotions', False))
    if feature == 'priority_support':
        return bool(plan.has_priority_support or getattr(plan, 'support_level', 'standard') in ('prioritaire', 'dedie'))
    if feature == 'dedicated_support':
        return getattr(plan, 'support_level', 'standard') == 'dedie'
    if feature == 'custom_page':
        return not is_b2b_plan(plan) and bool(plan.has_custom_page)
    if feature == 'express_delivery':
        return not is_b2b_plan(plan) and bool(plan.can_offer_express_delivery)
    if feature == 'live_tracking':
        return not is_b2b_plan(plan) and bool(plan.has_advanced_delivery_tracking)
    if feature == 'detailed_finance':
        return bool(plan.can_view_finance_detailed)
    if feature == 'bulk_discounts':
        return is_b2b_plan(plan) and bool(plan.can_offer_bulk_discounts)
    if feature == 'api_access':
        return is_b2b_plan(plan) and bool(plan.has_api_access)
    if feature == 'exports':
        if is_b2b_plan(plan):
            return bool(plan.can_export_finance_csv)
        return bool(plan.can_export_excel)
    raise ValueError(f'Outil inconnu : {feature}')


def store_has(store, feature):
    return has(store.get_current_plan(), feature) if store is not None else False


RANKS = ('free', 'pro', 'business')


def plan_for_sale(plan, accepts):
    """Le moins cher des forfaits en vente au-dessus de l'actuel (même famille : commerce ou grossiste)
    pour lequel ``accepts(forfait)`` est vrai ; None s'il n'y en a pas (Business fermé n'est jamais proposé)."""
    from payments.models import SubscriptionPlan
    model = type(plan) if plan is not None else SubscriptionPlan
    current = getattr(plan, 'plan_type', 'free')
    higher = RANKS[RANKS.index(current) + 1:] if current in RANKS else RANKS[1:]
    for candidate in model.objects.filter(plan_type__in=higher, is_active=True, is_available=True).order_by('price'):
        if accepts(candidate):
            return candidate
    return None


def required_message(feature, plan=None):
    label = LABELS.get(feature, feature)
    current = f' Votre forfait actuel : {plan.name}.' if plan is not None else ''
    target = plan_for_sale(plan, lambda candidate: has(candidate, feature))
    if target is None:
        return f"« {label} » n'est inclus dans aucun forfait en vente pour le moment.{current}"
    return (f"« {label} » fait partie du forfait {target.name}.{current} "
            f"Passez à {target.name} dans « Mon forfait » pour l'utiliser.")


class PlanFeatureRequired(PermissionDenied):
    def __init__(self, feature, plan=None):
        self.feature = feature
        super().__init__(required_message(feature, plan))


def require(store, feature):
    plan = store.get_current_plan()
    if not has(plan, feature):
        raise PlanFeatureRequired(feature, plan)
    return plan


def tool_lines(plan):
    """Lignes de la carte pour les outils réellement branchés."""
    lines = []
    if has(plan, 'advanced_stats'):
        lines.append('Statistiques avancées : ventes jour par jour, meilleurs produits, clients fidèles, meilleures heures')
    if has(plan, 'exports'):
        lines.append('Export Excel/CSV de vos ventes et dépenses')
    pdf = plan.can_export_finance_pdf if is_b2b_plan(plan) else plan.can_export_pdf
    if pdf:
        lines.append('Export PDF de vos rapports')
    if has(plan, 'product_import'):
        lines.append(LABELS['product_import'])
    if has(plan, 'stock_alerts'):
        lines.append('Alertes de stock faible dans vos notifications')
    if has(plan, 'promotions'):
        lines.append('Promotions : prix barré sur vos produits')
    if has(plan, 'detailed_finance'):
        lines.append('Rapport financier détaillé : ventes par catégorie et par commande')
    if has(plan, 'custom_page'):
        lines.append('Page de boutique personnalisée : couleur, présentation, réseaux sociaux')
    if has(plan, 'express_delivery'):
        lines.append('Livraison express proposée à vos clients')
    if has(plan, 'live_tracking'):
        lines.append('Suivi de la livraison en temps réel sur carte, pour vous et vos clients')
    if has(plan, 'dedicated_support'):
        lines.append('Ligne de support dédiée (WhatsApp et téléphone) et réponse en priorité')
    elif has(plan, 'priority_support'):
        lines.append('Support prioritaire : vos demandes sont traitées en premier, avec le contact direct de Gaboshop')
    if has(plan, 'bulk_discounts'):
        lines.append('Prix dégressifs : tarifs par palier de quantité pour vos acheteurs')
    if has(plan, 'api_access'):
        lines.append("Accès API : clés d'intégration pour relier votre stock et vos commandes à vos logiciels")
    return lines
