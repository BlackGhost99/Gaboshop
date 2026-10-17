# Clés d'intégration des grossistes (option « Accès API » du forfait).

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('b2b', '0008_outils_forfaits_2026_10_16'),
        ('stores', '0023_outils_forfaits_2026_10_16'),
    ]

    operations = [
        migrations.CreateModel(
            name='WholesalerApiKey',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Nom donné par le grossiste (ex. « Logiciel de caisse »)', max_length=80)),
                ('prefix', models.CharField(help_text='Début de la clé, visible dans la liste', max_length=8)),
                ('key_hash', models.CharField(editable=False, help_text='Empreinte SHA-256 de la clé', max_length=64, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('last_used_at', models.DateTimeField(blank=True, null=True)),
                ('revoked_at', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('store', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='api_keys', to='stores.store')),
            ],
            options={
                'verbose_name': 'Clé API grossiste',
                'verbose_name_plural': 'Clés API grossistes',
                'ordering': ['-created_at'],
                'indexes': [models.Index(fields=['store', 'is_active'], name='b2b_apikey_store_active_idx')],
            },
        ),
    ]
