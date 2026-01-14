#!/usr/bin/env python
"""
Script pour tester l'endpoint du catalogue B2B
"""
import os
import django
import requests
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gaboshop.settings')
django.setup()

from stores.models import Store
from users.models import User
from django.db.models import Q

def get_test_user():
    """Récupérer un utilisateur de test B2C"""
    # Chercher un utilisateur gérant d'un magasin B2C (pas BERNABE qui est aussi B2B)
    stores = Store.objects.filter(is_b2c=True, is_b2b=False, is_active=True)
    print(f"Stores B2C purs trouvés: {stores.count()}")
    for store in stores:
        print(f"  - {store.name} (manager: {store.manager.username if store.manager else 'None'})")
        if store.manager and store.manager.is_active:
            return store.manager
    return None

def test_catalog_endpoint():
    """Tester l'endpoint du catalogue B2B"""
    print("=== TEST ENDPOINT CATALOGUE B2B ===\n")

    # Récupérer un utilisateur de test
    user = get_test_user()
    if not user:
        print("❌ Aucun utilisateur B2C trouvé pour les tests")
        return

    print(f"Utilisateur de test: {user.username} ({user.email})")

    # Récupérer le store B2B (BERNABE, ID: 3)
    try:
        wholesaler = Store.objects.get(id=3, is_b2b=True, is_active=True)
        print(f"Grossiste: {wholesaler.name} (ID: {wholesaler.id})")
    except Store.DoesNotExist:
        print("❌ Grossiste B2B non trouvé")
        return

    # Tester directement les services B2B
    from b2b.services.supply import get_b2b_products, get_b2b_categories
    from b2b.models import B2BProductPricing
    from django.db.models import Count

    # Récupérer le store de l'utilisateur (B2C)
    buyer_store = Store.objects.filter(
        manager=user,
        is_b2c=True,
        is_active=True
    ).first()

    if not buyer_store:
        print("[ERROR] Aucun store B2C trouvé pour cet utilisateur")
        return

    print(f"Store acheteur: {buyer_store.name} (ID: {buyer_store.id})")

    # Simuler la logique de la vue
    try:
        # Vérifier les permissions
        from b2b.services.permissions import can_purchase_from_wholesaler
        can_purchase, error_msg = can_purchase_from_wholesaler(buyer_store, wholesaler)
        if not can_purchase:
            print(f"[ERROR] Permission refusee: {error_msg}")
            return

        # Récupérer les catégories avec compte de produits
        categories = get_b2b_categories(wholesaler.id)
        categories_with_count = categories.annotate(
            product_count=Count('products', filter=Q(
                products__store=wholesaler,
                products__is_available=True,
                products__b2b_pricings__is_active=True
            ))
        ).filter(product_count__gt=0)

        # Récupérer les produits
        products = get_b2b_products(wholesaler.id, None, None)

        print("\n=== RESULTATS DU TEST ===")
        print(f"Status: 200 (simule)")

        # Infos du grossiste
        b2b_profile = wholesaler.b2b_profile if hasattr(wholesaler, 'b2b_profile') else None
        print(f"\nStore: {wholesaler.name} (ID: {wholesaler.id})")
        print(f"Minimum order: {float(b2b_profile.minimum_order_amount) if b2b_profile else 0} FCFA")

        # Catégories
        print(f"\nCategories ({categories_with_count.count()}):")
        for cat in categories_with_count:
            print(f"  - {cat.name} ({cat.product_count} produits)")

        # Produits
        print(f"\nProduits ({products.count()}):")
        for product in products[:3]:  # Afficher seulement les 3 premiers
            print(f"  - {product.name}")

            # Récupérer le prix B2B
            pricing = B2BProductPricing.objects.filter(
                product=product,
                b2b_store=wholesaler,
                is_active=True
            ).first()
            if pricing:
                print(f"    Prix B2B: {float(pricing.b2b_price)} FCFA")
                print(f"    MOQ: {pricing.min_quantity}")
            else:
                print(f"    Prix B2B: N/A")

            print(f"    Categorie B2B: {product.b2b_category.name if product.b2b_category else 'N/A'}")
            print()

        print("[SUCCESS] Test reussi ! Le catalogue B2B fonctionne correctement.")

    except Exception as e:
        print(f"[ERROR] Erreur lors du test: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_catalog_endpoint()
