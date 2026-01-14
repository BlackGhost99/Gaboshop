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
        'is_b2b_display',
        'is_b2c_display',
        'is_active_display',
        'total_products_display',
        'is_open_display'
    )
    list_filter = ('is_active', 'is_verified', 'is_b2b', 'is_b2c', 'city', 'zone', 'category', 'created_at')
    search_fields = ('name', 'manager__phone', 'manager__email', 'address', 'city', 'phone')
    readonly_fields = ('created_at', 'updated_at', 'total_products_display', 'has_b2b_profile_display')
    fieldsets = (
        ('Informations Générales', {
            'fields': ('name', 'description', 'category', 'manager', 'logo', 'banner_image')
        }),
        ('Contact et Localisation', {
            'fields': ('phone', 'email', 'address', 'city', 'zone', 'latitude', 'longitude')
        }),
        ('Configuration Business', {
            'fields': (
                'service_fee',
                'min_order_amount'
            )
        }),
        ('Configuration B2B/B2C', {
            'fields': (
                'is_b2c',
                'is_b2b',
                'b2b_min_order_amount',
                'b2b_delivery_delay',
                'has_b2b_profile_display'
            )
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
    
    def is_b2b_display(self, obj):
        return obj.is_b2b
    is_b2b_display.boolean = True
    is_b2b_display.short_description = 'B2B'
    
    def is_b2c_display(self, obj):
        return obj.is_b2c
    is_b2c_display.boolean = True
    is_b2c_display.short_description = 'B2C'
    
    def has_b2b_profile_display(self, obj):
        return hasattr(obj, 'b2b_profile')
    has_b2b_profile_display.boolean = True
    has_b2b_profile_display.short_description = 'Profil B2B'
    
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
