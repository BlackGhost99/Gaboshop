"""Référentiel de départ (9 provinces, villes, arrondissements du Grand Libreville, quartiers de Libreville).
Seule Libreville est ouverte. Une zone de prix existante qui porte le nom d'un quartier y est rattachée."""
from django.db import migrations


def apply(apps, schema_editor):
    from delivery.geo_data import seed
    Province = apps.get_model('delivery', 'Province')
    City = apps.get_model('delivery', 'City')
    Arrondissement = apps.get_model('delivery', 'Arrondissement')
    Neighborhood = apps.get_model('delivery', 'Neighborhood')
    DeliveryZone = apps.get_model('delivery', 'DeliveryZone')
    seed(Province, City, Arrondissement, Neighborhood)
    for zone in DeliveryZone.objects.all():
        Neighborhood.objects.filter(city__name__iexact=zone.city, name__iexact=zone.name, zone__isnull=True).update(zone=zone)


class Migration(migrations.Migration):

    dependencies = [
        ('delivery', '0015_adresses_quartiers'),
    ]

    operations = [
        migrations.RunPython(apply, migrations.RunPython.noop),
    ]
