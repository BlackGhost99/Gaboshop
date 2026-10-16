"""Répartition de Libreville selon loi 020/2025 du 27 juin 2025 (Journal officiel n°72 Ter).
Le Pratique du Gabon complète les noms d'usage mais ne constitue pas une délimitation.
Aucun tarif, zone de livraison, commande ou adresse historique n'est modifié.
Les PK partagés entre plusieurs arrondissements sont distingués par leur côté.
"""
from django.db import migrations

OFFICIAL = {
  1: [
    "Aéroport",
    "Okala Sud",
    "Mikolongo",
    "Lycée Indjendjé Gondjout",
    "Alibandeng",
    "Pierre de Mbigou",
    "Camp de Gaulle",
    "Tahiti",
    "Ambowé",
    "Charbonnages",
    "Cité de la Démocratie",
    "Lac Bleu",
    "Diba-Diba",
    "Ondogo 1 GR",
    "Bel-Air",
    "Lycée Léon Mba",
    "Gué-Gué",
    "Bas de Gué-Gué",
    "Haut de Gué-Gué",
    "Ongongo",
    "Kalikak",
    "Camp des Boys",
    "Derrière la Prison",
    "Palais de Justice",
    "École Normale",
    "Cité Pompidou",
    "Gros-Bouquet I",
    "Gros-Bouquet II",
    "Trois-Quartiers",
    "Batterie IV",
    "Quaben",
    "Louis",
    "Jeanne Ébori",
    "Jeanne et Blanche",
    "Ancienne Sobraga (côté ENS)"
  ],
  2: [
    "Université Omar Bongo",
    "Ancienne RTG",
    "Ancienne Sobraga (côté Multipress)",
    "Saint Nicolas",
    "Pont Deemin",
    "Camp Boirot",
    "Derrière Mbolo",
    "Port-Môle",
    "Vallée Sainte-Marie",
    "Archevêché",
    "Jean-Paul II",
    "Bessieux",
    "Hôtel de Ville",
    "Fonction publique",
    "Cocotiers",
    "Atong Abè",
    "Nkembo Messanza",
    "Nkembo Marché",
    "La Campagne",
    "Sotega",
    "SOCIGA",
    "Avéa",
    "Atsib-Ntsos",
    "IUSO",
    "Cité de la Caisse",
    "Cité Mebiame",
    "Rio Cuvette"
  ],
  3: [
    "Sorbonne",
    "Mont-Bouët",
    "Sainte-Anne",
    "Akémindjogoni",
    "Abénélang",
    "Cinq Palmiers",
    "Carrefour Hassan",
    "Présidence",
    "CHUL",
    "Avenue de Cointet",
    "Derrière l'Hôpital",
    "Montagne Sainte",
    "Petit Paris",
    "La Peyrie",
    "Peyrie Dakar",
    "Akébé-Ville",
    "Nombakélé-Nord",
    "Stade Omnisports",
    "STFO",
    "Venez-Voir",
    "Likouala",
    "Akébé Plaine",
    "Belle-Vue",
    "Belle-Vue 2",
    "Kinguélé I",
    "Kinguélé II",
    "Akébé Frontière",
    "Awendjé Zone B2",
    "Belles Peintures",
    "Dragon",
    "Cosmopark",
    "Rio",
    "PK5",
    "PK6",
    "PK7",
    "PK8 (les 2 écoles)"
  ],
  4: [
    "Ambilambani",
    "Baraka",
    "Carrefour Boulingui",
    "Camp Baraka",
    "Plaine Niger (côté cimetière)",
    "Awendjé II",
    "Poste Centrale",
    "Hollando",
    "BICIG Centre",
    "Waterman",
    "Chambre de Commerce",
    "Saint-Benoît",
    "Nombakélé-Sud",
    "Batavéa",
    "London",
    "Saint-Michel",
    "Toulon",
    "Baraka Mission",
    "Plaine Niger",
    "Quartier Glass"
  ],
  5: [
    "Cité Damas",
    "Bisségué",
    "Beau Séjour",
    "FOPI",
    "Mindoubé",
    "IAI",
    "Golf",
    "Ozangué",
    "Melen ENA",
    "Nzeng-Miang",
    "PK10 (côté droit)",
    "PK11 (côté droit)",
    "PK12 (côté droit)",
    "Bangos",
    "Bizango-Rail",
    "Lalala",
    "Lalala à gauche",
    "Lalala à droite",
    "Lalala Dakar",
    "ACAE",
    "SODUCO",
    "Oloumi",
    "Ozoungué",
    "INJS",
    "Nze Mkre"
  ],
  6: [
    "Ondogo 2",
    "Montalier",
    "Lycée Djoué Dabany",
    "PK9",
    "PK10 (côté gauche)",
    "PK11 (côté gauche)",
    "Derrière l'Hôpital Militaire",
    "Melen",
    "Oveng",
    "Bambouchine",
    "Akougbé",
    "Sibang-Nkol-Ogoum",
    "Sibang Arboretum",
    "Adzébé-Sibang",
    "Marché-bananes",
    "SGA",
    "Nzeng-Ayong"
  ]
}
ALIASES = {
  'Haut de Gué-Gué': 1,
  'Bas de Gué-Gué': 1,
  'Batterie IV': 1,
  'Charbonnages': 1,
  'Alibandeng': 1,
  'Louis': 1,
  'Derrière la Prison': 1,
  'Kalikak': 1,
  'Cocotiers': 2,
  'Sotega': 2,
  'Avéa': 2,
  'Atong Abè': 2,
  'Nkembo': 2,
  'Mont-Bouët': 3,
  'Montagne Sainte': 3,
  'Petit Paris': 3,
  'Venez-Voir': 3,
  'Akébé': 3,
  'Belle-Vue': 3,
  'Kinguélé': 3,
  'Rio': 3,
  'PK5': 3,
  'PK6': 3,
  'PK7': 3,
  'PK8': 3,
  'Quartier Glass': 4,
  'London': 4,
  'Toulon': 4,
  'Plaine Niger': 4,
  'Lalala': 5,
  'Oloumi': 5,
  'Beau Séjour': 5,
  'Nzeng-Ayong': 6,
  'PK9': 6
}

def forward(apps, schema_editor):
    City = apps.get_model('delivery','City')
    Arrondissement = apps.get_model('delivery','Arrondissement')
    Neighborhood = apps.get_model('delivery','Neighborhood')
    for city in City.objects.filter(name='Libreville', province__name='Estuaire'):
        by_number = {a.number:a for a in Arrondissement.objects.filter(city=city)}
        for number,names in OFFICIAL.items():
            arrondissement=by_number.get(int(number))
            if not arrondissement:
                continue
            for name in names:
                quartier,_ = Neighborhood.objects.get_or_create(city=city,name=name,defaults={'arrondissement':arrondissement})
                if quartier.arrondissement_id != arrondissement.id:
                    quartier.arrondissement=arrondissement
                    quartier.save(update_fields=['arrondissement'])
        for name,number in ALIASES.items():
            arrondissement=by_number.get(number)
            if arrondissement:
                Neighborhood.objects.filter(city=city,name=name).exclude(arrondissement=arrondissement).update(arrondissement=arrondissement)
        # Ne pas attribuer arbitrairement les noms génériques partagés :
        # PK10 et PK11 peuvent relever du 5e ou du 6e selon le côté de la route.
        Neighborhood.objects.filter(city=city,name__in=['PK10','PK11']).update(arrondissement=None)

class Migration(migrations.Migration):
    dependencies=[('delivery','0018_quartiers_par_arrondissement_2026_10_16')]
    operations=[migrations.RunPython(forward,migrations.RunPython.noop)]
