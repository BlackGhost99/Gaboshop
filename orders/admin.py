from django.contrib import admin
import logging

logger = logging.getLogger(__name__)
from django.utils.html import format_html
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
	model = OrderItem
	extra = 0
	readonly_fields = ('unit_price', 'subtotal_display')
	fields = ('product', 'quantity', 'unit_price', 'subtotal_display')
    
	def subtotal_display(self, obj):
		return f"{obj.subtotal} FCFA"
	subtotal_display.short_description = 'Sous-total'

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
	list_display = (
		'order_number',
		'client_display',
		'store',
		'is_b2b',
		'source_store',
		'city',
		'status_display',
		'total_amount_display',
		'items_count',
		'created_at',
		'delivery_status'
	)
	list_filter = ('is_b2b', 'status', 'store', 'created_at', 'city', 'delivery_zone')
	search_fields = ('order_number', 'client__phone', 'store__name', 'source_store__name', 'delivery_address', 'city')
	readonly_fields = (
		'order_number', 'is_b2b', 'source_store', 'created_at', 'updated_at', 'confirmed_at', 
		'delivered_at', 'items_total_display', 'total_amount_display'
	)
	inlines = [OrderItemInline]
	fieldsets = (
		('Informations Commande', {
			'fields': ('order_number', 'client', 'store', 'is_b2b', 'source_store', 'status', 'notes')
		}),
		('Montants', {
			'fields': ('items_total_display', 'delivery_fee', 'service_fee', 'tax_amount', 'payment_fees', 'total_amount_display')
		}),
		('Livraison', {
			'fields': ('city', 'delivery_address', 'delivery_phone', 'delivery_zone')
		}),
		('Dates', {
			'fields': ('created_at', 'updated_at', 'confirmed_at', 'delivered_at'),
			'classes': ('collapse',)
		}),
	)
    
	def client_display(self, obj):
		return obj.client.phone
	client_display.short_description = 'Client'
    
	def status_display(self, obj):
		status_colors = {
			'pending': 'gray',
			'confirmed': 'blue',
			'preparing': 'orange',
			'ready': 'green',
			'assigned': 'purple',
			'in_transit': 'cyan',
			'delivered': 'green',
			'cancelled': 'red',
			'refunded': 'brown'
		}
		color = status_colors.get(obj.status, 'black')
		return format_html(
			'<span style="color: {}; font-weight: bold;">{}</span>',
			color,
			obj.get_status_display()
		)
	status_display.short_description = 'Statut'
    
	def total_amount_display(self, obj):
		return f"{obj.total_amount} FCFA"
	total_amount_display.short_description = 'Total'
    
	def items_total_display(self, obj):
		return f"{obj.items_total} FCFA"
	items_total_display.short_description = 'Total articles'
    
	def items_count(self, obj):
		return obj.items.count()
	items_count.short_description = 'Articles'
    
	def delivery_status(self, obj):
		if hasattr(obj, 'delivery'):
			return obj.delivery.get_status_display()
		return "Aucune livraison"
	delivery_status.short_description = 'Livraison'
    
	# Actions personnalisées
	actions = ['mark_as_confirmed', 'mark_as_preparing', 'mark_as_ready']
    
	def mark_as_confirmed(self, request, queryset):
		from django.utils import timezone
		updated = queryset.update(status='confirmed', confirmed_at=timezone.now())
		self.message_user(request, f'{updated} commandes confirmées.')
	mark_as_confirmed.short_description = "Marquer comme confirmées"
    
	def mark_as_preparing(self, request, queryset):
		updated = queryset.update(status='preparing')
		self.message_user(request, f'{updated} commandes en préparation.')
	mark_as_preparing.short_description = "Marquer comme en préparation"
    
	def mark_as_ready(self, request, queryset):
		# Boucler pour déclencher l'assignation automatique pour chaque commande
		from delivery.services import auto_assign_delivery

		count = 0
		for order in queryset:
			order.status = 'ready'
			order.save()
			try:
				auto_assign_delivery(order)
			except Exception:
				logger.exception('Erreur auto-assign depuis admin')
			count += 1

		self.message_user(request, f'{count} commandes prêtes pour livraison.')
	mark_as_ready.short_description = "Marquer comme prêtes"

