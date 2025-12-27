from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager
from django.db import models
import secrets
from django.utils import timezone


class UserManager(BaseUserManager):
	"""Custom manager for User where phone is the unique identifiers
	for authentication instead of usernames.
	"""
	use_in_migrations = True

	def create_user(self, phone, password=None, **extra_fields):
		if not phone:
			raise ValueError('The phone must be set')

		# Normaliser le numéro de téléphone selon les mêmes règles que LoginSerializer
		phone = phone.strip().replace(' ', '')
		if phone.startswith('+241'):
			phone = phone
		elif phone.startswith('241'):
			phone = '+' + phone
		elif phone.startswith('0'):
			phone = '+241' + phone[1:]
		elif phone.isdigit() and len(phone) == 8:
			phone = '+241' + phone
		# else: keep as provided

		# keep compatibility with previous code paths that used normalize_email for emails
		phone = phone
		# Ensure username is set (AbstractUser still has a username field with unique constraint)
		username = extra_fields.pop('username', None) or phone
		extra_fields.setdefault('email', extra_fields.get('email', ''))
		user = self.model(username=username, phone=phone, **extra_fields)
		user.set_password(password)
		user.save(using=self._db)
		return user

	def create_superuser(self, phone, password, **extra_fields):
		extra_fields.setdefault('is_staff', True)
		extra_fields.setdefault('is_superuser', True)
		extra_fields.setdefault('is_active', True)

		if extra_fields.get('is_staff') is not True:
			raise ValueError('Superuser must have is_staff=True.')
		if extra_fields.get('is_superuser') is not True:
			raise ValueError('Superuser must have is_superuser=True.')

		return self.create_user(phone, password, **extra_fields)


class User(AbstractUser):
	"""
	Modèle User personnalisé qui remplace le modèle User par défaut de Django
	On utilise le numéro de téléphone comme identifiant principal
	"""
    
	# Types d'utilisateurs dans GABOSHOP
	USER_TYPE_CHOICES = (
		('client', 'Client'),
		('store_manager', 'Gérant de Magasin'),
		('delivery_agent', 'Livreur'),
		('admin', 'Administrateur'),
	)
    
	# === CHAMPS PRINCIPAUX ===
	user_type = models.CharField(
		max_length=20, 
		choices=USER_TYPE_CHOICES, 
		default='client'
	)
    
	# Override username to make it optional (we use `phone` as the primary identifier)
	username = models.CharField(
		max_length=150,
		unique=False,
		blank=True,
		null=True,
		help_text="Optional username; phone is used as the primary identifier",
	)
    
	# Numéro de téléphone comme identifiant principal (format Gabon)
	phone = models.CharField(
		max_length=20, 
		unique=True,
		help_text="Numéro au format Gabon: +24101234567 ou 01234567"
	)
    
	# Email optionnel (certains utilisateurs n'ont pas d'email)
	email = models.EmailField(blank=True)
    
	# === CHAMPS SPÉCIFIQUES PAR TYPE ===
	# Pour les livreurs
	is_available = models.BooleanField(default=True, help_text="Livreur disponible pour livraison")
	current_location = models.CharField(max_length=255, blank=True, help_text="Localisation actuelle du livreur")
	city = models.CharField(max_length=100, default='Libreville', help_text="Ville de résidence ou d'opération")
    
	# Pour tous les utilisateurs
	is_verified = models.BooleanField(default=False, help_text="Compte vérifié")
	profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True, help_text="Photo de profil")
	date_joined = models.DateTimeField(auto_now_add=True)
    
	# === CONFIGURATION AUTH ===
	# REMPLACER username par phone pour l'authentification
	USERNAME_FIELD = 'phone'
	REQUIRED_FIELDS = ['email']  # Seul email est requis pour createsuperuser

	objects = UserManager()
    
	class Meta:
		db_table = 'users'
		verbose_name = 'Utilisateur'
		verbose_name_plural = 'Utilisateurs'
		ordering = ['-date_joined']
    
	def __str__(self):
		return f"{self.phone} ({self.get_user_type_display()})"

	# Helpers rôle
	def is_client(self):
		return self.user_type == 'client'

	def is_store_manager(self):
		return self.user_type == 'store_manager'

	def is_delivery_agent(self):
		return self.user_type == 'delivery_agent'

	def is_admin(self):
		return self.user_type == 'admin' or self.is_staff or self.is_superuser

	def get_display_name(self):
		"""Retourne un nom d'affichage approprié"""
		if self.first_name and self.last_name:
			return f"{self.first_name} {self.last_name}"
		elif self.first_name:
			return self.first_name
		else:
			return f"User {self.phone}"


class DeliveryAgentApiKey(models.Model):
	"""
	API key for delivery agents to allow persistent auth from mobile devices.
	"""
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='api_key')
	key = models.CharField(max_length=64, unique=True, db_index=True)
	created_at = models.DateTimeField(auto_now_add=True)
	last_used_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		verbose_name = "API Key Livreur"
		verbose_name_plural = "API Keys Livreurs"

	def __str__(self):
		return f"API Key for {self.user.phone}"

	@classmethod
	def generate_key(cls):
		return secrets.token_urlsafe(32)

	@classmethod
	def create_for_user(cls, user):
		key = cls.generate_key()
		return cls.objects.create(user=user, key=key, created_at=timezone.now())



class ClientProfile(models.Model):
	"""
	Profil spécifique aux clients
	"""
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_profile')
	
	# Adresses
	adresse_principale = models.TextField(help_text="Adresse principale de livraison")
	zone_principale = models.CharField(max_length=100, help_text="Zone à Libreville")
	adresses_supplementaires = models.JSONField(default=list, blank=True, help_text="Liste d'adresses supplémentaires")
	
	# Préférences
	preferences_livraison = models.TextField(blank=True, help_text="Instructions de livraison par défaut")
	
	# Statistiques
	total_commandes = models.PositiveIntegerField(default=0)
	total_depense = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
	
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	
	class Meta:
		verbose_name = "Profil Client"
		verbose_name_plural = "Profils Clients"
	
	def __str__(self):
		return f"Client: {self.user.phone}"


class GerantProfile(models.Model):
	"""
	Profil spécifique aux gérants de magasins
	"""
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='gerant_profile')
	
	# Informations professionnelles
	date_debut_activite = models.DateField(null=True, blank=True)
	documents_verification = models.JSONField(default=dict, blank=True, help_text="CNI, registre commerce, etc.")
	
	# Statistiques
	total_ventes = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
	total_commandes_recues = models.PositiveIntegerField(default=0)
	
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	
	class Meta:
		verbose_name = "Profil Gérant"
		verbose_name_plural = "Profils Gérants"
	
	def __str__(self):
		return f"Gérant: {self.user.phone}"


class LivreurProfile(models.Model):
	"""
	Profil spécifique aux livreurs
	"""
	VEHICULE_CHOICES = (
		('moto', 'Moto'),
		('scooter', 'Scooter'),
		('velo', 'Vélo'),
		('voiture', 'Voiture'),
	)
	
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='livreur_profile')
	
	# Disponibilité et localisation
	disponible = models.BooleanField(default=True, help_text="Livreur disponible pour assignation")
	position_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
	position_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
	last_position_update = models.DateTimeField(null=True, blank=True)
	
	# Informations véhicule
	type_vehicule = models.CharField(max_length=20, choices=VEHICULE_CHOICES, default='moto')
	immatriculation = models.CharField(max_length=50, blank=True)
	
	# Documents
	cni = models.CharField(max_length=50, blank=True, help_text="Numéro CNI")
	permis = models.CharField(max_length=50, blank=True, help_text="Numéro permis de conduire")
	documents_verifies = models.BooleanField(default=False)
	
	# Statistiques et performance
	total_livraisons = models.PositiveIntegerField(default=0)
	livraisons_reussies = models.PositiveIntegerField(default=0)
	livraisons_echouees = models.PositiveIntegerField(default=0)
	note_moyenne = models.DecimalField(max_digits=3, decimal_places=2, default=0.00, help_text="Note sur 5")
	total_revenus = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
	
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	
	class Meta:
		verbose_name = "Profil Livreur"
		verbose_name_plural = "Profils Livreurs"
		indexes = [
			models.Index(fields=['disponible', 'position_lat', 'position_lng']),
		]
	
	def __str__(self):
		return f"Livreur: {self.user.phone} ({self.type_vehicule})"
	
	def taux_reussite(self):
		"""Calcule le taux de réussite des livraisons"""
		if self.total_livraisons == 0:
			return 0
		return (self.livraisons_reussies / self.total_livraisons) * 100


class UserProfile(models.Model):
	"""
	Profile étendu pour tous les utilisateurs
	"""
	user = models.OneToOneField(
		User,
		on_delete=models.CASCADE,
		related_name='profile'
	)
    
	# Informations de contact
	address = models.TextField(blank=True, help_text="Adresse complète du client")
	city = models.CharField(max_length=100, blank=True, default="Libreville")
	zone = models.CharField(max_length=100, blank=True, help_text="Zone/Quartier à Libreville")
    
	# Informations supplémentaires
	date_of_birth = models.DateField(null=True, blank=True)
	profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    
	# Préférences
	preferred_payment_method = models.CharField(
		max_length=20,
		choices=(
			('mobile_money', 'Mobile Money'),
			('card', 'Carte Bancaire'),
			('cash', 'Espèces'),
		),
		default='mobile_money'
	)
    
	# Métadonnées
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
    
	def __str__(self):
		return f"Profile de {self.user.phone}"
    
	class Meta:
		verbose_name = "Profile Utilisateur"
		verbose_name_plural = "Profiles Utilisateurs"
