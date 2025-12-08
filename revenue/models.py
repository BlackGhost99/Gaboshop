from django.db import models
from django.utils import timezone
from stores.models import Store
from users.models import User
from orders.models import Order

class StoreSubscription(models.Model):
    """
    Abonnements SaaS pour les magasins
    """
    PLAN_CHOICES = (
        ('starter', 'Starter (Gratuit)'),
        ('pro', 'Pro (10.000 FCFA/mois)'),
        ('business', 'Business (30.000 FCFA/mois)'),
    )

    store = models.OneToOneField(Store, on_delete=models.CASCADE, related_name='subscription')
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='starter')
    
    # Période de validité
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # Paiement
    auto_renew = models.BooleanField(default=True)
    last_payment_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Abonnement Magasin"
        verbose_name_plural = "Abonnements Magasins"

    def __str__(self):
        return f"{self.store.name} - {self.get_plan_display()}"

    @property
    def is_valid(self):
        if self.plan == 'starter':
            return True
        return self.is_active and self.end_date and self.end_date > timezone.now()


class BannerAd(models.Model):
    """
    Publicités et bannières sponsorisées
    """
    POSITION_CHOICES = (
        ('home_top', 'Accueil - Haut'),
        ('home_middle', 'Accueil - Milieu'),
        ('category_top', 'Catégorie - Haut'),
        ('search_result', 'Résultat de recherche'),
    )

    title = models.CharField(max_length=100)
    image = models.ImageField(upload_to='ads/')
    link = models.URLField(blank=True, help_text="Lien de redirection (interne ou externe)")
    
    # Ciblage
    store = models.ForeignKey(Store, on_delete=models.CASCADE, null=True, blank=True, related_name='ads')
    position = models.CharField(max_length=20, choices=POSITION_CHOICES, default='home_top')
    
    # Validité
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    
    # Performance
    views_count = models.PositiveIntegerField(default=0)
    clicks_count = models.PositiveIntegerField(default=0)
    
    # Financier
    price_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    class Meta:
        verbose_name = "Publicité"
        verbose_name_plural = "Publicités"
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.title} ({self.get_position_display()})"


class Cashback(models.Model):
    """
    Portefeuille Cashback des clients
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cashbacks')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Source
    source_order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='generated_cashback')
    description = models.CharField(max_length=200, help_text="Raison du cashback (ex: Fidélité commande #123)")
    
    # État
    is_credit = models.BooleanField(default=True, help_text="True = Gain, False = Utilisation")
    expiry_date = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cashback"
        verbose_name_plural = "Historique Cashback"
        ordering = ['-created_at']

    def __str__(self):
        sign = "+" if self.is_credit else "-"
        return f"{sign}{self.amount} FCFA - {self.user.phone}"
