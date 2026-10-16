"""Zones de livraison choisies par le client : une seule règle pour l'affichage et la commande."""
from .models import City, DeliveryZone, Neighborhood


def active_zones(city):
    return DeliveryZone.objects.filter(is_active=True, city__iexact=(city or '').strip()).order_by('name')


def city_neighborhoods(city):
    return Neighborhood.objects.filter(is_active=True, city__is_active=True, city__name__iexact=(city or '').strip())


def open_cities_sentence():
    names = list(City.objects.filter(is_active=True, is_open=True).values_list('name', flat=True))
    if not names:
        return ''
    listed = names[0] if len(names) == 1 else ', '.join(names[:-1]) + ' et ' + names[-1]
    return f"Nous livrons actuellement à {listed}."


def resolve_neighborhood(neighborhood_id):
    """Le quartier choisi dans la liste ; erreur claire s'il n'existe pas ou si la ville n'est pas desservie."""
    try:
        neighborhood = Neighborhood.objects.select_related('city', 'arrondissement', 'zone').get(
            pk=int(neighborhood_id), is_active=True, city__is_active=True)
    except (Neighborhood.DoesNotExist, TypeError, ValueError):
        raise ValueError('Quartier introuvable : choisissez-le dans la liste.')
    if not neighborhood.city.is_open:
        raise ValueError(f"Gaboshop ne livre pas encore à {neighborhood.city.name}. {open_cities_sentence()}".strip())
    return neighborhood


def zone_name_for(neighborhood):
    """Nom utilisé pour le prix : la zone de prix du quartier, sinon le nom du quartier (prix du commerce)."""
    if neighborhood.zone_id and neighborhood.zone.is_active:
        return neighborhood.zone.name
    return neighborhood.name


def resolve_zone(city, zone):
    """Nom exact de la zone choisie. Quand la ville a des zones, il faut en choisir une : une faute de frappe
    ferait sinon payer le prix du commerce au lieu du prix de la zone affiché. Sans zone dans la ville, texte libre.
    Un nom de quartier connu (ancienne application) donne la zone de prix de ce quartier."""
    typed = (zone or '').strip()
    neighborhood = city_neighborhoods(city).select_related('zone').filter(name__iexact=typed).first() if typed else None
    if neighborhood is not None:
        return zone_name_for(neighborhood)
    zones = active_zones(city)
    if not zones.exists():
        if typed or not city_neighborhoods(city).exists():
            return typed
        raise ValueError('Choisissez votre quartier dans la liste.')
    match = zones.filter(name__iexact=typed).first()
    if match is None:
        names = ', '.join(zones.values_list('name', flat=True))
        raise ValueError(f'Choisissez votre zone dans la liste : {names}.')
    return match.name


def geo_tree():
    """Tout le référentiel en une réponse (petit : quelques centaines de lignes), filtré côté écran."""
    from .models import Arrondissement, Province
    provinces = list(Province.objects.filter(is_active=True).values('id', 'name'))
    cities = list(City.objects.filter(is_active=True, province__is_active=True)
                  .values('id', 'name', 'province_id', 'is_open'))
    arrondissements = list(Arrondissement.objects.filter(is_active=True, city__is_active=True)
                           .values('id', 'name', 'city_id', 'number'))
    neighborhoods = []
    for n in Neighborhood.objects.filter(is_active=True, city__is_active=True).select_related('zone'):
        neighborhoods.append({
            'id': n.id, 'name': n.name, 'city_id': n.city_id, 'arrondissement_id': n.arrondissement_id,
            'zone': n.zone.name if n.zone_id and n.zone.is_active else None,
        })
    return {'provinces': provinces, 'cities': cities, 'arrondissements': arrondissements,
            'neighborhoods': neighborhoods, 'message': open_cities_sentence()}
