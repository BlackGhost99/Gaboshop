"""
Modèle pour l'audit trail des changements de statut
"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class AuditLog(models.Model):
	"""
	Enregistre chaque changement de statut et action importante
	"""
	ACTION_TYPES = (
		# Order & Delivery actions
		('order_status_change', 'Changement de statut de commande'),
		('delivery_status_change', 'Changement de statut de livraison'),
		('order_created', 'Création de commande'),
		('delivery_assigned', 'Attribution de livreur'),
		('order_cancelled', 'Annulation de commande'),
		('fraud_detected', 'Fraude potentielle détectée'),
		
		# Payment actions
		('payment_initiated', 'Paiement initié'),
		('payment_completed', 'Paiement confirmé'),
		('payment_failed', 'Paiement échoué'),
		('payment_refunded', 'Paiement remboursé'),
		
		# Store actions
		('store_created', 'Création de magasin'),
		('store_updated', 'Mise à jour de magasin'),
		('store_activated', 'Activation de magasin'),
		('store_deactivated', 'Désactivation de magasin'),
		
		# User actions
		('user_registered', 'Inscription utilisateur'),
		('user_login', 'Connexion utilisateur'),
		('user_profile_updated', 'Mise à jour profil'),
		('user_password_changed', 'Changement de mot de passe'),
		
		# Finance actions
		('commission_calculated', 'Commission calculée'),
		('payout_processed', 'Paiement livreur traité'),
		('subscription_created', 'Abonnement créé'),
		('subscription_renewed', 'Abonnement renouvelé'),
	)
	
	# Identification de l'action
	action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
	action_timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
	
	# Utilisateur qui a effectué l'action
	user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='audit_logs')
	user_role = models.CharField(max_length=20)  # Snapshot du rôle au moment de l'action
	
	# Ressource affectée
	object_type = models.CharField(max_length=50)  # 'order', 'delivery', 'payment', 'store', 'user', etc.
	object_id = models.PositiveIntegerField()
	
	# Changements
	old_value = models.CharField(max_length=100, blank=True, null=True)
	new_value = models.CharField(max_length=100, blank=True, null=True)
	
	# Détails supplémentaires
	ip_address = models.GenericIPAddressField(null=True, blank=True)
	user_agent = models.TextField(blank=True)
	reason = models.TextField(blank=True, help_text="Raison du changement")
	
	# Flags de sécurité
	is_suspicious = models.BooleanField(default=False, help_text="Marqué comme suspect par le système")
	notes = models.TextField(blank=True, help_text="Notes de l'administrateur")
	
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	
	class Meta:
		verbose_name = "Audit Log"
		verbose_name_plural = "Audit Logs"
		ordering = ['-action_timestamp']
		indexes = [
			models.Index(fields=['action_timestamp', 'object_type']),
			models.Index(fields=['user', 'action_timestamp']),
			models.Index(fields=['object_type', 'object_id']),
			models.Index(fields=['is_suspicious']),
		]
	
	def __str__(self):
		return f"{self.get_action_type_display()} - {self.object_type}#{self.object_id} ({self.action_timestamp})"
	
	@staticmethod
	def log_action(action_type, user, object_type, object_id, old_value=None, new_value=None, 
	               ip_address=None, user_agent=None, reason=None, is_suspicious=False, **kwargs):
		"""
		Helper pour créer un log audit
		
		Args:
			action_type: Type d'action
			user: User qui a effectué l'action
			object_type: Type d'objet ('order' ou 'delivery')
			object_id: ID de l'objet
			old_value: Ancienne valeur
			new_value: Nouvelle valeur
			ip_address: IP de l'utilisateur
			user_agent: User agent du navigateur
			reason: Raison du changement
			is_suspicious: Si marqué comme suspect
		"""
		return AuditLog.objects.create(
			action_type=action_type,
			user=user,
			user_role=user.user_type if user else 'anonymous',
			object_type=object_type,
			object_id=object_id,
			old_value=old_value,
			new_value=new_value,
			ip_address=ip_address,
			user_agent=user_agent,
			reason=reason,
			is_suspicious=is_suspicious,
		)
