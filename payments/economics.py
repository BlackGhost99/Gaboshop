"""Simulateur « Combien gagne Gaboshop » : qui paie quoi et qui reçoit quoi sur une commande.

Calcul pur (aucune écriture en base) qui suit les mêmes règles que les commandes réelles :
- paiement en ligne : Gaboshop encaisse tout, retient sa commission et sa part de livraison,
  paie SingPay et la réduction de forfait, puis verse le commerce et le livreur ;
- paiement direct ou espèces : l'argent ne passe pas par Gaboshop, ce qui lui revient est une dette.
"""
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

HUNDRED = Decimal('100')

# champ -> (minimum, maximum)
INPUTS = {
    'basket': (0, 100_000_000),
    'delivery_fee': (0, 1_000_000),
    'commission_percent': (0, 100),
    'courier_share_percent': (0, 100),
    'client_fee_percent': (0, 100),
    'singpay_fee_percent': (0, 100),
    'singpay_payout_fee_percent': (0, 100),
    'forfait_discount_percent': (0, 100),
    'debt_recovery_percent': (0, 100),
    'small_order_fee': (0, 100_000),
    'small_order_threshold': (0, 100_000_000),
}
# Champs facultatifs (écran plus ancien) : valeur par défaut.
OPTIONAL = {'small_order_fee': '0', 'small_order_threshold': '5000'}
FLOWS = ('online', 'direct')


def _franc(value):
    """FCFA sans centimes : franc entier."""
    return Decimal(value).quantize(Decimal('1'), rounding=ROUND_HALF_UP)


def _pct(amount, percent):
    return Decimal(amount) * Decimal(percent) / HUNDRED


def clean_inputs(raw):
    """Valide les valeurs envoyées par l'écran ; lève ValueError avec un message lisible."""
    data = {}
    for name, (lo, hi) in INPUTS.items():
        if (name not in raw or raw[name] in (None, '')) and name in OPTIONAL:
            raw = {**raw, name: OPTIONAL[name]}
        if name not in raw or raw[name] in (None, ''):
            raise ValueError(f'{name} : valeur manquante')
        try:
            value = Decimal(str(raw[name]))
        except (InvalidOperation, ValueError, TypeError):
            raise ValueError(f'{name} : nombre attendu')
        if value < lo or value > hi:
            raise ValueError(f'{name} : entre {lo} et {hi}')
        data[name] = value
    flow = str(raw.get('flow') or 'online')
    if flow not in FLOWS:
        raise ValueError('flow : online ou direct')
    data['flow'] = flow
    data['store_delivers'] = str(raw.get('store_delivers', '')).lower() in ('true', '1', 'on', 'oui')
    data['direct_delivery_margin'] = str(raw.get('direct_delivery_margin', 'true')).lower() in ('true', '1', 'on', 'oui')
    return data


def simulate(p):
    """Répartition d'une commande. ``p`` vient de ``clean_inputs``."""
    basket = _franc(p['basket'])
    delivery = _franc(p['delivery_fee'])
    commission = _franc(_pct(basket, p['commission_percent']))
    store_delivers = p['store_delivers']

    if p['flow'] == 'online':
        # Mêmes règles que api/v1/payments.py : frais client sur produits + livraison.
        client_fee = _franc(_pct(basket + delivery, p['client_fee_percent']))
        forfait = min(delivery, _franc(_pct(delivery, p['forfait_discount_percent'])))
        # Frais « petit panier » : fixe, seulement sous le seuil (les gros paniers sont couverts par les pourcentages).
        small = _franc(p['small_order_fee']) if basket < p['small_order_threshold'] else Decimal('0')
        client_pays = basket + delivery + client_fee + small - forfait
        courier = Decimal('0') if store_delivers else _franc(_pct(delivery, p['courier_share_percent']))
        delivery_margin = Decimal('0') if store_delivers else delivery - courier
        store = basket - commission + (delivery if store_delivers else Decimal('0'))
        singpay = _franc(_pct(client_pays, p['singpay_fee_percent']))
        payouts = _franc(_pct(store + courier, p['singpay_payout_fee_percent']))
        lines = [
            ('commission', 'Commission sur les produits', commission),
            ('delivery_margin', 'Part Gaboshop de la livraison', delivery_margin),
            ('client_fee', 'Frais Mobile Money payés par le client', client_fee),
            ('small_order', 'Frais petit panier', small),
            ('forfait', 'Réduction forfait offerte par Gaboshop', -forfait),
            ('singpay', 'Frais SingPay sur le paiement reçu', -singpay),
            ('payouts', 'Frais SingPay sur les versements', -payouts),
        ]
        gaboshop = sum((amount for _k, _l, amount in lines), Decimal('0'))
        debt = Decimal('0')
    else:
        # Paiement direct : le client paie le commerce et le livreur ; ni frais Mobile Money Gaboshop ni forfait.
        client_pays = basket + delivery
        margin_on = p['direct_delivery_margin'] and not store_delivers
        courier_gets = Decimal('0') if store_delivers else (
            _franc(_pct(delivery, p['courier_share_percent'])) if margin_on else delivery)
        delivery_margin = (delivery - courier_gets) if margin_on else Decimal('0')
        store = basket - commission + (delivery if store_delivers else Decimal('0'))
        courier = courier_gets
        debt = commission + delivery_margin
        recovered = _franc(_pct(debt, p['debt_recovery_percent']))
        lines = [
            ('commission', 'Commission due par le commerce', commission),
            ('delivery_margin', 'Part livraison due à Gaboshop', delivery_margin),
            ('unrecovered', 'Dettes jamais payées (estimation)', recovered - debt),
        ]
        gaboshop = recovered

    return {
        'flow': p['flow'],
        'client_pays': str(client_pays),
        'store_receives': str(store),
        'courier_receives': str(courier),
        'gaboshop': str(gaboshop),
        'gaboshop_percent_of_client': str((gaboshop * HUNDRED / client_pays).quantize(Decimal('0.1')) if client_pays else Decimal('0')),
        'debt_to_gaboshop': str(debt),
        'lines': [{'key': k, 'label': label, 'amount': str(amount)} for k, label, amount in lines],
    }


def small_order_fee(items_total):
    """Frais petit panier réel d'une commande payée en ligne (réglage admin ; 0 si éteint ou panier au-dessus du seuil)."""
    from api.models import SystemSettings
    s = SystemSettings.get_settings()
    fee = _franc(s.small_order_fee or 0)
    if fee <= 0 or Decimal(items_total or 0) >= Decimal(s.small_order_threshold or 0):
        return Decimal('0')
    return fee


def default_inputs():
    """Valeurs de départ : les réglages actuels de l'admin."""
    from api.models import SystemSettings
    s = SystemSettings.get_settings()
    return {
        'basket': '15000',
        'delivery_fee': str(_franc(s.default_delivery_fee or 0)),
        'commission_percent': str(s.commission_global),
        'courier_share_percent': str(s.courier_share_percent),
        'client_fee_percent': str(s.airtel_money_fee),
        'singpay_fee_percent': str(s.singpay_fee_percent),
        'singpay_payout_fee_percent': str(s.singpay_payout_fee_percent),
        'forfait_discount_percent': '0',
        'debt_recovery_percent': '100',
        'small_order_fee': str(_franc(s.small_order_fee or 0)),
        'small_order_threshold': str(_franc(s.small_order_threshold or 0)),
        'flow': 'online',
        'store_delivers': False,
        'direct_delivery_margin': bool(s.direct_delivery_margin),
    }


def real_figures(days=30):
    """Ce qui s'est vraiment passé sur les commandes livrées de la période (montants figés sur les commandes)."""
    from django.db.models import Avg, Count, Sum
    from django.utils import timezone
    from orders.models import Order
    from api.models import SystemSettings

    since = timezone.now() - timedelta(days=days)
    delivered = Order.objects.filter(status='delivered', created_at__gte=since)
    online = delivered.filter(payment_arrangement__flow='platform_online')
    direct = delivered.exclude(payment_arrangement__flow='platform_online').filter(payment_arrangement__isnull=False)
    totals = delivered.aggregate(n=Count('id'), basket=Avg('items_total'), delivery=Avg('delivery_fee'),
                                 commission=Sum('commission_amount'), items=Sum('items_total'))
    online_totals = online.aggregate(n=Count('id'), paid=Sum('total_amount'), client_fee=Sum('operator_fee'))
    singpay_cost = _franc(_pct(online_totals['paid'] or 0, SystemSettings.current('singpay_fee_percent', Decimal('2.5'))))
    items = Decimal(totals['items'] or 0)
    return {
        'days': days,
        'delivered_orders': totals['n'] or 0,
        'online_orders': online_totals['n'] or 0,
        'direct_orders': direct.count(),
        'avg_basket': str(_franc(totals['basket'] or 0)),
        'avg_delivery_fee': str(_franc(totals['delivery'] or 0)),
        'avg_commission_percent': str((Decimal(totals['commission'] or 0) * HUNDRED / items).quantize(Decimal('0.1')) if items else Decimal('0')),
        'commission_total': str(_franc(totals['commission'] or 0)),
        'client_fees_total': str(_franc(online_totals['client_fee'] or 0)),
        'singpay_cost_estimate': str(singpay_cost),
    }
