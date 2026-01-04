#!/usr/bin/env python
# Configuration complète des plans Free/Pro/Business

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
print("  CONFIGURATION COMPLETE DES PLANS D'ABONNEMENT B2C")
print("=" * 70)

# ========== PLAN FREE ==========
plan_free, created = SubscriptionPlan.objects.update_or_create(
    plan_type='free',
    defaults={
        'name': 'Free',
        'slug': 'free',
        'price': Decimal('0.00'),
        
        # Limites
        'max_products': 20,
        'max_orders_per_month': 50,
        'max_products_non_food': 5,  # Limité
        
        # Frais de service
        'service_fee_client_amount': 500,
        'service_fee_to_wholesaler_amount': 1000,
        
        # Commissions
        'commission_reduction_percent': 0,  # Taux plein
        
        # Fonctionnalités
        'can_sell_non_food_products': True,  # Mais limité
        'can_access_b2b': False,
        'has_b2b_visibility': False,
        'can_offer_express_delivery': False,
        'has_advanced_delivery_tracking': False,
        'has_statistics': False,
        'has_priority_support': False,
        'can_sponsor_products': False,
        
        # Rapports et Exports - FREE: Voir uniquement, pas d'export
        'can_view_basic_reports': True,
        'can_view_detailed_reports': False,
        'can_export_excel': False,
        'can_export_pdf': False,
        'history_limit_days': 30,  # 30 jours max
        
        # Finance B2B - FREE: Pas d'accès B2B
        'can_view_finance_basic': False,
        'can_view_finance_detailed': False,
        'can_export_finance_csv': False,
        'can_export_finance_pdf': False,
        'finance_history_limit_days': None,
        
        # Quotas B2B - FREE: Pas d'accès
        'max_b2b_suppliers': None,
        'max_b2b_monthly_orders': None,
        
        # Visibilité B2B - FREE: Pas d'accès
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
        ]
    }
)
print(f"[{'CREE' if created else 'MIS A JOUR'}] Plan Free")

# ========== PLAN PRO ==========
plan_pro, created = SubscriptionPlan.objects.update_or_create(
    plan_type='pro',
    defaults={
        'name': 'Pro',
        'slug': 'pro',
        'price': Decimal('30000.00'),
        
        # Limites
        'max_products': None,  # Illimité
        'max_orders_per_month': None,  # Illimité
        'max_products_non_food': None,  # Illimité
        
        # Frais de service
        'service_fee_client_amount': 500,
        'service_fee_to_wholesaler_amount': 0,  # Gratuit !
        
        # Commissions
        'commission_reduction_percent': 40,  # -40%
        
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
        
        # Rapports et Exports - PRO: Voir détails + Export Excel/CSV
        'can_view_basic_reports': True,
        'can_view_detailed_reports': True,
        'can_export_excel': True,
        'can_export_pdf': False,  # Pas de PDF pour PRO
        'history_limit_days': 180,  # 6 mois
        
        # Finance B2B - PRO: Accès limité (basique + CSV)
        'can_view_finance_basic': True,
        'can_view_finance_detailed': False,  # Pas de détails pour PRO
        'can_export_finance_csv': True,  # CSV disponible
        'can_export_finance_pdf': False,
        'finance_history_limit_days': 90,  # 3 mois
        
        # Quotas B2B - PRO: Limité
        'max_b2b_suppliers': 10,  # Max 10 grossistes
        'max_b2b_monthly_orders': 50,  # Max 50 commandes B2B/mois
        
        # Visibilité B2B - PRO: Standard
        'b2b_catalog_priority': 5,
        'b2b_featured_access': False,
        
        # Type de magasin
        'applies_to': 'b2c',  # B2C uniquement, mais peut accéder B2B
        
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
        ]
    }
)
print(f"[{'CREE' if created else 'MIS A JOUR'}] Plan Pro")

# ========== PLAN BUSINESS ==========
plan_business, created = SubscriptionPlan.objects.update_or_create(
    plan_type='business',
    defaults={
        'name': 'Business',
        'slug': 'business',
        'price': Decimal('50000.00'),  # B2C: 50k, B2B: 80k (géré ailleurs)
        
        # Limites
        'max_products': None,  # Illimité
        'max_orders_per_month': None,  # Illimité
        'max_products_non_food': None,  # Illimité
        
        # Frais de service
        'service_fee_client_amount': 500,
        'service_fee_to_wholesaler_amount': 0,  # Gratuit !
        
        # Commissions
        'commission_reduction_percent': 75,  # -75% (mais logique spéciale: 0% food, 2% reste)
        
        # Fonctionnalités
        'can_sell_non_food_products': True,
        'can_access_b2b': True,  # Accès approvisionnement
        'has_b2b_visibility': True,  # Visibilité grossiste
        'can_offer_express_delivery': True,
        'has_advanced_delivery_tracking': True,
        'has_statistics': True,
        'has_priority_support': True,
        'has_custom_page': True,
        'can_sponsor_products': True,
        'priority_listing': 10,
        
        # Rapports et Exports - BUSINESS: Tout + Export Excel/CSV + PDF
        'can_view_basic_reports': True,
        'can_view_detailed_reports': True,
        'can_export_excel': True,
        'can_export_pdf': True,  # PDF officiel uniquement Business
        'history_limit_days': None,  # Illimité
        
        # Finance B2B - BUSINESS: Complet
        'can_view_finance_basic': True,
        'can_view_finance_detailed': True,
        'can_export_finance_csv': True,
        'can_export_finance_pdf': True,  # PDF disponible
        'finance_history_limit_days': None,  # Illimité
        
        # Quotas B2B - BUSINESS: Illimité
        'max_b2b_suppliers': None,  # Illimité
        'max_b2b_monthly_orders': None,  # Illimité
        
        # Visibilité B2B - BUSINESS: Maximale
        'b2b_catalog_priority': 10,
        'b2b_featured_access': True,  # Accès prioritaire aux grossistes featured
        
        # Type de magasin
        'applies_to': 'both',  # B2C et B2B
        
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
        ]
    }
)
print(f"[{'CREE' if created else 'MIS A JOUR'}] Plan Business")

print("\n" + "=" * 70)
print("  [OK] CONFIGURATION TERMINEE")
print("=" * 70)
