from datetime import datetime, time, timedelta, timezone as dt_timezone

import re

from django.core.exceptions import ValidationError
from django.db import models
from users.models import User

# Heure du Gabon (WAT) : UTC+1 toute l'année. Le serveur, lui, compte en UTC.
LIBREVILLE_TZ = dt_timezone(timedelta(hours=1))


def default_commission_rate():
	"""Commission d'un nouveau commerce ou d'une nouvelle catégorie : réglée dans l'espace admin."""
	from decimal import Decimal
	from api.models import SystemSettings
	return Decimal(str(SystemSettings.current('commission_global', Decimal('8.00'))))


def default_delivery_fee():
	from decimal import Decimal
	from api.models import SystemSettings
	return Decimal(str(SystemSettings.current('default_delivery_fee', Decimal('2000.00'))))


def default_express_delivery_fee():
	from decimal import Decimal
	from api.models import SystemSettings
	return Decimal(str(SystemSettings.current('default_express_delivery_fee', Decimal('3500.00'))))


def default_opening_time():
	from api.models import SystemSettings
	return _as_time(SystemSettings.current('default_store_opening', time(8, 0)))


def default_closing_time():
	from api.models import SystemSettings
	return _as_time(SystemSettings.current('default_store_closing', time(20, 0)))


def within_hours(opening, closing):
	"""Vrai si l'heure de Libreville est dans la plage. Même heure des deux côtés = 24 h/24 ;
	fermeture avant l'ouverture (ex. 18:00 → 02:00) = plage de nuit."""
	opening, closing = _as_time(opening), _as_time(closing)
	now = datetime.now(LIBREVILLE_TZ).time().replace(tzinfo=None)
	if opening == closing:
		return True
	if opening < closing:
		return opening <= now <= closing
	return now >= opening or now <= closing


def _as_time(value):
	"""Heure d'ouverture lue en base (time) ou pas encore enregistrée (texte « 08:00 »)."""
	if isinstance(value, time):
		return value.replace(tzinfo=None)
	return time.fromisoformat(str(value))


ACCENT_COLOR_RE = re.compile(r'^#[0-9A-Fa-f]{6}$')


def validate_accent_color(value):
	if value and not ACCENT_COLOR_RE.match(value):
		raise ValidationError("Couleur invalide : indiquez un code hexadécimal à 6 chiffres, par exemple #1E40AF.")


class StoreCategory(models.Model):
	"""
	Catégories de magasins (Épicerie, Vêtements, Électronique, etc.)
	"""
	name = models.CharField(max_length=100, unique=True)
	description = models.TextField(blank=True)
	icon = models.CharField(max_length=50, blank=True, help_text="Icône FontAwesome ou autre")
	is_active = models.BooleanField(default=True)
	sells_everything = models.BooleanField(
		default=False,
		help_text="Grande surface (hypermarché, supermarché, mall…) : peut utiliser toutes les catégories de produits, chacune avec son taux",
	)
    
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
		default=default_commission_rate,
		help_text="Commission de GABOSHOP en % (défaut 8%)"
	)
	delivery_fee = models.DecimalField(
		max_digits=8, 
		decimal_places=2, 
		default=default_delivery_fee,
		help_text="Frais de livraison standard en FCFA"
	)
	# Indique si le magasin gère les livraisons lui-même (optionnel)
	# Par défaut, le magasin ne gère pas la livraison (False)
	offers_delivery = models.BooleanField(default=False, help_text="Le magasin gère-t-il la livraison ? (par défaut: non)")
	# Destinataire des versements Gaboshop vers le commerce (jamais exposé publiquement)
	agent_code = models.CharField(
		max_length=100,
		blank=True,
		default='',
		help_text="Code agent Mobile Money indiqué par le commerce pour recevoir ses ventes"
	)
	# Numéro Mobile Money indiqué par le commerce pour recevoir ses ventes (+241XXXXXXXX)
	payout_phone = models.CharField(
		max_length=20,
		blank=True,
		default='',
		help_text="Numéro Mobile Money du commerce pour recevoir ses ventes (Airtel 07…, Moov 06…)"
	)
	# SingPay ne verse pas à un simple numéro : Gaboshop enregistre le code agent ou le numéro du
	# commerce comme décaissement dans son espace marchand SingPay, puis colle ici l'identifiant obtenu.
	singpay_disbursement_id = models.CharField(
		max_length=100,
		blank=True,
		default='',
		help_text="Identifiant de décaissement SingPay du commerce (créé par Gaboshop dans l'espace marchand SingPay)"
	)
	delivery_fee_express = models.DecimalField(
		max_digits=8, 
		decimal_places=2, 
		default=default_express_delivery_fee,
		help_text="Frais de livraison express en FCFA"
	)
	service_fee = models.DecimalField(
		max_digits=8,
		decimal_places=2,
		default=0.00,
		help_text="Champ desactive (laisser a 0)"
	)
	min_order_amount = models.DecimalField(
		max_digits=8, 
		decimal_places=2, 
		default=0.00,
		help_text="Montant minimum de commande en FCFA"
	)
	payment_preferences = models.JSONField(default=dict, blank=True, help_text="Restrictions et instructions de paiement du commerce")
    
	# Statut et métadonnées
	is_active = models.BooleanField(default=True)
	# Validé par Gaboshop : sans ça, le commerce prépare sa boutique mais n'est visible de personne et ne vend pas.
	is_verified = models.BooleanField(default=False)
	verified_at = models.DateTimeField(null=True, blank=True)
	# De confiance : sa part peut lui être versée dès la préparation ; sinon après la réception confirmée par le client.
	is_trusted = models.BooleanField(default=False)
	# Versements gelés par l'admin (enquête, plainte) : les ventes continuent, l'argent reste chez Gaboshop.
	payouts_frozen = models.BooleanField(default=False)
	
	# Configuration B2B/B2C
	STORE_TYPE_CHOICES = (
		('retail', 'Détail (B2C)'),
		('wholesaler', 'Grossiste (B2B)'),
		('industry', 'Industrie (B2B)'),
	)
	B2B_STORE_TYPES = {'wholesaler', 'industry'}
	store_type = models.CharField(
		max_length=20,
		choices=STORE_TYPE_CHOICES,
		default='retail',
		help_text="Type de magasin: Détail (pour clients), Grossiste/Industrie (pour commerçants)"
	)
	
	# Capacités B2C/B2B (dérivées de store_type mais gardées pour compatibilité)
	is_b2c = models.BooleanField(
		default=True,
		help_text="Le magasin peut-il vendre au détail (B2C) ?"
	)
	is_b2b = models.BooleanField(
		default=False,
		help_text="Le magasin peut-il vendre en gros (B2B) ?"
	)
	
	# Options B2B
	b2b_min_order_amount = models.DecimalField(
		max_digits=10,
		decimal_places=2,
		default=0,
		help_text="Montant minimum de commande B2B en FCFA"
	)
	b2b_delivery_delay = models.PositiveIntegerField(
		default=24,
		help_text="Délai de livraison B2B en heures"
	)

	subscription_plan = models.CharField(
		max_length=20,
		choices=[('starter', 'Starter'), ('pro', 'Pro'), ('business', 'Business')],
		default='starter',
		help_text="Badge du forfait affiché aux clients ; suit l'abonnement réel (refresh_plan_badge)"
	)
	stock_alert_threshold = models.PositiveSmallIntegerField(
		default=3,
		help_text="Alerte de stock (forfaits qui l'incluent) quand il reste ce nombre d'unités ou moins ; 0 = seulement à la rupture"
	)
	# Horaires par défaut d'un nouveau commerce : réglés dans l'espace admin.
	opening_time = models.TimeField(default=default_opening_time)
	closing_time = models.TimeField(default=default_closing_time)
    
	# Images
	logo = models.ImageField(upload_to='stores/logos/', blank=True, null=True)
	banner_image = models.ImageField(upload_to='stores/banners/', blank=True, null=True)

	# Page de boutique personnalisée (forfaits avec l'outil « custom_page ») : facultatif.
	# Les valeurs restent en base si le forfait expire ; la vitrine ne les montre alors plus.
	accent_color = models.CharField(
		max_length=7, blank=True, default='', validators=[validate_accent_color],
		help_text="Couleur d'accent de la vitrine, au format #RRGGBB"
	)
	tagline = models.CharField(max_length=120, blank=True, default='', help_text="Message d'accueil ou slogan de la vitrine")
	about = models.TextField(blank=True, default='', max_length=2000, help_text="Présentation « À propos » de la vitrine")
	facebook_url = models.URLField(max_length=200, blank=True, default='')
	instagram_url = models.URLField(max_length=200, blank=True, default='')
	tiktok_url = models.URLField(max_length=200, blank=True, default='')
	website_url = models.URLField(max_length=200, blank=True, default='')
    
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
	
	def get_market_mode(self):
		return 'b2b' if self.store_type in self.B2B_STORE_TYPES else 'b2c'
	
	@property
	def market_mode(self):
		return self.get_market_mode()

	@property
	def payout_operator(self):
		"""Opérateur du numéro de versement : 07… Airtel Money, 06… Moov Money."""
		local = '0' + self.payout_phone[4:] if self.payout_phone.startswith('+241') else ''
		if local.startswith('07'):
			return 'airtel'
		if local.startswith('06'):
			return 'moov'
		return ''
	
	def set_market_mode(self, mode):
		mode_normalized = (mode or '').strip().lower()
		if mode_normalized not in ('b2b', 'b2c'):
			raise ValueError("market_mode must be 'b2b' or 'b2c'")
		if mode_normalized == 'b2b':
			self.is_b2b = True
			self.is_b2c = False
			if self.store_type == 'retail':
				self.store_type = 'wholesaler'
		else:
			self.is_b2b = False
			self.is_b2c = True
			self.store_type = 'retail'
    
	def is_open(self):
		"""Ouvert à l'heure de Libreville (UTC+1, sans heure d'été).

		Même heure d'ouverture et de fermeture = ouvert 24 h/24. Fermeture avant l'ouverture
		(ex. 18:00 → 02:00) = ouvert pendant la nuit.
		"""
		if not self.is_active:
			return False
		return within_hours(self.opening_time, self.closing_time)
    
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
	
	def get_active_subscription(self):
		"""
		Récupère l'abonnement ACTIF du magasin
		Utilisé par le système de forfaits temps réel
		"""
		from django.utils import timezone
		from payments.models import StoreSubscription
		
		from payments.models import paid_first
		return StoreSubscription.objects.filter(
			store=self,
			status='active',
			end_date__gte=timezone.now().date()
		).order_by(*paid_first()).first()
	
	def get_current_plan(self):
		"""
		Récupère le plan ACTUEL du magasin
		Pour les stores B2B (grossistes), retourne B2BSubscriptionPlan
		Pour les stores B2C, retourne SubscriptionPlan
		Retourne le plan d'abonnement ou le plan Free par défaut
		"""
		# Si c'est un store B2B (grossiste), utiliser B2BSubscriptionPlan
		if self.is_b2b:
			return self.get_current_b2b_plan()
		
		# Sinon, utiliser SubscriptionPlan (B2C)
		from payments.models import SubscriptionPlan
		
		subscription = self.get_active_subscription()
		
		if subscription and subscription.plan:
			return subscription.plan
		
		# Plan par défaut : Gratuit, créé s'il manque (jamais « Aucun forfait trouvé »).
		from payments.default_plans import ensure_free_plan
		return ensure_free_plan(SubscriptionPlan)
	
	def get_current_b2b_plan(self):
		"""
		Récupère le plan B2B ACTUEL du magasin (pour grossistes)
		Retourne B2BSubscriptionPlan ou le plan Free B2B par défaut
		"""
		from b2b.models import B2BStoreSubscription, B2BSubscriptionPlan
		
		try:
			b2b_subscription = self.b2b_subscription
			if b2b_subscription and b2b_subscription.is_active() and b2b_subscription.plan:
				return b2b_subscription.plan
		except B2BStoreSubscription.DoesNotExist:
			pass
		
		# Plan par défaut : B2B Gratuit, créé s'il manque.
		from payments.default_plans import ensure_free_b2b_plan
		return ensure_free_b2b_plan(B2BSubscriptionPlan)

	def refresh_plan_badge(self):
		"""Aligne le badge « Pro » / « Business » vu par les clients sur l'abonnement réellement actif."""
		plan = self.get_current_plan()
		badge = plan.plan_type if plan is not None and plan.plan_type in ('pro', 'business') else 'starter'
		if badge != self.subscription_plan:
			self.subscription_plan = badge
			self.save(update_fields=['subscription_plan'])
		return badge

	def is_subscription_active(self):
		"""Vérifie si le magasin a un forfait ACTIF"""
		return self.get_active_subscription() is not None
	
	def can_add_product(self):
		"""Vérifie si le magasin peut ajouter un produit selon son forfait"""
		plan = self.get_current_plan()
		if not plan or plan.max_products is None:
			return True
		return self.products.count() < plan.max_products
	
	def can_access_statistics(self):
		"""Vérifie si le magasin peut accéder aux statistiques"""
		plan = self.get_current_plan()
		return plan and plan.has_statistics
	
	def can_customize_store(self):
		"""Vérifie si le magasin peut personnaliser sa boutique"""
		from payments.plan_features import has
		return has(self.get_current_plan(), 'custom_page')
	
	def can_sponsor_products(self):
		"""Vérifie si le magasin peut sponsoriser des produits"""
		plan = self.get_current_plan()
		return plan and plan.can_sponsor_products


def visible_store_filter(user, prefix=''):
	"""Commerce visible : validé par Gaboshop ; son gérant et l'admin le voient aussi avant validation (aperçu)."""
	from django.db.models import Q
	visible = Q(**{f'{prefix}is_verified': True})
	if user is not None and getattr(user, 'is_authenticated', False):
		if user.is_staff or user.is_superuser or getattr(user, 'user_type', '') == 'admin':
			return Q()
		visible |= Q(**{f'{prefix}manager': user})
	return visible
