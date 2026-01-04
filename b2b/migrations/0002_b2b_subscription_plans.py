# Generated manually for B2B subscription plans

from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ('b2b', '0001_initial'),
        ('stores', '0009_add_b2c_b2b_fields'),
    ]

    operations = [
        migrations.CreateModel(
            name='B2BSubscriptionPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Nom du plan (ex: B2B Free)', max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=100, unique=True)),
                ('plan_type', models.CharField(choices=[('free', 'Free'), ('pro', 'Pro'), ('business', 'Business')], max_length=20, unique=True)),
                ('price', models.DecimalField(decimal_places=2, default=0, help_text='Prix mensuel en FCFA', max_digits=10)),
                ('description', models.TextField(blank=True, help_text='Description courte du plan')),
                ('tagline', models.CharField(blank=True, help_text="Slogan du plan (ex: 'Idéal pour débuter')", max_length=200)),
                ('max_b2b_products', models.IntegerField(blank=True, help_text='Nombre max de produits B2B (null = illimité)', null=True)),
                ('max_b2c_buyers', models.IntegerField(blank=True, help_text='Nombre max de magasins B2C clients (null = illimité)', null=True)),
                ('max_monthly_orders', models.IntegerField(blank=True, help_text='Nombre max de commandes B2B par mois (null = illimité)', null=True)),
                ('catalog_priority', models.IntegerField(default=0, help_text="Priorité d'affichage dans le catalogue B2B (plus élevé = plus visible)")),
                ('featured_in_catalog', models.BooleanField(default=False, help_text='Mis en avant dans le catalogue B2B')),
                ('can_offer_bulk_discounts', models.BooleanField(default=True, help_text='Peut proposer des remises pour achats en gros')),
                ('has_advanced_analytics', models.BooleanField(default=False, help_text='Accès aux statistiques avancées B2B')),
                ('has_priority_support', models.BooleanField(default=False, help_text='Support prioritaire')),
                ('can_create_promotions', models.BooleanField(default=False, help_text='Peut créer des promotions B2B')),
                ('has_api_access', models.BooleanField(default=False, help_text='Accès à l\'API pour intégrations')),
                ('commission_reduction_percent', models.DecimalField(decimal_places=2, default=0, help_text='Réduction sur les commissions en % (ex: 10 pour -10%)', max_digits=5)),
                ('custom_features', models.JSONField(blank=True, default=list, help_text='Liste d\'avantages personnalisés au format JSON')),
                ('is_active', models.BooleanField(default=True)),
                ('is_popular', models.BooleanField(default=False, help_text="Badge 'Populaire'")),
                ('display_order', models.IntegerField(default=0, help_text="Ordre d'affichage (croissant)")),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': "Plan d'abonnement B2B",
                'verbose_name_plural': "Plans d'abonnement B2B",
                'ordering': ['display_order', 'price'],
            },
        ),
        migrations.CreateModel(
            name='B2BStoreSubscription',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('plan_name', models.CharField(help_text='Nom du plan au moment de la souscription', max_length=100)),
                ('monthly_fee', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('status', models.CharField(choices=[('active', 'Actif'), ('cancelled', 'Annulé'), ('expired', 'Expiré'), ('pending_payment', 'En attente de paiement')], default='active', max_length=20)),
                ('start_date', models.DateField(default=timezone.now)),
                ('end_date', models.DateField(blank=True, help_text='Date de fin (null si actif)', null=True)),
                ('auto_renew', models.BooleanField(default=True, help_text='Renouvellement automatique')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('plan', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='subscriptions', to='b2b.b2bsubscriptionplan')),
                ('store', models.OneToOneField(limit_choices_to={'is_b2b': True}, on_delete=django.db.models.deletion.CASCADE, related_name='b2b_subscription', to='stores.store')),
            ],
            options={
                'verbose_name': 'Abonnement B2B',
                'verbose_name_plural': 'Abonnements B2B',
                'ordering': ['-created_at'],
            },
        ),
    ]

