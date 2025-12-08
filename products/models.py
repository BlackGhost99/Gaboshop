from django.db import models
from stores.models import Store


class ProductCategory(models.Model):
	"""
	Catégories de produits au sein d'un magasin
	"""
	store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='product_categories')
	name = models.CharField(max_length=100)
	description = models.TextField(blank=True)
	order = models.PositiveIntegerField(default=0, help_text="Ordre d'affichage")
    
	class Meta:
		verbose_name = "Catégorie de Produit"
		verbose_name_plural = "Catégories de Produits"
		ordering = ['order', 'name']
		unique_together = ['store', 'name']
    
	def __str__(self):
		return f"{self.name} - {self.store.name}"


class Product(models.Model):
	"""
	Produits vendus par les magasins
	"""
	# Relations
	store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='products')
	category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    
	# Informations produit
	name = models.CharField(max_length=200)
	description = models.TextField(blank=True)
	price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Prix en FCFA")
	compare_price = models.DecimalField(
		max_digits=10, 
		decimal_places=2, 
		null=True, 
		blank=True,
		help_text="Prix de comparaison (ancien prix)"
	)
    
	# Gestion stock
	stock = models.PositiveIntegerField(default=0)
	sku = models.CharField(max_length=100, blank=True, help_text="Référence interne")
	barcode = models.CharField(max_length=100, blank=True, help_text="Code-barres")
    
	# Statut et visibilité
	is_available = models.BooleanField(default=True)
	is_featured = models.BooleanField(default=False)
	
	# Sponsoring (pour produits mis en avant)
	is_sponsored = models.BooleanField(default=False, help_text="Produit sponsorisé (affiché en priorité)")
	sponsor_expiry = models.DateTimeField(null=True, blank=True, help_text="Date d'expiration du sponsoring")
	sponsor_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Prix payé pour le sponsoring")
    
	# Images
	image = models.ImageField(upload_to='products/', blank=True, null=True)
	image_2 = models.ImageField(upload_to='products/', blank=True, null=True)
	image_3 = models.ImageField(upload_to='products/', blank=True, null=True)
    
	# Métadonnées
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
    
	class Meta:
		verbose_name = "Produit"
		verbose_name_plural = "Produits"
		ordering = ['-created_at']
		indexes = [
			models.Index(fields=['store', 'is_available']),
			models.Index(fields=['category', 'is_available']),
		]
    
	def __str__(self):
		return f"{self.name} - {self.store.name}"
    
	def check_stock(self, quantity):
		"""Vérifie si le stock est suffisant"""
		return self.stock >= quantity
    
	def reduce_stock(self, quantity):
		"""Réduit le stock après vente"""
		if self.check_stock(quantity):
			self.stock -= quantity
			self.save()
			return True
		return False
    
	@property
	def has_discount(self):
		"""Vérifie si le produit a un prix promo"""
		return self.compare_price and self.compare_price > self.price
    
	@property
	def discount_percentage(self):
		"""Calcule le pourcentage de réduction"""
		if self.has_discount:
			return int(((self.compare_price - self.price) / self.compare_price) * 100)
		return 0
