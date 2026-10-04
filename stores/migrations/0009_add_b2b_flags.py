from django.db import migrations, models

# 0009_add_b2c_b2b_fields ajoute les memes colonnes : selon l'ordre d'execution, elles
# existent deja. Cette migration (deja appliquee sur des bases existantes) ne les ajoute
# donc en base que si elles manquent, sans changer l'etat des modeles.
FIELDS = {
    'b2b_delivery_delay': lambda: models.PositiveIntegerField(default=24, help_text='Délai de livraison B2B en heures'),
    'b2b_min_order_amount': lambda: models.DecimalField(decimal_places=2, default=0, help_text='Montant minimum de commande B2B en FCFA', max_digits=10),
    'is_b2b': lambda: models.BooleanField(default=False, help_text="Le magasin peut vendre à d'autres magasins (grossiste)"),
    'is_b2c': lambda: models.BooleanField(default=True, help_text='Le magasin peut vendre à des clients finaux'),
}


def add_missing_columns(apps, schema_editor):
    Store = apps.get_model('stores', 'Store')
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        existing = {c.name for c in connection.introspection.get_table_description(cursor, Store._meta.db_table)}
    for name, make_field in FIELDS.items():
        if name in existing:
            continue
        field = make_field()
        field.set_attributes_from_name(name)
        field.model = Store
        schema_editor.add_field(Store, field)


class Migration(migrations.Migration):

    dependencies = [
        ('stores', '0008_add_offers_delivery'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(model_name='store', name=name, field=make_field())
                for name, make_field in FIELDS.items()
            ],
            database_operations=[
                migrations.RunPython(add_missing_columns, migrations.RunPython.noop),
            ],
        ),
    ]
