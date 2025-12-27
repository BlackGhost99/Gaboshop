from django.db import migrations


def forwards(apps, schema_editor):
    ProductCategoryTemplate = apps.get_model('products', 'ProductCategoryTemplate')
    ProductCategory = apps.get_model('products', 'ProductCategory')
    Store = apps.get_model('stores', 'Store')

    for tmpl in ProductCategoryTemplate.objects.all():
        stores = Store.objects.filter(category_id=tmpl.store_category_id)
        for store in stores:
            ProductCategory.objects.get_or_create(
                store_id=store.id,
                name=tmpl.name,
                defaults={'description': tmpl.description or '', 'order': tmpl.order}
            )


def backwards(apps, schema_editor):
    # noop: do not remove product categories on reverse to avoid accidental data loss
    return


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0004_add_productcategorytemplate'),
        ('stores', '0007_store_store_type'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
