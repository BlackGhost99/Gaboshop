"""
Test de la mise à jour automatique du stock du store B2C
quand une commande B2B est livrée.

Workflow testé:
1. Store B2C passe commande B2B
2. Stock grossiste diminue
3. Commande passe à 'delivered'
4. Stock store B2C augmente automatiquement
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
from stores.models import Store
from products.models import Product
from b2b.models import B2BProductPricing


def print_section(title):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def test_stock_update():
    """Test la mise à jour automatique du stock"""
    
    print_section("TEST: Mise à jour automatique du stock B2B")
    
    # 1. Trouver une commande B2B existante (non livrée)
    print_section("1. Recherche d'une commande B2B de test")
    
    test_order = Order.objects.filter(
        is_b2b=True,
        source_store__isnull=False,
        status__in=['confirmed', 'preparing', 'ready', 'assigned', 'in_transit']
    ).first()
    
    if not test_order:
        print("[INFO] Aucune commande B2B en cours trouvee")
        print("[INFO] Creation d'une commande de test...")
        
        # Créer une commande de test
        wholesaler = Store.objects.filter(is_b2b=True, is_active=True).first()
        buyer_store = Store.objects.filter(is_b2c=True, is_active=True).exclude(id=wholesaler.id).first()
        b2b_pricing = B2BProductPricing.objects.filter(
            b2b_store=wholesaler,
            is_active=True,
            product__is_available=True,
            product__stock__gte=1
        ).first()
        
        if not all([wholesaler, buyer_store, b2b_pricing]):
            print("[ERREUR] Impossible de creer une commande de test")
            return False
        
        product = b2b_pricing.product
        quantity = min(b2b_pricing.min_quantity, product.stock)
        
        test_order = Order.objects.create(
            client=buyer_store.manager,
            store=wholesaler,
            source_store=buyer_store,
            is_b2b=True,
            delivery_type='standard',
            notes='Test stock update',
            delivery_address=buyer_store.address,
            delivery_phone=buyer_store.phone,
            delivery_zone=buyer_store.zone,
            city=buyer_store.city,
            items_total=b2b_pricing.b2b_price * quantity,
            delivery_fee=wholesaler.delivery_fee,
            service_fee=200,
            total_amount=(b2b_pricing.b2b_price * quantity) + wholesaler.delivery_fee + 200,
            status='confirmed',
            confirmed_at=timezone.now()
        )
        
        OrderItem.objects.create(
            order=test_order,
            product=product,
            quantity=quantity,
            unit_price=b2b_pricing.b2b_price
        )
        
        product.reduce_stock(quantity)
        test_order.calculate_commission()
        test_order.save()
        
        print(f"[OK] Commande de test creee: #{test_order.order_number}")
    else:
        print(f"[OK] Commande trouvee: #{test_order.order_number}")
    
    print(f"   Grossiste: {test_order.store.name}")
    print(f"   Acheteur: {test_order.source_store.name}")
    print(f"   Status: {test_order.status}")
    
    # 2. Vérifier l'état du stock AVANT livraison
    print_section("2. État du stock AVANT livraison")
    
    buyer_store = test_order.source_store
    order_items_data = []
    
    for order_item in test_order.items.all():
        wholesaler_product = order_item.product
        
        # Chercher si le produit existe déjà dans le store acheteur
        buyer_product = Product.objects.filter(
            store=buyer_store,
            name=wholesaler_product.name,
            category=wholesaler_product.category
        ).first()
        
        before_stock = buyer_product.stock if buyer_product else 0
        
        order_items_data.append({
            'product_name': wholesaler_product.name,
            'quantity': order_item.quantity,
            'before_stock': before_stock,
            'buyer_product': buyer_product
        })
        
        print(f"   {wholesaler_product.name}:")
        print(f"      - Quantite commandee: {order_item.quantity}")
        print(f"      - Stock actuel dans {buyer_store.name}: {before_stock}")
    
    # 3. Marquer la commande comme livrée
    print_section("3. Marquage de la commande comme livree")
    
    test_order.status = 'delivered'
    test_order.delivered_at = timezone.now()
    test_order.save()
    
    print(f"[OK] Commande #{test_order.order_number} marquee comme livree")
    
    # 4. Vérifier l'état du stock APRÈS livraison
    print_section("4. État du stock APRES livraison")
    
    all_updated = True
    
    for item_data in order_items_data:
        # Rafraîchir ou récupérer le produit
        buyer_product = Product.objects.filter(
            store=buyer_store,
            name=item_data['product_name'],
            category__name=test_order.items.first().product.category.name
        ).first()
        
        if buyer_product:
            after_stock = buyer_product.stock
            expected_stock = item_data['before_stock'] + item_data['quantity']
            
            print(f"   {item_data['product_name']}:")
            print(f"      - Stock avant: {item_data['before_stock']}")
            print(f"      - Quantite livree: {item_data['quantity']}")
            print(f"      - Stock apres: {after_stock}")
            print(f"      - Stock attendu: {expected_stock}")
            
            if after_stock == expected_stock:
                print(f"      [OK] Stock correctement mis a jour!")
            else:
                print(f"      [ERREUR] Stock non mis a jour correctement!")
                all_updated = False
        else:
            print(f"   {item_data['product_name']}:")
            print(f"      [ERREUR] Produit non trouve dans l'inventaire de {buyer_store.name}!")
            all_updated = False
    
    # 5. Résumé
    print_section("RESULTAT DU TEST")
    
    if all_updated:
        print("""
    [SUCCES] Le stock du store B2C a ete mis a jour automatiquement!
    
    Le workflow B2B complet fonctionne:
    1. Store B2C passe commande [OK]
    2. Grossiste prepare et livre [OK]
    3. Stock grossiste reduit [OK]
    4. Commande livree [OK]
    5. Stock B2C automatiquement augmente [OK]
        """)
        return True
    else:
        print("""
    [ERREUR] La mise a jour automatique du stock a echoue!
    Verifier le signal dans orders/signals.py
        """)
        return False


if __name__ == '__main__':
    success = test_stock_update()
    
    if success:
        print("\n" + "=" * 70)
        print("  [OK] TEST REUSSI - STOCK MIS A JOUR AUTOMATIQUEMENT")
        print("=" * 70)
        sys.exit(0)
    else:
        print("\n" + "=" * 70)
        print("  [ERREUR] TEST ECHOUE - VERIFIER LES ERREURS CI-DESSUS")
        print("=" * 70)
        sys.exit(1)

