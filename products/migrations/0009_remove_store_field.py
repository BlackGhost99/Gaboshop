from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0008_populate_storecategory_from_store'),
    ]

    operations = [
        # NOTE: skipping RemoveField('store') here to avoid table rebuild issues on SQLite.
        # The `store` column remains in DB for now. We still enforce store_category non-nullability.
        migrations.AlterField(
            model_name='productcategory',
            name='store_category',
            field=models.ForeignKey(on_delete=models.PROTECT, related_name='product_categories', to='stores.storecategory'),
        ),
    ]
