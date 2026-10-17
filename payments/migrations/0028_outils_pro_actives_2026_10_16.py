"""Les outils promis sur la carte Pro deviennent réels (contrôle du 16 oct. 2026).

Allume, pour les forfaits Pro et Business existants (commerces et grossistes) : statistiques avancées, exports
Excel/CSV et PDF, import de produits, alertes de stock et, côté commerces, promotions. Les autres réglages des
forfaits (prix, limites, autres cases cochées par l'admin) ne changent pas.
"""
from django.db import migrations


def apply(apps, schema_editor):
    from payments.default_plans import B2B_PRO_TOOLS, PRO_TOOLS
    apps.get_model('payments', 'SubscriptionPlan').objects.filter(plan_type__in=('pro', 'business')).update(**PRO_TOOLS)
    apps.get_model('b2b', 'B2BSubscriptionPlan').objects.filter(plan_type__in=('pro', 'business')).update(**B2B_PRO_TOOLS)


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0027_outils_forfaits_2026_10_16'),
        ('b2b', '0008_outils_forfaits_2026_10_16'),
    ]

    operations = [
        migrations.RunPython(apply, migrations.RunPython.noop),
    ]
