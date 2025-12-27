"""
Script pour créer les plans d'abonnement Starter, Pro et Business
"""
import os
import django

import sys
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
django.setup()

from payments.models import SubscriptionPlan


def create_subscription_plans():
    """Crée les 3 plans d'abonnement"""
    
    # Plan Starter (Gratuit)
    starter, created = SubscriptionPlan.objects.get_or_create(
        plan_type='starter',
        defaults={
            'name': 'Starter',
            'slug': 'starter',
            'price': 0,
            'max_products': 20,
            'can_sponsor_products': False,
            'has_statistics': False,
            'has_custom_page': False,
            'has_priority_support': False,
            'priority_listing': 0,
            'commission_rate': None,  # Utilise le taux par défaut
            'description': 'Plan gratuit pour démarrer sur GABOSHOP',
            'features_json': [
                'Recevoir des commandes',
                'Gestion basique des produits',
                'Support standard'
            ],
            'is_active': True
        }
    )
    if created:
        print(f"✓ Plan Starter créé: {starter}")
    else:
        print(f"- Plan Starter existe déjà: {starter}")
    
    # Plan Pro (10 000 FCFA/mois)
    pro, created = SubscriptionPlan.objects.get_or_create(
        plan_type='pro',
        defaults={
            'name': 'Pro',
            'slug': 'pro',
            'price': 15000,
            'max_products': None,  # Illimité
            'can_sponsor_products': False,
            'has_statistics': True,
            'has_custom_page': False,
            'has_priority_support': False,
            'priority_listing': 1,
            'commission_rate': None,
            'commission_multiplier': 0.60,  # Réduction de 40% par rapport au taux de base
            'description': 'Plan professionnel avec statistiques avancées',
            'features_json': [
                'Réduction de 40% sur le taux de commission de base (hors Alimentaire)',
                'Rapports de ventes détaillés',
                'Analytics en temps réel'
            ],
            'is_active': True
        }
    )
    if created:
        print(f"✓ Plan Pro créé: {pro}")
    else:
        print(f"- Plan Pro existe déjà: {pro}")
    
    # Plan Business (30 000 FCFA/mois)
    business, created = SubscriptionPlan.objects.get_or_create(
        plan_type='business',
        defaults={
            'name': 'Business',
            'slug': 'business',
            'price': 40000,
            'max_products': None,  # Illimité
            'can_sponsor_products': True,
            'has_statistics': True,
            'has_custom_page': True,
            'has_priority_support': True,
            'priority_listing': 10,
            'commission_rate': None,
            'commission_multiplier': 0.25,  # Réduction de 75% par rapport au taux de base
            'description': 'Plan premium pour maximiser votre visibilité',
            'features_json': [
                'Réduction de 75% sur le taux de commission de base (hors Alimentaire)',
                'Produits sponsorisés illimités',
                'Page personnalisée premium',
                'Support VIP prioritaire',
                'Mise en avant dans la plateforme'
            ],
            'is_active': True
        }
    )
    if created:
        print(f"✓ Plan Business créé: {business}")
    else:
        print(f"- Plan Business existe déjà: {business}")
    
    print("\n✅ Plans d'abonnement configurés avec succès!")
    print(f"\nRécapitulatif:")
    print(f"- Starter: Gratuit (max 20 produits)")
    print(f"- Pro: 15 000 FCFA/mois (produits illimités, stats)")
    print(f"- Business: 40 000 FCFA/mois (page personnalisée, support VIP)")


if __name__ == '__main__':
    create_subscription_plans()
