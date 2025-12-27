from django.contrib import admin
from django.utils.html import format_html
from .models import ProductCategory, Product


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'store_category', 'product_count', 'order')
    list_filter = ('store_category',)
    search_fields = ('name', 'store_category__name')
    exclude = ('store',)
    list_editable = ('order',)
    
    def product_count(self, obj):
        return obj.products.count()
    product_count.short_description = 'Nombre de produits'


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'store',
        'category',
        'price',
        'stock',
        'is_available',
        'has_discount_display',
        'created_at'
    )
    list_filter = ('is_available', 'is_featured', 'store', 'category', 'created_at')
    search_fields = ('name', 'description', 'store__name', 'sku')
    list_editable = ('price', 'stock', 'is_available')
    readonly_fields = ('created_at', 'updated_at', 'discount_percentage_display')
    fieldsets = (
        ('Informations Produit', {
            'fields': ('store', 'category', 'name', 'description', 'sku', 'barcode')
        }),
        ('Prix et Stock', {
            'fields': ('price', 'compare_price', 'stock', 'discount_percentage_display')
        }),
        ('Images', {
            'fields': ('image', 'image_2', 'image_3'),
            'classes': ('collapse',)
        }),
        ('Statut', {
            'fields': ('is_available', 'is_featured')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def price_display(self, obj):
        return f"{obj.price} FCFA"
    price_display.short_description = 'Prix'
    
    def stock_display(self, obj):
        if obj.stock == 0:
            return format_html('<span style="color: red;">⛔ {}</span>', obj.stock)
        elif obj.stock < 10:
            return format_html('<span style="color: orange;">⚠️ {}</span>', obj.stock)
        else:
            return format_html('<span style="color: green;">✅ {}</span>', obj.stock)
    stock_display.short_description = 'Stock'
    
    def is_available_display(self, obj):
        return obj.is_available
    is_available_display.boolean = True
    is_available_display.short_description = 'Disponible'
    
    def has_discount_display(self, obj):
        return obj.has_discount
    has_discount_display.boolean = True
    has_discount_display.short_description = 'Promo'
    
    def discount_percentage_display(self, obj):
        if obj.has_discount:
            return f"{obj.discount_percentage}% de réduction"
        return "Aucune promotion"
    discount_percentage_display.short_description = 'Réduction'
    
    # Actions personnalisées
    actions = ['mark_as_available', 'mark_as_unavailable', 'update_stock']
    
    def mark_as_available(self, request, queryset):
        updated = queryset.update(is_available=True)
        self.message_user(request, f'{updated} produits marqués comme disponibles.')
    mark_as_available.short_description = "Marquer comme disponible"
    
    def mark_as_unavailable(self, request, queryset):
        updated = queryset.update(is_available=False)
        self.message_user(request, f'{updated} produits marqués comme indisponibles.')
    mark_as_unavailable.short_description = "Marquer comme indisponible"
    
    def update_stock(self, request, queryset):
        # Cette action pourrait être améliorée avec un formulaire personnalisé
        for product in queryset:
            product.stock = 50  # Valeur par défaut
            product.save()
        self.message_user(request, f'Stock mis à jour pour {queryset.count()} produits.')
    update_stock.short_description = "Mettre le stock à 50"
from django.contrib import admin

# Register your models here.


# ProductCategoryTemplate admin removed after templates merged into ProductCategory
