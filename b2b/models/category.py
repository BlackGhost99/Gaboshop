"""
Catégories B2B pour la classification logique des produits
"""
from django.db import models


class B2BCategory(models.Model):
	"""
	Catégorie B2B pour classification logique des produits
	
	Les catégories B2B sont différentes des catégories B2C (marketing).
	Elles servent à la logique métier et à l'organisation des produits en gros.
	"""
	name = models.CharField(
		max_length=100,
		unique=True,
		help_text="Nom de la catégorie B2B"
	)
	
	description = models.TextField(
		blank=True,
		help_text="Description de la catégorie"
	)
	
	is_active = models.BooleanField(
		default=True,
		help_text="La catégorie est-elle active ?"
	)
	
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	
	class Meta:
		verbose_name = "Catégorie B2B"
		verbose_name_plural = "Catégories B2B"
		ordering = ['name']
		indexes = [
			models.Index(fields=['is_active']),
		]
	
	def __str__(self):
		return self.name



