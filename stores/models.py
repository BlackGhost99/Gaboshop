from django.db import models
from users.models import User


class StoreCategory(models.Model):
	"""
	Catégories de magasins (Épicerie, Vêtements, Électronique, etc.)
	"""
	name = models.CharField(max_length=100, unique=True)
	description = models.TextField(blank=True)
	icon = models.CharField(max_length=50, blank=True, help_text="Icône FontAwesome ou autre")
	is_active = models.BooleanField(default=True)
    
	class Meta:
		verbose_name = "Catégorie de Magasin"
		verbose_name_plural = "Catégories de Magasins"
		ordering = ['name']
    
	def __str__(self):
		return self.name


class Store(models.Model):
	"""
	Modèle pour les magasins partenaires de GABOSHOP
	"""
	# Informations de base
	name = models.CharField(max_length=200)
	description = models.TextField(blank=True)
	category = models.ForeignKey(StoreCategory, on_delete=models.PROTECT, related_name='stores')
	manager = models.ForeignKey(
		User, 
		on_delete=models.CASCADE, 
		limit_choices_to={'user_type': 'store_manager'},
		related_name='managed_stores'
	)
    
	# Contact et localisation
	phone = models.CharField(max_length=20, unique=True, help_text="Numéro unique par magasin")
	email = models.EmailField(blank=True)
	address = models.TextField()
	city = models.CharField(max_length=100, default='Libreville', help_text="Ville du magasin")
	zone = models.CharField(max_length=100, help_text="Zone à Libreville: Mont-Bouët, Louis, etc.")
	latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
	longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
	# Configuration business
	commission_rate = models.DecimalField(
		max_digits=5, 
		decimal_places=2, 
		default=8.00,
		help_text="Commission de GABOSHOP en % (défaut 8%)"
	)
	delivery_fee = models.DecimalField(
		max_digits=8, 
		decimal_places=2, 
		default=2000.00,
		help_text="Frais de livraison standard en FCFA"
	)
	delivery_fee_express = models.DecimalField(
		max_digits=8, 
		decimal_places=2, 
		default=3500.00,
		help_text="Frais de livraison express en FCFA"
	)
	service_fee = models.DecimalField(
		max_digits=8, 
		decimal_places=2, 
		default=0.00,
		help_text="Frais de service par commande (optionnel)"
	)
	min_order_amount = models.DecimalField(
		max_digits=8, 
		decimal_places=2, 
		default=0.00,
		help_text="Montant minimum de commande en FCFA"
	)
    
	# Statut et métadonnées
	is_active = models.BooleanField(default=True)
	is_verified = models.BooleanField(default=False)
	subscription_plan = models.CharField(
		max_length=20,
		choices=[('starter', 'Starter'), ('pro', 'Pro'), ('business', 'Business')],
		default='starter',
		help_text="Plan d'abonnement du magasin"
	)
	opening_time = models.TimeField(default='08:00')
	closing_time = models.TimeField(default='20:00')
    
	# Images
	logo = models.ImageField(upload_to='stores/logos/', blank=True, null=True)
	banner_image = models.ImageField(upload_to='stores/banners/', blank=True, null=True)
    
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
    
	class Meta:
		verbose_name = "Magasin"
		verbose_name_plural = "Magasins"
		ordering = ['-created_at']
		indexes = [
			models.Index(fields=['zone', 'is_active']),
			models.Index(fields=['category', 'is_active']),
		]
    
	def __str__(self):
		return f"{self.name} ({self.zone})"
    
	def is_open(self):
		from django.utils import timezone
		now = timezone.now().time()
		return self.opening_time <= now <= self.closing_time and self.is_active
    
	def total_products(self):
		return self.products.filter(is_available=True).count()
	
	def total_commandes_today(self):
		"""Nombre de commandes aujourd'hui"""
		from django.utils import timezone
		today = timezone.now().date()
		return self.orders.filter(created_at__date=today).count()
	
	def ventes_today(self):
		"""Total des ventes aujourd'hui"""
		from django.utils import timezone
		from django.db.models import Sum
		today = timezone.now().date()
		return self.orders.filter(
			created_at__date=today,
			status__in=['confirmed', 'preparing', 'ready', 'assigned', 'in_transit', 'delivered']
		).aggregate(total=Sum('total_amount'))['total'] or 0
