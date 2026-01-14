from django.contrib import admin
from django.utils.html import format_html
from .models import Delivery, DeliveryTracking, VehicleType, CityDistance, DeliveryProfile, DeliveryZone, ZoneVehicleRate

class DeliveryTrackingInline(admin.TabularInline):
	model = DeliveryTracking
	extra = 0
	readonly_fields = ('created_at',)
	fields = ('status', 'location', 'latitude', 'longitude', 'notes', 'created_at')

@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
	list_display = (
		'tracking_number',
		'order_link',
		'delivery_agent_display',
		'vehicle_type_display',
		'status_display',
		'delivery_fee_display',
		'agent_commission_display',
		'assigned_at',
		'delivered_at_display'
	)
	list_filter = ('status', 'delivery_agent', 'vehicle_type', 'is_intra_city', 'created_at')
	search_fields = ('tracking_number', 'order__order_number', 'delivery_agent__phone')
	readonly_fields = ('tracking_number', 'created_at', 'updated_at', 'minimum_required_vehicle_type', 'is_intra_city')
	inlines = [DeliveryTrackingInline]
	fieldsets = (
		('Informations Livraison', {
			'fields': ('tracking_number', 'order', 'delivery_agent', 'status')
		}),
		('Véhicules', {
			'fields': (
				'minimum_required_vehicle_type', 'selected_vehicle_type',
				'vehicle_type', 'is_intra_city', 'distance_km'
			)
		}),
		('Adresses', {
			'fields': ('city', 'pickup_address', 'delivery_address')
		}),
		('Frais et Commission', {
			'fields': ('delivery_fee', 'agent_commission')
		}),
		('Notes et Évaluation', {
			'fields': ('delivery_notes', 'customer_feedback', 'rating')
		}),
		('Dates', {
			'fields': ('assigned_at', 'picked_up_at', 'delivered_at', 'created_at', 'updated_at'),
			'classes': ('collapse',)
		}),
	)
    
	def order_link(self, obj):
		return format_html(
			'<a href="/admin/orders/order/{}/change/">#{}</a>',
			obj.order.id,
			obj.order.order_number
		)
	order_link.short_description = 'Commande'
    
	def delivery_agent_display(self, obj):
		return obj.delivery_agent.phone if obj.delivery_agent else "Non assigné"
	delivery_agent_display.short_description = 'Livreur'
    
	def status_display(self, obj):
		status_colors = {
			'pending': 'gray',
			'assigned': 'blue',
			'picked_up': 'orange',
			'in_transit': 'purple',
			'delivered': 'green',
			'failed': 'red'
		}
		color = status_colors.get(obj.status, 'black')
		return format_html(
			'<span style="color: {}; font-weight: bold;">{}</span>',
			color,
			obj.get_status_display()
		)
	status_display.short_description = 'Statut'
    
	def delivery_fee_display(self, obj):
		return f"{obj.delivery_fee} FCFA"
	delivery_fee_display.short_description = 'Frais livraison'
    
	def agent_commission_display(self, obj):
		return f"{obj.agent_commission} FCFA"
	agent_commission_display.short_description = 'Commission livreur'
    
	def delivered_at_display(self, obj):
		return obj.delivered_at if obj.delivered_at else "En cours"
	delivered_at_display.short_description = 'Livré le'
	
	def vehicle_type_display(self, obj):
		if obj.selected_vehicle_type:
			return obj.selected_vehicle_type.get_name_display()
		elif obj.vehicle_type:
			return obj.vehicle_type.get_name_display()
		return "Non sélectionné"
	vehicle_type_display.short_description = 'Véhicule'


@admin.register(DeliveryTracking)
class DeliveryTrackingAdmin(admin.ModelAdmin):
	list_display = ('delivery', 'status', 'location', 'created_at')
	list_filter = ('status', 'created_at')
	search_fields = ('delivery__tracking_number', 'location', 'notes')
	readonly_fields = ('created_at',)


class ZoneVehicleRateInline(admin.TabularInline):
	model = ZoneVehicleRate
	extra = 1
	fields = ('vehicle', 'base_price', 'price_per_km', 'is_active', 'notes')
	list_select_related = ('vehicle',)


@admin.register(VehicleType)
class VehicleTypeAdmin(admin.ModelAdmin):
	list_display = (
		'name', 'max_weight_kg', 'max_items', 'max_distance_km',
		'allow_intercity', 'is_active'
	)
	list_filter = ('is_active', 'allow_intercity', 'name')
	search_fields = ('name',)
	inlines = [ZoneVehicleRateInline]
	fieldsets = (
		('Informations générales', {
			'fields': ('name', 'is_active')
		}),
		('Capacités', {
			'fields': ('max_weight_kg', 'max_items', 'max_distance_km', 'allow_intercity')
		}),
		('Tarifs intra-ville', {
			'fields': ('base_price_intra_city', 'price_per_km_intra_city')
		}),
		('Tarifs inter-ville', {
			'fields': ('base_price_inter_city', 'price_per_km_inter_city')
		}),
	)
	actions = ['activate_vehicles', 'deactivate_vehicles']
	
	def activate_vehicles(self, request, queryset):
		queryset.update(is_active=True)
		self.message_user(request, f'{queryset.count()} type(s) de véhicule activé(s)')
	activate_vehicles.short_description = "Activer les types de véhicules sélectionnés"
	
	def deactivate_vehicles(self, request, queryset):
		queryset.update(is_active=False)
		self.message_user(request, f'{queryset.count()} type(s) de véhicule désactivé(s)')
	deactivate_vehicles.short_description = "Désactiver les types de véhicules sélectionnés"


@admin.register(CityDistance)
class CityDistanceAdmin(admin.ModelAdmin):
	list_display = ('from_city', 'to_city', 'distance_km', 'estimated_time_minutes')
	list_filter = ('from_city', 'to_city')
	search_fields = ('from_city', 'to_city')
	fieldsets = (
		('Villes', {
			'fields': ('from_city', 'to_city')
		}),
		('Distance et temps', {
			'fields': ('distance_km', 'estimated_time_minutes')
		}),
	)


@admin.register(DeliveryZone)
class DeliveryZoneAdmin(admin.ModelAdmin):
	list_display = ('name', 'city', 'inter_city_surcharge', 'is_active', 'created_at')
	list_filter = ('is_active', 'city')
	search_fields = ('name', 'city', 'description')
	inlines = [ZoneVehicleRateInline]
	fieldsets = (
		('Informations Zone', {
			'fields': ('name', 'city', 'is_active')
		}),
		('Configuration', {
			'fields': ('inter_city_surcharge', 'description')
		}),
		('Métadonnées', {
			'fields': ('created_at', 'updated_at'),
			'classes': ('collapse',)
		}),
	)
	readonly_fields = ('created_at', 'updated_at')


@admin.register(ZoneVehicleRate)
class ZoneVehicleRateAdmin(admin.ModelAdmin):
	list_display = ('zone', 'vehicle', 'base_price', 'price_per_km', 'is_active')
	list_filter = ('is_active', 'zone', 'vehicle')
	search_fields = ('zone__name', 'vehicle__name')
	fieldsets = (
		('Configuration', {
			'fields': ('zone', 'vehicle', 'is_active')
		}),
		('Tarification', {
			'fields': ('base_price', 'price_per_km', 'notes')
		}),
		('Métadonnées', {
			'fields': ('created_at', 'updated_at'),
			'classes': ('collapse',)
		}),
	)
	readonly_fields = ('created_at', 'updated_at')


@admin.register(DeliveryProfile)
class DeliveryProfileAdmin(admin.ModelAdmin):
	list_display = (
		'user', 'vehicle_type', 'status', 'allow_intercity',
		'average_rating', 'total_deliveries', 'success_rate'
	)
	list_filter = ('status', 'vehicle_type', 'allow_intercity')
	search_fields = ('user__phone', 'user__first_name', 'user__last_name', 'cin_number')
	fieldsets = (
		('Utilisateur', {
			'fields': ('user',)
		}),
		('Véhicule', {
			'fields': ('vehicle_type', 'vehicle_plate', 'allow_intercity')
		}),
		('Informations', {
			'fields': ('cin_number', 'status')
		}),
		('Statistiques', {
			'fields': ('average_rating', 'total_deliveries', 'success_rate'),
			'classes': ('collapse',)
		}),
	)

