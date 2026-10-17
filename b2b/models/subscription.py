"""
Modèles pour les abonnements B2B des grossistes
"""
from django.db import models
import re
import unicodedata
from django.utils import timezone
from decimal import Decimal


class B2BSubscriptionPlan(models.Model):
    """
    Plans d'abonnement pour les grossistes B2B (Free, Pro, Business)
    """
    PLAN_TYPE_CHOICES = (
        ('free', 'Free'),
        ('pro', 'Pro'),
        ('business', 'Business'),
    )
    
    # Informations de base
    name = models.CharField(max_length=100, unique=True, help_text="Nom du plan (ex: B2B Free)")
    slug = models.SlugField(max_length=100, unique=True)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPE_CHOICES, unique=True)
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        help_text="Prix mensuel en FCFA"
    )
    
    # Description et promotion
    description = models.TextField(blank=True, help_text="Description courte du plan")
    tagline = models.CharField(max_length=200, blank=True, help_text="Slogan du plan (ex: 'Idéal pour débuter')")
    
    # Limites et quotas
    max_b2b_products = models.IntegerField(
        null=True, 
        blank=True, 
        help_text="Nombre max de produits B2B (null = illimité)"
    )
    max_b2c_buyers = models.IntegerField(
        null=True,
        blank=True,
        help_text="Nombre max de magasins B2C clients (null = illimité)"
    )
    max_monthly_orders = models.IntegerField(
        null=True,
        blank=True,
        help_text="Nombre max de commandes B2B par mois (null = illimité)"
    )
    
    # Distribution & visibilité commerciale
    catalog_priority = models.IntegerField(
        default=0,
        help_text="Priorité d'affichage dans le catalogue B2B (Distribution prioritaire)"
    )
    featured_in_catalog = models.BooleanField(
        default=False,
        help_text="Référencé en tête du catalogue B2B (Grossiste recommandé)"
    )
    
    # Fonctionnalités booléennes
    can_offer_bulk_discounts = models.BooleanField(
        default=True,
        help_text="Peut proposer des remises pour achats en gros"
    )
    has_advanced_analytics = models.BooleanField(
        default=False,
        help_text="Accès aux statistiques avancées B2B (déprécié, utiliser can_view_detailed_reports)"
    )
    can_view_detailed_reports = models.BooleanField(
        default=False,
        help_text="Peut voir les détails par commande et par catégorie"
    )
    has_priority_support = models.BooleanField(
        default=False,
        help_text="Support prioritaire"
    )
    can_create_promotions = models.BooleanField(
        default=False,
        help_text="Peut créer des promotions B2B"
    )
    has_api_access = models.BooleanField(
        default=False,
        help_text="Accès à l'API pour intégrations"
    )
    can_import_products = models.BooleanField(
        default=False,
        help_text="Import de produits par fichier Excel/CSV"
    )
    has_stock_alerts = models.BooleanField(
        default=False,
        help_text="Alerte (notification et téléphone) quand un produit passe sous le seuil de stock"
    )

    # Commissions et frais
    commission_reduction_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Réduction sur les commissions en % (ex: 10 pour -10%)"
    )
    
    # FINANCE (aligné avec B2C et Buyers B2B)
    can_view_finance_basic = models.BooleanField(
        default=True,
        help_text="Peut voir les rapports financiers basiques (ventes du jour/mois)"
    )
    can_view_finance_detailed = models.BooleanField(
        default=False,
        help_text="Peut voir les détails financiers par commande et par catégorie"
    )
    can_export_finance_csv = models.BooleanField(
        default=False,
        help_text="Peut exporter les rapports financiers en Excel/CSV"
    )
    can_export_finance_pdf = models.BooleanField(
        default=False,
        help_text="Peut exporter les rapports financiers en PDF officiel"
    )
    finance_history_limit_days = models.IntegerField(
        null=True,
        blank=True,
        help_text="Limite d'historique financier en jours (null = illimité)"
    )
    
    # TYPE DE MAGASIN
    applies_to = models.CharField(
        max_length=20,
        choices=[('b2b_wholesaler', 'B2B Grossiste uniquement')],
        default='b2b_wholesaler',
        help_text="Type de magasin auquel ce plan s'applique"
    )
    
    # Avantages personnalisables (JSON pour flexibilité)
    custom_features = models.JSONField(
        default=list,
        blank=True,
        help_text="Liste d'avantages personnalisés au format JSON [{\"title\": \"...\", \"description\": \"...\", \"enabled\": true}]"
    )
    
    # Métadonnées
    is_active = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True, help_text="Décoché : le plan reste visible mais grisé « Bientôt disponible » et ne peut pas être acheté")
    is_popular = models.BooleanField(default=False, help_text="Badge 'Populaire'")
    display_order = models.IntegerField(default=0, help_text="Ordre d'affichage (croissant)")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Plan d'abonnement B2B"
        verbose_name_plural = "Plans d'abonnement B2B"
        ordering = ['display_order', 'price']
    
    def __str__(self):
        return f"{self.name} - {self.price} FCFA/mois"
    
    def get_all_features(self):
        """Retourne toutes les fonctionnalités du plan"""
        def normalize_text(value):
            text = (value or '').strip().lower()
            text = unicodedata.normalize('NFD', text)
            text = re.sub(r'[\u0300-\u036f]', '', text)
            text = re.sub(r'[^a-z0-9]+', ' ', text)
            return ' '.join(text.split())

        def feature_key(value):
            normalized = normalize_text(value)
            if not normalized:
                return ''
            match = re.search(r'\d+', normalized)
            if 'produit' in normalized:
                key = 'produits_b2b'
                if match:
                    return f"{key}:{match.group(0)}"
            if 'commande' in normalized and match:
                return f"commandes:{match.group(0)}"
            if 'client' in normalized and match:
                return f"clients:{match.group(0)}"
            return normalized

        features = []
        
        # Limites
        if self.max_b2b_products:
            features.append({
                'title': f"Jusqu'à {self.max_b2b_products} produits B2B",
                'category': 'limits',
                'enabled': True
            })
        else:
            features.append({
                'title': "Produits B2B illimités",
                'category': 'limits',
                'enabled': True
            })
        
        # Aucune limite de commerces clients n'est appliquée par le code : on ne promet pas de plafond.
        if not self.max_b2c_buyers:
            features.append({
                'title': "Clients B2C illimités",
                'category': 'limits',
                'enabled': True
            })
        
        if self.max_monthly_orders:
            features.append({
                'title': f"Jusqu'à {self.max_monthly_orders} commandes/mois",
                'category': 'limits',
                'enabled': True
            })
        else:
            features.append({
                'title': "Commandes illimitées",
                'category': 'limits',
                'enabled': True
            })
        
        # Seules les lignes que le code applique (payments/plan_features.py). Ne sont plus promis : remises en gros
        # (seul l'admin crée les prix par quantité), promotions, API, support prioritaire, approvisionnement
        # (un grossiste ne peut pas commander : b2b/services/permissions.py must_be_b2c_store).
        from payments.plan_features import keep_free_text, tool_lines
        for title in tool_lines(self):
            features.append({'title': title, 'category': 'features', 'enabled': True})

        if self.featured_in_catalog:
            features.append({
                'title': "Mise en avant dans la liste des grossistes",
                'category': 'marketing',
                'enabled': True
            })

        if self.catalog_priority > 0:
            features.append({
                'title': "Priorité d'affichage dans la liste des grossistes",
                'category': 'marketing',
                'enabled': True
            })

        if self.commission_reduction_percent > 0:
            features.append({
                'title': f"Réduction de {Decimal(self.commission_reduction_percent).normalize():f} % sur les commissions",
                'category': 'pricing',
                'enabled': True
            })

        # Finance - Ventes par catégorie (écran Finance, même case que les statistiques avancées)
        if self.can_view_detailed_reports:
            features.append({
                'title': "Finance : ventes par catégorie",
                'category': 'finance',
                'enabled': True
            })

        # Finance - Historique : un avantage seulement s'il est plus long que celui du forfait Gratuit.
        free = type(self).objects.filter(plan_type='free').exclude(pk=self.pk).first()
        free_limit = free.finance_history_limit_days if free is not None else None
        longer = (self.plan_type != 'free' and free is not None and free_limit is not None
                  and (self.finance_history_limit_days is None or self.finance_history_limit_days > free_limit))
        if longer:
            if self.finance_history_limit_days is None:
                features.append({
                    'title': "Historique financier illimité",
                    'category': 'finance',
                    'enabled': True
                })
            elif self.finance_history_limit_days > 0:
                features.append({
                    'title': f"Historique financier : {self.finance_history_limit_days} jours",
                    'category': 'finance',
                    'enabled': True
                })

        # Avantages saisis par l'admin : gardés seulement s'ils ne promettent pas un outil inexistant.
        for custom_feature in self.custom_features:
            title = custom_feature.get('title', '')
            if custom_feature.get('enabled', True) and keep_free_text(title):
                features.append({
                    'title': title,
                    'description': custom_feature.get('description', ''),
                    'category': custom_feature.get('category', 'custom'),
                    'enabled': True
                })

        unique = []
        seen = set()
        for item in features:
            title = item.get('title', '')
            key = feature_key(title)
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(item)

        return unique


class B2BStoreSubscription(models.Model):
    """
    Abonnement d'un magasin B2B (grossiste) à un plan
    """
    STATUS_CHOICES = (
        ('active', 'Actif'),
        ('cancelled', 'Annulé'),
        ('expired', 'Expiré'),
        ('pending_payment', 'En attente de paiement'),
    )
    
    # Relations
    store = models.OneToOneField(
        'stores.Store',
        on_delete=models.CASCADE,
        related_name='b2b_subscription',
        limit_choices_to={'is_b2b': True}
    )
    plan = models.ForeignKey(
        B2BSubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='subscriptions',
        null=True,
        blank=True
    )
    
    # Informations de l'abonnement
    plan_name = models.CharField(max_length=100, help_text="Nom du plan au moment de la souscription")
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Statut et dates
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True, help_text="Date de fin (null si actif)")
    auto_renew = models.BooleanField(default=True, help_text="Renouvellement automatique")
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Abonnement B2B"
        verbose_name_plural = "Abonnements B2B"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.store.name} - {self.plan_name} ({self.status})"
    
    def is_active(self):
        """Vérifie si l'abonnement est actif"""
        if self.status != 'active':
            return False
        if self.end_date and self.end_date < timezone.now().date():
            return False
        return True
    
    def get_remaining_days(self):
        """Nombre de jours restants"""
        if not self.end_date:
            return None
        remaining = (self.end_date - timezone.now().date()).days
        return max(0, remaining)
    
    def cancel(self):
        """Annule l'abonnement"""
        self.status = 'cancelled'
        self.auto_renew = False
        self.save()
    
    def renew(self, duration_days=30):
        """Renouvelle l'abonnement"""
        from datetime import timedelta
        if self.end_date:
            self.end_date = self.end_date + timedelta(days=duration_days)
        else:
            self.end_date = timezone.now().date() + timedelta(days=duration_days)
        self.status = 'active'
        self.save()
