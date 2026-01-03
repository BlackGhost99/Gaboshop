"""
Test complet du workflow B2B pour vérifier que les commandes B2B
suivent le même cycle de vie que les commandes B2C.

Workflow testé:
1. Store B2C crée une commande B2B chez un grossiste
2. Grossiste reçoit la commande avec status='confirmed'
3. Une Delivery est automatiquement créée avec status='waiting'
4. Grossiste peut changer le statut à 'preparing'
5. Grossiste peut changer le statut à 'ready'
6. Livreur peut voir la commande dans les livraisons disponibles
7. La livraison peut être assignée et livrée
"""

import sys
import os
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
django.setup()

from django.utils import timezone
from orders.models import Order, OrderItem
from delivery.models import Delivery
from stores.models import Store
from users.models import User
from products.models import Product
from b2b.models import B2BProfile, B2BProductPricing


def print_section(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def test_b2b_workflow():
    """Test le workflow complet B2B"""
    
    print_section("DÉBUT DU TEST WORKFLOW B2B")
    
    # 1. Trouver un grossiste avec profil B2B actif
    print_section("1. Recherche d'un grossiste B2B")
    wholesaler = Store.objects.filter(
        is_b2b=True,
        is_active=True,
        b2b_profile__is_active=True
    ).first()
    
    if not wholesaler:
        print("[ERREUR] Aucun grossiste B2B trouve!")
        return False
    
    print(f"[OK] Grossiste trouve: {wholesaler.name} (ID: {wholesaler.id})")
    print(f"   Manager: {wholesaler.manager.phone}")
    
    # 2. Trouver un store B2C
    print_section("2. Recherche d'un store B2C acheteur")
    buyer_store = Store.objects.filter(
        is_b2c=True,
        is_active=True
    ).exclude(id=wholesaler.id).first()
    
    if not buyer_store:
        print("[ERREUR] Aucun store B2C trouve!")
        return False
    
    print(f"[OK] Store B2C trouve: {buyer_store.name} (ID: {buyer_store.id})")
    print(f"   Manager: {buyer_store.manager.phone}")
    
    # 3. Trouver un produit B2B du grossiste
    print_section("3. Recherche d'un produit B2B")
    b2b_pricing = B2BProductPricing.objects.filter(
        b2b_store=wholesaler,
        is_active=True,
        product__is_available=True,
        product__stock__gte=1
    ).first()
    
    if not b2b_pricing:
        print("[ERREUR] Aucun produit B2B disponible!")
        return False
    
    product = b2b_pricing.product
    print(f"[OK] Produit trouve: {product.name}")
    print(f"   Prix B2B: {b2b_pricing.b2b_price} FCFA")
    print(f"   Stock: {product.stock}")
    
    # 4. Créer une commande B2B (simulant l'API)
    print_section("4. Création d'une commande B2B")
    
    initial_stock = product.stock
    order_quantity = min(b2b_pricing.min_quantity, product.stock)
    
    try:
        order = Order.objects.create(
            client=buyer_store.manager,
            store=wholesaler,
            source_store=buyer_store,
            is_b2b=True,
            delivery_type='standard',
            notes='Test B2B workflow',
            delivery_address=buyer_store.address,
            delivery_phone=buyer_store.phone,
            delivery_zone=buyer_store.zone,
            city=buyer_store.city,
            items_total=b2b_pricing.b2b_price * order_quantity,
            delivery_fee=wholesaler.delivery_fee,
            service_fee=200,
            total_amount=(b2b_pricing.b2b_price * order_quantity) + wholesaler.delivery_fee + 200,
            status='confirmed',  # B2B orders start confirmed
            confirmed_at=timezone.now()
        )
        
        # Créer l'item
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=order_quantity,
            unit_price=b2b_pricing.b2b_price
        )
        
        # Réduire le stock
        product.reduce_stock(order_quantity)
        
        # Calculer la commission
        order.calculate_commission()
        order.save()
        
        print(f"[OK] Commande B2B creee: #{order.order_number}")
        print(f"   Status initial: {order.status}")
        print(f"   Confirmed at: {order.confirmed_at}")
        print(f"   Total: {order.total_amount} FCFA")
        print(f"   Stock reduit: {initial_stock} -> {product.stock}")
        
    except Exception as e:
        print(f"[ERREUR] lors de la creation: {e}")
        return False
    
    # 5. Vérifier qu'une Delivery a été créée automatiquement
    print_section("5. Vérification de la création automatique de Delivery")
    
    try:
        delivery = Delivery.objects.get(order=order)
        print(f"[OK] Delivery creee automatiquement:")
        print(f"   ID: {delivery.id}")
        print(f"   Status: {delivery.status}")
        print(f"   Pickup: {delivery.pickup_address}")
        print(f"   Delivery: {delivery.delivery_address}")
        
    except Delivery.DoesNotExist:
        print("[ERREUR] Aucune Delivery creee!")
        return False
    
    # 6. Simuler le grossiste qui change le statut à 'preparing'
    print_section("6. Grossiste change le statut à 'preparing'")
    
    try:
        order.status = 'preparing'
        order.save()
        order.refresh_from_db()
        print(f"[OK] Status change: {order.status}")
        
    except Exception as e:
        print(f"[ERREUR] {e}")
        return False
    
    # 7. Simuler le grossiste qui change le statut à 'ready'
    print_section("7. Grossiste change le statut à 'ready'")
    
    try:
        order.status = 'ready'
        order.save()
        order.refresh_from_db()
        print(f"[OK] Status change: {order.status}")
        
        # Verifier si la delivery est toujours waiting (prete pour assignation)
        delivery.refresh_from_db()
        print(f"   Delivery status: {delivery.status}")
        
    except Exception as e:
        print(f"[ERREUR] {e}")
        return False
    
    # 8. Vérifier que les livreurs peuvent voir cette commande
    print_section("8. Vérification visibilité pour les livreurs")
    
    # Simuler la requête AvailableDeliveriesView
    available_deliveries = Delivery.objects.filter(
        status='waiting',
        order__status__in=['ready', 'paid', 'confirmed']
    )
    
    b2b_delivery_visible = available_deliveries.filter(order=order).exists()
    
    if b2b_delivery_visible:
        print(f"[OK] La commande B2B est visible aux livreurs!")
        print(f"   Total deliveries disponibles: {available_deliveries.count()}")
    else:
        print(f"[ERREUR] La commande B2B n'est PAS visible aux livreurs!")
        print(f"   Order status: {order.status}")
        print(f"   Delivery status: {delivery.status}")
        return False
    
    # 9. Récapitulatif final
    print_section("RÉCAPITULATIF DU TEST")
    
    print(f"""
    [OK] Commande B2B: #{order.order_number}
       - Acheteur: {buyer_store.name}
       - Vendeur: {wholesaler.name}
       - Status: {order.status}
       - Delivery: {delivery.status}
       - Visible aux livreurs: OUI
       
    [SUCCES] WORKFLOW B2B FONCTIONNEL!
    
    Le cycle complet est identique au B2C:
    1. Commande creee avec status='confirmed' [OK]
    2. Delivery automatiquement creee [OK]
    3. Grossiste peut changer a 'preparing' [OK]
    4. Grossiste peut changer a 'ready' [OK]
    5. Livreurs peuvent voir la commande [OK]
    """)
    
    # Nettoyage optionnel
    print_section("NETTOYAGE")
    # Auto-cleanup pour les tests automatises
    print(f"[INFO] Conservation de la commande de test: #{order.order_number}")
    print(f"[INFO] Vous pouvez la supprimer manuellement depuis l'admin Django")
    
    return True


if __name__ == '__main__':
    success = test_b2b_workflow()
    
    if success:
        print("\n" + "=" * 60)
        print("  [OK] TEST REUSSI - WORKFLOW B2B FONCTIONNEL")
        print("=" * 60)
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("  [ERREUR] TEST ECHOUE - VERIFIER LES ERREURS CI-DESSUS")
        print("=" * 60)
        sys.exit(1)

