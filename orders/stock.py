"""Stock des articles : réservation à la commande, retour en stock à l'annulation.

Les mises à jour passent par des requêtes conditionnelles (F) : deux commandes simultanées
ne peuvent pas vendre la même dernière unité.
"""
from collections import Counter

from django.db.models import F
from rest_framework.exceptions import ValidationError

from products.models import Product


def reserve_stock(lines):
	"""Retire les quantités du stock. ``lines`` : liste de (produit, quantité).

	Refuse toute la commande si un article n'a plus assez de stock. À appeler dans une transaction.
	"""
	wanted = Counter()
	names = {}
	for product, quantity in lines:
		wanted[product.pk] += int(quantity)
		names[product.pk] = product.name
	changes = {}
	for product_id, quantity in wanted.items():
		updated = Product.objects.filter(pk=product_id, stock__gte=quantity).update(stock=F('stock') - quantity)
		if not updated:
			left = Product.objects.filter(pk=product_id).values_list('stock', flat=True).first() or 0
			raise ValidationError({'items': [f'Stock insuffisant pour « {names[product_id]} » : il reste {left} unité(s).']})
		after = Product.objects.filter(pk=product_id).values_list('stock', flat=True).first() or 0
		changes[product_id] = (after + quantity, after)
	# Alertes de stock faible (forfaits qui l'incluent), une fois la commande enregistrée.
	from products.stock_alerts import after_sale
	after_sale(changes)


def restock_order(order):
	"""Remet en stock les articles d'une commande annulée."""
	quantities = Counter()
	for item in order.items.all():
		quantities[item.product_id] += item.quantity
	for product_id, quantity in quantities.items():
		Product.objects.filter(pk=product_id).update(stock=F('stock') + quantity)
