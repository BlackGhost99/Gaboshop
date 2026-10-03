"""
Debug script pour tester la création de commande
Vérifie les erreurs 400 de l'endpoint /api/v1/orders/create/
"""

import os
import django
import json
from decimal import Decimal

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from users.models import User
from products.models import Product, Store
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

def test_order_creation():
    """Test la création de commande pour identifier l'erreur 400"""
    
    client = APIClient()
    
    # 1. Créer un utilisateur client de test
    try:
        user = User.objects.get(username='testclient', user_type='client')
    except User.DoesNotExist:
        user = User.objects.create_user(
            username='testclient',
            email='testclient@test.com',
            password='testpass123',
            user_type='client',
            phone='+24177777777'
        )
    
    # 2. Obtenir le token d'authentification
    token, _ = Token.objects.get_or_create(user=user)
    client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    
    # 3. Trouver un magasin actif
    store = Store.objects.filter(is_active=True).first()
    if not store:
        print("❌ Pas de magasin actif disponible")
        return
    
    print(f"✓ Magasin sélectionné: {store.name}")
    print(f"  - Ouvert? {store.is_open()}")
    print(f"  - Montant minimum: {store.min_order_amount} FCFA")
    
    # 4. Trouver des produits disponibles du magasin
    products = Product.objects.filter(store=store, is_active=True)
    if not products.exists():
        print(f"❌ Pas de produits actifs pour le magasin {store.name}")
        return
    
    # 5. Préparer les données de commande
    order_data = {
        'store': store.id,
        'city': 'Libreville',
        'delivery_address': '123 Rue Test',
        'delivery_phone': user.phone,
        'delivery_zone': 'Zone Test',
        'delivery_type': 'standard',
        'delivery_requested': True,
        'notes': 'Test SingPay',
        'items': []
    }
    
    # Ajouter les produits jusqu'à atteindre le montant minimum
    total = Decimal('0')
    for product in products[:3]:  # Max 3 produits
        qty = 1
        item_total = product.price * qty
        order_data['items'].append({
            'product_id': product.id,
            'quantity': qty,
            'unit_price': str(product.price)
        })
        total += item_total
        print(f"  - {product.name}: {product.price} FCFA × {qty}")
        
        if total >= store.min_order_amount:
            break
    
    print(f"\n💰 Total: {total} FCFA (minimum requis: {store.min_order_amount} FCFA)")
    
    if not order_data['items']:
        print("❌ Impossible d'ajouter des produits")
        return
    
    # 6. Faire la requête POST
    print("\n📤 Envoi de la requête POST /api/v1/orders/create/")
    print(f"Données: {json.dumps(order_data, indent=2, default=str)}")
    
    response = client.post(
        'http://localhost:8000/api/v1/orders/create/',
        data=json.dumps(order_data),
        content_type='application/json'
    )
    
    print(f"\n📥 Réponse (Status {response.status_code}):")
    print(json.dumps(response.json(), indent=2))
    
    if response.status_code == 400:
        print("\n❌ ERREUR 400 - Détails des erreurs:")
        errors = response.json().get('error', {}).get('details', {})
        for field, messages in errors.items():
            print(f"  • {field}: {messages}")
        print("\nPossibles causes:")
        print("  1. Montant minimum de commande non atteint")
        print("  2. Magasin fermé")
        print("  3. Magasin inactif")
        print("  4. Un ou plusieurs produits indisponibles")
        print("  5. Type de livraison non disponible")
    elif response.status_code == 201:
        print("✓ Commande créée avec succès!")
    else:
        print(f"\n⚠️  Statut inattendu: {response.status_code}")

if __name__ == '__main__':
    test_order_creation()
