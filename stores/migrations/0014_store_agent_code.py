from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('stores', '0013_store_payment_preferences')]
    operations = [
        migrations.AddField(
            model_name='store',
            name='agent_code',
            field=models.CharField(blank=True, default='', help_text='Code agent / disbursement SingPay du commerce pour recevoir ses versements', max_length=100),
        ),
    ]
