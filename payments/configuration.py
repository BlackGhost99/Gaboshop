from copy import deepcopy
from decimal import Decimal, InvalidOperation

from django.conf import settings as django_settings
from rest_framework.exceptions import ValidationError

FLOWS = ('direct_split', 'store_collects_all', 'courier_cash', 'platform_online')
METHODS = ('cash', 'airtel_money', 'moov_money', 'bank_transfer')

DEFAULT_PAYMENT_POLICY = {
    'enabled_flows': ['direct_split', 'store_collects_all', 'courier_cash'],
    'default_flow': 'direct_split',
    'enabled_methods': ['cash', 'airtel_money', 'moov_money', 'bank_transfer'],
    'payment_timing': 'on_delivery',
    'commission_settlement_days': 7,
    'merchant_debt_limit': '100000',
    'courier_cash_limit': '100000',
}


def payments_simulated():
    """Site de test : paiements en ligne simulés (faux SingPay), jamais avec PAYMENTS_DISABLED."""
    return bool(getattr(django_settings, 'PAYMENTS_SIMULATED', False)) \
        and not getattr(django_settings, 'PAYMENTS_DISABLED', False)


def transfers_enabled():
    """Versements automatiques aux commerces et livreurs (toujours simulés sur le site de test)."""
    return payments_simulated() or bool(getattr(django_settings, 'SINGPAY_ENABLE_TRANSFER', False))


def platform_online_ready():
    if getattr(django_settings, 'PAYMENTS_DISABLED', False):
        return False
    if payments_simulated():
        return True
    required = ('SINGPAY_CLIENT_ID', 'SINGPAY_CLIENT_SECRET', 'SINGPAY_WALLET_ID')
    return all(bool(getattr(django_settings, key, '')) for key in required)


def _money(value, field):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError({field: 'Montant invalide.'})
    if result < 0:
        raise ValidationError({field: 'Le montant doit être positif ou nul.'})
    return str(result.quantize(Decimal('0.01')))


def validate_payment_policy(value):
    policy = {**deepcopy(DEFAULT_PAYMENT_POLICY), **(value or {})}
    flows = list(dict.fromkeys(policy.get('enabled_flows') or []))
    methods = list(dict.fromkeys(policy.get('enabled_methods') or []))
    if getattr(django_settings, 'PAYMENTS_DISABLED', False) and 'platform_online' in flows:
        # Site de test sans paiement : le circuit en ligne est retiré au lieu de bloquer tous les réglages.
        flows = [flow for flow in flows if flow != 'platform_online'] or list(DEFAULT_PAYMENT_POLICY['enabled_flows'])
        if policy.get('default_flow') not in flows:
            policy['default_flow'] = flows[0]
    if not flows or any(flow not in FLOWS for flow in flows):
        raise ValidationError({'enabled_flows': 'Activez au moins un circuit connu.'})
    if policy.get('default_flow') not in flows:
        raise ValidationError({'default_flow': 'Le circuit par défaut doit être actif.'})
    if not methods or any(method not in METHODS for method in methods):
        raise ValidationError({'enabled_methods': 'Activez au moins un moyen connu.'})
    if 'courier_cash' in flows and 'cash' not in methods:
        raise ValidationError({'enabled_methods': 'La collecte livreur nécessite les espèces.'})
    if 'platform_online' in flows and not platform_online_ready():
        raise ValidationError({'enabled_flows': 'Le paiement Gaboshop exige un compte marchand SingPay configuré.'})
    if policy.get('payment_timing') not in ('before_dispatch', 'on_delivery'):
        raise ValidationError({'payment_timing': 'Valeur invalide.'})
    try:
        days = int(policy.get('commission_settlement_days'))
        if days < 1:
            raise ValueError
    except (TypeError, ValueError):
        raise ValidationError({'commission_settlement_days': 'Entier supérieur ou égal à 1 requis.'})
    policy.update(enabled_flows=flows, enabled_methods=methods, commission_settlement_days=days)
    policy['merchant_debt_limit'] = _money(policy.get('merchant_debt_limit'), 'merchant_debt_limit')
    policy['courier_cash_limit'] = _money(policy.get('courier_cash_limit'), 'courier_cash_limit')
    return policy


def validate_store_preferences(value, global_policy=None):
    prefs = value or {}
    allowed = {'enabled_flows', 'enabled_methods', 'default_flow', 'instructions'}
    unknown = set(prefs) - allowed
    if unknown:
        raise ValidationError({'payment_preferences': f'Clés inconnues: {", ".join(sorted(unknown))}'})
    global_policy = global_policy or get_payment_policy()
    result = deepcopy(prefs)
    for key in ('enabled_flows', 'enabled_methods'):
        if key in result:
            invalid = set(result[key]) - set(global_policy[key])
            if invalid:
                raise ValidationError({key: 'Un commerce ne peut pas activer une option désactivée globalement.'})
    instructions = result.get('instructions', {})
    if not isinstance(instructions, dict):
        raise ValidationError({'instructions': 'Objet attendu.'})
    for method, text in instructions.items():
        if method not in METHODS or not isinstance(text, str) or len(text) > 200:
            raise ValidationError({'instructions': 'Indiquez un texte court (200 caractères maximum) par moyen de paiement.'})
    return result


def get_payment_policy(store=None):
    from api.models import SystemSettings
    policy = validate_payment_policy(SystemSettings.get_settings().payment_policy or DEFAULT_PAYMENT_POLICY)
    if not store or not store.payment_preferences:
        return policy
    prefs = validate_store_preferences(store.payment_preferences, policy)
    merged = deepcopy(policy)
    for key in ('enabled_flows', 'enabled_methods'):
        if key in prefs:
            merged[key] = [x for x in policy[key] if x in prefs[key]]
    if prefs.get('default_flow') in merged['enabled_flows']:
        merged['default_flow'] = prefs['default_flow']
    elif merged['default_flow'] not in merged['enabled_flows'] and merged['enabled_flows']:
        merged['default_flow'] = merged['enabled_flows'][0]
    merged['instructions'] = prefs.get('instructions', {})
    return merged


ONLINE_METHODS = ('airtel_money', 'moov_money')


def available_payment_options(store, delivery_requested=True, b2b=False, user=None):
    policy, options = _available_payment_options(store, delivery_requested, b2b)
    # Client dont les livraisons en espèces échouent : le Gardien anti-fraude bloque les espèces.
    if user is not None and not b2b:
        from core import guardian
        if guardian.cash_blocked(user):
            options = [o for o in options if o['method'] != 'cash' and o['flow'] != 'courier_cash']
    if payments_simulated():
        # Site de test : le client est prévenu que rien n'est vraiment débité.
        options = [{**o, 'simulated': True} if o['flow'] == 'platform_online' else o for o in options]
    return policy, options


def _available_payment_options(store, delivery_requested=True, b2b=False):
    """Proposer ensemble les circuits directs et SingPay quand ils sont autorisés.

    La politique globale et les préférences du commerce filtrent toujours les circuits.
    Le paiement en ligne n'est jamais proposé sans configuration prête ; les méthodes
    manuelles non-espèces exigent des instructions de paiement du commerce.
    """
    policy = get_payment_policy(store)
    labels = {
        'direct_split': 'Payer le commerce directement',
        'store_collects_all': 'Tout payer au commerce',
        'courier_cash': 'Espèces au livreur à la livraison',
    }
    options = []
    ordered_flows = [policy['default_flow']] + [
        flow for flow in policy['enabled_flows'] if flow != policy['default_flow']
    ]
    for flow in ordered_flows:
        if flow == 'platform_online':
            if not platform_online_ready():
                continue
            # Ne pas forcer Airtel/Moov si l'administrateur les a désactivés.
            for method in ONLINE_METHODS:
                if method not in policy['enabled_methods']:
                    continue
                options.append({
                    'flow': flow, 'method': method, 'delivery_by': 'gaboshop',
                    'label': 'Paiement en ligne Gaboshop', 'instructions': '',
                })
                if not b2b and delivery_requested and getattr(store, 'offers_delivery', False):
                    options.append({
                        'flow': flow, 'method': method, 'delivery_by': 'store',
                        'label': 'Tout au commerce (il livre lui-même)', 'instructions': '',
                    })
            continue

        for method in policy['enabled_methods']:
            # Pilote B2C : jamais d'espèces encaissées par un livreur Gaboshop.
            # Si la boutique livre elle-même, son livreur encaisse pour son compte,
            # via store_collects_all, et non via le grand livre d'un livreur Gaboshop.
            if not b2b and flow == 'courier_cash':
                continue
            if flow == 'courier_cash' and (method != 'cash' or not delivery_requested):
                continue
            if not b2b and method == 'cash' and delivery_requested:
                if flow != 'store_collects_all' or not store.offers_delivery:
                    continue
            instructions = policy.get('instructions', {}).get(method, '')
            if method != 'cash' and not instructions:
                continue
            label = labels[flow]
            if (not b2b and flow == 'store_collects_all'
                    and method == 'cash' and delivery_requested and store.offers_delivery):
                label = 'Espèces à la livraison — livreur de la boutique'
            options.append({
                'flow': flow, 'method': method, 'label': label,
                'instructions': instructions,
            })
    return policy, options


def matching_option(options, flow, method, delivery_by=''):
    """L'option choisie par le client, ou None. Pour le paiement en ligne, ``delivery_by`` distingue
    « livreur Gaboshop » (par défaut) et « le commerce livre lui-même »."""
    for option in options:
        if option['flow'] != flow or option['method'] != method:
            continue
        if flow == 'platform_online' and option.get('delivery_by') != (delivery_by or 'gaboshop'):
            continue
        return option
    return None
