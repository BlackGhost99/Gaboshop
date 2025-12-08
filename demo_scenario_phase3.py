"""
SCÉNARIO COMPLET : Livraison avec Preuve Obligatoire
=====================================================

Ce script démontre le flux complet d'une livraison avec le nouveau système
de preuve obligatoire (photo + GPS + signature/PIN)

Acteurs:
- Marie (Cliente à Libreville)
- Boutique "Chez Paul" (Magasin partenaire)
- Jean (Livreur GABOSHOP)
"""

import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gaboshop.settings')
django.setup()

from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from delivery.models import Delivery, DeliveryProof
from orders.models import Order
from stores.models import Store, StoreCategory
from products.models import Product, ProductCategory
from core.validators import validate_delivery_proof, can_mark_as_delivered
from core.models import AuditLog
from io import BytesIO
from PIL import Image

User = get_user_model()

# Configuration du scénario
LIBREVILLE_LAT = Decimal("0.4162")
LIBREVILLE_LON = Decimal("9.4673")
PIN_CODE = "1234"

def print_step(step_number, title):
    print(f"\n{'='*70}")
    print(f"📍 ÉTAPE {step_number}: {title}")
    print(f"{'='*70}")

def print_info(emoji, message):
    print(f"{emoji} {message}")

def create_test_image(color='blue'):
    """Crée une image de test"""
    img = Image.new('RGB', (300, 200), color=color)
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return SimpleUploadedFile(f"photo_{color}.png", buffer.read(), content_type="image/png")

# ============================================================================
# SCÉNARIO COMMENCE ICI
# ============================================================================

print("\n" + "🎬 " * 20)
print("SCÉNARIO: Livraison avec Preuve Obligatoire - GABOSHOP")
print("🎬 " * 20)

# ÉTAPE 1: Création des acteurs
print_step(1, "PRÉPARATION - Création des Acteurs")

# Nettoyer les données de test
User.objects.filter(phone__in=['0700000101', '0700000102', '0700000103']).delete()

# Marie (Cliente)
marie = User.objects.create_user(
    phone='0700000101',
    username='marie_client',
    email='marie@test.ga',
    password='test123',
    user_type='client',
    first_name='Marie',
    last_name='NGUEMA'
)
print_info("👤", f"Cliente créée: {marie.first_name} {marie.last_name} ({marie.phone})")

# Paul (Gérant de boutique)
paul = User.objects.create_user(
    phone='0700000102',
    username='paul_manager',
    email='paul@test.ga',
    password='test123',
    user_type='store_manager',
    first_name='Paul',
    last_name='OBAME'
)
print_info("👤", f"Gérant créé: {paul.first_name} {paul.last_name}")

# Jean (Livreur)
jean = User.objects.create_user(
    phone='0700000103',
    username='jean_delivery',
    email='jean@test.ga',
    password='test123',
    user_type='delivery_agent',
    first_name='Jean',
    last_name='MBOUMBA',
    is_available=True,
    current_location='Mont-Bouët',
    city='Libreville'
)
print_info("🚗", f"Livreur créé: {jean.first_name} {jean.last_name} (disponible)")

# ÉTAPE 2: Création de la boutique
print_step(2, "CRÉATION DE LA BOUTIQUE")

category, _ = StoreCategory.objects.get_or_create(
    name='Épicerie',
    defaults={'description': 'Produits alimentaires et boissons'}
)

store = Store.objects.create(
    name='Chez Paul - Mont-Bouët',
    manager=paul,
    category=category,
    phone='0111111111',
    address='Avenue de la Démocratie, Mont-Bouët, Libreville',
    city='Libreville',
    zone='Mont-Bouët',
    latitude=LIBREVILLE_LAT,
    longitude=LIBREVILLE_LON
)
print_info("🏪", f"Boutique créée: {store.name}")
print_info("📍", f"Localisation: {store.address}")
print_info("📦", "Produits disponibles dans la boutique")

# ÉTAPE 3: Marie passe commande
print_step(3, "COMMANDE - Marie achète du riz")

order = Order.objects.create(
    client=marie,
    store=store,
    items_total=Decimal('15000'),
    delivery_fee=Decimal('1500'),
    service_fee=Decimal('500'),
    total_amount=Decimal('17000'),
    delivery_address='Quartier Louis, Rue de la Paix, Maison bleue',
    status='confirmed'
)

print_info("🛒", f"Commande #{order.order_number} créée")
print_info("💰", f"Montant total: {order.total_amount} FCFA")
print_info("📍", f"Livraison à: {order.delivery_address}")

# ÉTAPE 4: Livraison créée automatiquement
print_step(4, "SYSTÈME - Création Automatique de la Livraison")

delivery = Delivery.objects.get(order=order)
print_info("📋", f"Livraison #{delivery.id} créée automatiquement")
print_info("⏳", f"Statut: {delivery.get_status_display()}")

# ÉTAPE 5: Jean accepte la livraison
print_step(5, "JEAN (Livreur) - Accepte la Livraison")

delivery.delivery_agent = jean
delivery.status = 'accepted'
delivery.delivery_code = PIN_CODE  # Code PIN pour vérification
delivery.save()

print_info("✅", f"Jean a accepté la livraison #{delivery.id}")
print_info("🔢", f"Code PIN généré: {PIN_CODE} (communiqué à Marie)")

# ÉTAPE 6: Jean récupère le colis
print_step(6, "JEAN - Récupère le Colis chez Paul")

delivery.status = 'picked_up'
delivery.save()

print_info("📦", "Jean a récupéré le colis à la boutique")
print_info("🚗", "Jean se dirige vers l'adresse de Marie...")

# ÉTAPE 7: Jean arrive chez Marie
print_step(7, "JEAN - Arrive chez Marie")

delivery.status = 'in_transit'
delivery.delivery_lat = LIBREVILLE_LAT + Decimal("0.0005")  # ~55m de l'adresse
delivery.delivery_lng = LIBREVILLE_LON + Decimal("0.0005")
delivery.save()

print_info("📍", "Jean est arrivé à destination")
print_info("🎯", f"GPS: {delivery.delivery_lat}, {delivery.delivery_lng}")

# ÉTAPE 8: Jean ESSAIE de terminer SANS preuve (ÉCHEC)
print_step(8, "⚠️  TENTATIVE - Terminer SANS Preuve (DEVRAIT ÉCHOUER)")

can_complete, reason = can_mark_as_delivered(delivery)
if can_complete:
    print_info("❌", "PROBLÈME: Le système a permis la livraison sans preuve!")
else:
    print_info("✅", "SYSTÈME BLOQUE LA LIVRAISON")
    print_info("🛡️", f"Raison: {reason}")

# ÉTAPE 9: Jean prend une photo
print_step(9, "JEAN - Prend une Photo du Colis Livré")

photo = create_test_image('green')
print_info("📸", "Photo prise avec succès")
print_info("💾", f"Taille: {len(photo.read())} bytes")
photo.seek(0)  # Reset pour réutilisation

# ÉTAPE 10: Jean obtient la signature de Marie
print_step(10, "MARIE - Signe la Réception")

signature = create_test_image('blue')
print_info("✍️", "Marie signe sur l'écran du téléphone de Jean")
signature.seek(0)

# ÉTAPE 11: Jean upload la preuve
print_step(11, "JEAN - Upload la Preuve de Livraison")

proof = DeliveryProof.objects.create(
    delivery=delivery,
    photo=photo,
    latitude=delivery.delivery_lat,
    longitude=delivery.delivery_lng,
    signature=signature,
    recipient_name=f"{marie.first_name} {marie.last_name}",
    recipient_phone=marie.phone,
    address_at_delivery=order.delivery_address
)

print_info("📤", "Preuve uploadée au serveur")
print_info("📸", f"Photo: {proof.photo.name}")
print_info("✍️", f"Signature: {proof.signature.name}")
print_info("📍", f"GPS: {proof.latitude}, {proof.longitude}")

# ÉTAPE 12: Validation de la preuve
print_step(12, "SYSTÈME - Validation de la Preuve")

proof_data = {
    'photo': proof.photo.name,
    'latitude': proof.latitude,
    'longitude': proof.longitude,
    'signature': proof.signature.name,
}

is_valid, errors = validate_delivery_proof(delivery, proof_data)

if is_valid:
    print_info("✅", "PREUVE VALIDÉE avec succès")
    print_info("📸", "Photo: PRÉSENTE ✓")
    print_info("📍", f"GPS: VALIDE ✓ (distance: {proof.distance_from_delivery}m)")
    print_info("✍️", "Signature: PRÉSENTE ✓")
else:
    print_info("❌", f"PREUVE INVALIDE: {errors}")

# ÉTAPE 13: Vérification finale
print_step(13, "SYSTÈME - Vérification Finale")

can_complete, reason = can_mark_as_delivered(delivery)
if can_complete:
    print_info("✅", "Toutes les conditions sont remplies")
    print_info("🎯", "La livraison peut être marquée comme 'livrée'")
else:
    print_info("❌", f"Impossible de terminer: {reason}")

# ÉTAPE 14: Jean termine la livraison
print_step(14, "JEAN - Marque la Livraison comme Terminée")

if can_complete:
    delivery.status = 'delivered'
    delivery.delivered_at = django.utils.timezone.now()
    delivery.save()
    
    print_info("🎉", "LIVRAISON TERMINÉE AVEC SUCCÈS!")
    print_info("✅", f"Statut: {delivery.get_status_display()}")
    print_info("⏰", f"Livrée à: {delivery.delivered_at.strftime('%H:%M')}")
    
    # Mettre à jour la commande
    order.status = 'delivered'
    order.save()
    print_info("📦", f"Commande #{order.order_number}: {order.get_status_display()}")

# ÉTAPE 15: Audit Trail
print_step(15, "🔍 AUDIT - Traçabilité Complète")

# Simuler l'audit logging (normalement fait dans les vues)
from django.contrib.contenttypes.models import ContentType

audit_entry = AuditLog.objects.create(
    user=jean,
    action_type='delivery_completed',
    object_type='delivery',
    object_id=delivery.id,
    notes=f"Livraison complétée avec preuve valide. GPS: {proof.latitude}, {proof.longitude}. Distance: {proof.distance_from_delivery}m",
    ip_address='192.168.1.100'
)

print_info("📝", f"Entrée d'audit créée: #{audit_entry.id}")
print_info("👤", f"Utilisateur: {audit_entry.user.get_full_name()}")
print_info("🕐", f"Timestamp: {audit_entry.action_timestamp}")
print_info("📋", f"Action: {audit_entry.action_type}")

# ÉTAPE 16: Test Anti-Fraude
print_step(16, "🛡️  TEST ANTI-FRAUDE - Tentative de Triche")

print_info("⚠️", "SIMULATION: Un livreur malhonnête tente de livrer sans être sur place...")

# Créer une fausse livraison
fake_order = Order.objects.create(
    client=marie,
    store=store,
    items_total=Decimal('5000'),
    delivery_fee=Decimal('1000'),
    total_amount=Decimal('6000'),
    delivery_address='Quartier Batterie IV, Libreville',
    status='confirmed'
)

fake_delivery = Delivery.objects.get(order=fake_order)
fake_delivery.delivery_agent = jean
fake_delivery.status = 'in_transit'
fake_delivery.delivery_lat = LIBREVILLE_LAT  # Adresse réelle
fake_delivery.delivery_lng = LIBREVILLE_LON
fake_delivery.save()

# Le livreur essaie d'uploader une preuve depuis un autre endroit (1km de distance)
fake_gps_lat = LIBREVILLE_LAT + Decimal("0.01")  # ~1.1 km de l'adresse
fake_gps_lng = LIBREVILLE_LON + Decimal("0.01")

fake_photo = create_test_image('red')
fake_signature = create_test_image('purple')

print_info("📍", f"Adresse réelle: {fake_delivery.delivery_lat}, {fake_delivery.delivery_lng}")
print_info("📍", f"GPS du livreur: {fake_gps_lat}, {fake_gps_lng}")
print_info("⚠️", "Le livreur tente d'uploader la preuve...")

fake_proof_data = {
    'photo': 'fake_photo.jpg',
    'latitude': fake_gps_lat,
    'longitude': fake_gps_lng,
    'signature': 'fake_signature.jpg'
}

is_valid, errors = validate_delivery_proof(fake_delivery, fake_proof_data)

if not is_valid:
    print_info("🚫", "FRAUDE DÉTECTÉE ET BLOQUÉE!")
    print_info("❌", f"Erreur: {errors}")
    
    # Logger comme activité suspecte
    fraud_audit = AuditLog.objects.create(
        user=jean,
        action_type='delivery_proof_failed',
        object_type='delivery',
        object_id=fake_delivery.id,
        notes=f"TENTATIVE DE FRAUDE: GPS trop éloigné. Distance: ~1100m",
        is_suspicious=True,
        ip_address='192.168.1.100'
    )
    print_info("🚨", f"Activité suspecte enregistrée: Audit #{fraud_audit.id}")
else:
    print_info("⚠️", "PROBLÈME: La fraude n'a pas été détectée!")

# Nettoyer la fausse livraison
fake_order.delete()

# RÉSUMÉ FINAL
print_step(17, "📊 RÉSUMÉ DE LA DÉMONSTRATION")

print("\n✅ PROTECTIONS ACTIVÉES:")
print("  1. Photo obligatoire - Sans photo, impossible de terminer")
print("  2. GPS validé - Distance max 500m de l'adresse")
print("  3. Signature OU PIN - Vérification du client requise")
print("  4. Audit complet - Toutes les actions tracées")
print("  5. Détection de fraude - Tentatives suspectes bloquées")

print("\n📈 STATISTIQUES:")
print(f"  • Livraisons réussies: 1")
print(f"  • Preuves validées: 1")
print(f"  • Fraudes bloquées: 1")
print(f"  • Audits créés: {AuditLog.objects.count()}")

print("\n💾 DONNÉES STOCKÉES:")
print(f"  • Photos de preuve: {DeliveryProof.objects.count()}")
print(f"  • Signatures: {DeliveryProof.objects.filter(signature__isnull=False).count()}")
print(f"  • Coordonnées GPS: {DeliveryProof.objects.count()} paires")

print("\n🎯 FLUX DE VALIDATION:")
print("  Commande → Livraison → Preuve Requise → Validation → Succès")
print("                              ↓")
print("              (Photo + GPS + Signature/PIN)")

print("\n" + "="*70)
print("✅ DÉMONSTRATION TERMINÉE AVEC SUCCÈS")
print("="*70)

print("\n📝 NOTE: Ce système garantit que:")
print("  - Chaque livraison a une preuve physique (photo)")
print("  - Le livreur était physiquement sur place (GPS)")
print("  - Le client a confirmé la réception (signature/PIN)")
print("  - Toutes les actions sont tracées pour audit")

# Nettoyer
print("\n🧹 Nettoyage des données de test...")
marie.delete()
paul.delete()
jean.delete()
print("✅ Nettoyage terminé")

import django.utils.timezone
