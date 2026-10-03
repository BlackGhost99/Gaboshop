#!/usr/bin/env python
"""
TEST INTÉGRATION SINGPAY - Gaboshop
===================================

Script de test complet pour valider:
1. Création commande test
2. Initiation paiement Airtel/Moov
3. Réponse Singpay
4. Webhook confirmation
5. Statuts finaux

Utilisation:
    python test_singpay_integration.py
"""

import os
import sys
import json
import django
from decimal import Decimal
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gaboshop.settings')
sys.path.insert(0, os.path.dirname(__file__))
django.setup()

from django.conf import settings
from django.utils import timezone
from django.test import Client
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from users.models import User
from stores.models import Store
from products.models import Product, Category
from orders.models import Order, OrderItem
from payments.models import Payment
from payments.services import PaymentService
from payments.utils import call_singpay_payment

# ============================================================================
# UTILITAIRES DE TEST
# ============================================================================

class Colors:
    OK = '\033[92m'
    WARN = '\033[93m'
    FAIL = '\033[91m'
    INFO = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.INFO}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.INFO}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.INFO}{'='*80}{Colors.RESET}")

def print_ok(text):
    print(f"{Colors.OK}✅ {text}{Colors.RESET}")

def print_fail(text):
    print(f"{Colors.FAIL}❌ {text}{Colors.RESET}")

def print_warn(text):
    print(f"{Colors.WARN}⚠️  {text}{Colors.RESET}")

def print_info(text):
    print(f"{Colors.INFO}ℹ️  {text}{Colors.RESET}")

# ============================================================================
# CONFIGURATION TEST
# ============================================================================

class SingpayTestConfig:
    # Test data
    TEST_CLIENT_PHONE = "+24177777777"  # Format Gabon standard
    TEST_AMOUNT = 15000  # 15,000 FCFA
    TEST_DELIVERY_FEE = 2000
    
    # Operators
    OPERATORS = ['airtel', 'moov']
    
    # Timeouts
    TIMEOUT_SINGPAY = 30

# ============================================================================
# SETUP DONNÉES TEST
# ============================================================================

def setup_test_data():
    """Créer ou récupérer données test"""
    print_header("SETUP - Préparation des données")
    
    # 1. Créer/Récupérer user test
    user, created = User.objects.get_or_create(
        username='testclient',
        defaults={
            'email': 'testclient@gaboshop.test',
            'phone': '+24177777777',
            'first_name': 'Test',
            'last_name': 'Client',
        }
    )
    if created:
        user.set_password('testpass123')
        user.save()
        print_ok(f"User créé: {user.username}")
    else:
        print_ok(f"User récupéré: {user.username}")
    
    # 2. Créer/Récupérer store test
    store, created = Store.objects.get_or_create(
        name='Test Store Singpay',
        defaults={
            'manager': user,
            'is_active': True,
            'is_open': True,
            'min_order_amount': Decimal('5000'),
            'delivery_fee': Decimal(SingpayTestConfig.TEST_DELIVERY_FEE),
            'commission_rate': Decimal('10'),
        }
    )
    if created:
        print_ok(f"Store créé: {store.name}")
    else:
        print_ok(f"Store récupéré: {store.name}")
    
    # 3. Créer/Récupérer category
    category, created = Category.objects.get_or_create(
        name='Test Category',
        defaults={'display_order': 0}
    )
    if created:
        print_ok(f"Category créée: {category.name}")
    
    # 4. Créer/Récupérer produit
    product, created = Product.objects.get_or_create(
        sku='TEST-SINGPAY-001',
        defaults={
            'name': 'Test Product Singpay',
            'category': category,
            'store': store,
            'price': Decimal('15000'),
            'stock': 100,
            'is_available': True,
        }
    )
    if created:
        print_ok(f"Produit créé: {product.sku}")
    else:
        print_ok(f"Produit récupéré: {product.sku}")
    
    return user, store, product

# ============================================================================
# TEST 1: CRÉATION COMMANDE
# ============================================================================

def test_create_order(user, store, product):
    """Étape 1: Créer une commande test"""
    print_header("TEST 1 - Création Commande")
    
    try:
        order_data = {
            'items': [
                {
                    'product_id': product.id,
                    'quantity': 1,
                    'unit_price': Decimal('15000')
                }
            ],
            'delivery_address': '123 Rue Test, Libreville',
            'delivery_phone': SingpayTestConfig.TEST_CLIENT_PHONE,
            'delivery_zone': 'TEST_ZONE',
            'notes': 'Commande test Singpay'
        }
        
        from orders.services import OrderService
        order = OrderService.create_order(user, store, order_data)
        
        print_ok(f"Commande créée: #{order.order_number}")
        print_info(f"  - ID: {order.id}")
        print_info(f"  - Montant: {order.total_amount} FCFA")
        print_info(f"  - Statut: {order.status}")
        
        return order
        
    except Exception as e:
        print_fail(f"Erreur création commande: {e}")
        raise

# ============================================================================
# TEST 2: VALIDATION CONFIG SINGPAY
# ============================================================================

def test_singpay_config():
    """Étape 2: Valider config Singpay"""
    print_header("TEST 2 - Validation Config Singpay")
    
    config_items = {
        'SINGPAY_BASE_URL': settings.SINGPAY_BASE_URL,
        'SINGPAY_CLIENT_ID': settings.SINGPAY_CLIENT_ID[:10] + '...',
        'SINGPAY_WALLET_ID': settings.SINGPAY_WALLET_ID,
        'SINGPAY_TIMEOUT': settings.SINGPAY_TIMEOUT,
    }
    
    for key, value in config_items.items():
        if value:
            print_ok(f"{key}: {value}")
        else:
            print_fail(f"{key}: MANQUANT ❌")
    
    return all(config_items.values())

# ============================================================================
# TEST 3: TEST FORMAT PHONE
# ============================================================================

def test_phone_formatting():
    """Étape 3: Valider formatage numéro Gabon"""
    print_header("TEST 3 - Formatage Numéro Gabon")
    
    test_phones = [
        '+24177777777',      # Standard
        '24177777777',       # Sans +
        '077777777',         # Local
        '0077777777',        # Local alt
        '+241 77777777',     # Avec espace
    ]
    
    for phone in test_phones:
        try:
            formatted = PaymentService._format_gabon_phone(phone, 'airtel')
            print_ok(f"{phone} → {formatted}")
        except Exception as e:
            print_fail(f"{phone} → Erreur: {e}")

# ============================================================================
# TEST 4: INITIATION PAIEMENT API
# ============================================================================

def test_payment_init_api(order, user):
    """Étape 4: Tester endpoint API de paiement"""
    print_header("TEST 4 - Initiation Paiement via API")
    
    api_client = APIClient()
    
    # Authentifier
    token, _ = Token.objects.get_or_create(user=user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    
    # Test pour chaque opérateur
    for operator in SingpayTestConfig.OPERATORS:
        print_info(f"\nTest {operator.upper()}...")
        
        payload = {
            'payment_method': f'{operator}_money',
            'phone_number': SingpayTestConfig.TEST_CLIENT_PHONE,
            'operator': operator,
        }
        
        try:
            response = api_client.post(
                f'/api/v1/orders/{order.id}/payments/init/',
                payload,
                format='json'
            )
            
            print_info(f"  Status: {response.status_code}")
            
            if response.status_code in [200, 201]:
                data = response.json()
                print_ok(f"{operator.upper()} - Réponse valide")
                print_info(f"  Success: {data.get('success')}")
                print_info(f"  Message: {data.get('message')}")
                
                if 'data' in data:
                    payment_data = data['data']
                    print_info(f"  Transaction ID: {payment_data.get('payment', {}).get('transaction_id')}")
                    print_info(f"  Next Steps: {payment_data.get('next_steps')}")
                    
            else:
                print_fail(f"{operator.upper()} - Status {response.status_code}")
                print_info(f"  Erreur: {response.json()}")
                
        except Exception as e:
            print_fail(f"{operator.upper()} - Exception: {e}")

# ============================================================================
# TEST 5: APPEL DIRECT SINGPAY
# ============================================================================

def test_singpay_direct_call(order):
    """Étape 5: Appel direct API Singpay"""
    print_header("TEST 5 - Appel Direct API Singpay")
    
    for operator in SingpayTestConfig.OPERATORS:
        print_info(f"\nTest {operator.upper()}...")
        
        try:
            response = call_singpay_payment(
                operator=operator,
                amount=SingpayTestConfig.TEST_AMOUNT,
                reference=f"TEST_{order.order_number}_{operator.upper()}",
                phone=SingpayTestConfig.TEST_CLIENT_PHONE,
                portefeuille=settings.SINGPAY_WALLET_ID,
                is_transfer=False,
            )
            
            print_info(f"Réponse:\n{json.dumps(response, indent=2, default=str)}")
            
            if response.get('error'):
                print_fail(f"{operator.upper()} - Erreur API: {response.get('error')}")
                if 'missing' in response:
                    print_warn(f"  Config manquante: {response.get('missing')}")
            else:
                print_ok(f"{operator.upper()} - Réponse reçue")
                
        except Exception as e:
            print_fail(f"{operator.upper()} - Exception: {e}")

# ============================================================================
# TEST 6: WEBHOOK SIMULATION
# ============================================================================

def test_webhook_simulation(order):
    """Étape 6: Simuler webhook de confirmation"""
    print_header("TEST 6 - Simulation Webhook Confirmation")
    
    api_client = APIClient()
    
    # Récupérer le paiement créé
    try:
        payment = Payment.objects.filter(order=order).first()
        if not payment:
            print_fail("Aucun Payment créé pour cette commande")
            return
        
        print_ok(f"Payment trouvé: {payment.transaction_id}")
        
        # Simuler webhook Singpay
        webhook_payload = {
            'transaction_id': payment.transaction_id,
            'status': 'SUCCESS',
            'amount': int(SingpayTestConfig.TEST_AMOUNT),
            'reference': f"GABOSHOP_{order.order_number}",
            'transaction': {
                'airtel_money_id': f"AM_{payment.id}",
                'result': 'SUCCESS'
            },
            'status_payload': {
                'success': True,
                'code': '00'
            }
        }
        
        print_info(f"\nPayload webhook:\n{json.dumps(webhook_payload, indent=2)}")
        
        response = api_client.post(
            '/api/v1/orders/{}/payments/webhook/'.format(order.id),
            webhook_payload,
            format='json'
        )
        
        print_info(f"Réponse webhook: {response.status_code}")
        if response.status_code == 200:
            print_ok("Webhook traité")
        else:
            print_fail(f"Erreur webhook: {response.json()}")
        
        # Vérifier statuts finaux
        order.refresh_from_db()
        payment.refresh_from_db()
        
        print_info(f"\nStatuts finaux:")
        print_info(f"  Order: {order.status}")
        print_info(f"  Payment: {payment.status}")
        
    except Exception as e:
        print_fail(f"Erreur webhook: {e}")

# ============================================================================
# TEST 7: VÉRIFICATION BD
# ============================================================================

def test_database_state(order):
    """Étape 7: Vérifier état final BD"""
    print_header("TEST 7 - État BD Final")
    
    try:
        payment = Payment.objects.get(order=order)
        
        print_ok(f"Payment record:")
        print_info(f"  ID: {payment.id}")
        print_info(f"  Order: {payment.order.order_number}")
        print_info(f"  Method: {payment.payment_method}")
        print_info(f"  Status: {payment.status}")
        print_info(f"  Amount: {payment.amount}")
        print_info(f"  Transaction ID: {payment.transaction_id}")
        print_info(f"  Operator Reference: {payment.operator_reference}")
        print_info(f"  Created: {payment.created_at}")
        
    except Payment.DoesNotExist:
        print_fail("Aucun Payment trouvé pour cette commande")

# ============================================================================
# MAIN
# ============================================================================

def main():
    """Exécuter tous les tests"""
    
    print(f"\n{Colors.BOLD}{Colors.INFO}🧪 TEST SINGPAY INTEGRATION{Colors.RESET}")
    print(f"{Colors.INFO}Date: {datetime.now().isoformat()}{Colors.RESET}")
    print(f"{Colors.INFO}Sandbox Singpay: ACTIVE{Colors.RESET}\n")
    
    try:
        # Étape 0: Setup
        user, store, product = setup_test_data()
        
        # Étape 1: Config
        if not test_singpay_config():
            print_fail("Config Singpay incomplète. Arrêt.")
            return
        
        # Étape 2: Phone formatting
        test_phone_formatting()
        
        # Étape 3: Créer commande
        order = test_create_order(user, store, product)
        
        # Étape 4: API Payment Init
        test_payment_init_api(order, user)
        
        # Étape 5: Direct Singpay Call (avec sandbox)
        test_singpay_direct_call(order)
        
        # Étape 6: Webhook Simulation
        test_webhook_simulation(order)
        
        # Étape 7: BD State
        test_database_state(order)
        
        print_header("✅ TESTS COMPLÉTÉS")
        
    except Exception as e:
        print_fail(f"Erreur critique: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
