from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0005_merge_templates_into_categories'),
    ]

    operations = [
        migrations.DeleteModel(
            name='ProductCategoryTemplate',
        ),
    ]
