from django.contrib import admin
from django.utils.html import format_html
from .models import StoreCategory, Store


@admin.register(StoreCategory)
class StoreCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'store_count', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'name': ('name',)}
    
    def store_count(self, obj):
        return obj.stores.count()
    store_count.short_description = 'Nombre de magasins'


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    list_display = (
        'name', 
        'manager', 
        'city',
        'zone', 
        'category', 
        'commission_rate', 
        'is_active_display',
        'total_products_display',
        'is_open_display'
    )
    list_filter = ('is_active', 'is_verified', 'city', 'zone', 'category', 'created_at')
    search_fields = ('name', 'manager__phone', 'manager__email', 'address', 'city')
    # `is_active_display` is a boolean display helper, not the actual field name,
    # so keep only editable fields that exist on the model in `list_editable`.
    list_editable = ('commission_rate',)
    readonly_fields = ('created_at', 'updated_at', 'total_products_display')
    fieldsets = (
        ('Informations Générales', {
            'fields': ('name', 'description', 'category', 'manager', 'logo', 'banner_image')
        }),
        ('Contact et Localisation', {
            'fields': ('phone', 'email', 'address', 'city', 'zone', 'latitude', 'longitude')
        }),
        ('Configuration Business', {
            'fields': ('commission_rate', 'offers_delivery', 'delivery_fee', 'min_order_amount')
        }),
        ('Horaires et Statut', {
            'fields': ('opening_time', 'closing_time', 'is_active', 'is_verified')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at', 'total_products_display'),
            'classes': ('collapse',)
        }),
    )
    
    def is_active_display(self, obj):
        return obj.is_active
    is_active_display.boolean = True
    is_active_display.short_description = 'Actif'
    
    def total_products_display(self, obj):
        return obj.total_products()
    total_products_display.short_description = 'Produits'
    
    def is_open_display(self, obj):
        return obj.is_open()
    is_open_display.boolean = True
    is_open_display.short_description = 'Ouvert'
    
    # Actions personnalisées
    actions = ['activate_stores', 'deactivate_stores']
    
    def activate_stores(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} magasins activés avec succès.')
    activate_stores.short_description = "Activer les magasins sélectionnés"
    
    def deactivate_stores(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} magasins désactivés avec succès.')
    deactivate_stores.short_description = "Désactiver les magasins sélectionnés"
from django.contrib import admin

# Register your models here.
