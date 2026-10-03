from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('stores', '0012_alter_store_service_fee')]
    operations = [migrations.AddField(model_name='store', name='payment_preferences', field=models.JSONField(blank=True, default=dict, help_text='Restrictions et instructions de paiement du commerce'))]
