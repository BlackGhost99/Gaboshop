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
	delivery_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Frais de livraison")
	service_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0.00, help_text="Frais de service plateforme")
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
		"""Calcule les frais de livraison selon le type"""
		if self.delivery_type == 'express':
			self.delivery_fee = self.store.delivery_fee_express
		else:
			self.delivery_fee = self.store.delivery_fee
		return self.delivery_fee
	
	def calculate_service_fee(self):
		"""Calcule les frais de service"""
		if self.store.service_fee > 0:
			self.service_fee = self.store.service_fee
		else:
			# Frais de service par défaut (100-300 FCFA)
			self.service_fee = Decimal('200.00')
		return self.service_fee
	
	def calculate_commission(self):
		"""Calcule la commission GABOSHOP"""
		from payments.models import CategoryCommission

		if self.items_total > 0:
			# Determine current plan
			plan = self.store.get_current_plan()
			plan_type = plan.plan_type if plan else 'free'
			multiplier = Decimal(getattr(plan, 'commission_multiplier', 1)) if plan else Decimal('1')

			total_commission = Decimal('0.00')
			# Sum commission per OrderItem using category base rates
			for item in self.items.all():
				product = item.product
				item_subtotal = item.subtotal
				base_rate = None
				
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
					# Try category-level commission (linked to StoreCategory)
					if product and product.category and product.category.store_category:
						try:
							cc = CategoryCommission.objects.get(store_category=product.category.store_category)
							base_rate = Decimal(cc.base_rate)
						except CategoryCommission.DoesNotExist:
							base_rate = None
					# Fallback to store-level commission rate
					if base_rate is None:
						base_rate = Decimal(self.store.commission_rate or Decimal('0.00'))

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
    
	def calculate_totals(self):
		"""Recalcule tous les totaux basés sur les OrderItems"""
		self.items_total = sum(item.subtotal for item in self.items.all())
		self.calculate_delivery_fee()
		self.calculate_service_fee()
		self.calculate_commission()
		# Le total inclut désormais les frais de paiement s'ils sont définis
		self.total_amount = self.items_total + self.delivery_fee + self.service_fee + self.tax_amount + self.payment_fees
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
