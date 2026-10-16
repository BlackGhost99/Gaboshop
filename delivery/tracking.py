"""Suivi en direct d'une livraison, façon Uber/Gozem : où est le commerce, où est le client, où est le livreur.

Le livreur envoie sa position pendant la course ; le client de la commande, le commerce, l'admin et le livreur
lisent la carte. Le client ne voit le livreur que pendant la course, jamais avant ni après.
"""
import math
from datetime import timedelta
from decimal import Decimal, InvalidOperation

from django.utils import timezone

# Course en cours : le livreur a accepté et n'a pas encore livré.
ACTIVE_STATUSES = ('assigned', 'accepted_by_driver', 'accepted', 'picked_up', 'in_delivery', 'in_transit')
CARRYING_STATUSES = ('picked_up', 'in_delivery', 'in_transit')
# Une position plus vieille n'est plus montrée comme « en direct ».
FRESH_FOR = timedelta(minutes=5)
# Vitesse moyenne en ville (moto, embouteillages de Libreville) pour l'estimation d'arrivée.
CITY_SPEED_KMH = 20

# Le Gabon, avec une marge : une position hors de ce cadre est une erreur de GPS.
LAT_RANGE = (Decimal('-4.5'), Decimal('2.8'))
LNG_RANGE = (Decimal('8.0'), Decimal('15.0'))


def parse_point(lat, lng):
    """(lat, lng) en Decimal à 6 décimales, ou ValueError avec un message clair."""
    try:
        lat = Decimal(str(lat)).quantize(Decimal('0.000001'))
        lng = Decimal(str(lng)).quantize(Decimal('0.000001'))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError('Position GPS invalide.')
    if not (LAT_RANGE[0] <= lat <= LAT_RANGE[1] and LNG_RANGE[0] <= lng <= LNG_RANGE[1]):
        raise ValueError('Position GPS hors du Gabon : réactivez la localisation et réessayez.')
    return lat, lng


def distance_km(a, b):
    """Distance à vol d'oiseau (km) entre deux points (lat, lng)."""
    lat1, lng1, lat2, lng2 = map(math.radians, (float(a[0]), float(a[1]), float(b[0]), float(b[1])))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lng2 - lng1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def destination_of(order):
    """Point d'arrivée : la position GPS partagée par le client, sinon sa zone phare, sinon le centre du quartier."""
    if order.delivery_latitude is not None and order.delivery_longitude is not None:
        return (order.delivery_latitude, order.delivery_longitude), 'gps'
    landmark = order.landmark if order.landmark_id else None
    if landmark is not None and landmark.latitude is not None and landmark.longitude is not None:
        return (landmark.latitude, landmark.longitude), 'landmark'
    neighborhood = order.neighborhood if order.neighborhood_id else None
    if neighborhood is not None and neighborhood.latitude is not None and neighborhood.longitude is not None:
        return (neighborhood.latitude, neighborhood.longitude), 'quartier'
    return None, ''


def destination_fields(order):
    """Champs delivery_lat / delivery_lng d'une nouvelle livraison."""
    point, _source = destination_of(order)
    return {'delivery_lat': point[0] if point else None, 'delivery_lng': point[1] if point else None}


def _point(pair):
    return {'lat': float(pair[0]), 'lng': float(pair[1])} if pair else None


def directions_links(point):
    """Liens d'itinéraire gratuits (applications déjà sur le téléphone du livreur)."""
    if not point:
        return {}
    lat, lng = float(point[0]), float(point[1])
    return {
        'google': f'https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode=driving',
        'waze': f'https://waze.com/ul?ll={lat},{lng}&navigate=yes',
    }


def can_read(user, order):
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser or getattr(user, 'user_type', '') == 'admin':
        return True
    if order.client_id == user.id or order.store.manager_id == user.id:
        return True
    delivery = getattr(order, 'delivery', None)
    return bool(delivery and delivery.delivery_agent_id == user.id)


def tracking_payload(order, user):
    """Ce que la carte affiche pour cette commande et cet utilisateur."""
    delivery = getattr(order, 'delivery', None)
    store = order.store
    store_point = (store.latitude, store.longitude) if store.latitude is not None and store.longitude is not None else None
    destination, source = destination_of(order)
    is_client = order.client_id == user.id
    status = delivery.status if delivery else ''
    active = status in ACTIVE_STATUSES

    courier = None
    if delivery and delivery.delivery_agent_id and active:
        agent = delivery.delivery_agent
        point = None
        fresh = False
        if delivery.courier_lat is not None and delivery.courier_lng is not None:
            point = (delivery.courier_lat, delivery.courier_lng)
            fresh = bool(delivery.courier_location_at and timezone.now() - delivery.courier_location_at <= FRESH_FOR)
        courier = {
            'name': (agent.first_name or '').strip() or 'Votre livreur',
            'phone': agent.phone,
            'position': _point(point),
            'updated_at': delivery.courier_location_at.isoformat() if delivery.courier_location_at else None,
            'live': fresh,
        }

    # Prochaine étape du livreur : le commerce tant que le colis n'est pas récupéré, puis le client.
    carrying = status in CARRYING_STATUSES
    target = destination if carrying else (store_point or destination)
    eta = remaining = None
    if courier and courier['position'] and target:
        remaining = distance_km((courier['position']['lat'], courier['position']['lng']), target)
        if carrying:
            eta = max(1, round(remaining * 1.3 / CITY_SPEED_KMH * 60))  # 1,3 : les routes ne sont pas droites

    data = {
        'order_id': order.id, 'order_number': order.order_number,
        'status': status,
        'status_label': delivery.get_status_display() if delivery else '',
        'active': active, 'carrying': carrying,
        'store': {'name': store.name, 'address': store.address, 'position': _point(store_point)},
        'destination': {'address': order.delivery_address, 'position': _point(destination), 'source': source},
        'courier': courier,
        'remaining_km': round(remaining, 1) if remaining is not None else None,
        'eta_minutes': eta,
        'directions': directions_links(target),
    }
    if not is_client:
        data['client'] = {'phone': order.delivery_phone}
    return data


def record_courier_position(delivery, lat, lng):
    """Enregistre la position du livreur (refus clair si la course n'est pas en cours)."""
    if delivery.status not in ACTIVE_STATUSES:
        raise ValueError("Aucune course en cours pour cette livraison : la position n'est pas partagée.")
    lat, lng = parse_point(lat, lng)
    delivery.courier_lat, delivery.courier_lng, delivery.courier_location_at = lat, lng, timezone.now()
    delivery.save(update_fields=['courier_lat', 'courier_lng', 'courier_location_at', 'updated_at'])
    return delivery
