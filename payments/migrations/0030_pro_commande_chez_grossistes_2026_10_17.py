"""Le forfait Pro peut commander chez les grossistes, avec une limite (17 oct. 2026, demande du propriétaire).

Pro : 3 grossistes différents sur 30 jours et 10 commandes en gros par mois ; Business : sans limite.
Le Gratuit n'y a pas accès. Les limites se règlent ensuite dans l'admin des forfaits.
"""
from django.db import migrations


def apply(apps, schema_editor):
    from payments.default_plans import PRO_B2B_LIMITS
    plans = apps.get_model('payments', 'SubscriptionPlan').objects
    plans.filter(plan_type='pro').update(can_access_b2b=True, **PRO_B2B_LIMITS)
    plans.filter(plan_type='business').update(can_access_b2b=True, max_b2b_suppliers=None, max_b2b_monthly_orders=None)


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0029_options_forfaits_reelles_2026_10_17'),
    ]

    operations = [
        migrations.RunPython(apply, migrations.RunPython.noop),
    ]
