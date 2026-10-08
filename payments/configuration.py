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


def platform_online_ready():
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


def available_payment_options(store, delivery_requested=True):
    policy = get_payment_policy(store)
    labels = {
        'direct_split': 'Payer le commerce directement', 'store_collects_all': 'Tout payer au commerce',
        'courier_cash': 'Espèces au livreur à la livraison', 'platform_online': 'Paiement en ligne Gaboshop (Mobile Money)',
    }
    options = []
    ordered_flows = [policy['default_flow']] + [flow for flow in policy['enabled_flows'] if flow != policy['default_flow']]
    # Le paiement en ligne (Mobile Money via Gaboshop) est proposé en premier quand il est disponible.
    if 'platform_online' in ordered_flows:
        ordered_flows.remove('platform_online')
        ordered_flows.insert(0, 'platform_online')
    for flow in ordered_flows:
        for method in policy['enabled_methods']:
            if flow == 'courier_cash' and (method != 'cash' or not delivery_requested):
                continue
            if flow == 'platform_online' and (method not in ('airtel_money', 'moov_money') or not platform_online_ready()):
                continue
            instructions = policy.get('instructions', {}).get(method, '')
            if flow != 'platform_online' and method != 'cash' and not instructions:
                continue
            options.append({'flow': flow, 'method': method, 'label': labels[flow], 'instructions': instructions})
    return policy, options
