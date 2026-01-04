#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test de validation de la logique de rapports et exports par plan
Vérifie que la règle "Voir ≠ Exporter" est bien respectée
"""

import os
import sys
import django

# Setup Django
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
django.setup()

from payments.models import SubscriptionPlan

# Force UTF-8 encoding for console output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

print("=" * 80)
print("  TEST DE VALIDATION - RAPPORTS ET EXPORTS PAR PLAN")
print("=" * 80)

# Règles attendues selon la logique fournie
expected_rules = {
    'free': {
        'can_view_basic_reports': True,
        'can_view_detailed_reports': False,
        'can_export_excel': False,
        'can_export_pdf': False,
        'history_limit_days': 30,
        'description': 'Voir uniquement, pas d\'export'
    },
    'pro': {
        'can_view_basic_reports': True,
        'can_view_detailed_reports': True,
        'can_export_excel': True,
        'can_export_pdf': False,
        'history_limit_days': 180,
        'description': 'Voir détails + Export Excel/CSV (pas PDF)'
    },
    'business': {
        'can_view_basic_reports': True,
        'can_view_detailed_reports': True,
        'can_export_excel': True,
        'can_export_pdf': True,
        'history_limit_days': None,
        'description': 'Tout + Export Excel/CSV + PDF officiel'
    }
}

all_passed = True

for plan_type, expected in expected_rules.items():
    print(f"\n[TEST] Plan {plan_type.upper()}")
    print(f"  Règle attendue: {expected['description']}")
    
    try:
        plan = SubscriptionPlan.objects.get(plan_type=plan_type)
        errors = []
        
        # Vérifier chaque champ
        for field, expected_value in expected.items():
            if field == 'description':
                continue
            
            actual_value = getattr(plan, field)
            
            if actual_value != expected_value:
                errors.append(f"    ✗ {field}: attendu {expected_value}, obtenu {actual_value}")
                all_passed = False
        
        if errors:
            print("  Résultat: ✗ ECHEC")
            for error in errors:
                print(error)
        else:
            print("  Résultat: ✓ REUSSI")
            print(f"    • Voir basique: {plan.can_view_basic_reports}")
            print(f"    • Voir détails: {plan.can_view_detailed_reports}")
            print(f"    • Export Excel: {plan.can_export_excel}")
            print(f"    • Export PDF: {plan.can_export_pdf}")
            print(f"    • Historique: {plan.history_limit_days or 'illimité'} jours")
    
    except SubscriptionPlan.DoesNotExist:
        print(f"  Résultat: ✗ ERREUR - Plan {plan_type} introuvable")
        all_passed = False

# Tableau récapitulatif
print("\n" + "=" * 80)
print("  TABLEAU RECAPITULATIF")
print("=" * 80)

print("\n{:<20} {:<10} {:<10} {:<12} {:<10} {:<15}".format(
    "Fonctionnalité", "FREE", "PRO", "BUSINESS", "", ""
))
print("-" * 80)

features = [
    ("Voir basique", "can_view_basic_reports"),
    ("Voir détails", "can_view_detailed_reports"),
    ("Export Excel/CSV", "can_export_excel"),
    ("Export PDF", "can_export_pdf"),
]

plans = {
    'free': SubscriptionPlan.objects.get(plan_type='free'),
    'pro': SubscriptionPlan.objects.get(plan_type='pro'),
    'business': SubscriptionPlan.objects.get(plan_type='business'),
}

for feature_name, field_name in features:
    free_val = "✓" if getattr(plans['free'], field_name) else "✗"
    pro_val = "✓" if getattr(plans['pro'], field_name) else "✗"
    business_val = "✓" if getattr(plans['business'], field_name) else "✗"
    
    print("{:<20} {:<10} {:<10} {:<12}".format(
        feature_name, free_val, pro_val, business_val
    ))

print("{:<20} {:<10} {:<10} {:<12}".format(
    "Historique",
    f"{plans['free'].history_limit_days}j",
    f"{plans['pro'].history_limit_days}j",
    "illimité"
))

print("\n" + "=" * 80)
if all_passed:
    print("  [✓] TOUS LES TESTS PASSES - La logique est correctement implémentée")
else:
    print("  [✗] CERTAINS TESTS ONT ECHOUE - Vérifier la configuration")
print("=" * 80)

