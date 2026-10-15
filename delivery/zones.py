"""Zones de livraison choisies par le client : une seule règle pour l'affichage et la commande."""
from .models import DeliveryZone


def active_zones(city):
    return DeliveryZone.objects.filter(is_active=True, city__iexact=(city or '').strip()).order_by('name')


def resolve_zone(city, zone):
    """Nom exact de la zone choisie. Quand la ville a des zones, il faut en choisir une : une faute de frappe
    ferait sinon payer le prix du commerce au lieu du prix de la zone affiché. Sans zone dans la ville, texte libre."""
    zones = active_zones(city)
    if not zones.exists():
        return (zone or '').strip()
    match = zones.filter(name__iexact=(zone or '').strip()).first()
    if match is None:
        names = ', '.join(zones.values_list('name', flat=True))
        raise ValueError(f'Choisissez votre zone dans la liste : {names}.')
    return match.name
