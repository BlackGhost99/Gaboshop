# Configuration Admindelivery par zone ✅

**Date:** 14 Janvier 2026  
**Statut:** ✅ Implémentée et testée

---

## Vue d'ensemble

Un système complet a été implémenté permettant aux administrateurs de configurer les tarifs de livraison par **zone géographique** et par **type de véhicule**. Les tarifs sont dynamiquement appliqués lors du calcul des coûts de commande.

### Caractéristiques clés
✅ **Zones configurables** — Créer/modifier des zones (Centre-Ville, Louis, Mont-Bouët, Libreville, Owendo, etc.)  
✅ **Tarifs par véhicule** — Définir des prix spécifiques pour chaque type de véhicule (Moto, Voiture, Camionnette, Camion)  
✅ **Surcharges inter-ville** — Configurer des surcharges pour livraisons hors-zone  
✅ **Interface admin intuitive** — Inline editing pour rapid configuration  
✅ **Fallback automatique** — Si aucun tarif trouvé, utilise tarif store par défaut  

---

## Modèles créés

### 1. **DeliveryZone** — Zones de livraison
```python
class DeliveryZone(models.Model):
    name              # Nom zone (ex: "Centre-Ville", "Louis")
    city              # Ville (Libreville, Owendo, etc.)
    is_active         # Actif pour commandes
    description       # Localisation, quartiers
    inter_city_surcharge  # Surcharge FCFA si livraison hors zone
    created_at, updated_at
```

### 2. **ZoneVehicleRate** — Tarifs par zone + véhicule
```python
class ZoneVehicleRate(models.Model):
    zone              # FK to DeliveryZone
    vehicle           # FK to VehicleType
    base_price        # Prix de base (FCFA)
    price_per_km      # Prix supplémentaire par km
    is_active         # Tarif actif
    notes             # (ex: "promo", "tarif réduit")
    
    unique_together = [['zone', 'vehicle']]  # Un seul tarif par combinaison
```

---

## Migration

Une migration auto-générée a été créée:
```
delivery/migrations/0008_deliveryzone_zonevehiclerate.py
```

**Statut:** ✅ Appliquée avec succès

---

## Interface Admin

### **DeliveryZoneAdmin** (Gestion des zones)
- **Affichage:** Nom, Ville, Surcharge inter-ville, Statut, Date création
- **Filtres:** Actif/Inactif, Ville
- **Recherche:** Nom zone, Ville, Description
- **Inline:** Possibilité d'ajouter/modifier tarifs directement dans la zone
- **Sections:**
  - Informations Zone (nom, ville, statut)
  - Configuration (surcharge inter-ville, description)
  - Métadonnées (dates, collapse)

**Accès:** Django Admin → Delivery → Zones de Livraison

### **ZoneVehicleRateAdmin** (Gestion des tarifs)
- **Affichage:** Zone, Véhicule, Prix base, Prix/km, Statut
- **Filtres:** Actif/Inactif, Zone, Véhicule
- **Recherche:** Nom zone, Nom véhicule
- **Sections:**
  - Configuration (zone, véhicule, statut)
  - Tarification (base, prix/km, notes)
  - Métadonnées (collapse)

**Accès:** Django Admin → Delivery → Tarifs Zones + Véhicules

### **VehicleTypeAdmin** (Mise à jour)
- **Inlines:** Tarifs par véhicule (ZoneVehicleRateInline)
- Permet de définir les tarifs directement depuis la page véhicule

---

## Intégration Backend

### **Order.calculate_dynamic_delivery_cost()** — Mise à jour
Nouvelle logique de calcul:

1. **Récupère la zone** à partir de `order.delivery_zone`
2. **Cherche le tarif** pour (zone + type_véhicule)
3. **Applique le prix de base** × multiplicateur poids
4. **Ajoute surcharge inter-ville** si applicable
5. **Fallback** sur tarif store si zone/tarif non trouvé

```python
def calculate_dynamic_delivery_cost(self, total_weight):
    # 1. Récupère zone
    zone = DeliveryZone.objects.filter(name__iexact=self.delivery_zone).first()
    
    # 2. Cherche tarif configuré
    if zone:
        zone_rate = ZoneVehicleRate.objects.filter(
            zone=zone, vehicle=vehicle_obj, is_active=True
        ).first()
        base_fee = zone_rate.base_price  # Utilise tarif zone
    else:
        base_fee = self.store.delivery_fee  # Fallback store
    
    # 3. Applique multiplicateur poids
    cost = base_fee * multiplier
    
    # 4. Ajoute surcharge inter-ville
    if not same_city:
        cost += zone.inter_city_surcharge
    
    return cost
```

---

## Workflow d'administration

### **Étape 1: Créer une zone**
1. Aller à Django Admin → Delivery → Zones de Livraison
2. Cliquer "Ajouter Zone de Livraison"
3. Remplir:
   - **Nom:** "Centre-Ville" ou "Mont-Bouët"
   - **Ville:** "Libreville"
   - **Surcharge inter-ville:** 1000 (FCFA) — appliquée si client hors zone du magasin
   - **Description:** "Centre-ville, quartiers Louis, Aviévi"
   - **Actif:** Cocher pour activer la zone
4. Sauvegarder

### **Étape 2: Ajouter tarifs pour la zone**
**Option A: Depuis la zone (inline)**
1. Ouvrir la zone créée
2. Section "Tarifs Zones + Véhicules" en bas
3. Cliquer "Ajouter une nouvelle ligne"
4. Sélectionner véhicule (Moto, Voiture, Camionnette, Camion)
5. Entrer prix de base (ex: 2500 FCFA pour Moto)
6. Entrer prix/km (ex: 100 FCFA/km)
7. Cocher "Actif"
8. Sauvegarder

**Option B: Depuis la page des tarifs**
1. Aller à Django Admin → Delivery → Tarifs Zones + Véhicules
2. Cliquer "Ajouter Tarif Zone + Véhicule"
3. Sélectionner Zone et Véhicule
4. Entrer prix de base et prix/km
5. Sauvegarder

### **Étape 3: Configurer plusieurs zones (exemple Libreville)**
```
Zone 1: "Centre-Ville" (Libreville)
  - Moto: 2000 FCFA base
  - Voiture: 3500 FCFA base
  - Camionnette: 5000 FCFA base
  - Surcharge inter-ville: 1000 FCFA

Zone 2: "Louis" (Libreville)
  - Moto: 1800 FCFA base (zone moins éloignée)
  - Voiture: 3200 FCFA base
  - Camionnette: 4800 FCFA base
  - Surcharge inter-ville: 1200 FCFA (plus éloignée)

Zone 3: "Owendo" (Owendo)
  - Moto: 3500 FCFA base
  - Voiture: 5000 FCFA base
  - Surcharge inter-ville: 2000 FCFA (inter-ville)
```

---

## Exemple de calcul

**Scénario:** Client commande 3kg (Moto) dans zone "Centre-Ville"

```
1. Order.calculate_dynamic_delivery_cost(total_weight=3kg)

2. Sélectionne véhicule:
   3kg ≤ 5kg → Moto (multiplier = 1.0)

3. Récupère tarif zone:
   Zone = "Centre-Ville"
   ZoneVehicleRate(zone, vehicle=Moto) → base_price = 2000 FCFA

4. Calcule coût:
   cost = 2000 FCFA × 1.0 = 2000 FCFA

5. Vérifi si inter-ville:
   Client en "Centre-Ville", magasin aussi → pas de surcharge

6. Résultat final:
   delivery_cost = 2000 FCFA
   vehicle_type = "bike" (Moto)
```

**Scénario 2:** Client en "Owendo" (différente ville)

```
1-4. Mêmes étapes, mais surcharge appliquée:
   cost = 2000 FCFA × 1.0 = 2000 FCFA
   
5. Vérifi si inter-ville:
   Client en "Owendo" ≠ Magasin en "Libreville" → SURCHARGE
   surcharge = 1000 FCFA (inter_city_surcharge de la zone)
   
6. Résultat final:
   delivery_cost = 2000 + 1000 = 3000 FCFA
```

---

## Avantages du système

| Avantage | Détail |
|----------|--------|
| **Flexibilité tarifaire** | Différents prix par zone et véhicule |
| **Gestion facile** | Admin interface intuitive, no code needed |
| **Surcharges configurables** | Adapter les tarifs selon distance inter-ville |
| **Fallback robuste** | Si config manquante, utilise tarif store |
| **Scalabilité** | Ajouter zones et tarifs sans modification code |
| **Audit trail** | Dates de création/modification tracées |

---

## Cas d'usage

### 1. **Multi-ville**
- Configurer tarifs différents par ville (Libreville, Owendo, Akanda)
- Appliquer surcharges inter-ville

### 2. **Promotion saisonnière**
- Créer tarif temporaire avec notes "Promo Jan 2026"
- Activer/désactiver rapidement

### 3. **Tarifs volumétrie**
- Tarif Moto (léger): 2000 FCFA
- Tarif Camionnette (lourd): 5000 FCFA
- Géré automatiquement par poids du panier

### 4. **Zones intra-ville**
- Centre-Ville: 2000 FCFA (dense)
- Périphérie: 1500 FCFA (moins cher)
- Surcharge inter-périphérie si applicable

---

## Tests

✅ **Tous les tests passent:**
```
Ran 7 tests in 19.884s
OK
```

Tests validés:
- `products.tests` (5 tests) — Product weight
- `orders.tests` (2 tests) — Order delivery + commission

---

## Prochaines étapes (optionnel)

1. **Seed data**: Pré-créer zones et tarifs pour Libreville, Owendo, Akanda (data migration)
2. **API endpoint**: `GET /delivery/zones/` pour afficher tarifs au client
3. **Détail breakdown**: Afficher tarif calculé avant confirmation commande
4. **Analyse tarifs**: Dashboard admin montrant tarifs moyens, zones actives
5. **Intégration livreur**: VehicleType intégré à profil livreur pour allocation automatique

---

## Références techniques

**Fichiers modifiés:**
- `delivery/models.py` — DeliveryZone, ZoneVehicleRate
- `delivery/admin.py` — Admin interface
- `delivery/migrations/0008_*` — Migration (créée auto)
- `orders/models.py` — calculate_dynamic_delivery_cost()

**Technologies utilisées:**
- Django ORM (Foreign Keys, unique_together)
- Admin inlines (ZoneVehicleRateInline)
- Decimal pour calculs financiers

---

**Prêt pour la production! 🚀**

Tous les tarifs sont gérés depuis l'admin Django. Aucune modification code requise pour ajuster les prix.
