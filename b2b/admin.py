"""
Configuration admin pour les modèles B2B
"""
from django.contrib import admin
from .models import B2BProfile, B2BCategory, B2BProductPricing


@admin.register(B2BProfile)
class B2BProfileAdmin(admin.ModelAdmin):
	"""
	Admin pour les profils B2B
	"""
	list_display = (
		'store', 'is_active', 'minimum_order_amount', 
		'visible_to_all', 'created_at'
	)
	list_filter = ('is_active', 'visible_to_all', 'created_at')
	search_fields = ('store__name', 'store__phone', 'store__email')
	readonly_fields = ('created_at', 'updated_at')
	
	fieldsets = (
		('Magasin', {
			'fields': ('store',)
		}),
		('Configuration B2B', {
			'fields': ('is_active', 'minimum_order_amount', 'visible_to_all')
		}),
		('Métadonnées', {
			'fields': ('created_at', 'updated_at'),
			'classes': ('collapse',)
		}),
	)


@admin.register(B2BCategory)
class B2BCategoryAdmin(admin.ModelAdmin):
	"""
	Admin pour les catégories B2B
	"""
	list_display = ('name', 'is_active', 'product_count', 'created_at')
	list_filter = ('is_active', 'created_at')
	search_fields = ('name', 'description')
	readonly_fields = ('created_at', 'updated_at', 'product_count')
	
	fieldsets = (
		('Informations', {
			'fields': ('name', 'description', 'is_active')
		}),
		('Métadonnées', {
			'fields': ('created_at', 'updated_at', 'product_count'),
			'classes': ('collapse',)
		}),
	)
	
	def product_count(self, obj):
		"""Nombre de produits dans cette catégorie"""
		return obj.products.filter(is_available=True).count()
	product_count.short_description = 'Produits'


@admin.register(B2BProductPricing)
class B2BProductPricingAdmin(admin.ModelAdmin):
	"""
	Admin pour les prix B2B
	"""
	list_display = (
		'product', 'b2b_store', 'b2b_price', 
		'min_quantity', 'max_quantity', 'is_active', 'created_at'
	)
	list_filter = ('is_active', 'b2b_store', 'created_at')
	search_fields = (
		'product__name', 'b2b_store__name', 
		'product__sku', 'product__barcode'
	)
	readonly_fields = ('created_at', 'updated_at')
	
	fieldsets = (
		('Produit et Grossiste', {
			'fields': ('product', 'b2b_store')
		}),
		('Prix et Quantités', {
			'fields': ('b2b_price', 'min_quantity', 'max_quantity', 'is_active')
		}),
		('Métadonnées', {
			'fields': ('created_at', 'updated_at'),
			'classes': ('collapse',)
		}),
	)

