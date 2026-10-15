"""Forfaits clients : abonnement mensuel payé par Mobile Money, qui réduit les frais de livraison.

La réduction ne s'applique qu'aux commandes payées en ligne : Gaboshop encaisse alors la livraison
et paie le livreur au prix plein, la différence est offerte par Gaboshop. Payée en espèces au livreur,
une livraison ne peut pas être réduite (le livreur toucherait moins).
"""
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone

from .models import ClientForfait, Forfait
from .utils import subscription_days


def active_forfait(user):
    """Forfait en cours du client, ou None."""
    if not getattr(user, 'is_authenticated', False):
        return None
    current = ClientForfait.objects.filter(user=user).select_related('forfait').first()
    if current and current.forfait and current.is_active():
        return current
    return None


def delivery_discount(user, delivery_fee):
    """Réduction (en FCFA, arrondie au franc) offerte sur les frais de livraison d'une commande payée en ligne."""
    current = active_forfait(user)
    rate = Decimal(str(current.forfait.discount_rate or 0)) if current else Decimal('0')
    if rate <= 0 or not delivery_fee:
        return Decimal('0')
    rate = min(rate, Decimal('100'))
    return (Decimal(delivery_fee) * rate / Decimal('100')).quantize(Decimal('1'), rounding=ROUND_HALF_UP)


def activate_forfait(user, forfait):
    """Active (ou prolonge) le forfait du client pour une période. Un forfait encore actif est prolongé."""
    now = timezone.now()
    current = ClientForfait.objects.filter(user=user).first()
    period = timedelta(days=subscription_days())
    if current and current.forfait_id == forfait.id and current.is_active():
        current.expiration_date = current.expiration_date + period
    else:
        current = current or ClientForfait(user=user)
        current.forfait = forfait
        current.expiration_date = now + period
    current.status = 'active'
    current.auto_renew = False
    current.save()
    return current


def forfait_payload(forfait):
    return {
        'id': forfait.id, 'name': forfait.name, 'description': forfait.description,
        'monthly_price': str(forfait.monthly_price), 'discount_rate': float(forfait.discount_rate or 0),
        'days': subscription_days(),
    }


def catalog():
    return [forfait_payload(f) for f in Forfait.objects.filter(is_active=True).order_by('monthly_price')]
