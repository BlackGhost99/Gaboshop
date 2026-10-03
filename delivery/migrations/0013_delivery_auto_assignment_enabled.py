from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('delivery', '0012_delivery_assignment_flow_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='delivery',
            name='auto_assignment_enabled',
            field=models.BooleanField(default=True, help_text='Auto-assignation active pour cette livraison'),
        ),
    ]
