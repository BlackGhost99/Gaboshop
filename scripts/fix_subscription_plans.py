#!/usr/bin/env python
# Script de correction complète des plans d'abonnement B2C et B2B
# Ce script aligne tous les plans avec les spécifications correctes

import os
import sys
import django
from decimal import Decimal

# Setup Django
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from payments.models import SubscriptionPlan
from b2b.models.subscription import B2BSubscriptionPlan

print("=" * 70)
print("  CORRECTION COMPLETE DES PLANS D'ABONNEMENT")
print("=" * 70)
print()

# Fonction pour comparer et afficher les changements
def compare_and_update(plan, defaults, plan_name):
    """Compare les valeurs actuelles avec les nouvelles et affiche les changements"""
    changes = []
    for key, new_value in defaults.items():
        if key == 'features_json':
            # Pour features_json, comparer les listes
            current_value = getattr(plan, key, [])
            if current_value != new_value:
                changes.append(f"  - {key}: {current_value} -> {new_value}")
        else:
            current_value = getattr(plan, key, None)
            if current_value != new_value:
                changes.append(f"  - {key}: {current_value} -> {new_value}")
    
    if changes:
        print(f"[MODIFICATION] Plan {plan_name}:")
        for change in changes:
            print(change)
        return True
    return False

# ============================================================================
# CORRECTION DES PLANS B2C
# ============================================================================

print("=" * 70)
print("  CORRECTION DES PLANS B2C (Free, Pro, Business)")
print("=" * 70)
print()

# ========== PLAN FREE ==========
free_defaults = {
    'name': 'Free',
    'slug': 'free',
    'price': Decimal('0.00'),
    
    # Limites
    'max_products': 20,
    'max_orders_per_month': 50,
    'max_products_non_food': 5,
    
    # Frais de service
    'service_fee_client_amount': 500,
    'service_fee_to_wholesaler_amount': 1000,
    
    # Commissions
    'commission_reduction_percent': 0,
    'commission_multiplier': Decimal('1.00'),
    
    # Fonctionnalités
    'can_sell_non_food_products': True,
    'can_access_b2b': False,
    'has_b2b_visibility': False,
    'can_offer_express_delivery': False,
    'has_advanced_delivery_tracking': False,
    'has_statistics': False,
    'has_priority_support': False,
    'has_custom_page': False,
    'can_sponsor_products': False,
    'priority_listing': 0,
    
    # Rapports et Exports
    'can_view_basic_reports': True,
    'can_view_detailed_reports': False,
    'can_export_excel': False,
    'can_export_pdf': False,
    'history_limit_days': 30,
    
    # Finance B2B
    'can_view_finance_basic': False,
    'can_view_finance_detailed': False,
    'can_export_finance_csv': False,
    'can_export_finance_pdf': False,
    'finance_history_limit_days': None,
    
    # Quotas B2B
    'max_b2b_suppliers': None,
    'max_b2b_monthly_orders': None,
    
    # Visibilité B2B
    'b2b_catalog_priority': 0,
    'b2b_featured_access': False,
    
    # Type de magasin
    'applies_to': 'b2c',
    
    # Support
    'support_level': 'standard',
    
    'description': 'Gratuit pour démarrer, avec limitations.',
    'features_json': [
        "20 produits maximum",
        "50 commandes/mois",
        "5 produits non-alimentaires max",
        "Frais de service: 500 F/commande",
        "Frais B2B: 1000 F/commande grossiste",
        "Commission standard",
        "Voir rapports basiques (ventes jour/mois)",
        "Historique limité à 30 jours",
        "Pas d'export (Excel/CSV/PDF)",
        "Support standard"
    ],
    'is_active': True
}

plan_free, created = SubscriptionPlan.objects.update_or_create(
    plan_type='free',
    defaults=free_defaults
)

if created:
    print(f"[CREE] Plan Free")
else:
    # Comparer les valeurs
    if compare_and_update(plan_free, free_defaults, 'Free'):
        plan_free.save()
        print(f"[MIS A JOUR] Plan Free")
    else:
        print(f"[OK] Plan Free déjà correct")

# ========== PLAN PRO ==========
pro_defaults = {
    'name': 'Pro',
    'slug': 'pro',
    'price': Decimal('30000.00'),
    
    # Limites
    'max_products': None,
    'max_orders_per_month': None,
    'max_products_non_food': None,
    
    # Frais de service
    'service_fee_client_amount': 500,
    'service_fee_to_wholesaler_amount': 0,
    
    # Commissions
    'commission_reduction_percent': 40,
    'commission_multiplier': Decimal('0.60'),  # -40% = 0.60
    
    # Fonctionnalités
    'can_sell_non_food_products': True,
    'can_access_b2b': False,
    'has_b2b_visibility': False,
    'can_offer_express_delivery': True,
    'has_advanced_delivery_tracking': False,
    'has_statistics': True,
    'has_priority_support': True,
    'has_custom_page': True,
    'can_sponsor_products': False,
    'priority_listing': 5,
    
    # Rapports et Exports
    'can_view_basic_reports': True,
    'can_view_detailed_reports': True,
    'can_export_excel': True,
    'can_export_pdf': False,
    'history_limit_days': 180,
    
    # Finance B2B
    'can_view_finance_basic': True,
    'can_view_finance_detailed': False,
    'can_export_finance_csv': True,
    'can_export_finance_pdf': False,
    'finance_history_limit_days': 90,
    
    # Quotas B2B
    'max_b2b_suppliers': 10,
    'max_b2b_monthly_orders': 50,
    
    # Visibilité B2B
    'b2b_catalog_priority': 5,
    'b2b_featured_access': False,
    
    # Type de magasin
    'applies_to': 'b2c',
    
    # Support
    'support_level': 'prioritaire',
    
    'description': 'Pour les commerces en croissance.',
    'features_json': [
        "Produits illimités",
        "Commandes illimitées",
        "Frais de service: 500 F/commande",
        "Frais B2B: 0 F (gratuit)",
        "Commission réduite -40%",
        "Livraison express disponible",
        "Rapports détaillés (par commande/catégorie)",
        "Export Excel/CSV",
        "Historique 6 mois",
        "Statistiques avancées",
        "Support prioritaire"
    ],
    'is_active': True
}

plan_pro, created = SubscriptionPlan.objects.update_or_create(
    plan_type='pro',
    defaults=pro_defaults
)

if created:
    print(f"[CREE] Plan Pro")
else:
    if compare_and_update(plan_pro, pro_defaults, 'Pro'):
        plan_pro.save()
        print(f"[MIS A JOUR] Plan Pro")
    else:
        print(f"[OK] Plan Pro déjà correct")

# ========== PLAN BUSINESS ==========
business_defaults = {
    'name': 'Business',
    'slug': 'business',
    'price': Decimal('50000.00'),
    
    # Limites
    'max_products': None,
    'max_orders_per_month': None,
    'max_products_non_food': None,
    
    # Frais de service
    'service_fee_client_amount': 500,
    'service_fee_to_wholesaler_amount': 0,
    
    # Commissions
    'commission_reduction_percent': 75,
    'commission_multiplier': Decimal('0.25'),  # -75% = 0.25
    
    # Fonctionnalités
    'can_sell_non_food_products': True,
    'can_access_b2b': True,
    'has_b2b_visibility': True,
    'can_offer_express_delivery': True,
    'has_advanced_delivery_tracking': True,
    'has_statistics': True,
    'has_priority_support': True,
    'has_custom_page': True,
    'can_sponsor_products': True,
    'priority_listing': 10,
    
    # Rapports et Exports
    'can_view_basic_reports': True,
    'can_view_detailed_reports': True,
    'can_export_excel': True,
    'can_export_pdf': True,
    'history_limit_days': None,
    
    # Finance B2B
    'can_view_finance_basic': True,
    'can_view_finance_detailed': True,
    'can_export_finance_csv': True,
    'can_export_finance_pdf': True,
    'finance_history_limit_days': None,
    
    # Quotas B2B
    'max_b2b_suppliers': None,
    'max_b2b_monthly_orders': None,
    
    # Visibilité B2B
    'b2b_catalog_priority': 10,
    'b2b_featured_access': True,
    
    # Type de magasin
    'applies_to': 'both',
    
    # Support
    'support_level': 'dedie',
    
    'description': 'Le plan ultime pour maximiser votre potentiel.',
    'features_json': [
        "Produits illimités",
        "Commandes illimitées",
        "Frais de service: 500 F/commande",
        "Frais B2B: 0 F (gratuit)",
        "Commission préférentielle (0% alimentaire, 2% reste)",
        "Accès complet approvisionnement B2B",
        "Livraison express + suivi avancé",
        "Rapports détaillés complets",
        "Export Excel/CSV + PDF officiel",
        "Historique illimité",
        "Rapports mensuels certifiés",
        "Support VIP dédié 24/7",
        "Produits sponsorisés"
    ],
    'is_active': True
}

plan_business, created = SubscriptionPlan.objects.update_or_create(
    plan_type='business',
    defaults=business_defaults
)

if created:
    print(f"[CREE] Plan Business")
else:
    if compare_and_update(plan_business, business_defaults, 'Business'):
        plan_business.save()
        print(f"[MIS A JOUR] Plan Business")
    else:
        print(f"[OK] Plan Business déjà correct")

print()
print("=" * 70)
print("  [OK] CORRECTION DES PLANS B2C TERMINEE")
print("=" * 70)
print()

# ============================================================================
# VERIFICATION DES PLANS B2B
# ============================================================================

print("=" * 70)
print("  VERIFICATION DES PLANS B2B")
print("=" * 70)
print()

# Vérifier que les plans B2B existent
b2b_plans = B2BSubscriptionPlan.objects.all()
if b2b_plans.exists():
    print(f"[INFO] {b2b_plans.count()} plan(s) B2B trouvé(s)")
    for plan in b2b_plans:
        print(f"  - {plan.name} ({plan.plan_type}) - {plan.price} FCFA/mois")
    print()
    print("[INFO] Pour corriger les plans B2B, exécutez: python scripts/setup_b2b_subscription_plans.py")
else:
    print("[ATTENTION] Aucun plan B2B trouvé")
    print("[INFO] Pour créer les plans B2B, exécutez: python scripts/setup_b2b_subscription_plans.py")

print()
print("=" * 70)
print("  [OK] CORRECTION TERMINEE")
print("=" * 70)
print()
print("Résumé:")
print("  - Plans B2C corrigés: Free, Pro, Business")
print("  - Vérifiez les plans B2B séparément si nécessaire")
print("  - Tous les plans sont maintenant alignés avec les spécifications")
print()
