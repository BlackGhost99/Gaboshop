"""Les options « sans effet » des forfaits deviennent réelles (17 oct. 2026).

Allume, pour les forfaits Pro et Business existants, les options marketing qui ont maintenant un code derrière :
support prioritaire, page de boutique personnalisée, livraison express, suivi en temps réel, rapport financier
détaillé ; côté grossistes : prix dégressifs, promotions, support prioritaire, accès API, rapport détaillé, badge
« Populaire » sur le Pro. Le forfait Gratuit perd le suivi en temps réel (réservé au Pro) et la livraison express.
Les prix, les limites et les autres cases cochées par l'admin ne changent pas.
"""
from django.db import migrations


def apply(apps, schema_editor):
    from payments.default_plans import B2B_PRO_TOOLS, PRO_TOOLS
    plans = apps.get_model('payments', 'SubscriptionPlan').objects
    plans.filter(plan_type__in=('pro', 'business')).update(**PRO_TOOLS)
    plans.filter(plan_type='business').update(support_level='dedie')
    plans.filter(plan_type='free').update(has_advanced_delivery_tracking=False, can_offer_express_delivery=False)
    b2b = apps.get_model('b2b', 'B2BSubscriptionPlan').objects
    b2b.filter(plan_type__in=('pro', 'business')).update(**B2B_PRO_TOOLS)
    b2b.filter(plan_type='pro').update(is_popular=True)


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0028_outils_pro_actives_2026_10_16'),
        ('b2b', '0008_outils_forfaits_2026_10_16'),
    ]

    operations = [
        migrations.RunPython(apply, migrations.RunPython.noop),
    ]
