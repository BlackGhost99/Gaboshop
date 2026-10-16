"""Facture Gaboshop d'une commande (PDF) : tout ce qu'il faut pour régler un souci.

Vendeur, client, adresse, articles avec taille/couleur, montants, mode et références de paiement,
livraison (livreur, code), et comment joindre le support. Générée à la demande, jamais modifiable.
"""
from decimal import Decimal
from io import BytesIO
from base64 import b64encode
from functools import lru_cache
from pathlib import Path

from django.contrib.staticfiles import finders

from django.template.loader import render_to_string
from django.utils import timezone

@lru_cache(maxsize=1)
def _invoice_logo_data_uri():
    """Incorporer le logo directement au PDF sans URL publique ni requête réseau.

    Le PNG est suivi par Git dans orders/static/orders. Le cache évite
    des lectures répétées du fichier pour chaque facture.
    """
    logo = finders.find('orders/gaboshop-invoice-logo.png')
    if not logo:
        return ''
    try:
        data = Path(logo).read_bytes()
    except OSError:
        return ''
    if data[:8] != bytes((137, 80, 78, 71, 13, 10, 26, 10)):
        return ''
    return 'data:image/png;base64,' + b64encode(data).decode('ascii')


METHOD_LABELS = {
    'cash': 'Espèces', 'airtel_money': 'Airtel Money', 'moov_money': 'Moov Money',
    'mobile_money': 'Mobile Money', 'card': 'Carte bancaire', 'singpay': 'Paiement en ligne (SingPay)',
}


def _money(value):
    value = Decimal(value or 0).quantize(Decimal('1'))
    return f"{value:,.0f}".replace(',', ' ') + ' FCFA'


def _local(dt):
    return timezone.localtime(dt).strftime('%d/%m/%Y à %H:%M') if dt else ''


def can_view(user, order):
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser or getattr(user, 'user_type', '') == 'admin':
        return True
    return order.client_id == user.id or order.store.manager_id == user.id


def invoice_context(order):
    from api.models import SystemSettings
    from products.options import describe
    settings = SystemSettings.get_settings()
    store = order.store
    client = order.client

    items = [{
        'name': item.product.name, 'options': describe(item.options), 'quantity': item.quantity,
        'unit_price': _money(item.unit_price), 'subtotal': _money(item.subtotal),
    } for item in order.items.select_related('product')]

    lines = [('Sous-total articles', _money(order.items_total))]
    if order.delivery_requested:
        lines.append(('Livraison' + (f" ({order.vehicle_type})" if order.vehicle_type else ''), _money(order.delivery_fee)))
    for label, value in (('Frais Mobile Money', order.operator_fee), ('Frais petit panier', order.payment_fees),
                         ('Taxes', order.tax_amount)):
        if Decimal(value or 0) > 0:
            lines.append((label, _money(value)))
    discount = order.applied_forfait_discount() if hasattr(order, 'applied_forfait_discount') else 0
    if Decimal(discount or 0) > 0:
        lines.append(('Réduction forfait (offerte par Gaboshop)', '-' + _money(discount)))

    payment = []
    payment_state = 'À confirmer'
    payment_is_paid = False
    arrangement = getattr(order, 'payment_arrangement', None)
    if arrangement is not None:
        payment.append(('Circuit de paiement', arrangement.get_flow_display()))
        payment.append(('Moyen', METHOD_LABELS.get(arrangement.method, arrangement.method)))
        obligations = list(arrangement.obligations.filter(payer='client'))
        for obligation in obligations:
            payment.append((obligation.get_kind_display(), f"{_money(obligation.amount)} — {obligation.get_status_display()}"))
        # Ne jamais faire passer une facture de commande pour un reçu de paiement.
        # Dans les circuits directs, plusieurs obligations distinctes peuvent rester impayées.
        statuses = [o.status for o in obligations if o.amount > 0]
        if statuses:
            if all(s in ('paid', 'waived') for s in statuses):
                payment_state, payment_is_paid = 'Règlement confirmé', True
            elif any(s in ('partially_paid', 'paid') for s in statuses):
                payment_state = 'Partiellement réglé'
            elif all(s in ('refunded', 'partially_refunded', 'cancelled') for s in statuses):
                payment_state = 'Annulé ou remboursé'
            else:
                payment_state = 'En attente de règlement'
    online = getattr(order, 'payment', None)
    if online is not None:
        payment.append(('Paiement en ligne', f"{_money(online.amount)} — {online.get_status_display()}"))
        if online.status == 'success':
            payment_state, payment_is_paid = 'Règlement confirmé', True
        elif online.status == 'refunded':
            payment_state, payment_is_paid = 'Remboursé', False
        elif online.status in ('pending', 'processing'):
            payment_state, payment_is_paid = 'En attente de confirmation', False
        elif online.status in ('failed', 'cancelled'):
            payment_state, payment_is_paid = 'Non réglé', False
        if online.transaction_id:
            payment.append(('Référence transaction', online.transaction_id))
        if online.operator_reference:
            payment.append(('Référence opérateur', online.operator_reference))
        if online.client_phone:
            payment.append(('Numéro payeur', online.client_phone))

    delivery = []
    if order.delivery_requested:
        delivery.append(('Adresse', order.delivery_address))
        delivery.append(('Ville / zone', f"{order.city} — {order.delivery_zone}"))
        delivery.append(('Téléphone de livraison', order.delivery_phone))
        shipment = getattr(order, 'delivery', None)
        if shipment is not None:
            if shipment.tracking_number:
                delivery.append(('N° de suivi', shipment.tracking_number))
            agent = shipment.delivery_agent
            if agent is not None:
                delivery.append(('Livreur', f"{agent.get_full_name() or 'Livreur'} — {agent.phone}"))
            delivery.append(('Statut livraison', shipment.get_status_display()))
    else:
        delivery.append(('Retrait', 'Le client vient chercher sa commande au commerce'))
    if order.delivered_at:
        delivery.append(('Livrée le', _local(order.delivered_at)))

    support = [v for v in (settings.support_phone, settings.support_whatsapp and f"WhatsApp {settings.support_whatsapp}",
                           settings.support_email) if v]
    company_ids = [v for v in (settings.company_legal_form, settings.company_rccm and f"RCCM {settings.company_rccm}",
                               settings.company_nif and f"NIF {settings.company_nif}") if v]
    return {
        'brand': settings.company_trade_name or 'Gaboshop',
        'logo_data_uri': _invoice_logo_data_uri(),
        'company_name': settings.company_name or settings.company_trade_name or 'Gaboshop',
        'company_ids': ' · '.join(company_ids),
        'company_address': ', '.join(v for v in (settings.company_address, settings.company_city) if v),
        'support': ' · '.join(support),
        'number': f"FAC-{order.order_number}",
        'order_number': order.order_number,
        'issued_at': _local(timezone.now()),
        'ordered_at': _local(order.created_at),
        'status': order.get_status_display(),
        'store': {'name': store.name, 'phone': store.phone, 'address': ', '.join(v for v in (store.address, store.city) if v),
                  'category': store.category.name if store.category_id else ''},
        'client': {'name': client.get_full_name() or client.phone, 'phone': client.phone, 'email': client.email},
        'items': items, 'lines': lines, 'total': _money(order.total_amount),
        'payment': payment, 'payment_state': payment_state, 'payment_is_paid': payment_is_paid,
        'delivery_requested': order.delivery_requested,
        'delivery': delivery, 'notes': order.notes,
        'problem': order.client_problem,
    }


def render_invoice_pdf(order):
    from xhtml2pdf import pisa
    html = render_to_string('orders/invoice.html', invoice_context(order))
    buffer = BytesIO()
    result = pisa.CreatePDF(html, dest=buffer, encoding='utf-8')
    if result.err:
        raise RuntimeError('PDF impossible à générer')
    return buffer.getvalue()
