"""
Prix par palier de quantité (prix dégressifs) des grossistes.

Un produit vendu en gros a une ligne B2BProductPricing par palier : la ligne de plus petite quantité est le
prix de base (et la quantité minimale de commande), les lignes suivantes sont les paliers dégressifs.
Les paliers ne valent que si le forfait du grossiste inclut « bulk_discounts » : sans lui, le prix de base
s'applique, même si des paliers sont encore enregistrés (le serveur est la source de vérité du prix).
"""
from decimal import Decimal

from b2b.models import B2BProductPricing
from payments.plan_features import store_has


def bulk_discounts_active(wholesaler):
	"""Le forfait actuel du grossiste inclut-il les prix dégressifs ?"""
	return store_has(wholesaler, 'bulk_discounts')


def effective_tiers(rows, bulk_discounts):
	"""
	Paliers réellement appliqués, du plus petit au plus grand.

	rows: lignes B2BProductPricing d'un produit chez un grossiste (actives ou non).
	bulk_discounts: le forfait du grossiste inclut-il les prix dégressifs ?
	"""
	active = sorted((row for row in rows if row.is_active), key=lambda row: row.min_quantity)
	return active if bulk_discounts else active[:1]


def maximum_quantity(rows, bulk_discounts):
	"""Plafond de commande hérité des anciennes lignes (max_quantity du dernier palier), ou None."""
	active = sorted((row for row in rows if row.is_active), key=lambda row: row.min_quantity)
	if not active or (not bulk_discounts and len(active) > 1):
		return None
	return active[-1].max_quantity


def tier_for_quantity(tiers, quantity):
	"""Palier applicable à cette quantité : le plus haut dont le seuil est atteint (None sous la quantité minimale)."""
	chosen = None
	for tier in tiers:
		if tier.min_quantity <= quantity:
			chosen = tier
	return chosen


def tiers_payload(tiers):
	"""Paliers pour l'acheteur : seuil, prix unitaire et économie par rapport au prix de base."""
	if not tiers:
		return []
	base = Decimal(tiers[0].b2b_price)
	payload = []
	for tier in tiers:
		price = Decimal(tier.b2b_price)
		saving = 0
		if base > 0 and price < base:
			saving = int(((base - price) / base * 100).quantize(Decimal('1')))
		payload.append({
			'min_qty': tier.min_quantity,
			'price': float(price),
			'saving_percent': saving,
		})
	return payload


def pricing_rows(product, wholesaler_id):
	"""Lignes de prix d'un produit chez un grossiste (utilise le préchargement s'il existe)."""
	return [row for row in product.b2b_pricings.all() if row.b2b_store_id == int(wholesaler_id)]


def price_for_quantity(product, wholesaler, quantity, bulk=None):
	"""
	(prix unitaire, erreur) pour une quantité demandée, selon le forfait du grossiste.
	Le prix est toujours calculé ici : celui envoyé par l'acheteur n'est jamais cru.
	"""
	rows = list(B2BProductPricing.objects.filter(product=product, b2b_store=wholesaler, is_active=True))
	if bulk is None:
		bulk = bulk_discounts_active(wholesaler)
	tiers = effective_tiers(rows, bulk)
	if not tiers:
		return None, f"« {product.name} » n'a pas de prix de gros pour le moment."
	tier = tier_for_quantity(tiers, quantity)
	if tier is None:
		return None, f"Quantité minimum de {tiers[0].min_quantity} requise pour {product.name}."
	cap = maximum_quantity(rows, bulk)
	if cap and quantity > cap:
		return None, f"Quantité maximum de {cap} pour {product.name}."
	return tier.b2b_price, ''
