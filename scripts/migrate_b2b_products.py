#!/usr/bin/env python
"""
Script de migration des produits existants vers market_type
Tous les produits avec B2BProductPricing actif deviennent market_type='both'
(car ils sont déjà vendus en B2C et maintenant aussi en B2B)
"""
import os
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gaboshop.settings')
django.setup()

from products.models import Product
from b2b.models import B2BProductPricing
from django.db.models import Q

def migrate_b2b_products():
    """Migre les produits existants vers market_type approprié"""
    print("=== Migration des produits B2B ===\n")
    
    # Récupérer tous les produits qui ont au moins un B2BProductPricing actif
    products_with_b2b = Product.objects.filter(
        b2b_pricings__is_active=True
    ).distinct()
    
    count = 0
    for product in products_with_b2b:
        # Si le produit a un pricing B2B actif, il est vendu en B2B ET B2C
        if product.market_type != 'both':
            product.market_type = 'both'
            product.save(update_fields=['market_type'])
            count += 1
            print(f"✓ {product.name} (ID: {product.id}) → market_type='both'")
    
    print(f"\n=== Migration terminée ===")
    print(f"Produits mis à jour: {count}")
    print(f"Total produits avec B2B pricing: {products_with_b2b.count()}")
    
    # Statistiques
    total_products = Product.objects.count()
    b2c_only = Product.objects.filter(market_type='b2c').count()
    b2b_only = Product.objects.filter(market_type='b2b').count()
    both = Product.objects.filter(market_type='both').count()
    
    print(f"\n=== Statistiques ===")
    print(f"Total produits: {total_products}")
    print(f"B2C uniquement: {b2c_only}")
    print(f"B2B uniquement: {b2b_only}")
    print(f"B2C et B2B: {both}")

if __name__ == "__main__":
    migrate_b2b_products()

