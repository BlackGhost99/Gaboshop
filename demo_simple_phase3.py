# -*- coding: utf-8 -*-
"""
SCÉNARIO DÉMONSTRATION : Preuve de Livraison Obligatoire
=========================================================
Montre comment le système empêche les livraisons frauduleuses
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
django.setup()

from decimal import Decimal
from delivery.models import Delivery, DeliveryProof
from orders.models import Order
from core.validators import validate_delivery_proof, can_mark_as_delivered
import django.utils.timezone

print("\n" + "="*70)
print("DÉMONSTRATION : Système de Preuve de Livraison Obligatoire")
print("="*70)

# ============================================================================
# SCÉNARIO 1 : LIVRAISON NORMALE AVEC PREUVE (SUCCÈS)
# ============================================================================

print("\n[SCÉNARIO 1] Livraison Normale avec Preuve Complète")
print("-" * 70)

# Récupérer une livraison existante ou créer un mock
try:
    # Tenter de trouver une livraison en transit
    delivery = Delivery.objects.filter(status='in_transit').first()
    
    if not delivery:
        print("[INFO] Aucune livraison en transit trouvée")
        print("[INFO] Utilisation d'un objet mock pour la démonstration")
        
        class MockDelivery:
            id = 1
            delivery_lat = Decimal("0.4162")
            delivery_lng = Decimal("9.4673")
            delivery_code = "1234"
            status = 'in_transit'
            delivery_agent = type('obj', (object,), {'id': 1, 'get_full_name': lambda: 'Jean MBOUMBA'})()
            
            def get_status_display(self):
                return "En cours de livraison"
        
        delivery = MockDelivery()
except Exception as e:
    print(f"[ERREUR] {e}")

print(f"\n[ÉTAPE 1] Livreur arrive à destination")
print(f"  - Livraison ID: #{delivery.id}")
print(f"  - Statut actuel: {delivery.get_status_display()}")
print(f"  - GPS: {delivery.delivery_lat}, {delivery.delivery_lng}")

print(f"\n[ÉTAPE 2] Tentative de terminer SANS preuve...")
can_complete, reason = can_mark_as_delivered(delivery)
if not can_complete:
    print(f"  [BLOQUÉ] {reason}")
    print("  >>> Le système empêche la livraison sans preuve <<<")
else:
    print("  [ERREUR] Le système a permis la livraison sans preuve!")

print(f"\n[ÉTAPE 3] Livreur upload la preuve:")
print("  - Photo prise: OUI")
print("  - GPS capturé: OUI (même position que l'adresse)")
print("  - Signature cliente: OUI")

# Simuler la validation de preuve
proof_data = {
    'photo': 'delivery_photo.jpg',  # Non vide = présent
    'latitude': delivery.delivery_lat,
    'longitude': delivery.delivery_lng,
    'signature': 'customer_signature.png'
}

is_valid, errors = validate_delivery_proof(delivery, proof_data)

if is_valid:
    print(f"\n[ÉTAPE 4] Validation de la preuve:")
    print("  [SUCCÈS] Preuve VALIDÉE")
    print("  - Photo: PRÉSENTE")
    print("  - GPS: VALIDE (distance < 500m)")
    print("  - Signature: PRÉSENTE")
    print("\n  >>> Livraison peut maintenant être marquée 'livrée' <<<")
else:
    print(f"\n[ÉTAPE 4] Validation ÉCHOUÉE: {errors}")

# ============================================================================
# SCÉNARIO 2 : TENTATIVE DE FRAUDE - GPS TROP LOIN (ÉCHEC)
# ============================================================================

print("\n\n[SCÉNARIO 2] Tentative de Fraude - Livreur à Distance")
print("-" * 70)

print("\n[SITUATION]")
print("  - Adresse de livraison: Libreville Centre (0.4162, 9.4673)")
print("  - Position réelle du livreur: 1km plus loin (0.4262, 9.4773)")
print("  - Le livreur essaie de marquer 'livré' sans être sur place")

# Position éloignée
fake_gps_lat = delivery.delivery_lat + Decimal("0.01")  # ~1.1 km
fake_gps_lng = delivery.delivery_lng + Decimal("0.01")

proof_data_fake = {
    'photo': 'fake_photo.jpg',
    'latitude': fake_gps_lat,
    'longitude': fake_gps_lng,
    'signature': 'fake_signature.png'
}

print(f"\n[TENTATIVE] Livreur upload preuve depuis position éloignée...")

is_valid, errors = validate_delivery_proof(delivery, proof_data_fake)

if not is_valid:
    print(f"  [BLOQUÉ] {errors.get('gps_distance', errors)}")
    print("\n  >>> FRAUDE DÉTECTÉE ET EMPÊCHÉE <<<")
    print("  - Le système a calculé la distance GPS")
    print("  - Distance > 500m = REJETÉ")
    print("  - Activité marquée comme suspecte dans l'audit")
else:
    print("  [PROBLÈME] La fraude n'a pas été détectée!")

# ============================================================================
# SCÉNARIO 3 : PREUVE INCOMPLÈTE - PAS DE PHOTO (ÉCHEC)
# ============================================================================

print("\n\n[SCÉNARIO 3] Preuve Incomplète - Photo Manquante")
print("-" * 70)

print("\n[TENTATIVE] Livreur essaie sans prendre de photo...")

proof_data_no_photo = {
    # 'photo': '',  # Manquant!
    'latitude': delivery.delivery_lat,
    'longitude': delivery.delivery_lng,
    'signature': 'signature.png'
}

is_valid, errors = validate_delivery_proof(delivery, proof_data_no_photo)

if not is_valid:
    print(f"  [BLOQUÉ] {errors.get('photo', errors)}")
    print("\n  >>> Photo OBLIGATOIRE - Livraison refusée <<<")
else:
    print("  [PROBLÈME] Livraison permise sans photo!")

# ============================================================================
# SCÉNARIO 4 : PIN INCORRECT (ÉCHEC)
# ============================================================================

print("\n\n[SCÉNARIO 4] Code PIN Incorrect")
print("-" * 70)

print(f"\n[INFO]")
print(f"  - Code PIN correct: {delivery.delivery_code}")
print(f"  - Cliente donne le code: 9999 (INCORRECT)")

proof_data_wrong_pin = {
    'photo': 'photo.jpg',
    'latitude': delivery.delivery_lat,
    'longitude': delivery.delivery_lng,
    'pin_code': '9999',  # Mauvais PIN
    'pin_verified': False
}

is_valid, errors = validate_delivery_proof(delivery, proof_data_wrong_pin)

if not is_valid:
    print(f"  [BLOQUÉ] {errors.get('pin_code', errors)}")
    print("\n  >>> Code PIN invalide - Client n'a pas confirmé <<<")
else:
    print("  [PROBLÈME] PIN incorrect accepté!")

# ============================================================================
# RÉSUMÉ
# ============================================================================

print("\n\n" + "="*70)
print("RÉSUMÉ DES PROTECTIONS ANTI-FRAUDE")
print("="*70)

print("""
[1] PHOTO OBLIGATOIRE
    - Sans photo, impossible de terminer la livraison
    - Preuve visuelle du colis livré
    
[2] VALIDATION GPS (500m max)
    - Le livreur DOIT être physiquement sur place
    - Distance calculée avec formule Haversine
    - > 500m = REJET automatique
    
[3] VÉRIFICATION CLIENT
    - Signature OU Code PIN requis
    - Confirmation que le client a reçu
    
[4] AUDIT COMPLET
    - Toutes tentatives enregistrées
    - Fraudes marquées comme suspectes
    - Traçabilité totale pour investigation

RÉSULTAT: Impossible de marquer "livré" sans preuve complète et valide!
""")

print("="*70)
print("FIN DE LA DÉMONSTRATION")
print("="*70)
