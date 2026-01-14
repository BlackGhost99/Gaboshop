#!/usr/bin/env python
"""
Script pour vérifier et corriger la configuration du plan Business
Vérifie que le plan Business a bien can_access_b2b=True
"""

import os
import sys
import django
from decimal import Decimal

# Setup Django
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
django.setup()

from payments.models import SubscriptionPlan

print("=" * 70)
print("  VÉRIFICATION ET CORRECTION DU PLAN BUSINESS")
print("=" * 70)

# Vérifier le plan Business
try:
    plan_business = SubscriptionPlan.objects.get(plan_type='business')
    print(f"\n✓ Plan Business trouvé: {plan_business.name}")
    print(f"  - can_access_b2b: {plan_business.can_access_b2b}")
    
    if not plan_business.can_access_b2b:
        print("\n⚠️  ATTENTION: Le plan Business n'a pas can_access_b2b=True")
        print("   Correction en cours...")
        plan_business.can_access_b2b = True
        plan_business.save()
        print("   ✓ Plan Business corrigé: can_access_b2b=True")
    else:
        print("   ✓ Configuration correcte")
        
except SubscriptionPlan.DoesNotExist:
    print("\n⚠️  Le plan Business n'existe pas!")
    print("   Création du plan Business...")
    plan_business = SubscriptionPlan.objects.create(
        plan_type='business',
        name='Business',
        slug='business',
        price=Decimal('50000.00'),
        can_access_b2b=True,
        has_b2b_visibility=True,
        has_statistics=True,
        has_priority_support=True,
        has_custom_page=True,
        can_sponsor_products=True,
    )
    print("   ✓ Plan Business créé avec can_access_b2b=True")

# Vérifier les autres plans
print("\n" + "=" * 70)
print("  VÉRIFICATION DES AUTRES PLANS")
print("=" * 70)

for plan_type in ['free', 'pro', 'business']:
    try:
        plan = SubscriptionPlan.objects.get(plan_type=plan_type)
        print(f"\n{plan.name} ({plan_type}):")
        print(f"  - can_access_b2b: {plan.can_access_b2b}")
        if plan_type == 'business' and not plan.can_access_b2b:
            print("  ⚠️  DOIT ÊTRE True!")
        elif plan_type != 'business' and plan.can_access_b2b:
            print("  ⚠️  Normalement False pour ce plan")
    except SubscriptionPlan.DoesNotExist:
        print(f"\n⚠️  Plan {plan_type} n'existe pas")

print("\n" + "=" * 70)
print("  VÉRIFICATION TERMINÉE")
print("=" * 70)
