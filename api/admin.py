from django.contrib import admin
from .models import SystemSettings, CommissionByCategory, AIActionLog


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    """
    Interface d'administration pour les paramètres système.
    Configuration simplifiée avec tous les paramètres organisés par catégorie.
    """
    
    fieldsets = (
        ('🟦 1. COMMISSIONS', {
            'fields': ('commission_global', 'commission_event'),
            'description': 'Gestion des commissions sur les ventes'
        }),
        ('🟧 2. PAIEMENTS', {
            'fields': ('moov_money_fee', 'airtel_money_fee', 'payment_before_order', 'unpaid_order_expiry_minutes'),
            'description': 'Configuration des méthodes de paiement mobile'
        }),
        ('🟥 3. VILLES & GÉOLOCALISATION', {
            'fields': ('auto_detect_cities', 'default_city', 'enabled_cities', 'max_delivery_distance_km'),
            'description': 'Paramètres de localisation et zones de service'
        }),
        ('🟩 4. LIVRAISON', {
            'fields': ('price_per_km', 'auto_assign_delivery', 'max_orders_per_delivery'),
            'description': 'Configuration du système de livraison'
        }),
        ('🟨 5. COMMANDES', {
            'fields': ('cart_validity_hours', 'order_opening_time', 'order_closing_time'),
            'description': 'Gestion des paniers et horaires de commande'
        }),
        ('🟪 6. MAGASINS', {
            'fields': ('default_store_opening', 'default_store_closing', 'store_verification_required', 'pro_mode_monthly_fee'),
            'description': 'Paramètres globaux des magasins'
        }),
        ('⚫ 7. NOTIFICATIONS', {
            'fields': ('enable_sms', 'enable_email', 'notification_templates'),
            'description': 'Configuration des notifications système'
        }),
        ('📊 Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    def has_add_permission(self, request):
        """Empêcher la création de plusieurs instances"""
        return not SystemSettings.objects.exists()
    
    def has_delete_permission(self, request, obj=None):
        """Empêcher la suppression des paramètres système"""
        return False


@admin.register(CommissionByCategory)
class CommissionByCategoryAdmin(admin.ModelAdmin):
    """
    Interface d'administration pour les commissions par catégorie.
    Permet de définir des taux de commission spécifiques par catégorie de magasin.
    """
    list_display = ('category', 'commission_rate', 'is_active', 'updated_at')
    list_filter = ('is_active', 'category')
    search_fields = ('category__name',)
    list_editable = ('commission_rate', 'is_active')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('category', 'commission_rate', 'is_active')
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(AIActionLog)
class AIActionLogAdmin(admin.ModelAdmin):
    """
    Interface d'administration pour les logs d'actions IA
    """
    list_display = ('id', 'action', 'initiator', 'confirmed', 'success', 'timestamp')
    list_filter = ('action', 'confirmed', 'success', 'timestamp')
    search_fields = ('initiator__phone', 'action', 'details')
    readonly_fields = ('timestamp', 'ip_address', 'user_agent')
    date_hierarchy = 'timestamp'
    
    fieldsets = (
        ('Action', {
            'fields': ('actor', 'initiator', 'action', 'details')
        }),
        ('Résultat', {
            'fields': ('confirmed', 'success', 'error_message')
        }),
        ('Métadonnées', {
            'fields': ('timestamp', 'ip_address', 'user_agent'),
            'classes': ('collapse',),
        }),
    )
    
    def has_add_permission(self, request):
        """Les logs sont créés automatiquement, pas d'ajout manuel"""
        return False
