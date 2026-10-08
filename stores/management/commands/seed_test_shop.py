"""Site de test uniquement : boutique de test avec un article à 100 F pour essayer un vrai paiement.

Ne fait rien sans STAGING_TEST_SHOP=1 (posé dans render-staging.yaml, jamais en production).
Idempotent : relancé à chaque démarrage, il ne recrée rien de ce qui existe.
Active aussi le « Paiement en ligne Gaboshop » quand les clés SingPay sont configurées.
"""
import os
from datetime import time
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from api.models import SystemSettings
from payments.configuration import get_payment_policy, platform_online_ready, validate_payment_policy
from products.models import Product
from stores.models import Store, StoreCategory
from users.models import User

MANAGER_PHONE = '+24100000001'
STORE_PHONE = '+24100000002'


class Command(BaseCommand):
    help = 'Site de test : boutique de test (article à 100 F) et paiement en ligne activé si SingPay est configuré.'

    @transaction.atomic
    def handle(self, *args, **options):
        if os.environ.get('STAGING_TEST_SHOP') != '1':
            self.stdout.write('STAGING_TEST_SHOP absent : aucune donnée de test créée.')
            return

        category, _ = StoreCategory.objects.get_or_create(
            name='Test', defaults={'description': 'Catégorie du site de test'}
        )
        manager = User.objects.filter(phone=MANAGER_PHONE).first()
        if manager is None:
            # Compte sans mot de passe utilisable : personne ne peut s'y connecter.
            manager = User.objects.create_user(
                phone=MANAGER_PHONE, password=None, user_type='store_manager',
                first_name='Boutique', last_name='Test',
            )
        store, _ = Store.objects.get_or_create(
            phone=STORE_PHONE,
            defaults={
                'name': 'Boutique Test Gaboshop', 'description': 'Boutique du site de test, pour essayer les paiements.',
                'category': category, 'manager': manager, 'address': 'Libreville', 'zone': 'Centre',
                'opening_time': time(0, 0), 'closing_time': time(23, 59, 59),
                'is_active': True, 'is_verified': True, 'min_order_amount': Decimal('0'),
                'offers_delivery': False,
            },
        )
        Product.objects.get_or_create(
            store=store, name='Article test 100 F',
            defaults={
                'description': 'Article fictif pour tester un vrai paiement Mobile Money de 100 F.',
                'price': Decimal('100'), 'stock': 1000, 'is_available': True,
            },
        )

        if platform_online_ready():
            system_settings = SystemSettings.get_settings()
            policy = get_payment_policy()
            if 'platform_online' not in policy['enabled_flows']:
                policy['enabled_flows'] = policy['enabled_flows'] + ['platform_online']
                system_settings.payment_policy = validate_payment_policy(policy)
                system_settings.save(update_fields=['payment_policy'])
                self.stdout.write('Paiement en ligne Gaboshop activé (clés SingPay présentes).')
        self.stdout.write('Boutique de test prête.')
