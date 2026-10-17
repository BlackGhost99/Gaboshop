"""Livraison express d'un commerce : ce que voit le commerçant et ce que le serveur accepte quand il règle ses frais.

Règle unique de l'outil : payments/plan_features.py (case « can_offer_express_delivery »).
Prix : le client paie le tarif standard de sa zone, plus le supplément du commerce
(frais express moins frais standard, voir Order.express_supplement).
"""
from decimal import Decimal

from rest_framework import serializers

from payments.plan_features import has, plan_for_sale, required_message


def express_info(store):
    """État de l'outil pour l'écran du commerçant : actif, ou forfait à prendre pour l'obtenir."""
    from orders.models import Order
    plan = store.get_current_plan()
    enabled = has(plan, 'express_delivery')
    info = {
        'enabled': enabled,
        'fee': str(store.delivery_fee_express),
        'standard_fee': str(store.delivery_fee),
        'supplement': str(Order(store=store, delivery_type='express').express_supplement()),
        'upgrade_hint': '',
        'plan_name': '',
    }
    if not enabled:
        target = plan_for_sale(plan, lambda candidate: has(candidate, 'express_delivery'))
        info['upgrade_hint'] = required_message('express_delivery', plan)
        info['plan_name'] = target.name if target is not None else ''
    return info


def check_express_fee_update(store, attrs):
    """Refuse un changement des frais express sans l'outil, ou des frais express inférieurs aux frais standard."""
    if store is None or 'delivery_fee_express' not in attrs:
        return
    plan = store.get_current_plan()
    new = Decimal(attrs['delivery_fee_express'])
    if not has(plan, 'express_delivery'):
        # Renvoyer la valeur inchangée reste permis (formulaire complet).
        if new != Decimal(store.delivery_fee_express):
            raise serializers.ValidationError({'delivery_fee_express': [required_message('express_delivery', plan)]})
        return
    standard = Decimal(attrs.get('delivery_fee', store.delivery_fee))
    if new < standard:
        raise serializers.ValidationError({'delivery_fee_express': [
            f"Les frais express ({int(new)} F) ne peuvent pas être inférieurs à vos frais de livraison standard ({int(standard)} F)."
        ]})
