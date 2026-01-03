"""
Prix B2B pour les produits vendus en gros
"""
from django.db import models
from stores.models import Store
from products.models import Product


class B2BProductPricing(models.Model):
	"""
	Prix B2B pour un produit vendu par un grossiste
	
	Un produit peut avoir plusieurs prix B2B selon le grossiste.
	Chaque prix peut avoir des conditions de quantité minimale/maximale.
	"""
	product = models.ForeignKey(
		Product,
		on_delete=models.CASCADE,
		related_name='b2b_pricings',
		help_text="Produit concerné"
	)
	
	b2b_store = models.ForeignKey(
		Store,
		on_delete=models.CASCADE,
		related_name='b2b_pricings',
		help_text="Grossiste qui vend ce produit"
	)
	
	b2b_price = models.DecimalField(
		max_digits=10,
		decimal_places=2,
		help_text="Prix B2B en FCFA"
	)
	
	min_quantity = models.PositiveIntegerField(
		default=1,
		help_text="Quantité minimale pour ce prix (MOQ)"
	)
	
	max_quantity = models.PositiveIntegerField(
		null=True,
		blank=True,
		help_text="Quantité maximale pour ce prix (optionnel)"
	)
	
	is_active = models.BooleanField(
		default=True,
		help_text="Ce prix B2B est-il actif ?"
	)
	
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	
	class Meta:
		verbose_name = "Prix B2B"
		verbose_name_plural = "Prix B2B"
		ordering = ['b2b_store', 'product', 'min_quantity']
		unique_together = [['product', 'b2b_store', 'min_quantity']]
		indexes = [
			models.Index(fields=['product', 'b2b_store', 'is_active']),
			models.Index(fields=['is_active']),
		]
	
	def __str__(self):
		return f"{self.product.name} - {self.b2b_store.name} (min: {self.min_quantity})"



