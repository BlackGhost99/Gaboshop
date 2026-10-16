"""Les types de commerce « grande surface » (hypermarché, supermarché, mall…) vendent de tout."""
import re
import unicodedata

from django.db import migrations

KEYWORDS = ('HYPER', 'SUPERMARCHE', 'SUPER MARCHE', 'SUPERETTE', 'MALL', 'GRANDE SURFACE', 'CENTRE COMMERCIAL',
            'MAGASIN GENERAL', 'BAZAR')


def _key(name):
    text = unicodedata.normalize('NFKD', str(name or '')).encode('ascii', 'ignore').decode().upper()
    return re.sub(r'[^A-Z0-9]+', ' ', text).strip()


def apply(apps, schema_editor):
    StoreCategory = apps.get_model('stores', 'StoreCategory')
    for category in StoreCategory.objects.all():
        if any(k in _key(category.name) for k in KEYWORDS):
            category.sells_everything = True
            category.save(update_fields=['sells_everything'])


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0021_grande_surface_vend_de_tout'),
    ]

    operations = [
        migrations.RunPython(apply, migrations.RunPython.noop),
    ]
