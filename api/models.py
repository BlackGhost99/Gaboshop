from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class SystemSettings(models.Model):
    """
    Modèle singleton pour tous les paramètres système du e-commerce.
    Un seul enregistrement doit exister en base de données.
    """
    
    # === 1. COMMISSIONS ===
    commission_global = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=10.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Commission globale par défaut (%)"
    )
    commission_event = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=5.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Commission exceptionnelle pour événements/promos (%)"
    )
    
    # === 2. PAIEMENTS ===
    moov_money_fee = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=1.50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Frais Moov Money (%)"
    )
    airtel_money_fee = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=1.50,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Frais Airtel Money (%)"
    )
    payment_before_order = models.BooleanField(
        default=True,
        help_text="Paiement requis avant validation de commande"
    )
    unpaid_order_expiry_minutes = models.IntegerField(
        default=30,
        validators=[MinValueValidator(1)],
        help_text="Délai max avant expiration d'une commande impayée (minutes)"
    )
    
    # === 3. VILLES & GÉOLOCALISATION ===
    auto_detect_cities = models.BooleanField(
        default=True,
        help_text="Détection automatique des villes"
    )
    default_city = models.CharField(
        max_length=100,
        default="Abidjan",
        help_text="Ville par défaut"
    )
    enabled_cities = models.TextField(
        default="Abidjan,Bouaké,Yamoussoukro,San-Pedro,Korhogo",
        help_text="Liste des villes activées (séparées par des virgules)"
    )
    max_delivery_distance_km = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        default=50.00,
        validators=[MinValueValidator(0)],
        help_text="Distance max de livraison (km)"
    )
    
    # === 4. LIVRAISON ===
    price_per_km = models.DecimalField(
        max_digits=8, 
        decimal_places=2, 
        default=200.00,
        validators=[MinValueValidator(0)],
        help_text="Prix par km (FCFA)"
    )
    auto_assign_delivery = models.BooleanField(
        default=False,
        help_text="Attribution automatique des livreurs"
    )
    max_orders_per_delivery = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1)],
        help_text="Max commandes simultanées par livreur"
    )
    
    # === 5. COMMANDES ===
    cart_validity_hours = models.IntegerField(
        default=24,
        validators=[MinValueValidator(1)],
        help_text="Durée de validité d'un panier (heures)"
    )
    order_opening_time = models.TimeField(
        default="08:00:00",
        help_text="Heure d'ouverture des commandes"
    )
    order_closing_time = models.TimeField(
        default="22:00:00",
        help_text="Heure de fermeture des commandes"
    )
    
    # === 6. MAGASINS ===
    default_store_opening = models.TimeField(
        default="08:00:00",
        help_text="Heure d'ouverture par défaut des magasins"
    )
    default_store_closing = models.TimeField(
        default="20:00:00",
        help_text="Heure de fermeture par défaut des magasins"
    )
    store_verification_required = models.BooleanField(
        default=True,
        help_text="Vérification requise pour les nouveaux magasins"
    )
    pro_mode_monthly_fee = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=50000.00,
        validators=[MinValueValidator(0)],
        help_text="Tarif mensuel Mode Pro (FCFA)"
    )
    
    # === 7. NOTIFICATIONS ===
    enable_sms = models.BooleanField(
        default=True,
        help_text="Activer les notifications SMS"
    )
    enable_email = models.BooleanField(
        default=True,
        help_text="Activer les notifications Email"
    )
    notification_templates = models.JSONField(
        default=dict,
        blank=True,
        help_text="Templates de notifications personnalisés"
    )
    
    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Paramètre Système"
        verbose_name_plural = "Paramètres Système"
    
    def __str__(self):
        return f"Paramètres Système (mis à jour le {self.updated_at.strftime('%d/%m/%Y %H:%M')})"
    
    def save(self, *args, **kwargs):
        """Assurer qu'un seul enregistrement existe (singleton pattern)"""
        if not self.pk and SystemSettings.objects.exists():
            # Si on essaie de créer un nouvel enregistrement alors qu'un existe déjà
            raise ValueError("Un seul enregistrement SystemSettings peut exister. Modifiez l'existant.")
        return super().save(*args, **kwargs)
    
    @classmethod
    def get_settings(cls):
        """Récupérer l'instance unique des paramètres système"""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings
    
    def get_enabled_cities_list(self):
        """Retourne la liste des villes activées"""
        return [city.strip() for city in self.enabled_cities.split(',') if city.strip()]


class CommissionByCategory(models.Model):
    """
    Commissions spécifiques par catégorie de magasin.
    Permet d'outrepasser la commission globale.
    """
    category = models.ForeignKey(
        'stores.StoreCategory', 
        on_delete=models.CASCADE,
        related_name='commissions'
    )
    commission_rate = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Taux de commission pour cette catégorie (%)"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Commission par Catégorie"
        verbose_name_plural = "Commissions par Catégorie"
        unique_together = ['category']
    
    def __str__(self):
        return f"{self.category.name} - {self.commission_rate}%"


class AIActionLog(models.Model):
    """
    Log de toutes les actions effectuées par l'IA
    """
    ACTION_TYPES = (
        ('search', 'Recherche'),
        ('prepare_order', 'Préparation commande'),
        ('confirm_order', 'Confirmation commande'),
        ('explain_error', 'Explication erreur'),
        ('suggest_action', 'Suggestion action'),
        ('trigger_alert', 'Déclenchement alerte'),
    )
    
    # Identification
    actor = models.CharField(max_length=20, default='AI', help_text="Toujours 'AI'")
    initiator = models.ForeignKey(
        'users.User', 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='ai_actions',
        help_text="Utilisateur qui a initié l'action"
    )
    action = models.CharField(max_length=50, choices=ACTION_TYPES)
    
    # Détails
    details = models.JSONField(default=dict, help_text="Détails de l'action (produits, montants, etc.)")
    confirmed = models.BooleanField(default=False, help_text="Action confirmée par l'utilisateur")
    
    # Résultat
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Métadonnées
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Log Action IA"
        verbose_name_plural = "Logs Actions IA"
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'action']),
            models.Index(fields=['initiator', 'timestamp']),
            models.Index(fields=['confirmed']),
        ]
    
    def __str__(self):
        return f"AI {self.action} - {self.initiator} - {self.timestamp}"