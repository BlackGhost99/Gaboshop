from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0009_update_gps_precision"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="singpay_disbursement_id",
            field=models.CharField(
                blank=True,
                help_text="ID de disbursement SingPay du livreur (utilise pour /transfer)",
                max_length=120,
            ),
        ),
    ]

