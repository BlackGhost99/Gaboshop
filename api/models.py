from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


GABON_CITIES = "Libreville,Akanda,Owendo,Ntoum,Port-Gentil,Franceville,Moanda,Oyem,Lambaréné,Mouila"


class SystemSettings(models.Model):
    """
    Modèle singleton pour tous les paramètres système du e-commerce.
    Un seul enregistrement doit exister en base de données.
    """
    
    # === 1. COMMISSIONS ===
    commission_global = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=8.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Commission par défaut d'un nouveau commerce ou d'une nouvelle catégorie (%)"
    )
    b2b_commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=8.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Commission de base sur une commande entre commerces (B2B), avant réduction du plan (%)"
    )
    business_b2b_commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=2.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Plan Business : commission sur les commandes B2B (%)"
    )
    business_food_commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Plan Business : commission sur l'alimentaire vendu aux clients (%)"
    )
    business_other_commission_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=2.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Plan Business : commission sur le reste vendu aux clients (%)"
    )
    food_category_keywords = models.CharField(
        max_length=255, default="ALIMENTATION,BOISSONS",
        help_text="Mots qui font compter une catégorie de commerce comme alimentaire (séparés par des virgules)"
    )
    courier_share_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=80.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Part des frais de livraison versée au livreur ; le reste revient à Gaboshop (%)"
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
    unpaid_order_expiry_minutes = models.IntegerField(
        default=30,
        validators=[MinValueValidator(1)],
        help_text="Durée de validité d'une demande de paiement en ligne (minutes)"
    )
    payment_policy = models.JSONField(default=dict, blank=True, help_text="Circuits et plafonds de paiement actifs")
    
    # === 3. VILLES & GÉOLOCALISATION ===
    default_city = models.CharField(
        max_length=100,
        default="Libreville",
        help_text="Ville par défaut"
    )
    enabled_cities = models.TextField(
        default=GABON_CITIES,
        help_text="Liste des villes activées (séparées par des virgules)"
    )
    
    # === 4. LIVRAISON ===
    auto_assign_delivery = models.BooleanField(
        default=False,
        help_text="Attribution automatique des livreurs"
    )
    max_orders_per_delivery = models.IntegerField(
        default=3,
        validators=[MinValueValidator(1)],
        help_text="Nombre max de livraisons en cours par livreur avant de lui en proposer une autre"
    )
    
    default_delivery_fee = models.DecimalField(
        max_digits=8, decimal_places=2, default=2000.00, validators=[MinValueValidator(0)],
        help_text="Frais de livraison standard d'un nouveau commerce, utilisés quand aucune zone ne correspond (FCFA)"
    )
    default_express_delivery_fee = models.DecimalField(
        max_digits=8, decimal_places=2, default=3500.00, validators=[MinValueValidator(0)],
        help_text="Frais de livraison express d'un nouveau commerce (FCFA)"
    )
    default_intercity_surcharge = models.DecimalField(
        max_digits=8, decimal_places=2, default=1000.00, validators=[MinValueValidator(0)],
        help_text="Supplément quand le client est dans une autre ville que le commerce et qu'aucune zone ne le précise (FCFA)"
    )
    assignment_timeout_minutes = models.IntegerField(
        default=10, validators=[MinValueValidator(1)],
        help_text="Temps laissé à un livreur pour accepter une course avant de la proposer au suivant (minutes)"
    )
    broadcast_after_minutes = models.IntegerField(
        default=40, validators=[MinValueValidator(1)],
        help_text="Sans livreur après ce délai, la course est proposée à tous les livreurs (minutes)"
    )
    assignment_retry_minutes = models.IntegerField(
        default=5, validators=[MinValueValidator(1)],
        help_text="Quand aucun livreur n'est libre, nouvel essai après (minutes)"
    )
    pin_max_attempts = models.IntegerField(
        default=5, validators=[MinValueValidator(1)],
        help_text="Codes PIN de livraison erronés avant blocage"
    )
    pin_lock_minutes = models.IntegerField(
        default=30, validators=[MinValueValidator(1)],
        help_text="Durée du blocage après trop de codes PIN erronés (minutes)"
    )
    late_delivery_hours = models.IntegerField(
        default=2, validators=[MinValueValidator(1)],
        help_text="Une livraison en route depuis plus longtemps est signalée en retard (heures)"
    )

    # === 5. COMMANDES ===
    cart_validity_hours = models.IntegerField(
        default=24,
        validators=[MinValueValidator(1)],
        help_text="Une commande toujours en attente est annulée après ce délai (heures)"
    )
    pending_reminder_hours = models.IntegerField(
        default=1, validators=[MinValueValidator(1)],
        help_text="Rappel au client pour une commande toujours en attente après (heures)"
    )
    max_rejected_declarations = models.IntegerField(
        default=3, validators=[MinValueValidator(1)],
        help_text="Déclarations de paiement refusées avant blocage des nouvelles déclarations"
    )
    rejected_window_days = models.IntegerField(
        default=30, validators=[MinValueValidator(1)],
        help_text="Période sur laquelle les déclarations refusées sont comptées (jours)"
    )
    order_hours_enabled = models.BooleanField(
        default=False,
        help_text="Limiter les commandes à une plage horaire commune à toute l'app"
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
        default=False,
        help_text="Un nouveau commerce reste désactivé tant que l'admin ne l'a pas activé"
    )
    
    subscription_days = models.IntegerField(
        default=30, validators=[MinValueValidator(1)],
        help_text="Durée d'un abonnement payé (jours)"
    )
    subscription_reminder_days = models.IntegerField(
        default=7, validators=[MinValueValidator(1)],
        help_text="Rappel avant la fin d'un abonnement (jours)"
    )

    # === 7. NOTIFICATIONS ===
    enable_whatsapp = models.BooleanField(
        default=True,
        help_text="Activer les notifications WhatsApp"
    )
    enable_sms = models.BooleanField(
        default=True,
        help_text="Activer les notifications SMS"
    )
    enable_email = models.BooleanField(
        default=True,
        help_text="Activer les notifications Email"
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
    
    @classmethod
    def current(cls, name, default=None):
        """Valeur d'un réglage, ou ``default`` si la base n'est pas joignable (tests, migrations)."""
        try:
            return getattr(cls.get_settings(), name)
        except Exception:
            return default

    @classmethod
    def courier_share(cls, delivery_fee):
        """Part du livreur sur des frais de livraison, selon le pourcentage réglé dans l'admin."""
        from decimal import Decimal
        percent = Decimal(str(cls.current('courier_share_percent', 80) or 0))
        return (Decimal(str(delivery_fee or 0)) * percent / Decimal('100')).quantize(Decimal('0.01'))

    def food_keywords(self):
        return [k.strip().upper() for k in (self.food_category_keywords or '').split(',') if k.strip()]

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
