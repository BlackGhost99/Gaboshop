"""
Serializers pour l'API B2B
"""

from rest_framework import serializers
from stores.models import Store
from products.models import Product
from orders.models import Order, OrderItem
from b2b.models import B2BProfile, B2BCategory, B2BProductPricing
from b2b.services.supply import get_b2b_price_for_product


class B2BProfileSerializer(serializers.ModelSerializer):
	"""Serializer pour les profils B2B"""
	store_name = serializers.CharField(source='store.name', read_only=True)
	store_zone = serializers.CharField(source='store.zone', read_only=True)
	store_logo = serializers.ImageField(source='store.logo', read_only=True)
	
	class Meta:
		model = B2BProfile
		fields = [
			'id', 'store', 'store_name', 'store_zone', 'store_logo',
			'is_active', 'minimum_order_amount', 'visible_to_all',
			'created_at'
		]
		read_only_fields = ['created_at']


class B2BCategorySerializer(serializers.ModelSerializer):
	"""Serializer pour les catégories B2B"""
	product_count = serializers.SerializerMethodField()
	
	class Meta:
		model = B2BCategory
		fields = ['id', 'name', 'description', 'is_active', 'product_count', 'created_at']
		read_only_fields = ['created_at']
	
	def get_product_count(self, obj):
		"""Nombre de produits dans cette catégorie B2B"""
		return obj.products.filter(is_available=True).count()


class B2BProductPricingSerializer(serializers.ModelSerializer):
	"""Serializer pour les prix B2B"""
	product_name = serializers.CharField(source='product.name', read_only=True)
	
	class Meta:
		model = B2BProductPricing
		fields = [
			'id', 'product', 'product_name', 'b2b_store',
			'b2b_price', 'min_quantity', 'max_quantity', 'is_active'
		]


class B2BProductSerializer(serializers.ModelSerializer):
	"""Serializer pour les produits avec prix B2B"""
	store_name = serializers.CharField(source='store.name', read_only=True)
	category_name = serializers.CharField(source='category.name', read_only=True)
	b2b_category_name = serializers.CharField(source='b2b_category.name', read_only=True)
	b2b_price = serializers.SerializerMethodField()
	b2b_pricings = B2BProductPricingSerializer(many=True, read_only=True)
	
	class Meta:
		model = Product
		fields = [
			'id', 'name', 'description', 'store', 'store_name',
			'category', 'category_name', 'b2b_category', 'b2b_category_name',
			'price', 'b2b_price', 'b2b_pricings', 'stock',
			'sku', 'barcode', 'is_available', 'image', 'image_2', 'image_3',
			'created_at'
		]
		read_only_fields = ['store', 'created_at']
	
	def get_b2b_price(self, obj):
		"""Prix B2B pour la quantité demandée (par défaut min_quantity)"""
		request = self.context.get('request')
		wholesaler_id = self.context.get('wholesaler_id')
		quantity = self.context.get('quantity', 1)
		
		if not wholesaler_id:
			return None
		
		try:
			wholesaler = Store.objects.get(id=wholesaler_id)
			price = get_b2b_price_for_product(obj, wholesaler, quantity)
			return float(price) if price else None
		except Store.DoesNotExist:
			return None


class WholesalerSerializer(serializers.ModelSerializer):
	"""Serializer pour les grossistes (Store avec profil B2B)"""
	b2b_profile = B2BProfileSerializer(read_only=True)
	total_products = serializers.IntegerField(read_only=True)
	
	class Meta:
		model = Store
		fields = [
			'id', 'name', 'description', 'category', 'phone', 'email',
			'address', 'city', 'zone', 'logo', 'banner_image',
			'b2b_profile', 'total_products', 'is_active', 'is_verified',
			'created_at'
		]
		read_only_fields = ['created_at']
	
	def get_total_products(self, obj):
		"""Nombre de produits B2B disponibles"""
		return obj.products.filter(
			is_available=True,
			b2b_pricings__is_active=True
		).distinct().count()


class B2BOrderItemSerializer(serializers.Serializer):
	"""Serializer pour les items d'une commande B2B"""
	product_id = serializers.IntegerField()
	quantity = serializers.IntegerField(min_value=1)


class B2BOrderCreateSerializer(serializers.Serializer):
	"""Serializer pour créer une commande B2B"""
	wholesaler_id = serializers.IntegerField()
	items = B2BOrderItemSerializer(many=True)
	delivery_type = serializers.ChoiceField(
		choices=Order.DELIVERY_TYPE_CHOICES,
		default='standard'
	)
	notes = serializers.CharField(required=False, allow_blank=True)
	delivery_address = serializers.CharField()
	delivery_phone = serializers.CharField()
	delivery_zone = serializers.CharField()
	city = serializers.CharField(default='Libreville')
	
	def validate_items(self, value):
		"""Valider qu'il y a au moins un item"""
		if not value:
			raise serializers.ValidationError("La commande doit contenir au moins un produit")
		return value


class B2BOrderSerializer(serializers.ModelSerializer):
	"""Serializer pour les commandes B2B"""
	wholesaler_name = serializers.CharField(source='store.name', read_only=True)
	source_store_name = serializers.CharField(source='source_store.name', read_only=True)
	client_name = serializers.CharField(source='client.get_display_name', read_only=True)
	
	class Meta:
		model = Order
		fields = [
			'id', 'order_number', 'status', 'delivery_type',
			'wholesaler_name', 'source_store_name', 'client_name',
			'items_total', 'delivery_fee', 'service_fee', 'total_amount',
			'delivery_address', 'delivery_phone', 'delivery_zone', 'city',
			'notes', 'created_at', 'confirmed_at', 'delivered_at'
		]
		read_only_fields = [
			'order_number', 'status', 'items_total', 'delivery_fee',
			'service_fee', 'total_amount', 'created_at', 'confirmed_at', 'delivered_at'
		]




