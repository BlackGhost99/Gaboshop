#!/usr/bin/env python
"""
Script pour tester l'endpoint /api/v1/orders/create/
et capturer l'erreur 400 exacte
"""
import os
import django
import sys
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.test import APIRequestFactory, force_authenticate
from api.v1.orders import OrderCreateView
from products.models import Store, Product

User = get_user_model()

def test_order_creation():
    """Test la création de commande et affiche l'erreur exacte"""
    
    print("=" * 60)
    print("🔍 TEST CREATION COMMANDE - CAPTURE D'ERREUR 400")
    print("=" * 60)
    print()
    
    # 1. Créer ou récupérer un utilisateur client
    user, created = User.objects.get_or_create(
        username='testclient',
        defaults={
            'email': 'testclient@test.com',
            'user_type': 'client',
            'phone': '+24177777777',
            'is_active': True
        }
    )
    
    if created:
        user.set_password('testpass123')
        user.save()
        print(f"✓ Utilisateur créé: {user.username}")
    else:
        print(f"✓ Utilisateur trouvé: {user.username}")
    
    # 2. Récupérer/créer un token
    token, _ = Token.objects.get_or_create(user=user)
    print(f"✓ Token: {token.key}")
    print()
    
    # 3. Récupérer un magasin actif
    store = Store.objects.filter(is_active=True).first()
    if not store:
        print("❌ Pas de magasin actif disponible")
        return
    
    print(f"✓ Magasin: {store.name} (ID: {store.id})")
    print(f"  - Ouvert: {store.is_open()}")
    print(f"  - Minimum: {store.min_order_amount} FCFA")
    print()
    
    # 4. Récupérer des produits
    products = Product.objects.filter(store=store, is_active=True)
    if not products.exists():
        print(f"❌ Pas de produits pour ce magasin")
        return
    
    product = products.first()
    print(f"✓ Produit: {product.name} (ID: {product.id})")
    print(f"  - Prix: {product.price} FCFA")
    print(f"  - Stock: {product.stock}")
    print()
    
    # 5. Créer le payload de test
    payload_data = {
        'store': store.id,
        'delivery_address': '123 Rue Test',
        'delivery_phone': '+24177777777',
        'delivery_zone': 'Zone Test',
        'items': [
            {
                'product_id': product.id,
                'quantity': 1
            }
        ]
        # NOTE: delivery_type, delivery_requested, notes, city sont OPTIONNELS
    }
    
    print("📤 Payload envoyé:")
    print(json.dumps(payload_data, indent=2, default=str))
    print()
    
    # 6. Tester via le serializer directement
    from orders.serializers import OrderCreateSerializer
    
    serializer = OrderCreateSerializer(
        data=payload_data,
        context={'request': None}  # Pas besoin de request pour tester les validations
    )
    
    if serializer.is_valid():
        print("✅ SERIALIZER VALIDE!")
        print(f"Data validée: {serializer.validated_data.keys()}")
    else:
        print("❌ ERREURS DE VALIDATION:")
        for field, errors in serializer.errors.items():
            print(f"  • {field}: {errors}")
    
    print()
    print("=" * 60)

if __name__ == '__main__':
    test_order_creation()
