"""
Simulation complète du flux PIN : 
1. Livreur accepte livraison
2. Vérifie PIN
3. Upload preuve
4. Confirme livraison (complete)
"""

import os
import sys
import django
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework_simplejwt.tokens import RefreshToken
from orders.models import Order
from stores.models import Store, StoreCategory
from products.models import Product
from delivery.models import Delivery, DeliveryProof
import json

User = get_user_model()

def print_test(title, result):
    symbol = "✓" if result == "PASS" else "✗"
    color = "\033[92m" if result == "PASS" else "\033[91m"
    reset = "\033[0m"
    print(f"{color}{symbol} {title}{reset}")

def cleanup():
    """Nettoyer les données de test"""
    print("\n🧹 Nettoyage des données précédentes...")
    DeliveryProof.objects.filter(delivery__order__order_number__startswith='TEST-PIN-FLOW').delete()
    Delivery.objects.filter(order__order_number__startswith='TEST-PIN-FLOW').delete()
    Order.objects.filter(order_number__startswith='TEST-PIN-FLOW').delete()
    Product.objects.filter(name='Test Product PIN').delete()
    Store.objects.filter(name__startswith='Test Store PIN').delete()
    User.objects.filter(email__contains='test-pin-').delete()

def setup_test_data():
    """Créer les données de test"""
    import random
    import time
    
    print("\n📝 Création des données de test...")
    
    # Générer des numéros de téléphone uniques
    timestamp = int(time.time() * 1000) % 999999
    phone1 = f'+2410777{timestamp:05d}1'
    phone2 = f'+2410777{timestamp:05d}2'
    phone3 = f'+2410777{timestamp:05d}3'
    
    # Utilisateurs
    client = User.objects.create_user(
        email=f'test-pin-client-{timestamp}@example.com',
        phone=phone1,
        password='testpass123',
        user_type='client',
        first_name='Client',
        last_name='PIN'
    )
    print(f"  ✓ Client créé: {client.email}")
    
    livreur = User.objects.create_user(
        email=f'test-pin-livreur-{timestamp}@example.com',
        phone=phone2,
        password='testpass123',
        user_type='delivery_agent',
        first_name='Livreur',
        last_name='PIN'
    )
    print(f"  ✓ Livreur créé: {livreur.email}")
    
    manager = User.objects.create_user(
        email=f'test-pin-manager-{timestamp}@example.com',
        phone=phone3,
        password='testpass123',
        user_type='store_manager',
        first_name='Manager',
        last_name='PIN'
    )
    print(f"  ✓ Manager créé: {manager.email}")
    
    # Store
    category = StoreCategory.objects.first() or StoreCategory.objects.create(name='Test')
    store = Store.objects.create(
        name=f'Test Store PIN {timestamp}',
        manager=manager,
        category=category,
        city='Libreville',
        phone=f'+241{timestamp:09d}',
        commission_rate=Decimal('8.00')  # Ensure commission_rate is Decimal
    )
    print(f"  ✓ Store créé: {store.name}")
    
    # Produit
    product = Product.objects.create(
        store=store,
        name='Test Product PIN',
        price=Decimal('50000'),
        stock=10
    )
    print(f"  ✓ Produit créé: {product.name}")
    
    # Commande
    order = Order.objects.create(
        order_number=f'TEST-PIN-FLOW-{timestamp}',
        client=client,
        store=store,
        delivery_address='123 Test Street',
        delivery_phone='+241077700099',
        city='Libreville',
        delivery_zone='Test Zone',
        items_total=Decimal('50000'),
        delivery_fee=Decimal('2000'),
        total_amount=Decimal('52000'),
        commission_rate=Decimal('5'),  # Add as Decimal, not float
        status='confirmed'
    )
    print(f"  ✓ Commande créée: {order.order_number}")
    
    # Livraison - Supprime d'abord si elle existe (OneToOne constraint)
    Delivery.objects.filter(order=order).delete()
    delivery = Delivery.objects.create(
        order=order,
        delivery_agent=livreur,
        status='pending'
    )
    print(f"  ✓ Livraison créée (ID={delivery.id}, PIN={delivery.delivery_code})")
    
    return client, livreur, manager, store, product, order, delivery

def test_complete_flow():
    """Test le flux complet PIN → Upload → Complete"""
    
    print("\n" + "="*70)
    print("TEST: Flux complet PIN → Upload Preuve → Confirmer Livraison")
    print("="*70)
    
    cleanup()
    client_user, livreur, manager, store, product, order, delivery = setup_test_data()
    
    # Créer un client test Django
    test_client = Client()
    
    # Authentifier le livreur avec JWT token
    refresh = RefreshToken.for_user(livreur)
    access_token = str(refresh.access_token)
    test_client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {access_token}'
    
    # ============================================================================
    # ÉTAPE 1: Livreur accepte la livraison
    # ============================================================================
    print("\n" + "-"*70)
    print("ÉTAPE 1: Livreur accepte la livraison (→ statut 'accepted')")
    print("-"*70)
    
    test_client.force_login(livreur)
    response = test_client.post(
        f'/api/v1/dashboard/delivery/{delivery.id}/accept/',
        content_type='application/json'
    )
    
    print(f"Status code: {response.status_code}")
    data = json.loads(response.content)
    print(f"Response: {json.dumps(data, indent=2)}")
    
    delivery.refresh_from_db()
    print(f"Statut livraison: {delivery.status}")
    print(f"PIN généré: {delivery.delivery_code}")
    
    if response.status_code == 200 and delivery.status == 'accepted':
        print_test("Livreur a accepté la livraison", "PASS")
    else:
        print_test("Livreur a accepté la livraison", "FAIL")
        return False
    
    # ============================================================================
    # ÉTAPE 2: Vérifier le PIN via endpoint frontend
    # ============================================================================
    print("\n" + "-"*70)
    print("ÉTAPE 2: Vérifier le PIN (endpoint /verify-pin/)")
    print("-"*70)
    
    pin_code = delivery.delivery_code
    print(f"PIN à vérifier: {pin_code}")
    
    response = test_client.post(
        f'/api/v1/dashboard/delivery/{delivery.id}/verify-pin/',
        data=json.dumps({'pin_code': pin_code}),
        content_type='application/json'
    )
    
    print(f"Status code: {response.status_code}")
    data = json.loads(response.content)
    print(f"Response: {json.dumps(data, indent=2)}")
    
    if response.status_code == 200 and data.get('success'):
        print_test("PIN vérifié avec succès", "PASS")
    else:
        print_test("PIN vérifié avec succès", "FAIL")
        return False
    
    # ============================================================================
    # ÉTAPE 3: Upload de la preuve (Livreur)
    # ============================================================================
    print("\n" + "-"*70)
    print("ÉTAPE 3: Upload de la preuve (photo + GPS + PIN)")
    print("-"*70)
    
    # Créer des fichiers de test
    id_card_file = SimpleUploadedFile(
        "id_card.jpg",
        b"fake image content for ID card",
        content_type="image/jpeg"
    )
    
    # FormData simulé
    response = test_client.post(
        f'/api/v1/dashboard/delivery/{delivery.id}/upload-proof/',
        data={
            'id_card_photo': id_card_file,
            'latitude': '0.3901',
            'longitude': '9.4544',
            'pin_code': pin_code,
            'pin_verified': 'true',
            'client_received_status': 'true'
        }
    )
    
    print(f"Status code: {response.status_code}")
    data = json.loads(response.content)
    print(f"Response: {json.dumps(data, indent=2, default=str)}")
    
    if response.status_code == 201 or response.status_code == 200:
        if data.get('success'):
            print_test("Preuve uploadée avec succès", "PASS")
        else:
            print_test("Preuve uploadée avec succès", "FAIL")
            print(f"  Erreur: {data.get('error', data.get('validation_errors'))}")
            return False
    else:
        print_test("Preuve uploadée avec succès", "FAIL")
        print(f"  Status: {response.status_code}, Erreur: {data}")
        return False
    
    # ============================================================================
    # ÉTAPE 4: Confirmer la livraison (complete)
    # ============================================================================
    print("\n" + "-"*70)
    print("ÉTAPE 4: Confirmer la livraison (/complete/)")
    print("-"*70)
    
    response = test_client.post(
        f'/api/v1/dashboard/delivery/{delivery.id}/complete/',
        data=json.dumps({}),
        content_type='application/json'
    )
    
    print(f"Status code: {response.status_code}")
    data = json.loads(response.content)
    print(f"Response: {json.dumps(data, indent=2, default=str)}")
    
    delivery.refresh_from_db()
    order.refresh_from_db()
    print(f"Statut livraison: {delivery.status}")
    print(f"Statut commande: {order.status}")
    
    if response.status_code == 200 and delivery.status == 'delivered':
        print_test("Livraison confirmée (statut=delivered)", "PASS")
    else:
        print_test("Livraison confirmée (statut=delivered)", "FAIL")
        return False
    
    # ============================================================================
    # RÉSUMÉ
    # ============================================================================
    print("\n" + "="*70)
    print("✅ RÉSUMÉ FINAL")
    print("="*70)
    print(f"✓ Livraison créée avec PIN: {delivery.delivery_code}")
    print(f"✓ Livreur acceptée → statut: {delivery.status}")
    print(f"✓ PIN vérifié en frontend")
    print(f"✓ Preuve uploadée (photo + GPS + PIN)")
    print(f"✓ Livraison confirmée → statut: delivered")
    print(f"✓ Commande mise à jour → statut: {order.status}")
    print("\n🎉 Flux complet PIN fonctionnel!")
    
    return True

if __name__ == '__main__':
    try:
        success = test_complete_flow()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Erreur: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
