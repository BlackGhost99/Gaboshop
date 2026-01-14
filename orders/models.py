from django.db import models
from users.models import User
from stores.models import Store
from products.models import Product
from decimal import Decimal


class Order(models.Model):
	"""
	Commandes passées par les clients
	"""
	ORDER_STATUS_CHOICES = (
		('created', '🟡 Créée'),
		('pending_payment', '🟡 En attente de paiement'),
		('paid', '🟢 Payée'),
		('confirmed', '🔵 Confirmée'),
		('preparing', '👨‍🍳 En préparation'),
		('ready', '✅ Prête pour livraison'),
		('assigned', '🚗 Livreur assigné'),
		('in_transit', '📦 En cours de livraison'),
		('delivered', '🎉 Livrée'),
		('cancelled', '❌ Annulée'),
		('refunded', '💸 Remboursée'),
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
	service_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Frais de service plateforme")
	operator_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Frais opérateur Mobile Money (Airtel/Moov)")
	tax_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Taxes (optionnel)")
	payment_fees = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Frais de transaction (Mobile Money)")
	commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Commission GABOSHOP")
	commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=8.00, help_text="Taux de commission en %")
	total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Total à payer")
    
	# Adresse de livraison
	city = models.CharField(max_length=100, default='Libreville', help_text="Ville de livraison")
	delivery_address = models.TextField(help_text="Adresse complète de livraison")
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

	def select_vehicle_for_weight(self, total_weight):
		"""Sélectionne un type de véhicule et un multiplicateur basé sur le poids (kg)"""
		from decimal import Decimal
		# Mapping configurable (peut être déplacé en settings ou en modèle)
		if total_weight <= Decimal('5.00'):
			return 'bike', Decimal('1.00')
		elif total_weight <= Decimal('20.00'):
			return 'motorbike', Decimal('1.50')
		else:
			return 'van', Decimal('2.50')

	def calculate_dynamic_delivery_cost(self, total_weight):
		"""Calcule le coût de livraison en fonction de la ville et du type de véhicule
		
		Utilise la configuration des zones et des tarifs par véhicule (ZoneVehicleRate)
		"""
		from decimal import Decimal
		from delivery.models import DeliveryZone, ZoneVehicleRate
		
		vehicle, multiplier = self.select_vehicle_for_weight(total_weight)
		
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
						base_fee = zone_rate.base_price
						cost = base_fee * multiplier
					else:
						# Pas de tarif spécifique, utiliser store.delivery_fee
						base_fee = self.store.delivery_fee if self.delivery_type == 'standard' else self.store.delivery_fee_express
						cost = base_fee * multiplier
				else:
					base_fee = self.store.delivery_fee if self.delivery_type == 'standard' else self.store.delivery_fee_express
					cost = base_fee * multiplier
				
				# Appliquer surcharge inter-ville si applicable
				if (not (hasattr(self, 'city') and self.city and self.store and self.store.city and self.store.city == self.city)):
					cost += zone.inter_city_surcharge
			except Exception:
				# En cas d'erreur, fallback sur tarif store
				base_fee = self.store.delivery_fee if self.delivery_type == 'standard' else self.store.delivery_fee_express
				cost = base_fee * multiplier
				if (not (hasattr(self, 'city') and self.city and self.store and self.store.city and self.store.city == self.city)):
					cost += Decimal('1000.00')
		else:
			# Pas de zone trouvée, utiliser tarif store avec surcharge fixe
			base_fee = self.store.delivery_fee if self.delivery_type == 'standard' else self.store.delivery_fee_express
			cost = base_fee * multiplier
			if (not (hasattr(self, 'city') and self.city and self.store and self.store.city and self.store.city == self.city)):
				cost += Decimal('1000.00')
		
		# Arrondir à 0.01
		cost = cost.quantize(Decimal('0.01'))
		self.vehicle_type = vehicle
		self.delivery_cost = cost
		return cost
	
	def calculate_service_fee(self):
		"""
		Calcule les frais de service selon le plan d'abonnement et le type de commande
		
		RÈGLE IMPORTANTE:
		- B2C: seul le CLIENT (qui passe la commande) paie le service_fee
		- B2B: seul le BUYER_STORE (source_store) paie le service_fee_to_wholesaler
		- Le vendeur (store) ne paie JAMAIS de frais de service
		"""
		if self.is_b2b and self.source_store:
			# Commande B2B: charger au buyer_store (source_store)
			from payments.subscription_check import SubscriptionChecker
			self.service_fee = SubscriptionChecker.get_service_fee_b2b(self.source_store)
		else:
			# Commande B2C: charger au client via le plan du store vendeur
			plan = self.store.get_current_plan()
			
			if plan and hasattr(plan, 'service_fee_client_amount'):
				self.service_fee = Decimal(str(plan.service_fee_client_amount))
			else:
				# Fallback si pas de plan ou ancien modèle
				self.service_fee = self.store.service_fee if self.store.service_fee > 0 else Decimal('500.00')
		
		return self.service_fee
	
	def calculate_commission(self):
		"""Calcule la commission GABOSHOP"""
		if self.items_total > 0:
			# Determine current plan
			plan = self.store.get_current_plan()
			plan_type = plan.plan_type if plan else 'free'
			
			# Pour les commandes B2B d'un grossiste, utiliser B2BSubscriptionPlan
			if self.is_b2b and self.store.is_b2b:
				# C'est une commande B2B reçue par un grossiste
				# Utiliser le plan B2B du grossiste
				b2b_plan = self.store.get_current_b2b_plan()
				if b2b_plan:
					# Commission de base B2B = 8%
					base_rate_b2b = Decimal('8.00')
					# Appliquer la réduction du plan B2B
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
			
			# Pour les commandes B2C ou les commandes B2B passées par un store B2C
			# Convert commission_reduction_percent to multiplier
			# Ex: 40% reduction → multiplier 0.60 (1 - 0.40)
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
						effective_rate = Decimal('2.00')
					# Business B2C: 0% alimentaire, 2% reste
					else:
						# Vérifier si c'est alimentaire
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
		
		CONFIGURATION SCALABLE:
		- Chaque opérateur a un taux de frais (3% par défaut pour Airtel/Moov)
		- Les frais sont calculés sur le total des articles + frais de livraison
		- Configuration centralisée et facile à modifier
		"""
		from decimal import Decimal
		
		# Configuration des frais par opérateur (en %)
		OPERATOR_FEES = {
			'airtel': Decimal('3.00'),  # 3% Airtel Money
			'moov': Decimal('3.00'),    # 3% Moov Money
			'card': Decimal('2.50'),    # 2.5% Carte Bancaire
			'cash': Decimal('0.00'),    # 0% Espèces
		}
		
		# Récupérer le taux de frais (fallback à 0 si opérateur non reconnu)
		fee_rate = OPERATOR_FEES.get(operator.lower(), Decimal('0.00'))
		
		# Les frais s'appliquent sur items_total + delivery_fee (pas sur service_fee)
		base_amount = self.items_total + self.delivery_fee
		
		# Calculer les frais
		operator_fee = (base_amount * fee_rate) / Decimal('100')
		
		return operator_fee.quantize(Decimal('0.01'))
    
	def calculate_totals(self):
		"""Recalcule tous les totaux basés sur les OrderItems"""
		from decimal import Decimal
		# Items total
		self.items_total = sum(item.subtotal for item in self.items.all())

		# Calcul du poids total (kg)
		total_weight = Decimal('0.00')
		for item in self.items.all():
			p_weight = item.product.weight_kg or item.product.estimated_weight_kg or Decimal('0.00')
			total_weight += (p_weight * Decimal(item.quantity))

		# Calcul de la livraison dynamique si demandée
		if self.delivery_requested:
			# Calcule et met à jour delivery_cost et vehicle_type
			dyn_cost = self.calculate_dynamic_delivery_cost(total_weight)
			# On met delivery_fee pour rester compatible (affiché dans l'API)
			self.delivery_fee = dyn_cost
		else:
			self.delivery_fee = Decimal('0.00')
			self.delivery_cost = Decimal('0.00')

		# Service, commission, opérateur
		self.calculate_service_fee()
		self.calculate_commission()
		self.operator_fee = self.calculate_operator_fee()  # Ajouter frais opérateur

		# Le total inclut désormais tous les frais
		self.total_amount = self.items_total + self.delivery_fee + self.service_fee + self.operator_fee + self.tax_amount + self.payment_fees
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
