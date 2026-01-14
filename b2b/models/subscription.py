"""
Modèles pour les abonnements B2B des grossistes
"""
from django.db import models
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
        
        if self.max_b2c_buyers:
            features.append({
                'title': f"Jusqu'à {self.max_b2c_buyers} clients B2C",
                'category': 'limits',
                'enabled': True
            })
        else:
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
        
        # Fonctionnalités
        if self.can_offer_bulk_discounts:
            features.append({
                'title': "Remises pour achats en gros",
                'category': 'features',
                'enabled': True
            })
        
        if self.can_view_detailed_reports or self.has_advanced_analytics:  # has_advanced_analytics pour compatibilité
            features.append({
                'title': "Statistiques avancées",
                'category': 'features',
                'enabled': True
            })
        
        if self.has_priority_support:
            features.append({
                'title': "Support prioritaire",
                'category': 'features',
                'enabled': True
            })
        
        if self.can_create_promotions:
            features.append({
                'title': "Créer des promotions",
                'category': 'features',
                'enabled': True
            })
        
        if self.has_api_access:
            features.append({
                'title': "Accès API",
                'category': 'features',
                'enabled': True
            })
        
        if self.featured_in_catalog:
            features.append({
                'title': "Mise en avant dans le catalogue",
                'category': 'marketing',
                'enabled': True
            })
        
        if self.catalog_priority > 0:
            features.append({
                'title': f"Priorité d'affichage niveau {self.catalog_priority}",
                'category': 'marketing',
                'enabled': True
            })
        
        if self.commission_reduction_percent > 0:
            features.append({
                'title': f"Réduction de {self.commission_reduction_percent}% sur les commissions",
                'category': 'pricing',
                'enabled': True
            })
        
        # Finance - Vue détaillée
        if self.can_view_finance_detailed:
            features.append({
                'title': "Finance : vue détaillée par commande et catégorie",
                'category': 'finance',
                'enabled': True
            })
        
        # Finance - Export CSV
        if self.can_export_finance_csv:
            features.append({
                'title': "Export CSV/Excel des rapports financiers",
                'category': 'finance',
                'enabled': True
            })
        
        # Finance - Export PDF
        if self.can_export_finance_pdf:
            features.append({
                'title': "Export PDF officiel des rapports financiers",
                'category': 'finance',
                'enabled': True
            })
        
        # Finance - Historique illimité
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
        
        # Accès approvisionnement B2B (seulement Pro et Business)
        if self.plan_type in ['pro', 'business']:
            features.append({
                'title': "Accès approvisionnement B2B (catalogues grossistes)",
                'category': 'features',
                'enabled': True
            })
        
        # Fonctionnalités personnalisées
        for custom_feature in self.custom_features:
            if custom_feature.get('enabled', True):
                features.append({
                    'title': custom_feature.get('title', ''),
                    'description': custom_feature.get('description', ''),
                    'category': custom_feature.get('category', 'custom'),
                    'enabled': True
                })
        
        return features


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

