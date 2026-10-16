"""Gamme Gratuit / Pro / Business (décision du propriétaire, 15 oct. 2026).

Crée les plans qui manquent (B2C et B2B) ; un plan existant garde son prix et ses limites.
Business reste visible mais grisé (is_available = False) tant que l'admin ne l'ouvre pas.
Un commerce sans abonnement est au forfait Gratuit : aucune ligne d'abonnement à créer.
"""
from django.db import migrations


def apply(apps, schema_editor):
    from payments.default_plans import ensure_range
    ensure_range(apps.get_model('payments', 'SubscriptionPlan'), apps.get_model('b2b', 'B2BSubscriptionPlan'))


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0025_plan_is_available'),
        ('b2b', '0007_plan_is_available'),
    ]

    operations = [
        migrations.RunPython(apply, migrations.RunPython.noop),
    ]
