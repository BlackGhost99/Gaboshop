from django.contrib import admin
from django.utils.html import format_html
from .models import Delivery, DeliveryTracking

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
		'status_display',
		'delivery_fee_display',
		'agent_commission_display',
		'assigned_at',
		'delivered_at_display'
	)
	list_filter = ('status', 'delivery_agent', 'created_at')
	search_fields = ('tracking_number', 'order__order_number', 'delivery_agent__phone')
	readonly_fields = ('tracking_number', 'created_at', 'updated_at')
	inlines = [DeliveryTrackingInline]
	fieldsets = (
		('Informations Livraison', {
			'fields': ('tracking_number', 'order', 'delivery_agent', 'status')
		}),
		('Adresses', {
			'fields': ('pickup_address', 'delivery_address')
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


@admin.register(DeliveryTracking)
class DeliveryTrackingAdmin(admin.ModelAdmin):
	list_display = ('delivery', 'status', 'location', 'created_at')
	list_filter = ('status', 'created_at')
	search_fields = ('delivery__tracking_number', 'location', 'notes')
	readonly_fields = ('created_at',)

