"""Taux de commission par catégorie de produits donnés par le propriétaire (15 oct. 2026).

Une catégorie générale qui existe déjà (même nom, sans tenir compte des accents ni des majuscules) prend le
nouveau taux ; une catégorie absente est créée dans le type de commerce qui lui correspond. B2B grossiste :
taux de base des commandes entre commerces (réglage admin). Les commandes passées gardent leur commission.
"""
import re
import unicodedata
from decimal import Decimal

from django.db import migrations

# nom de la catégorie de produits -> (taux %, type de commerce où la créer si elle manque)
RATES = [
    ('ALIMENTAIRE ESSENTIEL', '2', 'ALIMENTATION & BOISSONS'),
    ('ALIMENTAIRE GÉNÉRAL', '3', 'ALIMENTATION & BOISSONS'),
    ('BOISSONS', '3', 'ALIMENTATION & BOISSONS'),
    ('BÉBÉ', '3', 'ENFANTS & PUÉRICULTURE'),
    ('HYGIÈNE / ENTRETIEN', '4', 'MAISON & DÉCORATION'),
    ('MAISON', '5', 'MAISON & DÉCORATION'),
    ('ÉLECTROMÉNAGER', '4', 'ÉLECTRONIQUE & INFORMATIQUE'),
    ('TÉLÉPHONE / INFORMATIQUE', '3', 'ÉLECTRONIQUE & INFORMATIQUE'),
    ('ACCESSOIRES ÉLECTRONIQUES', '6', 'ÉLECTRONIQUE & INFORMATIQUE'),
    ('MODE', '7', 'MODE & TEXTILE'),
    ('CHAUSSURES', '6', 'MODE & TEXTILE'),
    ('BEAUTÉ / COSMÉTIQUE', '6', 'BEAUTÉ & SANTÉ'),
    ('PARFUM / PREMIUM', '7', 'BEAUTÉ & SANTÉ'),
    ('ACCESSOIRES / BIJOUX', '8', 'MODE & TEXTILE'),
    ('AUTO / PIÈCES', '5', 'AUTO & PIÈCES'),
    ('JOUETS', '5', 'ENFANTS & PUÉRICULTURE'),
    ('RESTAURATION', '8', 'RESTAURATION'),
    ('LUXE / PREMIUM', '8', 'LUXE & PREMIUM'),
]
B2B_RATE = Decimal('3')


def _key(name):
    text = unicodedata.normalize('NFKD', str(name or '')).encode('ascii', 'ignore').decode().upper()
    return re.sub(r'[^A-Z0-9]+', ' ', text).strip()


def apply_rates(apps, schema_editor):
    ProductCategory = apps.get_model('products', 'ProductCategory')
    StoreCategory = apps.get_model('stores', 'StoreCategory')
    SystemSettings = apps.get_model('api', 'SystemSettings')

    store_types = {_key(sc.name): sc for sc in StoreCategory.objects.all()}
    existing = {}
    for category in ProductCategory.objects.filter(store__isnull=True):
        existing.setdefault(_key(category.name), []).append(category)

    for order, (name, rate, store_type) in enumerate(RATES, start=1):
        rate = Decimal(rate)
        matches = existing.get(_key(name))
        if matches:
            for category in matches:
                category.commission_rate = rate
                category.save(update_fields=['commission_rate'])
            continue
        parent = store_types.get(_key(store_type))
        if parent is None:
            parent = StoreCategory.objects.create(name=store_type, is_active=True)
            store_types[_key(store_type)] = parent
        ProductCategory.objects.create(store_category=parent, name=name, commission_rate=rate, order=order)

    settings, _created = SystemSettings.objects.get_or_create(pk=1)  # même ligne que SystemSettings.get_settings()
    settings.b2b_commission_rate = B2B_RATE
    settings.save(update_fields=['b2b_commission_rate'])


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0020_produit_retire_par_admin'),
        ('stores', '0020_store_trust'),
        ('api', '0010_small_order_fee'),
    ]

    operations = [
        migrations.RunPython(apply_rates, migrations.RunPython.noop),
    ]
