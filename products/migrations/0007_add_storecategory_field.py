from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0006_remove_productcategorytemplate'),
        ('stores', '0007_store_store_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='productcategory',
            name='store_category',
            field=models.ForeignKey(null=True, blank=True, on_delete=models.PROTECT, related_name='product_categories', to='stores.storecategory'),
        ),
    ]
