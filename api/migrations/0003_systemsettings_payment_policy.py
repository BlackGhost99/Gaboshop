from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('api', '0002_aiactionlog')]
    operations = [migrations.AddField(model_name='systemsettings', name='payment_policy', field=models.JSONField(blank=True, default=dict, help_text='Circuits et plafonds de paiement actifs'))]
