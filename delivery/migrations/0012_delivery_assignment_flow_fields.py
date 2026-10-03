from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delivery', '0011_vehicle_type_size_bounds'),
    ]

    operations = [
        migrations.AlterField(
            model_name='delivery',
            name='assignment_timeout_minutes',
            field=models.PositiveIntegerField(default=10, help_text='Timeout pour acceptation livreur (minutes)'),
        ),
        migrations.AddField(
            model_name='delivery',
            name='assignment_started_at',
            field=models.DateTimeField(blank=True, help_text='Debut assignation automatique', null=True),
        ),
        migrations.AddField(
            model_name='delivery',
            name='assignment_round',
            field=models.PositiveIntegerField(default=0, help_text="Nombre d'assignations successives"),
        ),
        migrations.AddField(
            model_name='delivery',
            name='assignment_attempts',
            field=models.JSONField(blank=True, default=list, help_text='IDs livreurs deja sollicites'),
        ),
        migrations.AddField(
            model_name='delivery',
            name='is_open_to_all',
            field=models.BooleanField(default=False, help_text='Visible a tous les livreurs'),
        ),
        migrations.AddField(
            model_name='delivery',
            name='opened_at',
            field=models.DateTimeField(blank=True, help_text='Date ouverture globale', null=True),
        ),
    ]
