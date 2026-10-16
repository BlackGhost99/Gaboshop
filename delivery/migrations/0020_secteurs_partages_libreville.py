"""Éviter de présenter comme sûrs des rattachements de secteurs partagés.
Ne modifie ni les tarifs ni les zones de prix déjà configurées.
"""
from django.db import migrations

AMBIGUOUS = ('PK10', 'PK11', 'PK12', 'Plaine Orety')

def forward(apps, schema_editor):
    City = apps.get_model('delivery', 'City')
    Neighborhood = apps.get_model('delivery', 'Neighborhood')
    for city in City.objects.filter(name='Libreville', province__name='Estuaire'):
        Neighborhood.objects.filter(city=city, name__in=AMBIGUOUS).update(arrondissement=None)

class Migration(migrations.Migration):
    dependencies = [('delivery', '0019_quartiers_libreville_officiels_2025')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
