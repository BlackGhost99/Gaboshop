"""Auto migration: add ProductVariant and ProductImage models

Generated manually to match models in products/models.py
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('products', '0002_product_is_sponsored_product_sponsor_expiry_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProductVariant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, help_text='Nom de la variante, ex: Rouge / XL')),
                ('sku', models.CharField(blank=True, help_text='SKU optionnel pour la variante', max_length=120)),
                ('price', models.DecimalField(blank=True, decimal_places=2, help_text='Prix spécifique (si null = produit.price)', max_digits=10, null=True)),
                ('stock', models.IntegerField(default=0)),
                ('attributes', models.JSONField(default=dict, blank=True, help_text="Attributs libres ex: {'color': 'red', 'size': 'L'}")),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='variants', to='products.product')),
            ],
            options={
                'verbose_name': 'Variante Produit',
                'verbose_name_plural': 'Variantes Produits',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ProductImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='products/gallery/')),
                ('alt_text', models.CharField(blank=True, max_length=200)),
                ('order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='products.product')),
            ],
            options={
                'verbose_name': 'Image Produit',
                'verbose_name_plural': 'Images Produits',
                'ordering': ['order', '-created_at'],
            },
        ),
    ]
