#!/usr/bin/env python
"""
Script pour vérifier les données B2B dans la base de données
"""
import os
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gaboshop.settings')
django.setup()

from b2b.models import B2BProfile, B2BProductPricing, B2BCategory
from products.models import Product
from stores.models import Store

print("=== PROFILS B2B ACTIFS ===")
profiles = B2BProfile.objects.filter(is_active=True).select_related('store')
print(f"Trouvé {profiles.count()} profils B2B actifs:")
for p in profiles:
    print(f"- {p.store.name} (ID: {p.store.id}) - min_order: {p.minimum_order_amount}")

print("\n=== PRICING B2B ===")
pricings = B2BProductPricing.objects.filter(is_active=True).select_related('product', 'b2b_store')
print(f"Trouvé {pricings.count()} prix B2B actifs:")
for p in pricings[:10]:  # Limiter à 10 pour l'affichage
    print(f"- {p.product.name} chez {p.b2b_store.name}: {p.b2b_price} FCFA (min: {p.min_quantity})")
if pricings.count() > 10:
    print(f"... et {pricings.count() - 10} autres")

print("\n=== CATÉGORIES B2B ===")
categories = B2BCategory.objects.filter(is_active=True)
print(f"Trouvé {categories.count()} catégories B2B actives:")
for c in categories:
    product_count = c.products.filter(is_available=True).count()
    print(f"- {c.name} ({product_count} produits)")

print("\n=== PRODUITS AVEC CATÉGORIE B2B ===")
products_with_b2b = Product.objects.filter(
    is_available=True,
    b2b_category__isnull=False
).select_related('store', 'b2b_category')[:10]
print(f"Trouvé {Product.objects.filter(is_available=True, b2b_category__isnull=False).count()} produits avec catégorie B2B:")
for p in products_with_b2b:
    print(f"- {p.name} (store: {p.store.name}, catégorie: {p.b2b_category.name})")

print("\n=== STORES B2B ACTIFS ===")
b2b_stores = Store.objects.filter(is_b2b=True, is_active=True)
print(f"Trouvé {b2b_stores.count()} stores B2B actifs:")
for s in b2b_stores:
    pricing_count = B2BProductPricing.objects.filter(b2b_store=s, is_active=True).count()
    print(f"- {s.name} (ID: {s.id}) - {pricing_count} prix B2B")
