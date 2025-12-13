from django.contrib import admin
from django.utils.html import format_html
from .models import (
	Payment, Commission, Reversement,
	PaymentIntent, PaymentTransaction,
	SubscriptionPlan, StoreSubscription,
	Forfait, ClientForfait, Payout, PaymentCallbackLog
)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
	list_display = (
		'id',
		'order_link',
		'payment_method_display',
		'status_display',
		'amount_display',
		'transaction_id',
		'created_at'
	)
	list_filter = ('status', 'payment_method', 'created_at')
	search_fields = ('order__order_number', 'transaction_id', 'operator_reference')
	readonly_fields = ('created_at', 'updated_at', 'completed_at')
	fieldsets = (
		('Informations Paiement', {
			'fields': ('order', 'payment_method', 'status', 'amount')
		}),
		('Références Transaction', {
			'fields': ('transaction_id', 'operator_reference')
		}),
		('Dates', {
			'fields': ('created_at', 'updated_at', 'completed_at'),
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
    
	def payment_method_display(self, obj):
		method_icons = {
			'mobile_money': '📱',
			'card': '💳',
			'cash': '💵'
		}
		icon = method_icons.get(obj.payment_method, '')
		return f"{icon} {obj.get_payment_method_display()}"
	payment_method_display.short_description = 'Méthode'
    
	def status_display(self, obj):
		status_colors = {
			'pending': 'orange',
			'completed': 'green',
			'failed': 'red',
			'refunded': 'blue'
		}
		color = status_colors.get(obj.status, 'black')
		return format_html(
			'<span style="color: {}; font-weight: bold;">{}</span>',
			color,
			obj.get_status_display()
		)
	status_display.short_description = 'Statut'
    
	def amount_display(self, obj):
		return f"{obj.amount} FCFA"
	amount_display.short_description = 'Montant'

@admin.register(Commission)
class CommissionAdmin(admin.ModelAdmin):
	list_display = (
		'id',
		'store',
		'order_link',
		'order_amount_display',
		'commission_rate_display',
		'commission_amount_display',
		'is_settled',
		'created_at'
	)
	list_filter = ('is_settled', 'store', 'created_at')
	search_fields = ('store__name', 'order__order_number')
	list_editable = ('is_settled',)
	readonly_fields = ('created_at', 'updated_at')
    
	def order_link(self, obj):
		return format_html(
			'<a href="/admin/orders/order/{}/change/">#{}</a>',
			obj.order.id,
			obj.order.order_number
		)
	order_link.short_description = 'Commande'
    
	def order_amount_display(self, obj):
		return f"{obj.order_amount} FCFA"
	order_amount_display.short_description = 'Montant commande'
    
	def commission_rate_display(self, obj):
		return f"{obj.commission_rate}%"
	commission_rate_display.short_description = 'Taux'
    
	def commission_amount_display(self, obj):
		return f"{obj.commission_amount} FCFA"
	commission_amount_display.short_description = 'Commission'
    
	# The model field `is_settled` is shown directly in list_display and is editable via list_editable.

@admin.register(Reversement)
class ReversementAdmin(admin.ModelAdmin):
	list_display = (
		'id',
		'store',
		'period_display',
		'total_orders',
		'total_sales_display',
		'total_commissions_display',
		'net_amount_display',
		'status_display',
		'created_at'
	)
	list_filter = ('status', 'store', 'created_at')
	search_fields = ('store__name', 'transaction_reference')
	readonly_fields = ('created_at', 'processed_at', 'completed_at')
    
	def period_display(self, obj):
		return f"{obj.period_start} au {obj.period_end}"
	period_display.short_description = 'Période'
    
	def total_sales_display(self, obj):
		return f"{obj.total_sales} FCFA"
	total_sales_display.short_description = 'Ventes brutes'
    
	def total_commissions_display(self, obj):
		return f"{obj.total_commissions} FCFA"
	total_commissions_display.short_description = 'Commissions'
    
	def net_amount_display(self, obj):
		return format_html(
			'<strong style="color: green;">{} FCFA</strong>',
			obj.net_amount
		)
	net_amount_display.short_description = 'Montant net'
    
	def status_display(self, obj):
		status_colors = {
			'pending': 'orange',
			'processing': 'blue',
			'completed': 'green',
			'failed': 'red'
		}
		color = status_colors.get(obj.status, 'black')
		return format_html(
			'<span style="color: {}; font-weight: bold;">{}</span>',
			color,
			obj.get_status_display()
		)
	status_display.short_description = 'Statut'


# ============================================================================
# ADMIN POUR CINETPAY / AIRTEL / MOOV INTEGRATION
# ============================================================================

@admin.register(PaymentIntent)
class PaymentIntentAdmin(admin.ModelAdmin):
	"""Admin pour les PaymentIntent"""
	list_display = (
		'reference',
		'user_display',
		'order_display',
		'amount_display',
		'provider',
		'status_badge',
		'created_at'
	)
	list_filter = ('status', 'provider', 'created_at')
	search_fields = ('reference', 'user__username', 'order__order_number')
	readonly_fields = (
		'reference', 'created_at', 'expires_at', 'raw_response'
	)
	
	fieldsets = (
		('Informations Générales', {
			'fields': ('reference', 'user', 'order')
		}),
		('Montants et Devise', {
			'fields': ('amount', 'currency')
		}),
		('Provider', {
			'fields': ('provider', 'status', 'payment_token', 'payment_url')
		}),
		('Métadonnées', {
			'fields': ('metadata', 'raw_response'),
			'classes': ('collapse',)
		}),
		('Dates', {
			'fields': ('created_at', 'expires_at'),
			'classes': ('collapse',)
		}),
	)
	
	def user_display(self, obj):
		return f"{obj.user.username} ({obj.user.email})"
	user_display.short_description = 'Utilisateur'
	
	def order_display(self, obj):
		if obj.order:
			return format_html(
				'<a href="/admin/orders/order/{}/change/">Commande #{}</a>',
				obj.order.id,
				obj.order.order_number
			)
		return "-"
	order_display.short_description = 'Commande'
	
	def amount_display(self, obj):
		return f"{obj.amount} {obj.currency}"
	amount_display.short_description = 'Montant'
	
	def status_badge(self, obj):
		status_colors = {
			'WAITING': 'gray',
			'PENDING': 'orange',
			'SUCCESS': 'green',
			'FAILED': 'red',
			'REFUNDED': 'blue',
			'ERROR': 'darkred'
		}
		color = status_colors.get(obj.status, 'black')
		return format_html(
			'<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
			color,
			obj.status
		)
	status_badge.short_description = 'Statut'


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
	"""Admin pour les PaymentTransaction"""
	list_display = (
		'intent_reference',
		'provider_tx_id',
		'status',
		'processed_badge',
		'created_at'
	)
	list_filter = ('status', 'processed', 'created_at')
	search_fields = ('intent__reference', 'provider_tx_id')
	readonly_fields = ('created_at', 'raw_response')
	
	fieldsets = (
		('Transaction', {
			'fields': ('intent', 'provider_tx_id', 'status')
		}),
		('Traitement', {
			'fields': ('processed',)
		}),
		('Réponse Provider', {
			'fields': ('raw_response',),
			'classes': ('collapse',)
		}),
		('Dates', {
			'fields': ('created_at',),
			'classes': ('collapse',)
		}),
	)
	
	def intent_reference(self, obj):
		return format_html(
			'<a href="/admin/payments/paymentintent/{}/change/">{}</a>',
			obj.intent.id,
			obj.intent.reference
		)
	intent_reference.short_description = 'Reference Intent'
	
	def processed_badge(self, obj):
		if obj.processed:
			return format_html(
				'<span style="color: green; font-weight: bold;">✓ Traité</span>'
			)
		return format_html(
			'<span style="color: orange; font-weight: bold;">⏳ En attente</span>'
		)
	processed_badge.short_description = 'Statut Traitement'


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
	list_display = (
		'name',
		'plan_type',
		'price_display',
		'max_products_display',
		'features_display',
		'is_active'
	)
	list_filter = ('plan_type', 'is_active')
	search_fields = ('name', 'description')
	prepopulated_fields = {'slug': ('name',)}
	readonly_fields = ('created_at', 'updated_at')
	
	fieldsets = (
		('Informations de base', {
			'fields': ('name', 'slug', 'plan_type', 'price', 'description', 'is_active')
		}),
		('Limites et Fonctionnalités', {
			'fields': (
				'max_products',
				'can_sponsor_products',
				'has_statistics',
				'has_custom_page',
				'has_priority_support',
				'priority_listing',
				'commission_rate'
			)
		}),
		('Fonctionnalités additionnelles', {
			'fields': ('features_json',),
			'classes': ('collapse',)
		}),
		('Métadonnées', {
			'fields': ('created_at', 'updated_at'),
			'classes': ('collapse',)
		}),
	)
	
	def price_display(self, obj):
		if obj.price == 0:
			return format_html('<span style="color: green; font-weight: bold;">GRATUIT</span>')
		return format_html('<strong>{:,.0f} FCFA/mois</strong>', obj.price)
	price_display.short_description = 'Prix'
	
	def max_products_display(self, obj):
		if obj.max_products is None:
			return format_html('<span style="color: blue;">∞ Illimité</span>')
		return f"{obj.max_products} produits"
	max_products_display.short_description = 'Limite produits'
	
	def features_display(self, obj):
		features = []
		if obj.has_statistics:
			features.append('📊 Stats')
		if obj.has_custom_page:
			features.append('🎨 Page perso')
		if obj.has_priority_support:
			features.append('🎧 Support VIP')
		if obj.can_sponsor_products:
			features.append('⭐ Sponsoring')
		return ' | '.join(features) if features else '-'
	features_display.short_description = 'Fonctionnalités'


@admin.register(StoreSubscription)
class StoreSubscriptionAdmin(admin.ModelAdmin):
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
		return format_html('<strong>{}</strong> ({:,.0f} FCFA)', plan_name, price)
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


# ============================================================================
# ADMIN FOR FORFAIT/SUBSCRIPTION MANAGEMENT SYSTEM
# ============================================================================

@admin.register(Forfait)
class ForfaitAdmin(admin.ModelAdmin):
	"""Admin for forfait/subscription plans"""
	list_display = (
		'name',
		'price_display',
		'max_priority_orders_display',
		'discount_rate_display',
		'is_active'
	)
	list_filter = ('is_active', 'created_at')
	search_fields = ('name', 'description')
	readonly_fields = ('created_at', 'updated_at')
	
	fieldsets = (
		('Informations de base', {
			'fields': ('name', 'description', 'is_active')
		}),
		('Tarification et Limites', {
			'fields': ('monthly_price', 'max_priority_orders', 'discount_rate')
		}),
		('Métadonnées', {
			'fields': ('created_at', 'updated_at'),
			'classes': ('collapse',)
		}),
	)
	
	def price_display(self, obj):
		return format_html('<strong>{:,.0f} FCFA/mois</strong>', obj.monthly_price)
	price_display.short_description = 'Prix mensuel'
	
	def max_priority_orders_display(self, obj):
		if obj.max_priority_orders is None:
			return format_html('<span style="color: blue;">∞ Illimité</span>')
		return f"{obj.max_priority_orders} commandes"
	max_priority_orders_display.short_description = 'Commandes prioritaires'
	
	def discount_rate_display(self, obj):
		return f"{obj.discount_rate}%"
	discount_rate_display.short_description = 'Réduction'


@admin.register(ClientForfait)
class ClientForfaitAdmin(admin.ModelAdmin):
	"""Admin for client forfait subscriptions"""
	list_display = (
		'user_display',
		'forfait_display',
		'status_display',
		'start_date',
		'expiration_date_display',
		'is_active_display'
	)
	list_filter = ('status', 'forfait', 'start_date', 'auto_renew')
	search_fields = ('user__username', 'user__email', 'forfait__name')
	readonly_fields = ('created_at', 'updated_at', 'start_date')
	raw_id_fields = ('user', 'forfait')
	date_hierarchy = 'start_date'
	
	fieldsets = (
		('Client et Forfait', {
			'fields': ('user', 'forfait')
		}),
		('Dates', {
			'fields': ('start_date', 'expiration_date', 'status', 'auto_renew')
		}),
		('Métadonnées', {
			'fields': ('created_at', 'updated_at'),
			'classes': ('collapse',)
		}),
	)
	
	def user_display(self, obj):
		return format_html(
			'<a href="/admin/users/user/{}/change/">{} ({})</a>',
			obj.user.id,
			obj.user.get_full_name() or obj.user.username,
			obj.user.email
		)
	user_display.short_description = 'Client'
	
	def forfait_display(self, obj):
		if not obj.forfait:
			return '-'
		return format_html(
			'<strong>{}</strong><br/><small>{:,.0f} FCFA/mois</small>',
			obj.forfait.name,
			obj.forfait.monthly_price
		)
	forfait_display.short_description = 'Forfait'
	
	def status_display(self, obj):
		colors = {
			'active': 'green',
			'expired': 'red',
			'cancelled': 'gray',
			'suspended': 'orange'
		}
		color = colors.get(obj.status, 'black')
		return format_html(
			'<span style="color: {}; font-weight: bold;">{}</span>',
			color,
			obj.get_status_display()
		)
	status_display.short_description = 'Statut'
	
	def expiration_date_display(self, obj):
		from django.utils import timezone
		if obj.expiration_date < timezone.now():
			return format_html('<span style="color: red; font-weight: bold;">🔴 {}</span>', obj.expiration_date.date())
		elif (obj.expiration_date - timezone.now()).days <= 7:
			return format_html('<span style="color: orange; font-weight: bold;">🟠 {} (7j)</span>', obj.expiration_date.date())
		return format_html('<span style="color: green;">🟢 {}</span>', obj.expiration_date.date())
	expiration_date_display.short_description = 'Expiration'
	
	def is_active_display(self, obj):
		if obj.is_active():
			return format_html('<span style="color: green; font-weight: bold;">✓ Actif</span>')
		return format_html('<span style="color: red; font-weight: bold;">✗ Inactif</span>')
	is_active_display.short_description = 'Actif?'


@admin.register(PaymentCallbackLog)
class PaymentCallbackLogAdmin(admin.ModelAdmin):
	"""Admin for payment callback audit trail"""
	list_display = (
		'id_display',
		'order_display',
		'status_badge',
		'signature_badge',
		'received_at_display'
	)
	list_filter = ('signature_valid', 'processed', 'received_at')
	search_fields = ('id', 'order__order_number')
	readonly_fields = ('raw_data', 'received_at')
	date_hierarchy = 'received_at'
	
	fieldsets = (
		('Informations Webhook', {
			'fields': ('order', 'status_code', 'received_at')
		}),
		('Signature et Traitement', {
			'fields': ('signature_valid', 'processed')
		}),
		('Données Brutes', {
			'fields': ('raw_data',),
			'classes': ('collapse',)
		}),
	)
	
	def id_display(self, obj):
		return format_html('<code>#{}</code>', obj.id)
	id_display.short_description = 'ID'
	
	def order_display(self, obj):
		if obj.order:
			return format_html(
				'<a href="/admin/orders/order/{}/change/">Commande #{}</a>',
				obj.order.id,
				obj.order.order_number
			)
		return '-'
	order_display.short_description = 'Commande'
	
	def status_badge(self, obj):
		colors = {
			200: 'green',
			400: 'orange',
			500: 'red'
		}
		color = colors.get(obj.status_code, 'gray')
		return format_html(
			'<span style="background-color: {}; color: white; padding: 5px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
			color,
			obj.status_code
		)
	status_badge.short_description = 'HTTP Code'
	
	def signature_badge(self, obj):
		if obj.signature_valid:
			return format_html('<span style="color: green; font-weight: bold;">✓ Valide</span>')
		return format_html('<span style="color: red; font-weight: bold;">✗ Invalide</span>')
	signature_badge.short_description = 'Signature'
	
	def received_at_display(self, obj):
		return obj.received_at.strftime('%Y-%m-%d %H:%M:%S')
	received_at_display.short_description = 'Reçu le'


@admin.register(Payout)
class PayoutAdmin(admin.ModelAdmin):
	"""Admin for payouts to delivery agents and merchants"""
	list_display = (
		'id_display',
		'user_display',
		'payout_type_display',
		'amount_display',
		'status_display',
		'created_at',
	)
	list_filter = ('payout_type', 'status', 'created_at')
	search_fields = ('user__username', 'user__email', 'flutterwave_payout_id')
	readonly_fields = ('flutterwave_payout_id', 'created_at', 'updated_at', 'paid_at')
	raw_id_fields = ('user', 'order')
	date_hierarchy = 'created_at'
	
	fieldsets = (
		('Bénéficiaire et Commande', {
			'fields': ('user', 'order', 'payout_type')
		}),
		('Montant et Statut', {
			'fields': ('amount', 'status')
		}),
		('Raison et Détails', {
			'fields': ('reason',)
		}),
		('Flutterwave', {
			'fields': ('flutterwave_payout_id',),
			'classes': ('collapse',)
		}),
		('Métadonnées', {
			'fields': ('created_at', 'updated_at', 'paid_at'),
			'classes': ('collapse',)
		}),
	)
	
	def id_display(self, obj):
		return format_html('<code>#{}</code>', obj.id)
	id_display.short_description = 'ID'
	
	def user_display(self, obj):
		user_type = 'Livreur' if obj.payout_type == 'delivery' else 'Commerçant'
		return format_html(
			'<a href="/admin/users/user/{}/change/"><strong>{}</strong></a><br/><small>{} ({})</small>',
			obj.user.id,
			obj.user.get_full_name() or obj.user.username,
			user_type,
			obj.user.email
		)
	user_display.short_description = 'Bénéficiaire'
	
	def payout_type_display(self, obj):
		icons = {
			'delivery': '🚚 Livreur',
			'merchant': '🏪 Commerçant',
			'refund': '↩️ Remboursement'
		}
		return icons.get(obj.payout_type, obj.get_payout_type_display())
	payout_type_display.short_description = 'Type'
	
	def amount_display(self, obj):
		return format_html('<strong style="color: green;">{:,.0f} FCFA</strong>', obj.amount)
	amount_display.short_description = 'Montant'
	
	def status_display(self, obj):
		colors = {
			'pending': 'orange',
			'processing': 'blue',
			'paid': 'green',
			'failed': 'red',
			'cancelled': 'gray'
		}
		color = colors.get(obj.status, 'black')
		icons = {
			'pending': '⏳',
			'processing': '⚙️',
			'paid': '✅',
			'failed': '❌',
			'cancelled': '⊘'
		}
		icon = icons.get(obj.status, '')
		return format_html(
			'<span style="color: {}; font-weight: bold;">{} {}</span>',
			color,
			icon,
			obj.get_status_display()
		)
	status_display.short_description = 'Statut'

