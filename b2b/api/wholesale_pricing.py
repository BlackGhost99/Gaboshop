"""
Prix de gros et paliers dégressifs gérés par le grossiste lui-même.

GET    /api/b2b/my-pricing/            produits du grossiste, prix de base et paliers
POST   /api/b2b/my-pricing/            premier prix d'un produit (prix de base) ou palier dégressif
PUT    /api/b2b/my-pricing/<id>/       modifier un prix de base ou un palier
DELETE /api/b2b/my-pricing/<id>/       supprimer un palier (ou retirer le produit de la vente en gros)

Le prix de base et la quantité minimale sont ouverts à tout grossiste. Les paliers (prix dégressifs) demandent
l'outil « bulk_discounts » du forfait ; un forfait qui ne l'a plus peut toujours supprimer ou désactiver ses paliers.
"""
from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from b2b.api.views import IsStoreManager
from b2b.models import B2BProductPricing
from b2b.services.tiers import bulk_discounts_active
from payments.plan_features import required_message
from products.models import Product
from stores.models import Store

MAX_ROWS_PER_PRODUCT = 5  # prix de base + 4 paliers


def _error(message, code=status.HTTP_400_BAD_REQUEST, field=None):
	error = {'code': code, 'message': message}
	if field:
		error['field'] = field
	return Response({'success': False, 'error': error}, status=code)


def _wholesaler_store(user):
	store = Store.objects.filter(manager=user, is_active=True).first()
	if store is None:
		return None, _error('Aucun magasin actif trouvé pour votre compte', status.HTTP_404_NOT_FOUND)
	if not store.is_b2b:
		return None, _error('Les prix de gros sont réservés aux grossistes.', status.HTTP_403_FORBIDDEN)
	return store, None


def _bulk_refusal(store):
	return _error(required_message('bulk_discounts', store.get_current_plan()), status.HTTP_403_FORBIDDEN)


def _price(value):
	try:
		price = Decimal(str(value))
	except (InvalidOperation, TypeError, ValueError):
		return None
	if not price.is_finite() or price <= 0 or price >= Decimal('100000000'):
		return None
	return price.quantize(Decimal('0.01'))


def _quantity(value, default=None):
	if value in (None, ''):
		return default
	try:
		quantity = int(str(value))
	except (TypeError, ValueError):
		return None
	return quantity if 1 <= quantity <= 1000000 else None


def _check_sequence(rows):
	"""Du plus petit au plus grand seuil, le prix doit baisser : sinon ce n'est pas un prix dégressif."""
	ordered = sorted(rows, key=lambda row: row[0])
	for (low_qty, low_price), (high_qty, high_price) in zip(ordered, ordered[1:]):
		if high_price >= low_price:
			return (f"Un palier doit coûter moins cher que le précédent : dès {high_qty} unités, le prix doit être "
					f"inférieur à celui de {low_qty} unités.")
	return ''


def _serialize_product(product, rows, bulk):
	rows = sorted(rows, key=lambda row: row.min_quantity)
	base = rows[0] if rows else None

	def payload(row):
		saving = 0
		if base is not None and row.id != base.id and base.b2b_price > 0 and row.b2b_price < base.b2b_price:
			saving = int(((base.b2b_price - row.b2b_price) / base.b2b_price * 100).quantize(Decimal('1')))
		return {
			'id': row.id, 'b2b_price': float(row.b2b_price), 'min_quantity': row.min_quantity,
			'is_active': row.is_active, 'saving_percent': saving,
		}

	return {
		'id': product.id,
		'name': product.name,
		'price': float(product.price),
		'stock': product.stock,
		'image': product.image.url if getattr(product, 'image', None) else None,
		'base': payload(base) if base else None,
		'tiers': [payload(row) for row in rows[1:]],
		# Des paliers enregistrés ne valent que si le forfait les inclut : sinon c'est le prix de base qui s'applique.
		'tiers_applied': bool(bulk),
	}


class MyWholesalePricingView(APIView):
	permission_classes = [IsAuthenticated, IsStoreManager]

	def get(self, request):
		store, error = _wholesaler_store(request.user)
		if error:
			return error
		bulk = bulk_discounts_active(store)
		products = list(Product.objects.filter(store=store, is_available=True).order_by('name'))
		search = (request.query_params.get('search') or '').strip()
		if search:
			products = [p for p in products if search.lower() in p.name.lower()]
		by_product = {}
		for row in B2BProductPricing.objects.filter(b2b_store=store):
			by_product.setdefault(row.product_id, []).append(row)
		return Response({
			'success': True,
			'data': {
				'bulk_discounts': bulk,
				'bulk_discounts_message': '' if bulk else required_message('bulk_discounts', store.get_current_plan()),
				'max_rows_per_product': MAX_ROWS_PER_PRODUCT,
				'products': [_serialize_product(p, by_product.get(p.id, []), bulk) for p in products],
			},
		})

	def post(self, request):
		store, error = _wholesaler_store(request.user)
		if error:
			return error
		product = Product.objects.filter(id=request.data.get('product_id'), store=store).first() \
			if str(request.data.get('product_id') or '').isdigit() else None
		if product is None:
			return _error('Produit introuvable dans votre boutique.', status.HTTP_404_NOT_FOUND, 'product_id')
		price = _price(request.data.get('b2b_price'))
		if price is None:
			return _error('Indiquez un prix de gros supérieur à 0.', field='b2b_price')
		quantity = _quantity(request.data.get('min_quantity'), default=1)
		if quantity is None:
			return _error('La quantité doit être un nombre entier supérieur ou égal à 1.', field='min_quantity')

		with transaction.atomic():
			rows = list(B2BProductPricing.objects.select_for_update().filter(product=product, b2b_store=store))
			is_tier = bool(rows)
			if is_tier and not bulk_discounts_active(store):
				return _bulk_refusal(store)
			if len(rows) >= MAX_ROWS_PER_PRODUCT:
				return _error(f'Un produit peut avoir au plus {MAX_ROWS_PER_PRODUCT - 1} paliers dégressifs.')
			if any(row.min_quantity == quantity for row in rows):
				return _error(f'Un prix existe déjà dès {quantity} unités pour ce produit.', field='min_quantity')
			if is_tier and quantity <= min(row.min_quantity for row in rows):
				return _error('Un palier commence après la quantité minimale du prix de base.', field='min_quantity')
			problem = _check_sequence([(row.min_quantity, row.b2b_price) for row in rows] + [(quantity, price)])
			if problem:
				return _error(problem, field='b2b_price')
			created = B2BProductPricing.objects.create(
				product=product, b2b_store=store, b2b_price=price, min_quantity=quantity, is_active=True)
		bulk = bulk_discounts_active(store)
		rows = list(B2BProductPricing.objects.filter(product=product, b2b_store=store))
		return Response({
			'success': True,
			'message': 'Palier ajouté' if is_tier else 'Prix de gros enregistré',
			'data': {'id': created.id, 'product': _serialize_product(product, rows, bulk)},
		}, status=status.HTTP_201_CREATED)


class MyWholesalePricingDetailView(APIView):
	permission_classes = [IsAuthenticated, IsStoreManager]

	def _row(self, store, pricing_id):
		return B2BProductPricing.objects.select_related('product').filter(id=pricing_id, b2b_store=store).first()

	def put(self, request, pricing_id):
		store, error = _wholesaler_store(request.user)
		if error:
			return error
		with transaction.atomic():
			row = self._row(store, pricing_id)
			if row is None:
				return _error('Prix introuvable.', status.HTTP_404_NOT_FOUND)
			rows = list(B2BProductPricing.objects.select_for_update().filter(product=row.product, b2b_store=store))
			is_base = row.min_quantity == min(r.min_quantity for r in rows)
			price = row.b2b_price
			quantity = row.min_quantity
			active = row.is_active
			if 'b2b_price' in request.data:
				price = _price(request.data.get('b2b_price'))
				if price is None:
					return _error('Indiquez un prix de gros supérieur à 0.', field='b2b_price')
			if 'min_quantity' in request.data:
				quantity = _quantity(request.data.get('min_quantity'))
				if quantity is None:
					return _error('La quantité doit être un nombre entier supérieur ou égal à 1.', field='min_quantity')
			if 'is_active' in request.data:
				active = bool(request.data.get('is_active'))
			# Modifier ou réactiver un palier demande l'outil ; le désactiver reste toujours possible.
			reactivating = active and not row.is_active
			editing = (price != row.b2b_price) or (quantity != row.min_quantity)
			if not is_base and (editing or reactivating) and not bulk_discounts_active(store):
				return _bulk_refusal(store)
			others = [r for r in rows if r.id != row.id]
			if any(r.min_quantity == quantity for r in others):
				return _error(f'Un prix existe déjà dès {quantity} unités pour ce produit.', field='min_quantity')
			if is_base and others and quantity >= min(r.min_quantity for r in others):
				return _error('La quantité minimale doit rester inférieure à celle du premier palier.', field='min_quantity')
			if not is_base and quantity <= min(r.min_quantity for r in others):
				return _error('Un palier commence après la quantité minimale du prix de base.', field='min_quantity')
			if is_base and not active:
				return _error('Le prix de base ne peut pas être désactivé : retirez le produit de la vente en gros.')
			problem = _check_sequence([(r.min_quantity, r.b2b_price) for r in others] + [(quantity, price)])
			if problem:
				return _error(problem, field='b2b_price')
			row.b2b_price, row.min_quantity, row.is_active = price, quantity, active
			row.save()
		bulk = bulk_discounts_active(store)
		rows = list(B2BProductPricing.objects.filter(product=row.product, b2b_store=store))
		return Response({'success': True, 'message': 'Prix mis à jour', 'data': {'product': _serialize_product(row.product, rows, bulk)}})

	def delete(self, request, pricing_id):
		store, error = _wholesaler_store(request.user)
		if error:
			return error
		with transaction.atomic():
			row = self._row(store, pricing_id)
			if row is None:
				return _error('Prix introuvable.', status.HTTP_404_NOT_FOUND)
			rows = list(B2BProductPricing.objects.select_for_update().filter(product=row.product, b2b_store=store))
			is_base = row.min_quantity == min(r.min_quantity for r in rows)
			if is_base:
				# Sans prix de base, les paliers n'ont plus de sens : le produit sort de la vente en gros.
				B2BProductPricing.objects.filter(product=row.product, b2b_store=store).delete()
				message = 'Produit retiré de la vente en gros'
			else:
				row.delete()
				message = 'Palier supprimé'
		bulk = bulk_discounts_active(store)
		rows = list(B2BProductPricing.objects.filter(product=row.product, b2b_store=store))
		return Response({'success': True, 'message': message, 'data': {'product': _serialize_product(row.product, rows, bulk)}})
