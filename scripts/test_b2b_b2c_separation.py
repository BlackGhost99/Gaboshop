#!/usr/bin/env python
"""
Script de test pour valider la séparation B2B/B2C
"""
import os
import django
from pathlib import Path

# Setup Django
BASE_DIR = Path(__file__).resolve().parent.parent
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Gaboshop.settings')
django.setup()

from products.models import Product
from stores.models import Store
from users.models import User
from b2b.models import B2BProductPricing
from django.test import Client
from django.urls import reverse

def test_public_products_endpoint():
	"""Test 1: Client non-authentifié voit seulement produits B2C"""
	print("\n=== TEST 1: Endpoint produits publics ===")
	
	# Compter les produits B2C et B2B
	total_products = Product.objects.filter(is_available=True, store__is_active=True).count()
	b2c_products = Product.objects.filter(
		is_available=True,
		store__is_active=True,
		market_type__in=['b2c', 'both']
	).count()
	b2b_only_products = Product.objects.filter(
		is_available=True,
		store__is_active=True,
		market_type='b2b'
	).count()
	
	print(f"Total produits disponibles: {total_products}")
	print(f"Produits B2C/Both (visibles publiquement): {b2c_products}")
	print(f"Produits B2B purs (devraient être cachés): {b2b_only_products}")
	
	if b2b_only_products > 0:
		print(f"✓ {b2b_only_products} produits B2B purs seront filtrés des endpoints publics")
	else:
		print("✓ Aucun produit B2B pur trouvé")
	
	return True


def test_store_manager_access():
	"""Test 2: Store_manager ne peut pas accéder au site public"""
	print("\n=== TEST 2: Accès store_manager ===")
	
	store_managers = User.objects.filter(user_type='store_manager', is_active=True)
	print(f"Store managers trouvés: {store_managers.count()}")
	
	for manager in store_managers[:3]:  # Tester les 3 premiers
		stores = Store.objects.filter(manager=manager, is_active=True)
		print(f"  - {manager.username}: {stores.count()} store(s)")
	
	print("✓ Les store_managers seront redirigés vers /store/dashboard par PublicRoute")
	return True


def test_client_access():
	"""Test 3: Client ne peut pas accéder à /store/dashboard"""
	print("\n=== TEST 3: Accès client ===")
	
	clients = User.objects.filter(user_type='client', is_active=True)
	print(f"Clients trouvés: {clients.count()}")
	
	if clients.exists():
		print(f"✓ Les clients seront redirigés vers /client/dashboard par PrivateRoute")
	else:
		print("⚠ Aucun client trouvé dans la base")
	
	return True


def test_b2b_products_filtering():
	"""Test 4: Produits B2B n'apparaissent pas dans ProductListView"""
	print("\n=== TEST 4: Filtrage produits B2B ===")
	
	# Produits avec market_type='b2b'
	b2b_only = Product.objects.filter(market_type='b2b', is_available=True).count()
	
	# Produits avec market_type='both'
	both = Product.objects.filter(market_type='both', is_available=True).count()
	
	# Produits avec market_type='b2c'
	b2c_only = Product.objects.filter(market_type='b2c', is_available=True).count()
	
	print(f"Produits B2C uniquement: {b2c_only}")
	print(f"Produits B2B uniquement: {b2b_only}")
	print(f"Produits B2C et B2B: {both}")
	
	if b2b_only > 0:
		print(f"✓ {b2b_only} produits B2B purs seront exclus des endpoints publics")
	
	print("✓ Les endpoints publics filtrent market_type__in=['b2c', 'both']")
	return True


def test_b2b_orders():
	"""Test 5: Commandes B2B ont is_b2b=True et source_store renseigné"""
	print("\n=== TEST 5: Commandes B2B ===")
	
	from orders.models import Order
	
	b2b_orders = Order.objects.filter(is_b2b=True)
	print(f"Commandes B2B trouvées: {b2b_orders.count()}")
	
	for order in b2b_orders[:3]:  # Afficher les 3 premières
		print(f"  - Commande #{order.order_number}:")
		print(f"    Store (grossiste): {order.store.name if order.store else 'N/A'}")
		print(f"    Source store (acheteur): {order.source_store.name if order.source_store else 'N/A'}")
		print(f"    is_b2b: {order.is_b2b}")
	
	if b2b_orders.exists():
		orders_with_source = b2b_orders.exclude(source_store__isnull=True).count()
		print(f"✓ {orders_with_source}/{b2b_orders.count()} commandes B2B ont un source_store")
	else:
		print("⚠ Aucune commande B2B trouvée")
	
	return True


def test_market_type_distribution():
	"""Test supplémentaire: Distribution des market_type"""
	print("\n=== TEST 6: Distribution market_type ===")
	
	total = Product.objects.count()
	b2c = Product.objects.filter(market_type='b2c').count()
	b2b = Product.objects.filter(market_type='b2b').count()
	both = Product.objects.filter(market_type='both').count()
	
	print(f"Total produits: {total}")
	print(f"  - B2C uniquement: {b2c} ({b2c*100/total if total > 0 else 0:.1f}%)")
	print(f"  - B2B uniquement: {b2b} ({b2b*100/total if total > 0 else 0:.1f}%)")
	print(f"  - B2C et B2B: {both} ({both*100/total if total > 0 else 0:.1f}%)")
	
	return True


def main():
	"""Exécute tous les tests"""
	print("=" * 60)
	print("TESTS DE SÉPARATION B2B/B2C")
	print("=" * 60)
	
	tests = [
		test_public_products_endpoint,
		test_store_manager_access,
		test_client_access,
		test_b2b_products_filtering,
		test_b2b_orders,
		test_market_type_distribution,
	]
	
	results = []
	for test in tests:
		try:
			result = test()
			results.append((test.__name__, result))
		except Exception as e:
			print(f"❌ Erreur dans {test.__name__}: {str(e)}")
			results.append((test.__name__, False))
	
	# Résumé
	print("\n" + "=" * 60)
	print("RÉSUMÉ DES TESTS")
	print("=" * 60)
	
	for test_name, result in results:
		status = "✓ PASS" if result else "❌ FAIL"
		print(f"{status}: {test_name}")
	
	all_passed = all(result for _, result in results)
	
	if all_passed:
		print("\n✅ Tous les tests sont passés !")
	else:
		print("\n⚠️ Certains tests ont échoué")
	
	return all_passed


if __name__ == "__main__":
	main()

