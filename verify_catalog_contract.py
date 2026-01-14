#!/usr/bin/env python
"""
Script pour vérifier que l'endpoint catalogue B2B respecte le contrat API attendu
"""
import os
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gaboshop.settings')
django.setup()

from stores.models import Store
from users.models import User
from b2b.models import B2BProductPricing
from rest_framework.test import APIClient
from django.urls import reverse

def test_catalog_api_contract():
    """Tester le contrat API de l'endpoint catalogue"""
    print("=== VERIFICATION CONTRAT API CATALOGUE B2B ===\n")

    # Créer un client API
    client = APIClient()

    # Récupérer un utilisateur de test B2C
    stores = Store.objects.filter(is_b2c=True, is_b2b=False, is_active=True)
    if not stores.exists():
        print("❌ Aucun store B2C trouvé")
        return

    buyer_store = stores.first()
    user = buyer_store.manager

    print(f"Utilisateur de test: {user.username}")
    print(f"Store acheteur: {buyer_store.name} (ID: {buyer_store.id})")

    # Authentifier l'utilisateur
    client.force_authenticate(user=user)

    # Tester l'endpoint catalogue pour BERNABE (ID: 3)
    wholesaler_id = 3
    url = reverse('b2b:wholesaler-catalog', kwargs={'id': wholesaler_id})
    print(f"\nURL testée: {url}")

    response = client.get(url)

    if response.status_code != 200:
        print(f"[ERROR] Status: {response.status_code}")
        print(f"Erreur: {response.data}")
        return

    print("[SUCCESS] Status: 200")

    data = response.data['data']

    # Vérifier la structure attendue
    required_keys = ['wholesaler', 'categories', 'products', 'pagination']
    for key in required_keys:
        if key not in data:
            print(f"[ERROR] Cle manquante: {key}")
            return

    print("[SUCCESS] Structure de base correcte")

    # Vérifier les infos du grossiste
    wholesaler_data = data['wholesaler']
    required_wholesaler_keys = ['id', 'name', 'minimum_order_amount']
    for key in required_wholesaler_keys:
        if key not in wholesaler_data:
            print(f"[ERROR] Cle manquante dans wholesaler: {key}")
            return

    print("[SUCCESS] Infos grossiste correctes")
    print(f"  - Store: {wholesaler_data['name']} (ID: {wholesaler_data['id']})")
    print(f"  - Minimum order: {wholesaler_data['minimum_order_amount']} FCFA")

    # Vérifier les catégories
    categories = data['categories']
    print(f"[SUCCESS] Categories: {len(categories)} trouvees")

    for cat in categories[:2]:  # Vérifier les 2 premières
        required_cat_keys = ['id', 'name', 'product_count']
        for key in required_cat_keys:
            if key not in cat:
                print(f"[ERROR] Cle manquante dans categorie: {key}")
                return
        print(f"  - {cat['name']} ({cat['product_count']} produits)")

    # Vérifier les produits
    products = data['products']
    print(f"[SUCCESS] Produits: {len(products)} trouves")

    for product in products[:2]:  # Vérifier les 2 premiers
        required_product_keys = [
            'id', 'name', 'wholesale_price', 'min_order_quantity',
            'pricing_tiers', 'stock', 'in_stock'
        ]
        for key in required_product_keys:
            if key not in product:
                print(f"[ERROR] Cle manquante dans produit: {key}")
                return

        print(f"  - {product['name']}")
        print(f"    Prix gros: {product['wholesale_price']} FCFA")
        print(f"    MOQ: {product['min_order_quantity']}")
        print(f"    Stock: {product['stock']}")
        print(f"    En stock: {product['in_stock']}")

        # Vérifier les pricing tiers
        tiers = product['pricing_tiers']
        if tiers:
            print(f"    Tiers de prix: {len(tiers)}")
            for tier in tiers:
                required_tier_keys = ['min_qty', 'max_qty', 'price']
                for key in required_tier_keys:
                    if key not in tier:
                        print(f"[ERROR] Cle manquante dans tier: {key}")
                        return

    # Verifier la pagination
    pagination = data['pagination']
    required_pagination_keys = ['page', 'page_size', 'total_products', 'total_pages']
    for key in required_pagination_keys:
        if key not in pagination:
            print(f"[ERROR] Cle manquante dans pagination: {key}")
            return

    print("[SUCCESS] Pagination correcte")
    print(f"  - Page: {pagination['page']}/{pagination['total_pages']}")
    print(f"  - Total produits: {pagination['total_products']}")

    print("\n=== CONTRAT API RESPECTE ===")
    print("[SUCCESS] L'endpoint catalogue B2B fonctionne correctement")
    print("[SUCCESS] La reponse respecte le contrat attendu")
    print("[SUCCESS] Le frontend peut consommer les donnees sans logique supplementaire")

    # Afficher un exemple du format JSON
    print("\n=== EXEMPLE DE FORMAT JSON ===")
    import json
    sample = {
        "store": {
            "id": wholesaler_data['id'],
            "name": wholesaler_data['name'],
            "min_order_amount": wholesaler_data['minimum_order_amount']
        },
        "categories": [
            {
                "id": categories[0]['id'] if categories else 1,
                "name": categories[0]['name'] if categories else "Exemple",
                "products": [
                    {
                        "id": products[0]['id'] if products else 12,
                        "name": products[0]['name'] if products else "Eau minérale 1.5L",
                        "b2b_price": products[0]['wholesale_price'] if products else 350,
                        "min_quantity": products[0]['min_order_quantity'] if products else 24,
                        "available": products[0]['in_stock'] if products else True
                    }
                ] if products else []
            }
        ] if categories else []
    }

    print(json.dumps(sample, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test_catalog_api_contract()