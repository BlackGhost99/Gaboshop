"""
Serializers pour l'API B2B
"""
from rest_framework import serializers
from stores.models import Store
from products.models import Product
from orders.models import Order, OrderItem
from b2b.models import B2BProfile, B2BCategory, B2BProductPricing


class WholesalerSerializer(serializers.ModelSerializer):
	"""
	Serializer pour la liste des grossistes
	"""
	category_name = serializers.CharField(source='category.name', read_only=True)
	b2b_profile = serializers.SerializerMethodField()
	
	class Meta:
		model = Store
		fields = [
			'id', 'name', 'description', 'category', 'category_name',
			'phone', 'email', 'address', 'city', 'zone',
			'logo', 'banner_image', 'is_active', 'b2b_profile',
			'b2b_min_order_amount', 'b2b_delivery_delay'
		]
	
	def get_b2b_profile(self, obj):
		"""Retourne le profil B2B si disponible"""
		if hasattr(obj, 'b2b_profile'):
			return {
				'is_active': obj.b2b_profile.is_active,
				'minimum_order_amount': float(obj.b2b_profile.minimum_order_amount),
				'visible_to_all': obj.b2b_profile.visible_to_all,
			}
		return None


class B2BProfileSerializer(serializers.ModelSerializer):
	"""
	Serializer pour le profil B2B
	"""
	store_name = serializers.CharField(source='store.name', read_only=True)
	store_id = serializers.IntegerField(source='store.id', read_only=True)
	
	class Meta:
		model = B2BProfile
		fields = [
			'id', 'store', 'store_id', 'store_name',
			'is_active', 'minimum_order_amount', 'visible_to_all',
			'created_at', 'updated_at'
		]
		read_only_fields = ['created_at', 'updated_at']


class B2BCategorySerializer(serializers.ModelSerializer):
	"""
	Serializer pour les catégories B2B
	"""
	product_count = serializers.SerializerMethodField()
	
	class Meta:
		model = B2BCategory
		fields = ['id', 'name', 'description', 'is_active', 'product_count', 'created_at', 'updated_at']
		read_only_fields = ['created_at', 'updated_at']
	
	def get_product_count(self, obj):
		"""Nombre de produits dans cette catégorie"""
		return obj.products.filter(is_available=True).count()


class B2BCatalogCategorySerializer(serializers.ModelSerializer):
	"""
	Serializer pour les catégories dans le catalogue B2B (avec compteur)
	"""
	product_count = serializers.IntegerField(read_only=True)
	
	class Meta:
		model = B2BCategory
		fields = ['id', 'name', 'description', 'product_count']


class B2BProductPricingSerializer(serializers.ModelSerializer):
	"""
	Serializer pour les prix B2B
	"""
	product_name = serializers.CharField(source='product.name', read_only=True)
	b2b_store_name = serializers.CharField(source='b2b_store.name', read_only=True)
	
	class Meta:
		model = B2BProductPricing
		fields = [
			'id', 'product', 'product_name', 'b2b_store', 'b2b_store_name',
			'b2b_price', 'min_quantity', 'max_quantity', 'is_active',
			'created_at', 'updated_at'
		]
		read_only_fields = ['created_at', 'updated_at']


class B2BProductSerializer(serializers.ModelSerializer):
	"""
	Serializer pour les produits B2B avec prix
	"""
	category_name = serializers.CharField(source='category.name', read_only=True)
	b2b_category_name = serializers.CharField(source='b2b_category.name', read_only=True)
	b2b_pricings = B2BProductPricingSerializer(many=True, read_only=True)
	b2b_price = serializers.SerializerMethodField()
	min_quantity = serializers.SerializerMethodField()
	
	class Meta:
		model = Product
		fields = [
			'id', 'name', 'description', 'price', 'compare_price',
			'stock', 'sku', 'barcode', 'is_available', 'is_featured',
			'category', 'category_name', 'b2b_category', 'b2b_category_name',
			'market_type', 'image', 'b2b_pricings', 'b2b_price', 'min_quantity',
			'created_at', 'updated_at'
		]
		read_only_fields = ['created_at', 'updated_at']
	
	def get_b2b_price(self, obj):
		"""Prix B2B minimum (premier pricing actif)"""
		context = self.context
		wholesaler_id = context.get('wholesaler_id')
		
		if wholesaler_id:
			pricing = obj.b2b_pricings.filter(
				b2b_store_id=wholesaler_id,
				is_active=True
			).order_by('min_quantity').first()
			
			if pricing:
				return float(pricing.b2b_price)
		
		return None
	
	def get_min_quantity(self, obj):
		"""Quantité minimale B2B"""
		context = self.context
		wholesaler_id = context.get('wholesaler_id')
		
		if wholesaler_id:
			pricing = obj.b2b_pricings.filter(
				b2b_store_id=wholesaler_id,
				is_active=True
			).order_by('min_quantity').first()
			
			if pricing:
				return pricing.min_quantity
		
		return None


class B2BCatalogProductSerializer(serializers.ModelSerializer):
	"""
	Serializer pour les produits dans le catalogue B2B (version allégée)
	"""
	b2b_price = serializers.SerializerMethodField()
	min_quantity = serializers.SerializerMethodField()
	
	class Meta:
		model = Product
		fields = [
			'id', 'name', 'description', 'price', 'b2b_price',
			'stock', 'is_available', 'image', 'min_quantity',
			'b2b_category'
		]
	
	def get_b2b_price(self, obj):
		"""Prix B2B minimum"""
		context = self.context
		wholesaler_id = context.get('wholesaler_id')
		
		if wholesaler_id:
			pricing = obj.b2b_pricings.filter(
				b2b_store_id=wholesaler_id,
				is_active=True
			).order_by('min_quantity').first()
			
			if pricing:
				return float(pricing.b2b_price)
		
		return None
	
	def get_min_quantity(self, obj):
		"""Quantité minimale B2B"""
		context = self.context
		wholesaler_id = context.get('wholesaler_id')
		
		if wholesaler_id:
			pricing = obj.b2b_pricings.filter(
				b2b_store_id=wholesaler_id,
				is_active=True
			).order_by('min_quantity').first()
			
			if pricing:
				return pricing.min_quantity
		
		return None


class B2BOrderItemSerializer(serializers.Serializer):
	"""
	Serializer pour les items d'une commande B2B
	"""
	product_id = serializers.IntegerField()
	quantity = serializers.IntegerField(min_value=1)
	b2b_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)


class B2BOrderCreateSerializer(serializers.Serializer):
	"""
	Serializer pour créer une commande B2B
	"""
	wholesaler_id = serializers.IntegerField()
	items = B2BOrderItemSerializer(many=True)
	delivery_address = serializers.CharField()
	delivery_phone = serializers.CharField()
	delivery_zone = serializers.CharField()
	city = serializers.CharField(default='Libreville')
	notes = serializers.CharField(required=False, allow_blank=True)
	
	def validate_items(self, value):
		"""Valider qu'il y a au moins un item"""
		if not value or len(value) == 0:
			raise serializers.ValidationError("La commande doit contenir au moins un produit.")
		return value
	
	def validate(self, attrs):
		"""Validation globale"""
		wholesaler_id = attrs.get('wholesaler_id')
		items = attrs.get('items', [])
		
		# Vérifier que le grossiste existe
		try:
			wholesaler = Store.objects.get(id=wholesaler_id, is_b2b=True, is_active=True)
		except Store.DoesNotExist:
			raise serializers.ValidationError({
				'wholesaler_id': 'Grossiste non trouvé ou non actif.'
			})
		
		# Vérifier que le profil B2B est actif
		if not hasattr(wholesaler, 'b2b_profile') or not wholesaler.b2b_profile.is_active:
			raise serializers.ValidationError({
				'wholesaler_id': 'Le profil B2B de ce grossiste n\'est pas actif.'
			})
		
		# Valider chaque item
		for item in items:
			product_id = item.get('product_id')
			quantity = item.get('quantity')
			
			try:
				product = Product.objects.get(id=product_id, store=wholesaler, is_available=True)
			except Product.DoesNotExist:
				raise serializers.ValidationError({
					'items': f'Produit {product_id} non trouvé ou non disponible.'
				})
			
			# Vérifier le stock
			if product.stock < quantity:
				raise serializers.ValidationError({
					'items': f'Stock insuffisant pour le produit {product.name}. Stock disponible: {product.stock}'
				})
			
			# Vérifier le prix B2B
			b2b_price = item.get('b2b_price')
			if b2b_price:
				# Vérifier que le prix correspond à un pricing B2B valide
				pricing = B2BProductPricing.objects.filter(
					product=product,
					b2b_store=wholesaler,
					is_active=True,
					min_quantity__lte=quantity
				).order_by('-min_quantity').first()
				
				if not pricing:
					raise serializers.ValidationError({
						'items': f'Aucun prix B2B valide pour le produit {product.name} avec la quantité {quantity}.'
					})
		
		return attrs


class B2BOrderSerializer(serializers.ModelSerializer):
	"""
	Serializer pour les commandes B2B
	"""
	store_name = serializers.CharField(source='store.name', read_only=True)
	store_zone = serializers.CharField(source='store.zone', read_only=True)
	source_store_name = serializers.CharField(source='source_store.name', read_only=True)
	status_display = serializers.CharField(source='get_status_display', read_only=True)
	items = serializers.SerializerMethodField()
	
	class Meta:
		model = Order
		fields = [
			'id', 'order_number', 'store', 'store_name', 'store_zone',
			'source_store', 'source_store_name', 'is_b2b',
			'status', 'status_display', 'items_total', 'delivery_fee',
			'service_fee', 'tax_amount', 'payment_fees', 'total_amount',
			'city', 'delivery_address', 'delivery_phone', 'delivery_zone',
			'notes', 'items', 'created_at', 'updated_at', 'confirmed_at', 'delivered_at'
		]
		read_only_fields = [
			'id', 'order_number', 'items_total', 'total_amount', 'service_fee',
			'payment_fees', 'created_at', 'updated_at', 'confirmed_at', 'delivered_at'
		]
	
	def get_items(self, obj):
		"""Retourne les items de la commande"""
		items = OrderItem.objects.filter(order=obj)
		return [
			{
				'id': item.id,
				'product_id': item.product.id,
				'product_name': item.product.name,
				'quantity': item.quantity,
				'unit_price': float(item.unit_price),
				'subtotal': float(item.subtotal)
			}
			for item in items
		]

