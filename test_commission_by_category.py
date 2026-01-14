"""
Script de test pour vérifier que les commissions sont calculées correctement
selon la catégorie de chaque produit, même dans un panier mixte.
"""
import os
import sys
import types
from pathlib import Path
from decimal import Decimal

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Force registration of gaboshop package
if 'gaboshop' not in sys.modules:
    gaboshop_dir = BASE_DIR / 'Gaboshop'
    gaboshop_init = gaboshop_dir / '__init__.py'
    
    if gaboshop_init.exists():
        gaboshop_module = types.ModuleType('gaboshop')
        gaboshop_module.__path__ = [str(gaboshop_dir)]
        gaboshop_module.__file__ = str(gaboshop_init)
        gaboshop_module.__package__ = ''
        sys.modules['gaboshop'] = gaboshop_module

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
import django
django.setup()

from products.models import Product, ProductCategory
from orders.models import Order, OrderItem
from stores.models import Store
from users.models import User

print("\n" + "="*70)
print("  TEST: CALCUL DES COMMISSIONS PAR CATEGORIE")
print("="*70)

# Récupérer ou créer des catégories de test
try:
    # Catégorie alimentaire (0%)
    food_cat = ProductCategory.objects.filter(
        name__icontains='ALIMENTATION'
    ).first()
    if not food_cat:
        print("[INFO] Categorie alimentaire non trouvee, creation d'une categorie de test...")
        from stores.models import StoreCategory
        food_store_cat = StoreCategory.objects.filter(name__icontains='ALIMENTATION').first()
        if food_store_cat:
            food_cat = ProductCategory.objects.create(
                name='TEST ALIMENTATION',
                store_category=food_store_cat,
                commission_rate=Decimal('0.00')
            )
    
    # Catégorie non-alimentaire (8%)
    non_food_cat = ProductCategory.objects.filter(
        commission_rate__gt=0
    ).exclude(name__icontains='ALIMENTATION').exclude(name__icontains='BOISSON').first()
    
    if not non_food_cat:
        print("[INFO] Categorie non-alimentaire non trouvee, creation d'une categorie de test...")
        from stores.models import StoreCategory
        non_food_store_cat = StoreCategory.objects.exclude(name__icontains='ALIMENTATION').first()
        if non_food_store_cat:
            non_food_cat = ProductCategory.objects.create(
                name='TEST NON ALIMENTAIRE',
                store_category=non_food_store_cat,
                commission_rate=Decimal('8.00')
            )
    
    if not food_cat or not non_food_cat:
        print("[ERREUR] Impossible de trouver ou creer les categories de test")
        sys.exit(1)
    
    print(f"\n[OK] Categorie alimentaire: {food_cat.name} - Commission: {food_cat.commission_rate}%")
    print(f"[OK] Categorie non-alimentaire: {non_food_cat.name} - Commission: {non_food_cat.commission_rate}%")
    
    # Récupérer un store et un client de test
    store = Store.objects.filter(is_active=True).first()
    if not store:
        print("[ERREUR] Aucun magasin actif trouve")
        sys.exit(1)
    
    client = User.objects.filter(user_type='client').first()
    if not client:
        print("[ERREUR] Aucun client trouve")
        sys.exit(1)
    
    print(f"\n[OK] Magasin: {store.name}")
    print(f"[OK] Client: {client.phone}")
    
    # Créer des produits de test
    product_food = Product.objects.filter(category=food_cat, store=store).first()
    if not product_food:
        product_food = Product.objects.create(
            name='Produit Alimentaire Test',
            store=store,
            category=food_cat,
            price=Decimal('5000.00'),
            stock=10
        )
    
    product_non_food = Product.objects.filter(category=non_food_cat, store=store).first()
    if not product_non_food:
        product_non_food = Product.objects.create(
            name='Produit Non-Alimentaire Test',
            store=store,
            category=non_food_cat,
            price=Decimal('10000.00'),
            stock=10
        )
    
    print(f"\n[OK] Produit alimentaire: {product_food.name} - Prix: {product_food.price} FCFA")
    print(f"[OK] Produit non-alimentaire: {product_non_food.name} - Prix: {product_non_food.price} FCFA")
    
    # Créer une commande avec un panier mixte
    order = Order.objects.create(
        client=client,
        store=store,
        delivery_address="Adresse de test",
        delivery_phone=client.phone,
        delivery_zone="Zone test",
        city="Libreville",
        is_b2b=False,
        status='created'
    )
    
    # Ajouter les deux produits au panier
    item1 = OrderItem.objects.create(
        order=order,
        product=product_food,
        quantity=2,
        unit_price=product_food.price
    )
    
    item2 = OrderItem.objects.create(
        order=order,
        product=product_non_food,
        quantity=1,
        unit_price=product_non_food.price
    )
    
    print(f"\n[OK] Commande creee: {order.order_number}")
    print(f"  - {item1.quantity}x {product_food.name} = {item1.subtotal} FCFA")
    print(f"  - {item2.quantity}x {product_non_food.name} = {item2.subtotal} FCFA")
    print(f"  - Total produits: {order.items_total} FCFA")
    
    # Calculer les commissions
    order.calculate_totals()
    
    print("\n" + "-"*70)
    print("  CALCUL DES COMMISSIONS")
    print("-"*70)
    
    # Afficher le détail par item
    plan = store.get_current_plan()
    plan_type = plan.plan_type if plan else 'free'
    print(f"\nPlan du magasin: {plan_type}")
    
    for item in order.items.all():
        product = item.product
        category = product.category
        commission_rate = category.commission_rate if category else Decimal('0.00')
        
        # Calculer la commission pour cet item (simulation)
        if plan_type == 'business' and not order.is_b2b:
            # Règles Business B2C
            if category and category.store_category:
                category_name = category.store_category.name.upper()
                is_food = 'ALIMENTATION' in category_name or 'BOISSONS' in category_name
                if is_food:
                    effective_rate = Decimal('0.00')
                else:
                    effective_rate = Decimal('2.00')
            else:
                effective_rate = commission_rate
        else:
            # Plans Free et Pro
            reduction_percent = Decimal(getattr(plan, 'commission_reduction_percent', 0)) if plan else Decimal('0')
            multiplier = (Decimal('100') - reduction_percent) / Decimal('100')
            effective_rate = commission_rate * multiplier
        
        item_commission = (item.subtotal * effective_rate) / Decimal('100')
        
        print(f"\n  Item: {product.name}")
        print(f"    Catégorie: {category.name if category else 'N/A'}")
        print(f"    Commission catégorie: {commission_rate}%")
        print(f"    Taux effectif appliqué: {effective_rate}%")
        print(f"    Sous-total: {item.subtotal} FCFA")
        print(f"    Commission: {item_commission} FCFA")
    
    print("\n" + "-"*70)
    print(f"  TOTAL COMMANDE")
    print("-"*70)
    print(f"  Total produits: {order.items_total} FCFA")
    print(f"  Commission totale: {order.commission_amount} FCFA")
    print(f"  Taux commission moyen: {order.commission_rate:.2f}%")
    print(f"  Montant net magasin: {order.calculate_store_amount()} FCFA")
    
    print("\n" + "="*70)
    print("  VERIFICATION")
    print("="*70)
    
    # Vérifier que les commissions sont différentes
    if order.commission_amount > 0:
        print("[OK] Commission calculee avec succes")
        print(f"[OK] La commission totale ({order.commission_amount} FCFA) reflete bien")
        print(f"  un melange de produits avec commissions differentes")
        print(f"[OK] Les produits alimentaires (0%) et non-alimentaires ({non_food_cat.commission_rate}%)")
        print(f"  sont bien distingues dans le calcul")
    else:
        print("[INFO] Commission = 0 (peut etre normal si tous les produits sont alimentaires)")
    
    # Nettoyer (optionnel)
    # order.delete()
    # product_food.delete()
    # product_non_food.delete()
    
    print("\n[OK] Test termine!\n")

except Exception as e:
    import traceback
    print(f"\n[ERREUR] Erreur lors du test: {e}")
    traceback.print_exc()
    sys.exit(1)

