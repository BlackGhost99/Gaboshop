from django.db import models
from django.core.exceptions import ValidationError
from users.models import User
from orders.models import Order


class Delivery(models.Model):
	"""
	Gestion des livraisons
	"""
	DELIVERY_STATUS_CHOICES = (
		('waiting', 'En attente d\'assignation'),
		('pending', 'En attente d\'acceptation'),
		('assigned', 'Assignée'),
		('accepted', 'Acceptée par livreur'),
		('picked_up', 'Colis récupéré'),
		('in_transit', 'En cours'),
		('delivered', 'Livrée'),
		('failed', 'Échec'),
		('cancelled', 'Annulée'),
	)
	
	PROOF_TYPE_CHOICES = (
		('photo', 'Photo de livraison'),
		('signature', 'Signature client'),
		('pin', 'Code PIN'),
	)
    
	# Relations
	order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='delivery')
	delivery_agent = models.ForeignKey(
		User, 
		on_delete=models.SET_NULL, 
		null=True, 
		blank=True,
		limit_choices_to={'user_type': 'delivery_agent'},
		related_name='deliveries'
	)
    
	# Informations livraison
	status = models.CharField(max_length=20, choices=DELIVERY_STATUS_CHOICES, default='waiting')
	tracking_number = models.CharField(max_length=50, unique=True, blank=True)
	
	# Assignation automatique
	is_auto_assigned = models.BooleanField(default=False, help_text="Assigné automatiquement")
	distance_to_store = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, help_text="Distance en km")
	estimated_duration = models.PositiveIntegerField(null=True, blank=True, help_text="Durée estimée en minutes")
    
	# Adresses
	city = models.CharField(max_length=100, default='Libreville', help_text="Ville de livraison")
	pickup_address = models.TextField(help_text="Adresse du magasin")
	pickup_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
	pickup_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
	delivery_address = models.TextField(help_text="Adresse du client")
	delivery_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
	delivery_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
	# Frais et rémunération
	delivery_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
	agent_commission = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    
	# Timestamps
	assigned_at = models.DateTimeField(null=True, blank=True)
	accepted_at = models.DateTimeField(null=True, blank=True)
	picked_up_at = models.DateTimeField(null=True, blank=True)
	delivered_at = models.DateTimeField(null=True, blank=True)
    
	# Preuve de livraison
	delivery_proof_type = models.CharField(max_length=20, choices=PROOF_TYPE_CHOICES, blank=True)
	delivery_proof_photo = models.ImageField(upload_to='delivery_proofs/', blank=True, null=True)
	delivery_code = models.CharField(max_length=6, blank=True, help_text="Code PIN à 4-6 chiffres")
	code_verified = models.BooleanField(default=False)
	
	# Coordonnées GPS de la livraison (preuve de localisation)
	proof_latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="Latitude au moment de la livraison")
	proof_longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True, help_text="Longitude au moment de la livraison")
	proof_address = models.CharField(max_length=255, blank=True, help_text="Adresse capturée au moment de la livraison")
	
	# Signature du client
	client_signature = models.ImageField(upload_to='delivery_signatures/', blank=True, null=True, help_text="Signature digitale du client")
	client_name_confirmed = models.CharField(max_length=100, blank=True, help_text="Nom du réceptionnaire")
    
	# Notes
	delivery_notes = models.TextField(blank=True, help_text="Notes du livreur")
	customer_feedback = models.TextField(blank=True, help_text="Retour client")
	rating = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Note 1-5")
    
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
    
	class Meta:
		verbose_name = "Livraison"
		verbose_name_plural = "Livraisons"
		ordering = ['-created_at']
    
	def __str__(self):
		return f"Livraison #{self.tracking_number} - {self.order.order_number}"
    
	def save(self, *args, **kwargs):
		"""Génère un numéro de suivi unique et code PIN"""
		if not self.tracking_number:
			import random
			import string
			self.tracking_number = f"TRK{''.join(random.choices(string.ascii_uppercase + string.digits, k=10))}"
		
		if not self.delivery_code:
			import random
			self.delivery_code = ''.join(random.choices('0123456789', k=6))
        
		super().save(*args, **kwargs)


class DeliveryTracking(models.Model):
	"""
	Historique des positions et statuts de livraison
	"""
	delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name='tracking_history')
	status = models.CharField(max_length=50)
	location = models.CharField(max_length=255, blank=True)
	latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
	longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
	notes = models.TextField(blank=True)
    
	created_at = models.DateTimeField(auto_now_add=True)
    
	class Meta:
		verbose_name = "Suivi de Livraison"
		verbose_name_plural = "Suivis de Livraison"
		ordering = ['-created_at']

	def __str__(self):
		return f"{self.delivery.tracking_number} - {self.status} - {self.created_at}"


class DeliveryProfile(models.Model):
	"""
	Profil étendu pour les livreurs
	"""
	AGENT_STATUS_CHOICES = (
		('available', 'Disponible'),
		('busy', 'Occupé'),
		('offline', 'Hors-ligne'),
		('suspended', 'Suspendu'),
	)

	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='delivery_profile')
	cin_number = models.CharField(max_length=50, blank=True, help_text="Numéro CIN ou ID interne")
	vehicle_type = models.CharField(max_length=50, blank=True, help_text="Moto, Voiture, Vélo")
	vehicle_plate = models.CharField(max_length=20, blank=True)

	status = models.CharField(max_length=20, choices=AGENT_STATUS_CHOICES, default='offline')

	# Stats cachées pour performance
	average_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
	total_deliveries = models.PositiveIntegerField(default=0)
	success_rate = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)

	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "Profil Livreur"
		verbose_name_plural = "Profils Livreurs"

	def __str__(self):
		return f"Profil Livreur: {self.user.get_full_name()}"


class DeliveryProof(models.Model):
	"""
	Preuve de livraison complète avec photo, GPS et signature
	Requis pour marquer une livraison comme 'delivered'
	"""
	PROOF_STATUS_CHOICES = (
		('pending', 'En attente'),
		('verified', 'Vérifié'),
		('rejected', 'Rejeté'),
	)
	
	delivery = models.OneToOneField(
		Delivery, 
		on_delete=models.CASCADE, 
		related_name='proof',
		help_text="Livraison associée"
	)
	
	# Photo pièce d'identité OBLIGATOIRE (car client peut venir chercher le colis)
	id_card_photo = models.ImageField(
		upload_to='delivery_proofs/id_cards/%Y/%m/%d/',
		blank=True,  # Temporaire pour migration
		null=True,   # Temporaire pour migration
		help_text="Photo de la pièce d'identité du client (OBLIGATOIRE)"
	)
	id_card_photo_uploaded_at = models.DateTimeField(auto_now_add=True)
	
	# Photo du colis OPTIONNELLE (car toutes les routes ne sont pas accessibles)
	package_photo = models.ImageField(
		upload_to='delivery_proofs/packages/%Y/%m/%d/',
		blank=True,
		null=True,
		help_text="Photo du colis livré (optionnelle)"
	)
	package_photo_uploaded_at = models.DateTimeField(null=True, blank=True)
	
	# Statut de réception côté client (confirmé dans l'app client)
	client_received_status = models.BooleanField(
		default=True,
		help_text="Client confirme avoir reçu le colis"
	)
	
	# Coordonnées GPS obligatoires
	latitude = models.DecimalField(
		max_digits=9, 
		decimal_places=6,
		help_text="Latitude GPS au moment de la livraison"
	)
	longitude = models.DecimalField(
		max_digits=9, 
		decimal_places=6,
		help_text="Longitude GPS au moment de la livraison"
	)
	gps_accuracy = models.DecimalField(
		max_digits=6, 
		decimal_places=2, 
		null=True, 
		blank=True,
		help_text="Précision GPS en mètres"
	)
	address_at_delivery = models.CharField(
		max_length=255, 
		blank=True,
		help_text="Adresse capturée via reverse geocoding"
	)
	
	# Signature ou Code PIN (l'un des deux requis)
	signature = models.ImageField(
		upload_to='delivery_signatures/%Y/%m/%d/',
		blank=True,
		null=True,
		help_text="Signature digitale du client"
	)
	pin_code = models.CharField(
		max_length=6,
		blank=True,
		help_text="Code PIN de vérification"
	)
	pin_verified = models.BooleanField(
		default=False,
		help_text="Code PIN vérifié"
	)
	
	# Informations complémentaires
	recipient_name = models.CharField(
		max_length=100,
		blank=True,
		help_text="Nom de la personne qui a reçu le colis"
	)
	recipient_phone = models.CharField(
		max_length=20,
		blank=True,
		help_text="Téléphone du réceptionnaire"
	)
	notes = models.TextField(
		blank=True,
		help_text="Notes ou remarques du livreur"
	)
	
	# Validation et statut
	status = models.CharField(
		max_length=20,
		choices=PROOF_STATUS_CHOICES,
		default='pending'
	)
	verified_by = models.ForeignKey(
		User,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='verified_proofs',
		help_text="Admin qui a vérifié la preuve"
	)
	verified_at = models.DateTimeField(null=True, blank=True)
	rejection_reason = models.TextField(
		blank=True,
		help_text="Raison du rejet si statut = rejected"
	)
	
	# Distance entre GPS de livraison et adresse client
	distance_from_address = models.DecimalField(
		max_digits=6,
		decimal_places=2,
		null=True,
		blank=True,
		help_text="Distance en mètres entre GPS et adresse client"
	)
	
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	
	class Meta:
		verbose_name = "Preuve de Livraison"
		verbose_name_plural = "Preuves de Livraison"
		ordering = ['-created_at']
	
	def __str__(self):
		return f"Preuve - {self.delivery.tracking_number} - {self.status}"
	
	def clean(self):
		"""Validation: Photo pièce d'identité + GPS obligatoires, Signature OU PIN requis"""
		errors = {}
		
		# Photo pièce d'identité OBLIGATOIRE
		if not self.id_card_photo:
			errors['id_card_photo'] = "La photo de la pièce d'identité du client est obligatoire"
		
		# GPS obligatoire
		if not self.latitude or not self.longitude:
			errors['latitude'] = "Les coordonnées GPS sont obligatoires"
		
		# Signature OU PIN requis
		if not self.signature and not self.pin_code:
			errors['signature'] = "La signature ou le code PIN est requis"
		
		if errors:
			raise ValidationError(errors)
	
	def save(self, *args, **kwargs):
		"""Validation avant sauvegarde"""
		self.full_clean()
		super().save(*args, **kwargs)
	
	@property
	def has_required_proof(self):
		"""Preuve minimale: pièce d'identité + GPS + signature/PIN vérifié."""
		has_id_card = bool(self.id_card_photo)  # Photo pièce d'identité OBLIGATOIRE
		has_gps = bool(self.latitude and self.longitude)
		has_verification = bool(self.signature or (self.pin_code and self.pin_verified))
		return has_id_card and has_gps and has_verification

	@property
	def is_valid(self):
		"""Compat: preuve techniquement complète côté livreur (sans confirmation client)."""
		return self.has_required_proof

	@property
	def is_fully_confirmed(self):
		"""Preuve complète + validation explicite du client."""
		return self.has_required_proof and self.client_received_status

	@property
	def client_confirmation_pending(self):
		"""Indique si le client doit encore confirmer la réception."""
		return self.has_required_proof and not self.client_received_status
	
	@property
	def is_location_valid(self):
		"""Vérifie si la localisation GPS est proche de l'adresse de livraison"""
		if self.distance_from_address is None:
			return None  # Pas encore calculé
		
		# Tolérance: 100 mètres
		return self.distance_from_address <= 100

