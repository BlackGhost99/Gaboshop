from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0009_remove_store_field'),
    ]

    operations = [
        migrations.AlterField(
            model_name='productcategory',
            name='store',
            field=models.ForeignKey(null=True, blank=True, on_delete=models.CASCADE, related_name='product_categories', to='stores.store'),
        ),
    ]
