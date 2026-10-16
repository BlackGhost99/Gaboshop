from django.db import migrations


def forward(apps, schema_editor):
    from delivery.geo_data import link_and_landmarks
    link_and_landmarks(apps.get_model('delivery', 'City'), apps.get_model('delivery', 'Arrondissement'),
                       apps.get_model('delivery', 'Neighborhood'), apps.get_model('delivery', 'Landmark'))


class Migration(migrations.Migration):
    dependencies = [('delivery', '0017_zones_phares')]
    operations = [migrations.RunPython(forward, migrations.RunPython.noop)]
