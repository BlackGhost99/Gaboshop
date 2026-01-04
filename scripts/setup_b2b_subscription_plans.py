"""
Script pour créer les plans d'abonnement B2B par défaut
"""
import os
import sys
import django

# Reconfigure stdout for UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# Setup Django
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')
django.setup()

from b2b.models import B2BSubscriptionPlan


def create_b2b_subscription_plans():
    """Crée les 3 plans d'abonnement B2B par défaut"""
    
    plans_data = [
        {
            'name': 'B2B Free',
            'slug': 'b2b-free',
            'plan_type': 'free',
            'price': 0,
            'description': 'Plan gratuit pour débuter en tant que grossiste sur GABOSHOP. Commission de 8% sur les commandes.',
            'tagline': 'Idéal pour débuter',
            'max_b2b_products': 2,  # Seulement 2 produits en Free
            'max_b2c_buyers': None,  # Illimité
            'max_monthly_orders': None,  # Commandes illimitées
            'catalog_priority': 0,
            'featured_in_catalog': False,
            'can_offer_bulk_discounts': True,
            'has_advanced_analytics': False,
            'can_view_detailed_reports': False,
            'has_priority_support': False,
            'can_create_promotions': False,
            'has_api_access': False,
            'commission_reduction_percent': 0,  # 8% de commission (pas de réduction)
            # Finance - FREE: Basique uniquement
            'can_view_finance_basic': True,
            'can_view_finance_detailed': False,
            'can_export_finance_csv': False,
            'can_export_finance_pdf': False,
            'finance_history_limit_days': 30,  # 30 jours
            # Type de magasin
            'applies_to': 'b2b_wholesaler',
            'custom_features': [
                {
                    'title': '2 produits B2B maximum',
                    'description': 'Publiez jusqu\'à 2 produits dans le catalogue B2B',
                    'category': 'limits',
                    'enabled': True
                },
                {
                    'title': 'Commandes illimitées',
                    'description': 'Recevez autant de commandes que vous voulez',
                    'category': 'orders',
                    'enabled': True
                },
                {
                    'title': 'Commission 8%',
                    'description': 'GABOSHOP prélève 8% sur chaque commande B2B',
                    'category': 'pricing',
                    'enabled': True
                },
                {
                    'title': 'Interface simple',
                    'description': 'Interface de base pour gérer vos commandes',
                    'category': 'interface',
                    'enabled': True
                }
            ],
            'is_active': True,
            'is_popular': False,
            'display_order': 1
        },
        {
            'name': 'B2B Pro',
            'slug': 'b2b-pro',
            'plan_type': 'pro',
            'price': 25000,
            'description': 'Plan professionnel pour grossistes en croissance',
            'tagline': 'Le plus populaire',
            'max_b2b_products': 500,
            'max_b2c_buyers': None,  # Illimité
            'max_monthly_orders': None,  # Illimité
            'catalog_priority': 5,
            'featured_in_catalog': True,
            'can_offer_bulk_discounts': True,
            'has_advanced_analytics': True,
            'can_view_detailed_reports': True,
            'has_priority_support': False,
            'can_create_promotions': True,
            'has_api_access': False,
            'commission_reduction_percent': 15,
            # Finance - PRO: Détails + CSV
            'can_view_finance_basic': True,
            'can_view_finance_detailed': True,
            'can_export_finance_csv': True,
            'can_export_finance_pdf': False,
            'finance_history_limit_days': 180,  # 6 mois
            # Type de magasin
            'applies_to': 'b2b_wholesaler',
            'custom_features': [
                {
                    'title': 'Mise en avant catalogue',
                    'description': 'Vos produits apparaissent en priorité',
                    'category': 'marketing',
                    'enabled': True
                },
                {
                    'title': 'Statistiques détaillées',
                    'description': 'Rapports de ventes et analyses avancées',
                    'category': 'analytics',
                    'enabled': True
                },
                {
                    'title': 'Promotions personnalisées',
                    'description': 'Créez vos propres campagnes promotionnelles',
                    'category': 'marketing',
                    'enabled': True
                },
                {
                    'title': 'Badge "Grossiste Vérifié"',
                    'description': 'Augmente la confiance des acheteurs',
                    'category': 'trust',
                    'enabled': True
                }
            ],
            'is_active': True,
            'is_popular': True,
            'display_order': 2
        },
        {
            'name': 'B2B Business',
            'slug': 'b2b-business',
            'plan_type': 'business',
            'price': 50000,
            'description': 'Plan premium pour grossistes établis avec volume élevé',
            'tagline': 'Pour les leaders du marché',
            'max_b2b_products': None,  # Illimité
            'max_b2c_buyers': None,  # Illimité
            'max_monthly_orders': None,  # Illimité
            'catalog_priority': 10,
            'featured_in_catalog': True,
            'can_offer_bulk_discounts': True,
            'has_advanced_analytics': True,
            'can_view_detailed_reports': True,
            'has_priority_support': True,
            'can_create_promotions': True,
            'has_api_access': True,
            'commission_reduction_percent': 30,
            # Finance - BUSINESS: Complet + PDF
            'can_view_finance_basic': True,
            'can_view_finance_detailed': True,
            'can_export_finance_csv': True,
            'can_export_finance_pdf': True,  # PDF disponible
            'finance_history_limit_days': None,  # Illimité
            # Type de magasin
            'applies_to': 'b2b_wholesaler',
            'custom_features': [
                {
                    'title': 'Priorité maximale',
                    'description': 'Apparaissez en premier dans tous les catalogues',
                    'category': 'marketing',
                    'enabled': True
                },
                {
                    'title': 'Support VIP 24/7',
                    'description': 'Assistance prioritaire par téléphone et email',
                    'category': 'support',
                    'enabled': True
                },
                {
                    'title': 'Accès API complet',
                    'description': 'Intégrez GABOSHOP à vos systèmes',
                    'category': 'integration',
                    'enabled': True
                },
                {
                    'title': 'Account Manager dédié',
                    'description': 'Un conseiller personnel pour votre business',
                    'category': 'support',
                    'enabled': True
                },
                {
                    'title': 'Réduction 30% commissions',
                    'description': 'Économisez sur chaque transaction',
                    'category': 'pricing',
                    'enabled': True
                },
                {
                    'title': 'Formation personnalisée',
                    'description': 'Sessions de formation pour votre équipe',
                    'category': 'training',
                    'enabled': True
                }
            ],
            'is_active': True,
            'is_popular': False,
            'display_order': 3
        }
    ]
    
    created_count = 0
    updated_count = 0
    
    for plan_data in plans_data:
        plan, created = B2BSubscriptionPlan.objects.update_or_create(
            plan_type=plan_data['plan_type'],
            defaults=plan_data
        )
        
        if created:
            created_count += 1
            print(f"✅ Plan créé: {plan.name} ({plan.price} FCFA/mois)")
        else:
            updated_count += 1
            print(f"🔄 Plan mis à jour: {plan.name} ({plan.price} FCFA/mois)")
    
    print(f"\n📊 Résumé:")
    print(f"   - Plans créés: {created_count}")
    print(f"   - Plans mis à jour: {updated_count}")
    print(f"   - Total: {created_count + updated_count}")
    
    # Afficher les fonctionnalités de chaque plan
    print(f"\n📋 Fonctionnalités par plan:")
    for plan in B2BSubscriptionPlan.objects.all().order_by('display_order'):
        print(f"\n{plan.name}:")
        features = plan.get_all_features()
        for feature in features:
            print(f"  ✓ {feature['title']}")


if __name__ == '__main__':
    print("🚀 Création des plans d'abonnement B2B...\n")
    create_b2b_subscription_plans()
    print("\n✅ Terminé!")

