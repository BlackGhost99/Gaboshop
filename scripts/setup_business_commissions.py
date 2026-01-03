"""
Script pour configurer les commissions de base par catégorie.

Pour le plan Business, les règles spéciales seront appliquées dans le code:
- B2C alimentaire: 0%
- B2C autre: 2%
- B2B tout: 2%

Usage:
    python scripts/setup_business_commissions.py
"""

import os
import django
import sys

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
django.setup()

from payments.models import CategoryCommission
from stores.models import StoreCategory
from decimal import Decimal


def setup_commissions():
    """Configure les commissions de base par catégorie"""
    
    print("\n" + "="*70)
    print("  CONFIGURATION DES COMMISSIONS PAR CATEGORIE")
    print("="*70)
    
    # Taux de base par défaut (pour plans Free et Pro)
    default_rate = Decimal('8.00')  # 8%
    
    categories = StoreCategory.objects.all()
    
    print(f"\n[INFO] Configuration de {categories.count()} categories...")
    
    for category in categories:
        comm, created = CategoryCommission.objects.update_or_create(
            store_category=category,
            defaults={
                'base_rate': default_rate,
                'notes': 'Taux de base. Pour Business: 0% si alimentaire B2C, 2% sinon.'
            }
        )
        status = "CREE" if created else "MIS A JOUR"
        print(f"   [{status}] {category.name}: {comm.base_rate}%")
    
    print("\n" + "="*70)
    print("  [OK] COMMISSIONS CONFIGUREES")
    print("="*70)
    print("\nNOTE IMPORTANTE:")
    print("  Les règles spécifiques du plan Business sont appliquées")
    print("  dynamiquement dans le code de calcul de commission:")
    print("  - B2C alimentaire: 0%")
    print("  - B2C autre: 2%")
    print("  - B2B tout: 2%")
    print("\n")


if __name__ == '__main__':
    try:
        setup_commissions()
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERREUR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

