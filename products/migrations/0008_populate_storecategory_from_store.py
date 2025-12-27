from django.db import migrations


def forwards(apps, schema_editor):
    ProductCategory = apps.get_model('products', 'ProductCategory')
    Store = apps.get_model('stores', 'Store')

    # For each product category, set store_category from the related store
    for pc in ProductCategory.objects.all():
        try:
            store = Store.objects.get(id=pc.store_id)
            pc.store_category_id = store.category_id
            pc.save()
        except Exception:
            # ignore if store not found
            continue


def backwards(apps, schema_editor):
    # noop
    return


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0007_add_storecategory_field'),
        ('stores', '0007_store_store_type'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
