from django.db import models
from stores.models import Store, StoreCategory


class ProductCategory(models.Model):
	"""
	Catégories de produits (maintenues par catégorie de magasin).
	"""
	# Temporary state: keep `store` while migrating existing data, will be removed by migration.
	store = models.ForeignKey('stores.Store', on_delete=models.CASCADE, related_name='product_categories', null=True, blank=True)
	store_category = models.ForeignKey(StoreCategory, on_delete=models.PROTECT, related_name='product_categories', null=True, blank=True)
	name = models.CharField(max_length=100)
	description = models.TextField(blank=True)
	order = models.PositiveIntegerField(default=0, help_text="Ordre d'affichage")
	commission_rate = models.DecimalField(
		max_digits=5, 
		decimal_places=2, 
		default=8.00,
		help_text="Taux de commission en % pour les produits de cette catégorie"
	)

	class Meta:
		verbose_name = "Catégorie de Produit"
		verbose_name_plural = "Catégories de Produits"
		ordering = ['order', 'name']
		unique_together = ['store_category', 'name']

	def __str__(self):
		return f"{self.name} - {self.store_category.name}"



class Product(models.Model):
	"""
	Produits vendus par les magasins
	"""
	# Relations
	store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='products')
	category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
	b2b_category = models.ForeignKey(
		"b2b.B2BCategory",
		null=True,
		blank=True,
		on_delete=models.SET_NULL,
		related_name='products',
		help_text="Catégorie B2B (logique métier)"
	)
    
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
    
	# Poids pour calcul livraison
	weight_kg = models.DecimalField(
		max_digits=8, 
		decimal_places=2, 
		null=True, 
		blank=True,
		help_text="Poids du produit en kg"
	)
	estimated_weight_kg = models.DecimalField(
		max_digits=8,
		decimal_places=2,
		null=True,
		blank=True,
		help_text="Poids estimé si non renseigné (calculé automatiquement)"
	)
    
	# Statut et visibilité
	is_available = models.BooleanField(default=True)
	is_featured = models.BooleanField(default=False)
	
	# Type de marché
	MARKET_TYPE_CHOICES = [
		('b2c', 'B2C - Vente au détail'),
		('b2b', 'B2B - Vente en gros'),
		('both', 'B2C et B2B'),
	]
	market_type = models.CharField(
		max_length=10,
		choices=MARKET_TYPE_CHOICES,
		default='b2c',
		help_text="Type de marché pour ce produit"
	)
	
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
			models.Index(fields=['market_type', 'is_available'], name='product_market_avail_idx'),
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


class ProductVariant(models.Model):
	"""
	Variant d'un produit (taille, couleur, etc.)
	"""
	product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='variants')
	name = models.CharField(max_length=200, help_text="Nom de la variante, ex: Rouge / XL")
	sku = models.CharField(max_length=120, blank=True, help_text="SKU optionnel pour la variante")
	price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Prix spécifique (si null = produit.price)")
	stock = models.IntegerField(default=0)
	attributes = models.JSONField(default=dict, blank=True, help_text="Attributs libres ex: {'color': 'red', 'size': 'L'}")
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "Variante Produit"
		verbose_name_plural = "Variantes Produits"
		ordering = ['-created_at']

	def __str__(self):
		return f"{self.product.name} - {self.name}"

	def get_price(self):
		return self.price if self.price is not None else self.product.price


class ProductImage(models.Model):
	"""
	Images additionnelles liées à un produit. Utiliser pour galerie et upload multi-images.
	"""
	product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
	image = models.ImageField(upload_to='products/gallery/')
	alt_text = models.CharField(max_length=200, blank=True)
	order = models.PositiveIntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		verbose_name = "Image Produit"
		verbose_name_plural = "Images Produits"
		ordering = ['order', '-created_at']

	def __str__(self):
		return f"Image {self.id} - {self.product.name}"
