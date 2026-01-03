"""
Script pour configurer les 3 plans de souscription:
- Free (0F)
- Pro (30 000F)
- Business (50 000F B2C, 80 000F B2B)

Usage:
    python scripts/setup_subscription_plans.py
"""

import os
import django
import sys

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
django.setup()

from payments.models import SubscriptionPlan
from decimal import Decimal


def setup_plans():
    """Configure les 3 plans de souscription"""
    
    print("\n" + "="*70)
    print("  CONFIGURATION DES PLANS DE SOUSCRIPTION")
    print("="*70)
    
    # ===========================
    # PLAN FREE
    # ===========================
    print("\n[1/3] Plan FREE...")
    free_plan, created = SubscriptionPlan.objects.update_or_create(
        plan_type='free',
        defaults={
            'name': 'Free',
            'slug': 'free',
            'price': Decimal('0.00'),
            'max_products': 20,
            'max_orders_per_month': 50,
            'can_access_b2b': False,
            'has_b2b_visibility': False,
            'can_sponsor_products': False,
            'has_statistics': False,
            'has_custom_page': False,
            'has_priority_support': False,
            'priority_listing': 0,
            'commission_multiplier': Decimal('1.00'),  # Taux standard
            'description': 'Plan gratuit avec limitations pour démarrer',
            'features_json': [
                'Jusqu\'à 20 produits',
                'Jusqu\'à 50 commandes/mois',
                'Dashboard basique',
                'Commission standard par catégorie'
            ],
            'is_active': True
        }
    )
    status = "CREE" if created else "MIS A JOUR"
    print(f"   [{status}] Plan Free: 0 F/mois")
    print(f"      - Max produits: 20")
    print(f"      - Max commandes/mois: 50")
    print(f"      - Acces B2B: Non")
    print(f"      - Commission multiplier: 1.00 (standard)")
    
    # ===========================
    # PLAN PRO
    # ===========================
    print("\n[2/3] Plan PRO...")
    pro_plan, created = SubscriptionPlan.objects.update_or_create(
        plan_type='pro',
        defaults={
            'name': 'Pro',
            'slug': 'pro',
            'price': Decimal('30000.00'),
            'max_products': None,  # Illimité
            'max_orders_per_month': None,  # Illimité
            'can_access_b2b': False,  # Pas d'accès B2B
            'has_b2b_visibility': False,
            'can_sponsor_products': False,
            'has_statistics': True,  # Analytics basiques
            'has_custom_page': False,
            'has_priority_support': True,
            'priority_listing': 50,
            'commission_multiplier': Decimal('0.50'),  # 50% de réduction
            'description': 'Plan professionnel avec produits illimités et commission réduite',
            'features_json': [
                'Produits illimités',
                'Commandes illimitées',
                'Analytics basiques',
                'Support prioritaire',
                'Commission réduite de 50%'
            ],
            'is_active': True
        }
    )
    status = "CREE" if created else "MIS A JOUR"
    print(f"   [{status}] Plan Pro: 30 000 F/mois")
    print(f"      - Produits: Illimites")
    print(f"      - Commandes: Illimitees")
    print(f"      - Acces B2B: Non")
    print(f"      - Commission multiplier: 0.50 (reduction 50%)")
    print(f"      - Analytics: Basiques")
    
    # ===========================
    # PLAN BUSINESS
    # ===========================
    print("\n[3/3] Plan BUSINESS...")
    print("   Note: Prix dynamique selon type de store:")
    print("         - B2C: 50 000 F/mois")
    print("         - B2B: 80 000 F/mois")
    
    business_plan, created = SubscriptionPlan.objects.update_or_create(
        plan_type='business',
        defaults={
            'name': 'Business',
            'slug': 'business',
            'price': Decimal('50000.00'),  # Prix de base (B2C)
            'max_products': None,  # Illimité
            'max_orders_per_month': None,  # Illimité
            'can_access_b2b': True,  # Accès B2B pour B2C
            'has_b2b_visibility': True,  # Visibilité maximale pour B2B
            'can_sponsor_products': True,
            'has_statistics': True,  # Analytics avancés
            'has_custom_page': True,
            'has_priority_support': True,
            'priority_listing': 100,  # Priorité maximale
            'commission_multiplier': Decimal('0.25'),  # Base pour calcul (peut être override par catégorie)
            'description': 'Plan Business premium avec tous les avantages',
            'features_json': [
                'Produits illimités',
                'Commandes illimitées',
                'Accès complet B2B (approvisionnement pour B2C)',
                'Visibilité maximale (pour B2B)',
                'Analytics avancés + prévisions',
                'Support prioritaire',
                'Exports PDF/Excel',
                'Multi-utilisateurs',
                'Historique complet',
                'Gestion avancée (retours, remboursements)',
                'Commission réduite (0% alimentaire B2C, 2% reste)',
                'Frais de service B2B: 0 F',
                'Badge Business/Grossiste Business',
                'Accès anticipé nouvelles fonctionnalités'
            ],
            'is_active': True
        }
    )
    status = "CREE" if created else "MIS A JOUR"
    print(f"   [{status}] Plan Business: 50 000 F/mois (B2C) ou 80 000 F/mois (B2B)")
    print(f"      - Produits: Illimites")
    print(f"      - Commandes: Illimitees")
    print(f"      - Acces B2B: Oui (pour B2C)")
    print(f"      - Visibilite B2B: Maximale (pour B2B)")
    print(f"      - Commission: 0% alimentaire (B2C), 2% reste")
    print(f"      - Service fee B2B: 0 F")
    print(f"      - Analytics: Avances")
    
    print("\n" + "="*70)
    print("  [OK] PLANS CONFIGURES AVEC SUCCES")
    print("="*70)
    print("\nRESUME:")
    print(f"  - Free: {SubscriptionPlan.objects.filter(plan_type='free').count()} plan")
    print(f"  - Pro: {SubscriptionPlan.objects.filter(plan_type='pro').count()} plan")
    print(f"  - Business: {SubscriptionPlan.objects.filter(plan_type='business').count()} plan")
    print("\n")


if __name__ == '__main__':
    try:
        setup_plans()
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERREUR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

