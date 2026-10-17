"""
Services de logique d'approvisionnement B2B
"""

from django.db.models import Q, Prefetch
from stores.models import Store
from products.models import Product
from b2b.models import B2BProfile, B2BProductPricing, B2BCategory
from decimal import Decimal


def get_available_wholesalers(buyer_store=None):
	"""
	Retourne la liste des grossistes disponibles
	
	Args:
		buyer_store: Store (optionnel) - magasin acheteur pour filtrer
	
	Returns:
		QuerySet de Store avec profils B2B actifs
	"""
	queryset = Store.objects.filter(
		is_b2b=True,
		is_active=True,
		is_verified=True,
	).select_related('b2b_profile', 'category', 'manager').prefetch_related('products')
	
	# Filtrer uniquement les magasins avec profil B2B actif
	queryset = queryset.filter(
		b2b_profile__is_active=True
	)
	
	# Si un magasin acheteur est fourni, exclure ce magasin
	if buyer_store:
		queryset = queryset.exclude(id=buyer_store.id)
	
	# Filtrer par visibilité si nécessaire
	# Pour l'instant, on retourne tous les profils visible_to_all=True
	# ou ceux accessibles au magasin acheteur
	
	# Trier par priorité du plan B2B (catalog_priority desc, puis featured_in_catalog desc, puis name)
	# Joindre B2BStoreSubscription et B2BSubscriptionPlan pour accéder aux champs de priorité
	from b2b.models import B2BStoreSubscription, B2BSubscriptionPlan
	from django.db.models import Case, When, Value, IntegerField, BooleanField
	
	queryset = queryset.select_related('b2b_subscription', 'b2b_subscription__plan')

	# La priorité ne vaut que pendant l'abonnement : un grossiste expiré ou résilié repasse à égalité.
	from django.db.models import Q
	from django.utils import timezone
	paying = Q(b2b_subscription__status='active') & (
		Q(b2b_subscription__end_date__isnull=True) | Q(b2b_subscription__end_date__gte=timezone.now().date()))

	# Annoter avec catalog_priority et featured_in_catalog depuis le plan B2B
	queryset = queryset.annotate(
		catalog_priority_value=Case(
			When(paying & Q(b2b_subscription__plan__catalog_priority__isnull=False),
				 then='b2b_subscription__plan__catalog_priority'),
			default=Value(0),
			output_field=IntegerField()
		),
		featured_value=Case(
			When(paying & Q(b2b_subscription__plan__featured_in_catalog=True),
				 then=Value(1)),
			default=Value(0),
			output_field=IntegerField()
		)
	)
	
	# Trier par priorité décroissante, puis featured décroissant, puis nom
	return queryset.order_by('-catalog_priority_value', '-featured_value', 'name')


def get_b2b_products(wholesaler_id, category_id=None, search=None):
	"""
	Retourne les produits B2B d'un grossiste
	
	Args:
		wholesaler_id: int - ID du grossiste
		category_id: int (optionnel) - ID de la catégorie B2B
		search: str (optionnel) - Terme de recherche
	
	Returns:
		QuerySet de Product avec prix B2B
	"""
	try:
		wholesaler = Store.objects.get(id=wholesaler_id, is_b2b=True, is_active=True, is_verified=True)
	except Store.DoesNotExist:
		return Product.objects.none()
	
	# Vérifier que le profil B2B est actif
	if not hasattr(wholesaler, 'b2b_profile') or not wholesaler.b2b_profile.is_active:
		return Product.objects.none()
	
	# Récupérer les produits du grossiste qui ont des prix B2B actifs
	# Un produit est visible en B2B s'il a au moins un prix B2B actif pour ce grossiste
	# On ne filtre plus par market_type car un produit peut être B2B s'il a des prix B2B
	products = Product.objects.filter(
		store=wholesaler,
		is_available=True,
		b2b_pricings__b2b_store=wholesaler,
		b2b_pricings__is_active=True
	).select_related('category', 'b2b_category').prefetch_related(
		Prefetch(
			'b2b_pricings',
			queryset=B2BProductPricing.objects.filter(
				b2b_store=wholesaler,
				is_active=True
			).order_by('min_quantity')
		)
	).distinct()
	
	# Filtrer par catégorie B2B si fournie
	if category_id:
		products = products.filter(b2b_category_id=category_id)
	
	# Recherche textuelle
	if search:
		products = products.filter(
			Q(name__icontains=search) | Q(description__icontains=search)
		)
	
	return products.order_by('name')


def get_b2b_categories(wholesaler_id=None):
	"""
	Retourne les catégories B2B disponibles
	
	Args:
		wholesaler_id: int (optionnel) - ID du grossiste pour filtrer
	
	Returns:
		QuerySet de B2BCategory
	"""
	categories = B2BCategory.objects.filter(is_active=True)
	
	# Si un grossiste est fourni, filtrer par ses produits
	if wholesaler_id:
		try:
			wholesaler = Store.objects.get(id=wholesaler_id, is_b2b=True)
			# Récupérer les catégories B2B des produits du grossiste
			product_category_ids = Product.objects.filter(
				store=wholesaler,
				b2b_category__isnull=False,
				b2b_pricings__b2b_store=wholesaler,
				b2b_pricings__is_active=True
			).values_list('b2b_category_id', flat=True).distinct()
			
			categories = categories.filter(id__in=product_category_ids)
		except Store.DoesNotExist:
			return B2BCategory.objects.none()
	
	return categories.order_by('name')


def get_b2b_price_for_product(product, wholesaler, quantity=1):
	"""
	Retourne le prix B2B unitaire d'un produit pour une quantité donnée
	(palier dégressif si le forfait du grossiste l'inclut, sinon prix de base).
	
	Args:
		product: Product - Produit concerné
		wholesaler: Store - Grossiste
		quantity: int - Quantité demandée
	
	Returns:
		Decimal ou None - Prix B2B ou None si non disponible
	"""
	from b2b.services.tiers import price_for_quantity
	price, _ = price_for_quantity(product, wholesaler, quantity)
	return price


def calculate_b2b_order_totals(order_items, wholesaler, buyer_store):
	"""
	Calcule les totaux pour une commande B2B
	
	Args:
		order_items: list - Liste de dicts {'product_id': int, 'quantity': int}
		wholesaler: Store - Grossiste
		buyer_store: Store - Magasin acheteur
	
	Returns:
		dict - {
			'items_total': Decimal,
			'delivery_fee': Decimal,
			'total_amount': Decimal,
			'items': list - Liste des items avec prix B2B
		}
	"""
	items_total = Decimal('0.00')
	items = []
	errors = []
	
	# Récupérer le profil B2B du grossiste
	b2b_profile = wholesaler.b2b_profile if hasattr(wholesaler, 'b2b_profile') else None
	
	# Une même référence commandée sur plusieurs lignes compte pour sa quantité totale (palier dégressif).
	quantities = {}
	for item_data in order_items:
		product_id = item_data.get('product_id')
		quantities[product_id] = quantities.get(product_id, 0) + int(item_data.get('quantity', 1) or 1)
	
	from b2b.services.tiers import price_for_quantity, bulk_discounts_active
	bulk = bulk_discounts_active(wholesaler)
	for product_id, quantity in quantities.items():
		try:
			product = Product.objects.get(id=product_id, store=wholesaler)
		except Product.DoesNotExist:
			errors.append(f"Le produit {product_id} n'est pas proposé par ce grossiste.")
			continue
		b2b_price, error = price_for_quantity(product, wholesaler, quantity, bulk)
		if b2b_price is None:
			errors.append(error)
			continue
		
		item_subtotal = Decimal(str(b2b_price)) * Decimal(str(quantity))
		items_total += item_subtotal
		
		items.append({
			'product': product,
			'product_id': product_id,
			'quantity': quantity,
			'unit_price': b2b_price,
			'subtotal': item_subtotal
		})
	
	# Calculer les frais
	delivery_fee = wholesaler.delivery_fee or Decimal('0.00')
	
	# Total
	total_amount = items_total + delivery_fee
	
	return {
		'items_total': items_total,
		'delivery_fee': delivery_fee,
		'total_amount': total_amount,
		'items': items,
		'errors': errors,
	}


def validate_b2b_order(order_items, wholesaler, buyer_store):
	"""
	Valide une commande B2B avant création
	
	Args:
		order_items: list - Liste de dicts {'product_id': int, 'quantity': int}
		wholesaler: Store - Grossiste
		buyer_store: Store - Magasin acheteur
	
	Returns:
		tuple: (bool, str, dict) - (valide, message d'erreur, données calculées)
	"""
	# Vérifier les permissions
	from b2b.services.permissions import can_purchase_from_wholesaler
	can_purchase, error_msg = can_purchase_from_wholesaler(buyer_store, wholesaler)
	if not can_purchase:
		return False, error_msg, None
	
	# Vérifier qu'il y a des items
	if not order_items:
		return False, "La commande doit contenir au moins un produit", None
	
	# Calculer les totaux
	totals = calculate_b2b_order_totals(order_items, wholesaler, buyer_store)
	
	# Un produit sans prix valable pour la quantité demandée refuse la commande (jamais ignoré en silence)
	if totals['errors']:
		return False, totals['errors'][0], None
	
	# Vérifier le montant minimum
	b2b_profile = wholesaler.b2b_profile if hasattr(wholesaler, 'b2b_profile') else None
	if b2b_profile and b2b_profile.minimum_order_amount > 0:
		if totals['items_total'] < b2b_profile.minimum_order_amount:
			return False, f"Le montant minimum de commande est de {b2b_profile.minimum_order_amount} FCFA", None
	
	# Vérifier le stock
	for item in totals['items']:
		product = item['product']
		if product.stock < item['quantity']:
			return False, f"Stock insuffisant pour {product.name} (disponible: {product.stock})", None
	
	return True, "", totals
