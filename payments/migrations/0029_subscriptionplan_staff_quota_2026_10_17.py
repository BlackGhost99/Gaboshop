"""Quotas employés paramétrables par forfait B2C, sans modifier les plans existants."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('payments', '0028_outils_pro_actives_2026_10_16'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscriptionplan',
            name='can_manage_staff',
            field=models.BooleanField(
                default=False,
                help_text='Autorise le gérant à créer et gérer des accès employés (B2C)',
            ),
        ),
        migrations.AddField(
            model_name='subscriptionplan',
            name='max_staff_accounts',
            field=models.PositiveIntegerField(
                default=0,
                help_text='Nombre maximal de comptes employés actifs (hors gérant). 0 = aucun ; quota entier, jamais illimité par accident.',
            ),
        ),
    ]
