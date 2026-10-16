from django.db import models
from users.models import User
from stores.models import Store
from products.models import Product
from decimal import Decimal, ROUND_HALF_UP


class Order(models.Model):
	"""
	Commandes passées par les clients
	"""
	ORDER_STATUS_CHOICES = (
		('created', 'Créée'),
		('pending_payment', 'En attente de paiement'),
		('paid', 'Payée'),
		('confirmed', 'Confirmée'),
		('preparing', 'En préparation'),
		('ready', 'Prête pour livraison'),
		('assigned', 'Livreur assigné'),
		('in_transit', 'En cours de livraison'),
		('delivered', 'Livrée'),
		('cancelled', 'Annulée'),
		('refunded', 'Remboursée'),
	)
	
	DELIVERY_TYPE_CHOICES = (
		('standard', 'Standard (2-3h)'),
		('express', 'Express (1h)'),
	)
    
	# Relations
	client = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
	store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='orders')
    
	# Informations commande
	order_number = models.CharField(max_length=20, unique=True, editable=False)
	status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='created')
	delivery_type = models.CharField(max_length=20, choices=DELIVERY_TYPE_CHOICES, default='standard')
	notes = models.TextField(blank=True, help_text="Instructions spéciales du client")

	# B2B Fields
	is_b2b = models.BooleanField(default=False, help_text="Commande entre professionnels (Store à Store)")
	# Identifiant envoyé par l'app pour chaque validation de panier : un renvoi (connexion coupée) ne crée pas une 2e commande.
	client_request_id = models.CharField(max_length=64, blank=True, default='', editable=False)
	source_store = models.ForeignKey(
		Store, 
		on_delete=models.SET_NULL, 
		null=True, 
		blank=True, 
		related_name='placed_orders',
		help_text="Magasin qui a passé la commande (si B2B)"
	)
    
	# Montants
	items_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Sous-total produits")
	delivery_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Frais de livraison (calculés)")
	# Indique si le client souhaite une livraison (ON par défaut)
	delivery_requested = models.BooleanField(default=True, help_text="Le client souhaite-t-il être livré ? (ON par défaut)")
	# Type de véhicule imposé selon le poids total
	vehicle_type = models.CharField(max_length=50, null=True, blank=True, help_text="Type de véhicule assigné selon le poids")
	# Coût calculé de la livraison selon ville et véhicule
	delivery_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Coût calculé de la livraison selon ville et véhicule")
	service_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Champ desactive (laisser a 0)")
	operator_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Frais opérateur Mobile Money (Airtel/Moov)")
	tax_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Taxes (optionnel)")
	payment_fees = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Frais de transaction (Mobile Money)")
	commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Commission GABOSHOP")
	commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=8.00, help_text="Taux de commission en %")
	total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Total à payer")
    
	# Réduction de livraison offerte par Gaboshop au client abonné à un forfait (paiement en ligne uniquement).
	forfait_discount = models.DecimalField(max_digits=8, decimal_places=2, default=0, help_text="Réduction forfait client sur la livraison")

	# Le client signale un problème après la livraison : le versement automatique (48 h) est suspendu.
	client_problem_reported_at = models.DateTimeField(null=True, blank=True)
	client_problem = models.TextField(blank=True, default='')

	# Adresse de livraison
	city = models.CharField(max_length=100, default='Libreville', help_text="Ville de livraison")
	delivery_address = models.TextField(help_text="Adresse complète de livraison")
	delivery_address = models.TextField()
	delivery_phone = models.CharField(max_length=20)
	delivery_zone = models.CharField(max_length=100)
	# Quartier choisi dans la liste (Province › Ville › Arrondissement › Quartier) ; vide pour les anciennes commandes.
	neighborhood = models.ForeignKey('delivery.Neighborhood', on_delete=models.SET_NULL, null=True, blank=True,
									 related_name='orders')
	landmark = models.ForeignKey('delivery.Landmark', on_delete=models.SET_NULL, null=True, blank=True,
								 related_name='orders', help_text="Zone phare choisie près de l'adresse")
    
	# Timestamps
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)
	confirmed_at = models.DateTimeField(null=True, blank=True)
	delivered_at = models.DateTimeField(null=True, blank=True)
    
	class Meta:
		verbose_name = "Commande"
		verbose_name_plural = "Commandes"
		ordering = ['-created_at']
		indexes = [
			models.Index(fields=['client', 'status']),
			models.Index(fields=['store', 'status']),
			models.Index(fields=['status', 'created_at']),
		]
		constraints = [
			models.UniqueConstraint(
				fields=['client', 'client_request_id'], condition=~models.Q(client_request_id=''),
				name='order_unique_client_request',
			),
		]
    
	def __str__(self):
		return f"Commande #{self.order_number} - {self.client.phone}"
    
	def save(self, *args, **kwargs):
		"""Génère un numéro de commande unique avant sauvegarde"""
		if not self.order_number:
			import random
			import string
			self.order_number = f"CMD{''.join(random.choices(string.digits, k=8))}"

		# Calculs automatiques avant première sauvegarde qui ne nécessitent pas de relation inverse
		is_new = not self.pk
		if is_new:
			self.calculate_delivery_fee()
			self.calculate_service_fee()

		super().save(*args, **kwargs)

		# Do NOT attempt to access reverse relations (self.items) before PK is set.
		# Commission calculation depends on OrderItems and must run after items exist.
    
	def calculate_delivery_fee(self):
		"""Calcule les frais de livraison selon le type (fallback statique)"""
		# Méthode historique gardée comme fallback (utilise store.delivery_fee)
		if self.delivery_type == 'express':
			self.delivery_fee = self.store.delivery_fee_express
		else:
			self.delivery_fee = self.store.delivery_fee
		return self.delivery_fee

	def select_vehicle_for_load(self, total_weight, total_length, items_count):
		"""Sélectionne un type de véhicule basé sur le poids + longueur"""
		from decimal import Decimal
		from delivery.services.delivery_rules import DeliveryRulesService
		
		is_intercity = DeliveryRulesService.is_intercity_delivery(self)
		vehicle_type = DeliveryRulesService.select_vehicle_for_load(
			total_weight, total_length, items_count, is_intercity
		)
		
		if not vehicle_type:
			return 'TRUCK', Decimal('1.00')
		
		return vehicle_type.name, Decimal('1.00')

	def calculate_dynamic_delivery_cost(self, total_weight, total_length, items_count):
		"""Calcule le coût de livraison en fonction de la ville et du type de véhicule
		
		Utilise la configuration des zones et des tarifs par véhicule (ZoneVehicleRate)
		"""
		from decimal import Decimal
		from delivery.models import DeliveryZone, ZoneVehicleRate

		def to_decimal(value):
			return Decimal(str(value or 0))

		def intercity_surcharge_default():
			from api.models import SystemSettings
			return to_decimal(SystemSettings.current('default_intercity_surcharge', Decimal('1000.00')))

		def store_delivery_fee():
			fee = self.store.delivery_fee if self.delivery_type == 'standard' else self.store.delivery_fee_express
			return to_decimal(fee)
		
		vehicle, multiplier = self.select_vehicle_for_load(total_weight, total_length, items_count)
		
		# Récupérer la zone de livraison
		zone = None
		if hasattr(self, 'delivery_zone') and self.delivery_zone:
			try:
				zone = DeliveryZone.objects.filter(
					name__iexact=self.delivery_zone, 
					is_active=True
				).first()
			except Exception:
				zone = None
		
		# Récupérer le tarif configuré pour cette zone et ce type de véhicule
		# Si pas de zone trouvée ou pas de tarif, fallback sur le tarif du store
		if zone:
			try:
				# Chercher le tarif pour cette zone
				from delivery.models import VehicleType
				vehicle_obj = VehicleType.objects.filter(name__iexact=vehicle).first()
				
				if vehicle_obj:
					zone_rate = ZoneVehicleRate.objects.filter(
						zone=zone,
						vehicle=vehicle_obj,
						is_active=True
					).first()
					
					if zone_rate:
						base_fee = to_decimal(zone_rate.base_price)
						cost = base_fee * multiplier
					else:
						# Pas de tarif spécifique, utiliser store.delivery_fee
						base_fee = store_delivery_fee()
						cost = base_fee * multiplier
				else:
					base_fee = store_delivery_fee()
					cost = base_fee * multiplier
				
				# Appliquer surcharge inter-ville si applicable
				if (not (hasattr(self, 'city') and self.city and self.store and self.store.city and self.store.city == self.city)):
					cost += to_decimal(zone.inter_city_surcharge)
			except Exception:
				# En cas d'erreur, fallback sur tarif store
				base_fee = store_delivery_fee()
				cost = base_fee * multiplier
				if (not (hasattr(self, 'city') and self.city and self.store and self.store.city and self.store.city == self.city)):
					cost += intercity_surcharge_default()
		else:
			# Pas de zone trouvée, utiliser tarif store avec surcharge fixe
			base_fee = store_delivery_fee()
			cost = base_fee * multiplier
			if (not (hasattr(self, 'city') and self.city and self.store and self.store.city and self.store.city == self.city)):
				cost += intercity_surcharge_default()
		
		# FCFA sans centimes : franc entier
		cost = cost.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
		self.vehicle_type = vehicle
		self.delivery_cost = cost
		return cost
	
	def calculate_service_fee(self):
		"""Frais de service desactives (toujours 0)."""
		self.service_fee = Decimal('0.00')
		return self.service_fee
	
	def calculate_commission(self):
		"""Calcule la commission GABOSHOP"""
		if self.items_total > 0:
			# Determine current plan
			plan = self.store.get_current_plan()
			plan_type = plan.plan_type if plan else 'free'
			# Taux réglés dans l'espace admin (Réglages > Commissions)
			from api.models import SystemSettings
			rules = SystemSettings.get_settings()
			
			# Pour les commandes B2B d'un grossiste, utiliser B2BSubscriptionPlan
			if self.is_b2b and self.store.is_b2b:
				# C'est une commande B2B reçue par un grossiste
				# Utiliser le plan B2B du grossiste
				b2b_plan = self.store.get_current_b2b_plan()
				base_rate_b2b = Decimal(str(rules.b2b_commission_rate))
				if b2b_plan:
					# Appliquer la réduction du plan B2B
					reduction_percent = Decimal(getattr(b2b_plan, 'commission_reduction_percent', 0))
					multiplier = (Decimal('100') - reduction_percent) / Decimal('100')
					effective_rate = base_rate_b2b * multiplier
				else:
					effective_rate = base_rate_b2b
				
				# Calculer la commission totale pour la commande B2B
				total_commission = (self.items_total * effective_rate) / Decimal('100')
				self.commission_amount = total_commission.quantize(Decimal('0.01'))
				# Store an approximate effective commission rate for the order (used for display)
				try:
					self.commission_rate = (self.commission_amount / self.items_total) * Decimal('100')
				except Exception:
					self.commission_rate = Decimal('0.00')
				return self.commission_amount
			
			# Pour les commandes B2C ou les commandes B2B passées par un store B2C
			# Convert commission_reduction_percent to multiplier
			# Ex: 40% reduction ? multiplier 0.60 (1 - 0.40)
			reduction_percent = Decimal(getattr(plan, 'commission_reduction_percent', 0)) if plan else Decimal('0')
			multiplier = (Decimal('100') - reduction_percent) / Decimal('100')

			total_commission = Decimal('0.00')
			# Sum commission per OrderItem using category base rates
			for item in self.items.all():
				product = item.product
				item_subtotal = item.subtotal
				base_rate = None
				
				# Récupérer le taux de commission de la catégorie de produit
				if product and product.category:
					# Utiliser directement commission_rate de ProductCategory
					if product.category.commission_rate is not None:
						base_rate = Decimal(product.category.commission_rate)
				
				# Fallback to store-level commission rate
				if base_rate is None:
					base_rate = Decimal(self.store.commission_rate or Decimal('0.00'))
				
				# REGLES SPECIALES PLAN BUSINESS
				if plan_type == 'business':
					# Business B2B: 2% sur tout
					if self.is_b2b:
						effective_rate = Decimal(str(rules.business_b2b_commission_rate))
					# Business B2C: 0% alimentaire, 2% reste
					else:
						# Vérifier si c'est alimentaire
						is_food = False
						if product and product.category and product.category.store_category:
							category_name = product.category.store_category.name.upper()
							is_food = any(word in category_name for word in rules.food_keywords())
						
						if is_food:
							effective_rate = Decimal(str(rules.business_food_commission_rate))
						else:
							effective_rate = Decimal(str(rules.business_other_commission_rate))
				else:
					# Plans Free et Pro: utiliser base_rate * multiplier
					# Effective rate after plan multiplier
					effective_rate = (base_rate * Decimal(multiplier))
				
				item_commission = (item_subtotal * effective_rate) / Decimal('100')
				total_commission += item_commission

			self.commission_amount = total_commission.quantize(Decimal('0.01'))
			# Store an approximate effective commission rate for the order (used for display)
			try:
				self.commission_rate = (self.commission_amount / self.items_total) * Decimal('100')
			except Exception:
				self.commission_rate = Decimal('0.00')
		return self.commission_amount
	
	def calculate_store_amount(self):
		"""Calcule le montant net pour le magasin (après commission)"""
		return self.items_total - self.commission_amount
	
	def calculate_operator_fee(self, operator='airtel', payment_method='mobile_money'):
		"""
		Calcule les frais de l'opérateur Mobile Money (scalable)
		
		Args:
			operator: 'airtel', 'moov' ou autre opérateur
			payment_method: 'mobile_money', 'card', 'cash', etc.
		
		Returns:
			Decimal: Montant des frais opérateur
		"""
		from decimal import Decimal
		if payment_method not in ('mobile_money', 'airtel_money', 'moov_money'):
			return Decimal('0.00')
		
		# Configuration fallback si les paramètres système ne sont pas accessibles
		OPERATOR_FEES = {
			'airtel': Decimal('3.00'),
			'moov': Decimal('3.00'),
			'card': Decimal('2.50'),
			'cash': Decimal('0.00'),
		}
		
		operator_normalized = (operator or '').lower().strip()
		fee_rate = OPERATOR_FEES.get(operator_normalized, Decimal('0.00'))
		
		# Charger les taux réels depuis SystemSettings quand disponible
		try:
			from api.models import SystemSettings
			system_settings = SystemSettings.get_settings()
			if operator_normalized == 'airtel':
				fee_rate = Decimal(str(system_settings.airtel_money_fee or 0))
			elif operator_normalized == 'moov':
				fee_rate = Decimal(str(system_settings.moov_money_fee or 0))
		except Exception:
			# Conserver le fallback statique si la config système est indisponible
			pass
		
		# Les frais s'appliquent sur items_total + delivery_fee
		base_amount = self.items_total + self.delivery_fee
		
		# Calculer les frais
		operator_fee = (base_amount * fee_rate) / Decimal('100')
		
		# FCFA sans centimes : franc entier (montant réellement débité par SingPay)
		return operator_fee.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    
	@staticmethod
	def load_totals(pairs):
		"""Poids total (kg), longueur totale (m) et nombre d'articles de (produit, quantité)."""
		from decimal import Decimal
		from delivery.services.delivery_rules import DeliveryRulesService
		total_weight = Decimal('0.00')
		total_length = Decimal('0.00')
		items_count = 0
		for product, quantity in pairs:
			p_weight = product.weight_kg or product.estimated_weight_kg or Decimal('0.00')
			p_length = getattr(product, 'length_m', None) or DeliveryRulesService.DEFAULT_LENGTH_PER_ITEM
			qty = Decimal(quantity)
			total_weight += (p_weight * qty)
			total_length += (p_length * qty)
			items_count += int(quantity or 0)
		return total_weight, total_length, items_count

	def quote_delivery(self, pairs):
		"""Prix de livraison que paierait cette commande (non enregistrée) : même calcul qu'à la commande."""
		total_weight, total_length, items_count = self.load_totals(pairs)
		return self.calculate_dynamic_delivery_cost(total_weight, total_length, items_count)

	def calculate_totals(self, operator='airtel', payment_method='mobile_money'):
		"""Recalcule tous les totaux basés sur les OrderItems"""
		from decimal import Decimal
		# Items total
		self.items_total = sum(item.subtotal for item in self.items.all())

		# Calcul du poids total (kg) et longueur totale (m)
		total_weight, total_length, items_count = self.load_totals((item.product, item.quantity) for item in self.items.all())

		# Calcul de la livraison dynamique si demandée
		if self.delivery_requested:
			# Calcule et met à jour delivery_cost et vehicle_type
			dyn_cost = self.calculate_dynamic_delivery_cost(total_weight, total_length, items_count)
			# On met delivery_fee pour rester compatible (affiché dans l'API)
			self.delivery_fee = dyn_cost
		else:
			self.delivery_fee = Decimal('0.00')
			self.delivery_cost = Decimal('0.00')

		# Commission, operateur
		self.calculate_service_fee()
		self.calculate_commission()
		self.operator_fee = self.calculate_operator_fee(
			operator=operator,
			payment_method=payment_method
		)

		self.tax_amount = Decimal(str(self.tax_amount or 0))
		self.payment_fees = Decimal(str(self.payment_fees or 0))

		# Le total inclut désormais tous les frais
		self.total_amount = (self.items_total + self.delivery_fee + self.operator_fee + self.tax_amount
			+ self.payment_fees - self.applied_forfait_discount()).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
		self.save()

	def applied_forfait_discount(self):
		"""Réduction forfait, jamais plus que les frais de livraison."""
		from decimal import Decimal
		return min(Decimal(self.forfait_discount or 0), Decimal(self.delivery_fee or 0))


class OrderItem(models.Model):
	"""
	Articles individuels dans une commande
	"""
	order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
	product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    
	quantity = models.PositiveIntegerField(default=1)
	unit_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Prix au moment de la commande")
	# Choix du client : {'size': '42', 'color': 'Marron'} (vide si le produit n'a pas de choix).
	options = models.JSONField(default=dict, blank=True)
    
	class Meta:
		verbose_name = "Article de Commande"
		verbose_name_plural = "Articles de Commande"
    
	def __str__(self):
		return f"{self.quantity}x {self.product.name} - {self.order.order_number}"
    
	@property
	def subtotal(self):
		# Guard against missing unit_price (e.g., during admin add forms)
		price = self.unit_price if self.unit_price is not None else Decimal('0.00')
		qty = Decimal(self.quantity or 0)
		return qty * price

	def save(self, *args, **kwargs):
		# Ensure unit_price is set to the product's current price if missing
		if self.unit_price is None and self.product is not None:
			self.unit_price = self.product.price
		super().save(*args, **kwargs)

