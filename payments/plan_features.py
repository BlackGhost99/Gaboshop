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
}

# Promesses sans code derrière : jamais affichées sur la carte d'un forfait en vente, même saisies par l'admin.
UNBACKED_PATTERNS = (
    'express', 'api', 'multi boutique', 'multiboutique', 'synchronisation', 'tarifs negocies', 'tarif negocie',
    'page personnalisee', 'personnalisation', 'support prioritaire', 'support vip', 'support dedie', 'account manager',
    'gestionnaire de compte', 'formation', 'suivi detaille', 'suivi avance', 'gps', 'visibilite b2b', 'mis en avant',
    'mise en avant', 'sponsor', 'remise', 'achats en gros', 'badge',
)
# Lignes libres remplacées par les cases du forfait (la case décide, le texte ne peut plus mentir).
SUPERSEDED_PATTERNS = (
    'statist', 'rapport', 'export', 'import', 'alerte', 'promo', 'commission', 'historique', 'approvisionnement',
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
        # Les promotions (prix barré) sont un outil des commerces ; rien n'est construit pour les grossistes.
        return not is_b2b_plan(plan) and bool(getattr(plan, 'can_create_promotions', False))
    if feature == 'exports':
        if is_b2b_plan(plan):
            return bool(plan.can_export_finance_csv)
        return bool(plan.can_export_excel)
    raise ValueError(f'Outil inconnu : {feature}')


def store_has(store, feature):
    return has(store.get_current_plan(), feature) if store is not None else False


def required_message(feature, plan=None):
    label = LABELS.get(feature, feature)
    if feature == 'promotions' and plan is not None and is_b2b_plan(plan):
        return (f"« {label} » n'est pas encore proposé aux grossistes. "
                "Une promotion déjà en place reste affichée.")
    current = f' Votre forfait actuel : {plan.name}.' if plan is not None else ''
    return (f"« {label} » fait partie du forfait Pro.{current} "
            "Passez à Pro dans « Mon forfait » pour l'utiliser.")


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
        lines.append('Alertes de stock faible sur votre téléphone')
    if has(plan, 'promotions') and not is_b2b_plan(plan):
        lines.append('Promotions : prix barré sur vos produits')
    return lines
