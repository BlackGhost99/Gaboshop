"""
Script pour créer les dépenses manquantes pour les commandes B2B déjà livrées
"""
import os
import sys
import django

# Fix encoding for Windows console
if sys.platform == 'win32':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
django.setup()

from orders.models import Order
from finance.models import Expense, Supplier
from django.utils import timezone
from decimal import Decimal

def create_missing_expenses():
    """Crée les dépenses manquantes pour les commandes B2B livrées"""
    
    # Trouver toutes les commandes B2B livrées sans dépense associée
    b2b_orders = Order.objects.filter(
        is_b2b=True,
        status='delivered',
        source_store__isnull=False
    ).exclude(
        expense_record__isnull=False
    ).select_related('store', 'source_store', 'source_store__manager')
    
    print(f"[INFO] Trouve {b2b_orders.count()} commande(s) B2B livree(s) sans depense associee\n")
    
    created_count = 0
    error_count = 0
    
    for order in b2b_orders:
        try:
            # Vérifier si une dépense existe déjà (double vérification)
            if Expense.objects.filter(b2b_order=order).exists():
                print(f"[SKIP] Commande {order.order_number}: Depense deja existante, ignoree")
                continue
            
            # Get or create supplier
            supplier, created = Supplier.objects.get_or_create(
                store=order.source_store,
                name=order.store.name,
                defaults={
                    'contact_person': order.store.manager.get_full_name() if order.store.manager else None,
                    'phone': getattr(order.store, 'phone', None),
                }
            )
            
            if created:
                print(f"  [OK] Fournisseur cree: {supplier.name}")
            
            # Determine expense date
            if order.delivered_at:
                expense_date = order.delivered_at.date() if hasattr(order.delivered_at, 'date') else order.delivered_at
            elif order.updated_at:
                expense_date = order.updated_at.date() if hasattr(order.updated_at, 'date') else order.updated_at
            else:
                expense_date = timezone.now().date()
            
            # Create expense
            expense = Expense.objects.create(
                store=order.source_store,
                expense_type='APPROVISIONNEMENT',
                supplier=supplier,
                supplier_name=order.store.name,
                reference=order.order_number,
                amount=order.total_amount,
                currency='XAF',
                expense_date=expense_date,
                payment_method='AUTRE',
                payment_status='PAID',
                notes=f"Commande B2B #{order.order_number} - Auto-trackee (retroactive)",
                b2b_order=order,
                created_by=order.source_store.manager if order.source_store.manager else None,
            )
            
            print(f"[OK] Depense creee pour {order.order_number}: {expense.amount} FCFA")
            print(f"   Store: {order.source_store.name} -> Fournisseur: {order.store.name}")
            print(f"   Date: {expense_date}\n")
            
            created_count += 1
            
        except Exception as e:
            print(f"[ERROR] Erreur pour la commande {order.order_number}: {str(e)}\n")
            error_count += 1
    
    print(f"\n{'='*60}")
    print(f"[RESUME]")
    print(f"   Depenses creees: {created_count}")
    print(f"   Erreurs: {error_count}")
    print(f"   Total commandes traitees: {b2b_orders.count()}")
    print(f"{'='*60}")

if __name__ == '__main__':
    create_missing_expenses()

