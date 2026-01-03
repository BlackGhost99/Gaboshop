"""
Profil B2B pour les magasins grossistes
"""
from django.db import models
from stores.models import Store


class B2BProfile(models.Model):
	"""
	Profil B2B d'un magasin grossiste
	
	Un magasin peut avoir un profil B2B pour vendre en gros à d'autres magasins.
	"""
	store = models.OneToOneField(
		Store, 
		on_delete=models.CASCADE, 
		related_name="b2b_profile",
		help_text="Magasin associé à ce profil B2B"
	)
	
	is_active = models.BooleanField(
		default=True,
		help_text="Le profil B2B est-il actif ?"
	)
	
	minimum_order_amount = models.DecimalField(
		max_digits=10, 
		decimal_places=2, 
		default=0,
		help_text="Montant minimum de commande en FCFA"
	)
	
	visible_to_all = models.BooleanField(
		default=True,
		help_text="Visible par tous les magasins B2C (sinon accès restreint)"
	)
	
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	
	class Meta:
		verbose_name = "Profil B2B"
		verbose_name_plural = "Profils B2B"
		ordering = ['-created_at']
		indexes = [
			models.Index(fields=['is_active', 'visible_to_all']),
		]
	
	def __str__(self):
		return f"Profil B2B - {self.store.name}"



