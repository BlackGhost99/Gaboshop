from django.db import migrations, models


class Migration(migrations.Migration):

	dependencies = [
		('products', '0017_product_length_m'),
	]

	operations = [
		migrations.AddField(
			model_name='product',
			name='attributes',
			field=models.JSONField(blank=True, default=dict, help_text="Caractéristiques libres, ex: {'brand': 'Nike', 'model': 'Air Max', 'sizes': '40, 41, 42'}"),
		),
	]
