"""
Script de test pour vérifier que les routes B2B sont bien chargées
À exécuter avec: python manage.py shell < test_b2b_routes.py
"""

from django.urls import reverse, resolve
from django.core.urlresolvers import NoReverseMatch

# Liste des routes à tester
routes_to_test = [
    ('b2b:profile-create', {}),
    ('b2b:profile-activate', {'store_id': 1}),
    ('b2b:profile-deactivate', {'store_id': 1}),
    ('b2b:profile-detail', {'store_id': 1}),
    ('b2b:profile-update', {'store_id': 1}),
]

print("=" * 50)
print("Test des routes B2B Admin")
print("=" * 50)

for route_name, kwargs in routes_to_test:
    try:
        url = reverse(route_name, kwargs=kwargs)
        print(f"✓ {route_name:30} -> {url}")
    except NoReverseMatch as e:
        print(f"✗ {route_name:30} -> ERREUR: {e}")
    except Exception as e:
        print(f"✗ {route_name:30} -> ERREUR: {e}")

print("=" * 50)


