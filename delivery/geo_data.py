"""Référentiel de départ : 9 provinces du Gabon, leurs principales villes, les arrondissements des communes
du Grand Libreville et une première liste de quartiers. L'admin corrige et complète dans Admin › Livraison › Adresses.

Seule Libreville est ouverte aux livraisons au départ ; les autres villes s'affichent « Bientôt disponible ».
Les quartiers sont créés sans arrondissement : leur rattachement se vérifie sur place puis se règle dans l'admin.
"""

PROVINCES = [
    ('Estuaire', ['Libreville', 'Akanda', 'Owendo', 'Ntoum', 'Kango', 'Cocobeach']),
    ('Haut-Ogooué', ['Franceville', 'Moanda', 'Mounana', 'Okondja', 'Léconi', 'Akiéni', 'Bongoville', 'Bakoumba']),
    ('Moyen-Ogooué', ['Lambaréné', 'Ndjolé']),
    ('Ngounié', ['Mouila', 'Ndendé', 'Fougamou', 'Lébamba', 'Mbigou', 'Mimongo', 'Mandji']),
    ('Nyanga', ['Tchibanga', 'Mayumba', 'Moabi']),
    ('Ogooué-Ivindo', ['Makokou', 'Booué', 'Ovan', 'Mékambo']),
    ('Ogooué-Lolo', ['Koulamoutou', 'Lastoursville', 'Pana', 'Iboundji']),
    ('Ogooué-Maritime', ['Port-Gentil', 'Omboué', 'Gamba']),
    ('Woleu-Ntem', ['Oyem', 'Bitam', 'Mitzic', 'Minvoul', 'Médouneu']),
]

OPEN_CITIES = ['Libreville']

ARRONDISSEMENTS = {'Libreville': 6, 'Akanda': 2, 'Owendo': 2, 'Ntoum': 3}

NEIGHBORHOODS = {
    'Libreville': [
        'Centre-ville', 'Louis', 'Quartier Glass', 'Batterie IV', 'Haut de Gué-Gué', 'Bas de Gué-Gué',
        'Montagne Sainte', 'Mont-Bouët', 'Nombakélé', 'Akébé', 'Belle-Vue', 'Lalala', 'Nzeng-Ayong',
        'Nkembo', 'Cocotiers', 'Plaine Orety', 'Sotega', 'Charbonnages', 'Alibandeng', 'Kalikak', 'Avéa',
        'London', 'Derrière la Prison', 'Atong Abè', 'Awendjé', 'Kinguélé', 'Venez-Voir', 'Rio',
        'Beau Séjour', 'Petit Paris', 'Toulon', 'Oloumi', 'Ancienne Sobraga',
        'PK5', 'PK6', 'PK7', 'PK8', 'PK9', 'PK10', 'PK11', 'PK12',
    ],
    'Akanda': ['Angondjé', 'Okala', 'Cap Estérias', 'Malibé'],
    'Owendo': ['Alénakiri', 'Akournam'],
}


def ordinal(n):
    return '1er arrondissement' if n == 1 else f'{n}e arrondissement'


def seed(Province, City, Arrondissement, Neighborhood):
    """Ajoute ce qui manque, sans rien écraser de ce que l'admin a déjà réglé."""
    for p_order, (province_name, cities) in enumerate(PROVINCES, start=1):
        province, _ = Province.objects.get_or_create(name=province_name, defaults={'order': p_order})
        for c_order, city_name in enumerate(cities, start=1):
            city, created = City.objects.get_or_create(
                province=province, name=city_name,
                defaults={'order': c_order, 'is_open': city_name in OPEN_CITIES},
            )
            for n in range(1, ARRONDISSEMENTS.get(city_name, 0) + 1):
                Arrondissement.objects.get_or_create(city=city, name=ordinal(n), defaults={'number': n})
            for name in NEIGHBORHOODS.get(city_name, []):
                Neighborhood.objects.get_or_create(city=city, name=name)
