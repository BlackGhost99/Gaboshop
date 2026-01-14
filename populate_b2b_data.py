#!/usr/bin/env python
"""
Script pour peupler les données B2B (catégories, assignation aux produits, pricing)
"""
import os
import django
from pathlib import Path
from decimal import Decimal

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gaboshop.settings')
django.setup()

from b2b.models import B2BProfile, B2BProductPricing, B2BCategory
from products.models import Product
from stores.models import Store

def create_b2b_categories():
    """Créer les catégories B2B de base"""
    categories_data = [
        {"name": "Boissons", "description": "Eaux, jus, sodas, bières"},
        {"name": "Alimentaire", "description": "Conserves, huiles, sucre, café"},
        {"name": "Hygiène", "description": "Savons, dentifrices, produits d'hygiène"},
        {"name": "Entretien", "description": "Produits de nettoyage, détergents"},
        {"name": "Épicerie", "description": "Pâtes, riz, farines, condiments"},
    ]

    categories = []
    for cat_data in categories_data:
        cat, created = B2BCategory.objects.get_or_create(
            name=cat_data["name"],
            defaults={
                "description": cat_data["description"],
                "is_active": True
            }
        )
        categories.append(cat)
        if created:
            print(f"[+] Cree categorie B2B: {cat.name}")
        else:
            print(f"[-] Categorie B2B existe deja: {cat.name}")

    return categories

def assign_products_to_b2b_categories(store):
    """Assigner des catégories B2B aux produits du store"""
    # Récupérer les produits du store sans catégorie B2B
    products = Product.objects.filter(
        store=store,
        is_available=True,
        b2b_category__isnull=True
    )

    # Mapping simple basé sur les noms de produits
    category_mapping = {
        "eau": "Boissons",
        "jus": "Boissons",
        "soda": "Boissons",
        "bière": "Boissons",
        "vin": "Boissons",
        "huile": "Alimentaire",
        "sucre": "Alimentaire",
        "café": "Alimentaire",
        "thé": "Alimentaire",
        "conserve": "Alimentaire",
        "savon": "Hygiène",
        "dentifrice": "Hygiène",
        "shampooing": "Hygiène",
        "déodorant": "Hygiène",
        "lessive": "Entretien",
        "détergent": "Entretien",
        "nettoyant": "Entretien",
        "pâte": "Épicerie",
        "riz": "Épicerie",
        "farine": "Épicerie",
        "sel": "Épicerie",
    }

    categories = {cat.name: cat for cat in B2BCategory.objects.all()}

    assigned_count = 0
    for product in products:
        product_name_lower = product.name.lower()

        # Chercher une correspondance dans le mapping
        assigned = False
        for keyword, category_name in category_mapping.items():
            if keyword in product_name_lower:
                if category_name in categories:
                    product.b2b_category = categories[category_name]
                    product.save()
                    assigned_count += 1
                    print(f"[+] Assigne {product.name} -> {category_name}")
                    assigned = True
                    break

        # Si pas de correspondance, assigner à "Alimentaire" par défaut
        if not assigned and "Alimentaire" in categories:
            product.b2b_category = categories["Alimentaire"]
            product.save()
            assigned_count += 1
            print(f"[+] Assigne {product.name} -> Alimentaire (defaut)")

    return assigned_count

def create_b2b_pricing(store):
    """Créer des prix B2B pour les produits du store"""
    # Récupérer les produits avec catégorie B2B
    products = Product.objects.filter(
        store=store,
        is_available=True,
        b2b_category__isnull=False
    )

    # Appliquer une remise de 10% par défaut
    discount_percentage = Decimal('10.0')  # 10% de remise
    discount_factor = Decimal('1') - (discount_percentage / Decimal('100'))

    created_count = 0
    for product in products:
        # Calculer le prix B2B
        b2b_price = product.price * discount_factor

        # Créer ou mettre à jour le pricing
        pricing, created = B2BProductPricing.objects.get_or_create(
            product=product,
            b2b_store=store,
            defaults={
                'b2b_price': b2b_price,
                'min_quantity': 1,  # Quantité minimum 1 par défaut
                'is_active': True
            }
        )

        if created:
            created_count += 1
            print(f"[+] Cree prix B2B: {product.name} - {b2b_price} FCFA (min: 1)")
        else:
            # Mettre à jour si le prix a changé
            if pricing.b2b_price != b2b_price:
                pricing.b2b_price = b2b_price
                pricing.save()
                print(f"[+] Mis a jour prix B2B: {product.name} - {b2b_price} FCFA")

    return created_count

def main():
    print("=== PEUPLEMENT DES DONNÉES B2B ===\n")

    # Récupérer le store B2B
    try:
        store = Store.objects.get(id=3, is_b2b=True, is_active=True)  # BERNABE
        print(f"Store B2B trouvé: {store.name} (ID: {store.id})")
    except Store.DoesNotExist:
        print("❌ Store B2B non trouvé")
        return

    # 1. Créer les catégories B2B
    print("\n1. Création des catégories B2B...")
    categories = create_b2b_categories()

    # 2. Assigner les produits aux catégories B2B
    print("\n2. Assignation des produits aux catégories B2B...")
    assigned_count = assign_products_to_b2b_categories(store)
    print(f"[+] {assigned_count} produits assignes a des categories B2B")

    # 3. Créer les prix B2B
    print("\n3. Creation des prix B2B...")
    pricing_count = create_b2b_pricing(store)
    print(f"[+] {pricing_count} prix B2B crees")

    print("\n=== RÉCAPITULATIF ===")
    print(f"Catégories B2B: {B2BCategory.objects.filter(is_active=True).count()}")
    print(f"Produits avec catégorie B2B: {Product.objects.filter(store=store, is_available=True, b2b_category__isnull=False).count()}")
    print(f"Prix B2B actifs: {B2BProductPricing.objects.filter(b2b_store=store, is_active=True).count()}")

if __name__ == "__main__":
    main()
