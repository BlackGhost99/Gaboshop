from django.db import models
from users.models import User
from stores.models import Store
from products.models import Product
from decimal import Decimal


class Order(models.Model):
	"""
	Commandes passÃ©es par les clients
	"""
	ORDER_STATUS_CHOICES = (
		('created', '?? CrÃ©Ã©e'),
		('pending_payment', '?? En attente de paiement'),
		('paid', '?? PayÃ©e'),
		('confirmed', '?? ConfirmÃ©e'),
		('preparing', '????? En prÃ©paration'),
		('ready', '? PrÃªte pour livraison'),
		('assigned', '?? Livreur assignÃ©'),
		('in_transit', '?? En cours de livraison'),
		('delivered', '?? LivrÃ©e'),
		('cancelled', '? AnnulÃ©e'),
		('refunded', '?? RemboursÃ©e'),
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
	notes = models.TextField(blank=True, help_text="Instructions spÃ©ciales du client")

	# B2B Fields
	is_b2b = models.BooleanField(default=False, help_text="Commande entre professionnels (Store Ã  Store)")
	source_store = models.ForeignKey(
		Store, 
		on_delete=models.SET_NULL, 
		null=True, 
		blank=True, 
		related_name='placed_orders',
		help_text="Magasin qui a passÃ© la commande (si B2B)"
	)
    
	# Montants
	items_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Sous-total produits")
	delivery_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Frais de livraison (calculÃ©s)")
	# Indique si le client souhaite une livraison (ON par dÃ©faut)
	delivery_requested = models.BooleanField(default=True, help_text="Le client souhaite-t-il Ãªtre livrÃ© ? (ON par dÃ©faut)")
	# Type de vÃ©hicule imposÃ© selon le poids total
	vehicle_type = models.CharField(max_length=50, null=True, blank=True, help_text="Type de vÃ©hicule assignÃ© selon le poids")
	# CoÃ»t calculÃ© de la livraison selon ville et vÃ©hicule
	delivery_cost = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="CoÃ»t calculÃ© de la livraison selon ville et vÃ©hicule")
	service_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Champ desactive (laisser a 0)")
	operator_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Frais opÃ©rateur Mobile Money (Airtel/Moov)")
	tax_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Taxes (optionnel)")
	payment_fees = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Frais de transaction (Mobile Money)")
	commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Commission GABOSHOP")
	commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=8.00, help_text="Taux de commission en %")
	total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Total Ã  payer")
    
	# Adresse de livraison
	city = models.CharField(max_length=100, default='Libreville', help_text="Ville de livraison")
	delivery_address = models.TextField(help_text="Adresse complÃ¨te de livraison")
	delivery_address = models.TextField()
	delivery_phone = models.CharField(max_length=20)
	delivery_zone = models.CharField(max_length=100)
    
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
    
	def __str__(self):
		return f"Commande #{self.order_number} - {self.client.phone}"
    
	def save(self, *args, **kwargs):
		"""GÃ©nÃ¨re un numÃ©ro de commande unique avant sauvegarde"""
		if not self.order_number:
			import random
			import string
			self.order_number = f"CMD{''.join(random.choices(string.digits, k=8))}"

		# Calculs automatiques avant premiÃ¨re sauvegarde qui ne nÃ©cessitent pas de relation inverse
		is_new = not self.pk
		if is_new:
			self.calculate_delivery_fee()
			self.calculate_service_fee()

		super().save(*args, **kwargs)

		# Do NOT attempt to access reverse relations (self.items) before PK is set.
		# Commission calculation depends on OrderItems and must run after items exist.
    
	def calculate_delivery_fee(self):
		"""Calcule les frais de livraison selon le type (fallback statique)"""
		# MÃ©thode historique gardÃ©e comme fallback (utilise store.delivery_fee)
		if self.delivery_type == 'express':
			self.delivery_fee = self.store.delivery_fee_express
		else:
			self.delivery_fee = self.store.delivery_fee
		return self.delivery_fee

	def select_vehicle_for_load(self, total_weight, total_length, items_count):
		"""SÃ©lectionne un type de vÃ©hicule basÃ© sur le poids + longueur"""
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
		"""Calcule le coÃ»t de livraison en fonction de la ville et du type de vÃ©hicule
		
		Utilise la configuration des zones et des tarifs par vÃ©hicule (ZoneVehicleRate)
		"""
		from decimal import Decimal
		from delivery.models import DeliveryZone, ZoneVehicleRate

		def to_decimal(value):
			return Decimal(str(value or 0))

		def store_delivery_fee():
			fee = self.store.delivery_fee if self.delivery_type == 'standard' else self.store.delivery_fee_express
			return to_decimal(fee)
		
		vehicle, multiplier = self.select_vehicle_for_load(total_weight, total_length, items_count)
		
		# RÃ©cupÃ©rer la zone de livraison
		zone = None
		if hasattr(self, 'delivery_zone') and self.delivery_zone:
			try:
				zone = DeliveryZone.objects.filter(
					name__iexact=self.delivery_zone, 
					is_active=True
				).first()
			except Exception:
				zone = None
		
		# RÃ©cupÃ©rer le tarif configurÃ© pour cette zone et ce type de vÃ©hicule
		# Si pas de zone trouvÃ©e ou pas de tarif, fallback sur le tarif du store
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
						# Pas de tarif spÃ©cifique, utiliser store.delivery_fee
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
					cost += Decimal('1000.00')
		else:
			# Pas de zone trouvÃ©e, utiliser tarif store avec surcharge fixe
			base_fee = store_delivery_fee()
			cost = base_fee * multiplier
			if (not (hasattr(self, 'city') and self.city and self.store and self.store.city and self.store.city == self.city)):
				cost += Decimal('1000.00')
		
		# Arrondir Ã  0.01
		cost = cost.quantize(Decimal('0.01'))
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
			
			# Pour les commandes B2B d'un grossiste, utiliser B2BSubscriptionPlan
			if self.is_b2b and self.store.is_b2b:
				# C'est une commande B2B reÃ§ue par un grossiste
				# Utiliser le plan B2B du grossiste
				b2b_plan = self.store.get_current_b2b_plan()
				if b2b_plan:
					# Commission de base B2B = 8%
					base_rate_b2b = Decimal('8.00')
					# Appliquer la rÃ©duction du plan B2B
					reduction_percent = Decimal(getattr(b2b_plan, 'commission_reduction_percent', 0))
					multiplier = (Decimal('100') - reduction_percent) / Decimal('100')
					effective_rate = base_rate_b2b * multiplier
				else:
					# Fallback: 8% si pas de plan B2B
					effective_rate = Decimal('8.00')
				
				# Calculer la commission totale pour la commande B2B
				total_commission = (self.items_total * effective_rate) / Decimal('100')
				self.commission_amount = total_commission.quantize(Decimal('0.01'))
				# Store an approximate effective commission rate for the order (used for display)
				try:
					self.commission_rate = (self.commission_amount / self.items_total) * Decimal('100')
				except Exception:
					self.commission_rate = Decimal('0.00')
				return self.commission_amount
			
			# Pour les commandes B2C ou les commandes B2B passÃ©es par un store B2C
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
				
				# RÃ©cupÃ©rer le taux de commission de la catÃ©gorie de produit
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
						effective_rate = Decimal('2.00')
					# Business B2C: 0% alimentaire, 2% reste
					else:
						# VÃ©rifier si c'est alimentaire
						is_food = False
						if product and product.category and product.category.store_category:
							category_name = product.category.store_category.name.upper()
							is_food = 'ALIMENTATION' in category_name or 'BOISSONS' in category_name
						
						if is_food:
							effective_rate = Decimal('0.00')  # 0% pour alimentaire B2C Business
						else:
							effective_rate = Decimal('2.00')  # 2% pour reste B2C Business
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
		"""Calcule le montant net pour le magasin (aprÃ¨s commission)"""
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
		
		return operator_fee.quantize(Decimal('0.01'))
    
	def calculate_totals(self, operator='airtel', payment_method='mobile_money'):
		"""Recalcule tous les totaux basÃ©s sur les OrderItems"""
		from decimal import Decimal
		# Items total
		self.items_total = sum(item.subtotal for item in self.items.all())

		# Calcul du poids total (kg) et longueur totale (m)
		total_weight = Decimal('0.00')
		total_length = Decimal('0.00')
		items_count = 0
		from delivery.services.delivery_rules import DeliveryRulesService
		for item in self.items.all():
			p_weight = item.product.weight_kg or item.product.estimated_weight_kg or Decimal('0.00')
			p_length = getattr(item.product, 'length_m', None) or DeliveryRulesService.DEFAULT_LENGTH_PER_ITEM
			qty = Decimal(item.quantity)
			total_weight += (p_weight * qty)
			total_length += (p_length * qty)
			items_count += int(item.quantity or 0)

		# Calcul de la livraison dynamique si demandÃ©e
		if self.delivery_requested:
			# Calcule et met Ã  jour delivery_cost et vehicle_type
			dyn_cost = self.calculate_dynamic_delivery_cost(total_weight, total_length, items_count)
			# On met delivery_fee pour rester compatible (affichÃ© dans l'API)
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

		# Le total inclut dÃ©sormais tous les frais
		self.total_amount = self.items_total + self.delivery_fee + self.operator_fee + self.tax_amount + self.payment_fees
		self.save()


class OrderItem(models.Model):
	"""
	Articles individuels dans une commande
	"""
	order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
	product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='order_items')
    
	quantity = models.PositiveIntegerField(default=1)
	unit_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Prix au moment de la commande")
    
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

