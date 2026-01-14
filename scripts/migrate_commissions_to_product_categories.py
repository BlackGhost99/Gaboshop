"""
Script pour migrer les commissions de CategoryCommission (lié à StoreCategory) 
vers ProductCategory.commission_rate.

Ce script doit être exécuté après la migration qui ajoute le champ commission_rate
à ProductCategory.
"""
import os
import django
import sys
import types
from pathlib import Path
from decimal import Decimal

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Force registration of gaboshop package before Django is loaded
# This allows 'import gaboshop' to work even though directory is 'Gaboshop'
if 'gaboshop' not in sys.modules:
    gaboshop_dir = BASE_DIR / 'Gaboshop'
    gaboshop_init = gaboshop_dir / '__init__.py'
    
    if gaboshop_init.exists():
        # Create and register the parent gaboshop module
        gaboshop_module = types.ModuleType('gaboshop')
        gaboshop_module.__path__ = [str(gaboshop_dir)]
        gaboshop_module.__file__ = str(gaboshop_init)
        gaboshop_module.__package__ = ''
        sys.modules['gaboshop'] = gaboshop_module

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
django.setup()

from products.models import ProductCategory
from payments.models import CategoryCommission
from stores.models import StoreCategory

print("\n" + "="*70)
print("  MIGRATION DES COMMISSIONS VERS PRODUCTCATEGORY")
print("="*70)

migrated = 0
skipped = 0
not_found = 0
default_applied = 0

# Taux par défaut si aucune commission n'est trouvée
DEFAULT_COMMISSION_RATE = Decimal('8.00')

for product_category in ProductCategory.objects.all():
    commission_rate = None
    
    # Essayer de récupérer la commission depuis CategoryCommission via store_category
    if product_category.store_category:
        try:
            category_commission = CategoryCommission.objects.get(
                store_category=product_category.store_category
            )
            commission_rate = Decimal(category_commission.base_rate)
            product_category.commission_rate = commission_rate
            product_category.save()
            print(f"[OK] Migre: {product_category.name} ({product_category.store_category.name}) -> {commission_rate}%")
            migrated += 1
        except CategoryCommission.DoesNotExist:
            # Si pas de CategoryCommission, utiliser le taux par défaut
            product_category.commission_rate = DEFAULT_COMMISSION_RATE
            product_category.save()
            print(f"[DEF] Defaut: {product_category.name} ({product_category.store_category.name}) -> {DEFAULT_COMMISSION_RATE}% (pas de CategoryCommission)")
            default_applied += 1
    else:
        # Si pas de store_category, utiliser le taux par défaut
        product_category.commission_rate = DEFAULT_COMMISSION_RATE
        product_category.save()
        print(f"[DEF] Defaut: {product_category.name} (pas de store_category) -> {DEFAULT_COMMISSION_RATE}%")
        default_applied += 1

print("\n" + "="*70)
print("  RESUME DE LA MIGRATION")
print("="*70)
print(f"  Categories migrees depuis CategoryCommission: {migrated}")
print(f"  Categories avec taux par defaut: {default_applied}")
print(f"  Total traite: {migrated + default_applied}")
print("="*70)
print("\n[OK] Migration terminee!\n")

