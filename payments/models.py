from django.db import models
from orders.models import Order
from stores.models import Store
from products.models import Product
from users.models import User
from uuid import uuid4


def gen_ref():
	"""Generate a short unique reference for payment intents."""
	return uuid4().hex.upper()


class Payment(models.Model):
	"""
	Transactions de paiement
	"""
	PAYMENT_METHOD_CHOICES = (
		('airtel_money', 'Airtel Money'),
		('moov_money', 'Moov Money'),
		('card', 'Carte Bancaire'),
		('cash', 'Espèces'),
	)
    
	PAYMENT_STATUS_CHOICES = (
		('pending', 'En attente'),
		('processing', 'En cours de traitement'),
		('success', 'Succès'),
		('failed', 'Échoué'),
		('refunded', 'Remboursé'),
		('cancelled', 'Annulé'),
	)
    
	# Relations
	order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='payment')
    
	# Informations paiement
	payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
	status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
	amount = models.DecimalField(max_digits=10, decimal_places=2, help_text="Montant total payé")
	fees_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Frais de transaction inclus")
    
	# Informations client
	client_phone = models.CharField(max_length=20, blank=True, help_text="Numéro Mobile Money du client")
	client_name = models.CharField(max_length=200, blank=True)
    
	# Références transaction
	transaction_id = models.CharField(max_length=100, blank=True, help_text="ID de transaction externe")
	operator_reference = models.CharField(max_length=100, blank=True, help_text="Référence opérateur Mobile Money")
	webhook_data = models.JSONField(default=dict, blank=True, help_text="Données brutes du webhook")
    
	# Métadonnées
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	completed_at = models.DateTimeField(null=True, blank=True)
    
	class Meta:
		verbose_name = "Paiement"
		verbose_name_plural = "Paiements"
		ordering = ['-created_at']
		indexes = [
			models.Index(fields=['status', 'created_at']),
			models.Index(fields=['transaction_id']),
		]
    
	def __str__(self):
		return f"Paiement #{self.id} - {self.order.order_number}"


class PaymentIntent(models.Model):
	"""Intent de paiement avant confirmation opérateur."""
	order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE)
	reference = models.CharField(max_length=64, unique=True, default=gen_ref)
	amount = models.PositiveIntegerField()
	currency = models.CharField(max_length=3, default='XAF')
	provider = models.CharField(max_length=32, default='cinetpay')
	status = models.CharField(max_length=32, default='WAITING')
	payment_token = models.CharField(max_length=512, null=True, blank=True)
	payment_url = models.URLField(null=True, blank=True)
	raw_response = models.JSONField(null=True, blank=True)
	metadata = models.JSONField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	expires_at = models.DateTimeField(null=True, blank=True)

	class Meta:
		verbose_name = "Intent de Paiement"
		verbose_name_plural = "Intents de Paiement"
		indexes = [
			models.Index(fields=['reference']),
			models.Index(fields=['status']),
		]

	def __str__(self):
		return f"Intent {self.reference} - {self.amount} {self.currency}"


class PaymentTransaction(models.Model):
	"""Transaction opérateur liée à un PaymentIntent."""
	intent = models.ForeignKey(PaymentIntent, on_delete=models.CASCADE, related_name='transactions')
	provider_tx_id = models.CharField(max_length=128, unique=True, null=True, blank=True)
	status = models.CharField(max_length=32)
	raw_response = models.JSONField(null=True, blank=True)
	processed = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		verbose_name = "Transaction de Paiement"
		verbose_name_plural = "Transactions de Paiement"

	def __str__(self):
		return f"Tx {self.provider_tx_id or self.id} - {self.status}"


class Commission(models.Model):
	"""
	Commissions prélevées par GABOSHOP
	"""
	order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name='commission')
	store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='commissions')
    
	# Calcul commissions
	order_amount = models.DecimalField(max_digits=10, decimal_places=2)
	commission_rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Taux en %")
	commission_amount = models.DecimalField(max_digits=10, decimal_places=2)
	delivery_fee_share = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    
	# Statut
	is_settled = models.BooleanField(default=False)
    
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
    
	class Meta:
		verbose_name = "Commission"
		verbose_name_plural = "Commissions"
		ordering = ['-created_at']
    
	def __str__(self):
		return f"Commission {self.commission_amount} FCFA - {self.store.name}"


class Reversement(models.Model):
	"""
	Reversements aux magasins
	"""
	REVERSEMENT_STATUS_CHOICES = (
		('pending', 'En attente'),
		('processing', 'En traitement'),
		('completed', 'Complété'),
		('failed', 'Échoué'),
	)
    
	store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='reversements')
    
	# Informations reversement
	period_start = models.DateField()
	period_end = models.DateField()
	total_orders = models.PositiveIntegerField()
	total_sales = models.DecimalField(max_digits=12, decimal_places=2)
	total_commissions = models.DecimalField(max_digits=12, decimal_places=2)
	net_amount = models.DecimalField(max_digits=12, decimal_places=2)
    
	# Statut et métadonnées
	status = models.CharField(max_length=20, choices=REVERSEMENT_STATUS_CHOICES, default='pending')
	transaction_reference = models.CharField(max_length=100, blank=True)
    
	created_at = models.DateTimeField(auto_now_add=True)
	processed_at = models.DateTimeField(null=True, blank=True)
	completed_at = models.DateTimeField(null=True, blank=True)
    
	class Meta:
		verbose_name = "Reversement"
		verbose_name_plural = "Reversements"
		ordering = ['-period_end']
    
	def __str__(self):
		return f"Reversement {self.net_amount} FCFA - {self.store.name}"


class DeliveryPayout(models.Model):
	"""
	Paiements aux livreurs
	"""
	PAYOUT_STATUS_CHOICES = (
		('pending', 'En attente'),
		('processing', 'En traitement'),
		('completed', 'Payé'),
		('failed', 'Échoué'),
	)
	
	delivery_agent = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payouts',
									   limit_choices_to={'user_type': 'delivery_agent'})
	order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='delivery_payout')
	
	# Montants
	delivery_fee_from_client = models.DecimalField(max_digits=10, decimal_places=2, 
												   help_text="Frais payés par le client")
	distance_km = models.DecimalField(max_digits=6, decimal_places=2)
	price_per_km = models.DecimalField(max_digits=8, decimal_places=2)
	calculated_payout = models.DecimalField(max_digits=10, decimal_places=2,
											help_text="Montant calculé pour le livreur")
	platform_profit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00,
										  help_text="Bénéfice de la plateforme")
	
	# Statut
	status = models.CharField(max_length=20, choices=PAYOUT_STATUS_CHOICES, default='pending')
	
	created_at = models.DateTimeField(auto_now_add=True)
	paid_at = models.DateTimeField(null=True, blank=True)
	
	class Meta:
		verbose_name = "Paiement Livreur"
		verbose_name_plural = "Paiements Livreurs"
		ordering = ['-created_at']
	
	def __str__(self):
		return f"Paiement {self.calculated_payout} FCFA - {self.delivery_agent.username}"


class SubscriptionPlan(models.Model):
	"""
	Plans d'abonnement pour les magasins (Starter, Pro, Business)
	"""
	PLAN_TYPE_CHOICES = (
		('starter', 'Starter'),
		('pro', 'Pro'),
		('business', 'Business'),
	)
	
	name = models.CharField(max_length=100, unique=True)
	slug = models.SlugField(max_length=100, unique=True)
	plan_type = models.CharField(max_length=20, choices=PLAN_TYPE_CHOICES, unique=True)
	price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Prix mensuel en FCFA")
	
	# Limites et fonctionnalités
	max_products = models.IntegerField(null=True, blank=True, help_text="Limite de produits (null = illimité)")
	can_sponsor_products = models.BooleanField(default=False, help_text="Peut sponsoriser des produits")
	has_statistics = models.BooleanField(default=False, help_text="Accès aux statistiques avancées")
	has_custom_page = models.BooleanField(default=False, help_text="Page personnalisée")
	has_priority_support = models.BooleanField(default=False, help_text="Support VIP")
	priority_listing = models.IntegerField(default=0, help_text="Ordre de priorité dans les listings (plus élevé = plus visible)")
	
	# Configuration
	commission_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, 
										  help_text="Taux de commission spécifique au plan (si null, utilise le taux par défaut)")
	
	# Métadonnées
	description = models.TextField(blank=True)
	features_json = models.JSONField(default=list, blank=True, help_text="Liste des fonctionnalités en JSON")
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	
	class Meta:
		verbose_name = "Plan d'abonnement"
		verbose_name_plural = "Plans d'abonnement"
		ordering = ['price']
	
	def __str__(self):
		return f"{self.name} - {self.price} FCFA/mois"
	
	def get_features_list(self):
		"""Retourne la liste des fonctionnalités"""
		features = []
		if self.max_products:
			features.append(f"Jusqu'à {self.max_products} produits")
		else:
			features.append("Produits illimités")
		if self.has_statistics:
			features.append("Statistiques et rapports de ventes")
		if self.has_custom_page:
			features.append("Page personnalisée")
		if self.has_priority_support:
			features.append("Support VIP")
		if self.can_sponsor_products:
			features.append("Produits sponsorisés")
		if self.priority_listing > 0:
			features.append("Meilleure visibilité sur la plateforme")
		return features + self.features_json


class StoreSubscription(models.Model):
	"""
	Abonnements Mode Pro des magasins
	"""
	SUBSCRIPTION_STATUS_CHOICES = (
		('active', 'Actif'),
		('cancelled', 'Annulé'),
		('expired', 'Expiré'),
		('pending_payment', 'Attente paiement'),
	)
	
	store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='subscriptions')
	plan = models.ForeignKey('SubscriptionPlan', on_delete=models.PROTECT, related_name='subscriptions', null=True, blank=True)
	
	# Informations abonnement (fallback si pas de plan)
	plan_name = models.CharField(max_length=100, default='Starter')
	monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	status = models.CharField(max_length=20, choices=SUBSCRIPTION_STATUS_CHOICES, default='active')
	
	# Dates
	start_date = models.DateField(auto_now_add=True)
	end_date = models.DateField()
	auto_renew = models.BooleanField(default=True)
	
	# Métadonnées
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	
	class Meta:
		verbose_name = "Abonnement Magasin"
		verbose_name_plural = "Abonnements Magasins"
		ordering = ['-end_date']
	
	def __str__(self):
		plan_display = self.plan.name if self.plan else self.plan_name
		return f"Abonnement {self.store.name} - {plan_display}"
	
	def is_active(self):
		"""Vérifie si l'abonnement est actif"""
		from django.utils import timezone
		return self.status == 'active' and self.end_date >= timezone.now().date()
	
	def get_plan_features(self):
		"""Retourne les fonctionnalités du plan"""
		if self.plan:
			return self.plan.get_features_list()
		return []
	
	def can_add_product(self, current_count):
		"""Vérifie si le magasin peut ajouter un produit"""
		if not self.plan:
			return current_count < 20  # Limite par défaut Starter
		if self.plan.max_products is None:
			return True  # Illimité
		return current_count < self.plan.max_products


class SponsoredProduct(models.Model):
	"""
	Produits sponsorisés / mises en avant payantes
	"""
	SPONSOR_STATUS_CHOICES = (
		('active', 'Actif'),
		('expired', 'Expiré'),
		('paused', 'Suspendu'),
	)
	
	product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sponsorships')
	store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='sponsored_products')
	
	# Détails sponsoring
	sponsor_type = models.CharField(max_length=50, default='featured',
									help_text="Type: featured, banner, top_search, etc.")
	price_paid = models.DecimalField(max_digits=10, decimal_places=2)
	status = models.CharField(max_length=20, choices=SPONSOR_STATUS_CHOICES, default='active')
	
	# Durée
	start_date = models.DateTimeField(auto_now_add=True)
	end_date = models.DateTimeField()
	
	# Analytics
	impressions = models.PositiveIntegerField(default=0)
	clicks = models.PositiveIntegerField(default=0)
	
	created_at = models.DateTimeField(auto_now_add=True)
	
	class Meta:
		verbose_name = "Produit Sponsorisé"
		verbose_name_plural = "Produits Sponsorisés"
		ordering = ['-end_date']
	
	def __str__(self):
		return f"Sponsoring {self.product.name}"


class ClientCredit(models.Model):
	"""
	Cashbacks et crédits clients
	"""
	CREDIT_STATUS_CHOICES = (
		('available', 'Disponible'),
		('used', 'Utilisé'),
		('expired', 'Expiré'),
	)
	
	client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_credits',
							   limit_choices_to={'user_type': 'client'})
	
	# Montant
	amount = models.DecimalField(max_digits=10, decimal_places=2)
	credit_type = models.CharField(max_length=50, default='promotion',
									 help_text="Type: promotion, referral, loyalty, compensation, etc.")
	reason = models.TextField(blank=True)
	
	# Statut
	status = models.CharField(max_length=20, choices=CREDIT_STATUS_CHOICES, default='available')
	
	# Dates
	created_at = models.DateTimeField(auto_now_add=True)
	expiration_date = models.DateTimeField()
	used_at = models.DateTimeField(null=True, blank=True)
	
	class Meta:
		verbose_name = "Crédit Client"
		verbose_name_plural = "Crédits Clients"
		ordering = ['-created_at']
	
	def __str__(self):
		return f"{self.amount} FCFA - {self.client.phone}"


# ===============================================================================
# FORFAITS CLIENTS & ABONNEMENTS
# ===============================================================================

class Forfait(models.Model):
	"""
	Forfaits pour les clients (Basic, Premium, Express,...)
	Chaque forfait peut influencer :
	- les frais
	- les limites
	- les délais de livraison
	- le type de services disponibles
	"""
	name = models.CharField(max_length=50, unique=True)
	description = models.TextField(blank=True)
	monthly_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
	
	# Exemple : basic = 1 transaction prioritaire, premium = illimité
	max_priority_orders = models.IntegerField(default=0, help_text="Nombre de commandes prioritaires par mois")

	# Exemple : réduction sur les frais > premium
	discount_rate = models.FloatField(default=0, help_text="Réduction en % sur les frais de livraison")
	
	# Fonctionnalités du forfait
	can_schedule_delivery = models.BooleanField(default=False, help_text="Peut planifier une livraison")
	can_track_realtime = models.BooleanField(default=False, help_text="Peut suivre en temps réel")
	can_contact_driver = models.BooleanField(default=False, help_text="Peut contacter le livreur")
	priority_support = models.BooleanField(default=False, help_text="Support prioritaire")
	
	# Métadonnées
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "Forfait Client"
		verbose_name_plural = "Forfaits Clients"
		ordering = ['monthly_price']

	def __str__(self):
		return f"{self.name} ({self.monthly_price} FCFA/mois)"


class ClientForfait(models.Model):
	"""
	Tableau de correspondance User (Client) → Forfait
	Permet de savoir en temps réel quel forfait est appliqué au client.
	"""
	user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='client_forfait')
	forfait = models.ForeignKey(Forfait, on_delete=models.SET_NULL, null=True, blank=True, related_name='clients')
	start_date = models.DateTimeField(auto_now_add=True)
	expiration_date = models.DateTimeField(help_text="Date d'expiration du forfait")
	status = models.CharField(
		max_length=20,
		choices=[
			('active', 'Actif'),
			('expired', 'Expiré'),
			('suspended', 'Suspendu'),
			('cancelled', 'Annulé'),
		],
		default='active'
	)
	auto_renew = models.BooleanField(default=True, help_text="Renouvellement automatique")
	
	# Métadonnées
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "Forfait Client"
		verbose_name_plural = "Forfaits Clients"
		ordering = ['-expiration_date']

	def __str__(self):
		return f"{self.user.phone} - {self.forfait.name if self.forfait else 'Aucun forfait'}"
	
	def is_active(self):
		"""Vérifie si le forfait est actif"""
		from django.utils import timezone
		return self.status == 'active' and self.expiration_date >= timezone.now()


# ===============================================================================
# CALLBACKS & LOGS FLUTTERWAVE
# ===============================================================================

class PaymentCallbackLog(models.Model):
	"""
	Sauvegarde chaque webhook reçu de Flutterwave (sécurité, audit).
	"""
	id = models.BigAutoField(primary_key=True)
	received_at = models.DateTimeField(auto_now_add=True)
	order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='payment_logs')
	status_code = models.IntegerField(default=200, help_text="Code de réponse HTTP")
	raw_data = models.JSONField(help_text="Données brutes du webhook")
	signature_valid = models.BooleanField(default=False, help_text="Signature Flutterwave validée")
	processed = models.BooleanField(default=False, help_text="Webhook traité avec succès")

	class Meta:
		verbose_name = "Log Callback Flutterwave"
		verbose_name_plural = "Logs Callbacks Flutterwave"
		ordering = ['-received_at']

	def __str__(self):
		return f"Callback {self.id} - {self.received_at.strftime('%Y-%m-%d %H:%M:%S')}"


# ===============================================================================
# PAIEMENTS AUTOMATIQUES (Livreurs + Commerçants)
# ===============================================================================

class Payout(models.Model):
	"""
	Paiements automatiques aux livreurs et commerçants
	Générés automatiquement après une livraison réussie
	"""
	TYPES = [
		('delivery', 'Paiement Livreur'),
		('merchant', 'Paiement Commerçant'),
		('refund', 'Remboursement'),
	]
	
	STATUSES = [
		('pending', 'En attente'),
		('processing', 'En traitement'),
		('paid', 'Payé'),
		('failed', 'Échec'),
		('cancelled', 'Annulé'),
	]

	id = models.BigAutoField(primary_key=True)
	user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='general_payouts')
	order = models.ForeignKey('orders.Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='general_payouts')
	payout_type = models.CharField(max_length=20, choices=TYPES)
	amount = models.DecimalField(max_digits=12, decimal_places=2, help_text="Montant en FCFA")
	status = models.CharField(max_length=20, choices=STATUSES, default='pending')
	
	# Référence Flutterwave
	flutterwave_payout_id = models.CharField(max_length=200, blank=True, null=True, unique=True)
	
	# Description et raison
	reason = models.TextField(blank=True, help_text="Raison du paiement")
	
	# Métadonnées
	created_at = models.DateTimeField(auto_now_add=True)
	paid_at = models.DateTimeField(null=True, blank=True, help_text="Quand le paiement a été effectué")
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = "Paiement (Payout)"
		verbose_name_plural = "Paiements (Payouts)"
		ordering = ['-created_at']
		indexes = [
			models.Index(fields=['user', 'status']),
			models.Index(fields=['payout_type', 'status']),
		]

	def __str__(self):
		payout_type_display = dict(self.TYPES).get(self.payout_type, self.payout_type)
		return f"{payout_type_display} - {self.user.phone} - {self.amount} FCFA ({self.status})"

