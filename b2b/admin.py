"""
Configuration de l'admin Django pour le module B2B
"""
from django.contrib import admin
from django.utils.html import format_html
from b2b.models import (
    B2BProfile, 
    B2BCategory, 
    B2BProductPricing,
    B2BSubscriptionPlan,
    B2BStoreSubscription
)


@admin.register(B2BProfile)
class B2BProfileAdmin(admin.ModelAdmin):
    list_display = ('store', 'minimum_order_amount', 'visible_to_all', 'is_active', 'created_at')
    list_filter = ('is_active', 'visible_to_all', 'created_at')
    search_fields = ('store__name',)
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('store',)


@admin.register(B2BCategory)
class B2BCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')


@admin.register(B2BProductPricing)
class B2BProductPricingAdmin(admin.ModelAdmin):
    list_display = ('product', 'b2b_store', 'b2b_price_display', 'min_quantity', 'max_quantity', 'is_active')
    list_filter = ('is_active', 'b2b_store')
    search_fields = ('product__name', 'b2b_store__name')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('product', 'b2b_store')
    
    def b2b_price_display(self, obj):
        formatted_price = f"{obj.b2b_price:,.0f}"
        return format_html('<strong>{} FCFA</strong>', formatted_price)
    b2b_price_display.short_description = 'Prix B2B'


@admin.register(B2BSubscriptionPlan)
class B2BSubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'plan_type',
        'price_display',
        'max_products_display',
        'features_summary',
        'is_popular',
        'is_active'
    )
    list_filter = ('plan_type', 'is_active', 'is_popular', 'featured_in_catalog')
    search_fields = ('name', 'description', 'tagline')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('name', 'slug', 'plan_type', 'price', 'applies_to', 'description', 'tagline')
        }),
        ('Limites et quotas', {
            'fields': (
                'max_b2b_products',
                'max_b2c_buyers',
                'max_monthly_orders'
            )
        }),
        ('Distribution & visibilité commerciale', {
            'fields': (
                'catalog_priority',
                'featured_in_catalog',
                'is_popular',
                'display_order'
            ),
            'description': 'Contrôle de la visibilité et de la distribution dans le catalogue B2B'
        }),
        ('Fonctionnalités', {
            'fields': (
                'can_offer_bulk_discounts',
                'has_advanced_analytics',  # Déprécié, gardé pour compatibilité
                'can_view_detailed_reports',
                'has_priority_support',
                'can_create_promotions',
                'has_api_access'
            )
        }),
        ('Tarification', {
            'fields': ('commission_reduction_percent',)
        }),
        ('Finance', {
            'fields': (
                'can_view_finance_basic',
                'can_view_finance_detailed',
                'can_export_finance_csv',
                'can_export_finance_pdf',
                'finance_history_limit_days',
            ),
            'description': 'Contrôle des accès aux rapports financiers et exports (aligné avec B2C)'
        }),
        ('Avantages personnalisés', {
            'fields': ('custom_features',),
            'classes': ('collapse',),
            'description': 'Format JSON: [{"title": "Avantage", "description": "Description", "category": "custom", "enabled": true}]'
        }),
        ('Statut', {
            'fields': ('is_active',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def price_display(self, obj):
        if obj.price == 0:
            return format_html('<span style="color: green; font-weight: bold;">GRATUIT</span>')
        formatted_price = f"{obj.price:,.0f}"
        return format_html('<strong>{} FCFA/mois</strong>', formatted_price)
    price_display.short_description = 'Prix'
    
    def max_products_display(self, obj):
        if obj.max_b2b_products is None:
            return format_html('<span style="color: blue;">∞ Illimité</span>')
        return f"{obj.max_b2b_products} produits"
    max_products_display.short_description = 'Limite produits'
    
    def features_summary(self, obj):
        features = []
        if obj.can_view_detailed_reports or obj.has_advanced_analytics:
            features.append('📊 Analytics')
        if obj.has_priority_support:
            features.append('🎧 Support VIP')
        if obj.can_create_promotions:
            features.append('🎁 Promotions')
        if obj.has_api_access:
            features.append('🔌 API')
        if obj.featured_in_catalog:
            features.append('⭐ Featured')
        return ' | '.join(features) if features else '-'
    features_summary.short_description = 'Fonctionnalités'


@admin.register(B2BStoreSubscription)
class B2BStoreSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'store_link',
        'plan_display',
        'status_display',
        'start_date',
        'end_date_display',
        'auto_renew_display'
    )
    list_filter = ('status', 'auto_renew', 'start_date')
    search_fields = ('store__name', 'plan__name', 'plan_name')
    readonly_fields = ('created_at', 'updated_at', 'start_date')
    raw_id_fields = ('store', 'plan')
    
    fieldsets = (
        ('Magasin et Plan', {
            'fields': ('store', 'plan', 'plan_name', 'monthly_fee')
        }),
        ('Statut et Dates', {
            'fields': ('status', 'start_date', 'end_date', 'auto_renew')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def store_link(self, obj):
        return format_html(
            '<a href="/admin/stores/store/{}/change/">{}</a>',
            obj.store.id,
            obj.store.name
        )
    store_link.short_description = 'Magasin'
    
    def plan_display(self, obj):
        plan_name = obj.plan.name if obj.plan else obj.plan_name
        price = obj.plan.price if obj.plan else obj.monthly_fee
        if price == 0:
            return format_html('<span style="color: green; font-weight: bold;">{}</span>', plan_name)
        formatted_price = f"{price:,.0f}"
        return format_html('<strong>{}</strong> ({} FCFA)', plan_name, formatted_price)
    plan_display.short_description = 'Plan'
    
    def status_display(self, obj):
        colors = {
            'active': 'green',
            'cancelled': 'red',
            'expired': 'gray',
            'pending_payment': 'orange'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = 'Statut'
    
    def end_date_display(self, obj):
        if not obj.end_date:
            return format_html('<span style="color: blue;">Pas de limite</span>')
        from django.utils import timezone
        if obj.end_date < timezone.now().date():
            return format_html('<span style="color: red;">{}</span>', obj.end_date)
        return obj.end_date
    end_date_display.short_description = 'Date de fin'
    
    def auto_renew_display(self, obj):
        if obj.auto_renew:
            return format_html('<span style="color: green;">✓ Oui</span>')
        return format_html('<span style="color: gray;">✗ Non</span>')
    auto_renew_display.short_description = 'Auto-renouvellement'
