#!/usr/bin/env python
"""
Test simple pour vérifier que l'endpoint POST /api/v1/orders/create/ fonctionne
Simule une requête frontend pour créer une commande avec SingPay
"""

import requests
import json

# Configuration
BASE_URL = "http://localhost:8000"
API_ENDPOINT = f"{BASE_URL}/api/v1/orders/create/"

def test_order_creation_with_frontend_payload():
    """
    Teste avec un payload similaire au frontend
    Note: Vous devez être authentifié pour que ça marche
    """
    
    # ⚠️ Remplacez ces valeurs avec vos données réelles
    # Pour obtenir un token : Backend > Users > API Tokens
    TOKEN = "YOUR_AUTH_TOKEN_HERE"  
    
    # Payload similaire au frontend
    payload = {
        "store": 1,  # ID du store
        "city": "Libreville",
        "delivery_address": "123 Rue Test",
        "delivery_phone": "+24177777777",
        "delivery_zone": "Zone Test",
        # Champs optionnels (avant, ils causaient une erreur 400)
        # "delivery_type": "standard",  # ← Maintenant optionnel
        # "delivery_requested": True,    # ← Maintenant optionnel
        # "notes": "Test SingPay",       # ← Maintenant optionnel
        "items": [
            {
                "product_id": 1,
                "quantity": 1
            }
        ]
    }
    
    headers = {
        "Authorization": f"Token {TOKEN}",
        "Content-Type": "application/json"
    }
    
    print("=" * 60)
    print("📤 TEST CREATION COMMANDE")
    print("=" * 60)
    print(f"\nEndpoint: POST {API_ENDPOINT}")
    print(f"\nPayload:")
    print(json.dumps(payload, indent=2))
    
    try:
        response = requests.post(
            API_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=10
        )
        
        print(f"\n📥 Réponse (Status {response.status_code}):")
        print(json.dumps(response.json(), indent=2))
        
        if response.status_code == 201:
            print("\n✅ SUCCÈS! Commande créée avec succès")
            order_data = response.json().get('data', {})
            order_id = order_data.get('id')
            print(f"   Order ID: {order_id}")
            return order_id
        elif response.status_code == 400:
            print("\n❌ ERREUR 400 - Bad Request")
            errors = response.json().get('error', {}).get('details', {})
            print("   Erreurs:")
            for field, messages in errors.items():
                print(f"   • {field}: {messages}")
        else:
            print(f"\n⚠️  Status inattendu: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ ERREUR: Impossible de se connecter à {BASE_URL}")
        print("   Assurez-vous que le serveur Django est en cours d'exécution")
        print(f"   Commande: python manage.py runserver")
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")

if __name__ == '__main__':
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║  TEST ENDPOINT CREATION COMMANDE (POST /api/v1/orders/create/)  ║
    ║  Vérification de la correction du problème 400 Bad Request  ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    print("\n⚠️  IMPORTANT:")
    print("   1. Modifiez TOKEN avec votre vrai token d'authentification")
    print("   2. Modifiez les IDs (store, product) avec vos vraies données")
    print("   3. Assurez-vous que le serveur Django est en cours d'exécution")
    print("   4. Exécutez: D:/Expériences/Gaboshop/venv-1/Scripts/python.exe test_order_request.py")
    print()
    
    # Décommenter après configuration:
    # test_order_creation_with_frontend_payload()
