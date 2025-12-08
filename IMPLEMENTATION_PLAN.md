# 📋 GABOSHOP - PLAN D'IMPLÉMENTATION COMPLET

**Date de création:** 4 décembre 2025  
**Version:** 1.0  
**Statut:** Architecture de référence

---

## 🌍 1. VISION DU PROJET

GABOSHOP est une plateforme d'achat en ligne qui connecte clients, magasins et agents de livraison (motos/scooters). Elle permet à la population de Libreville et du Gabon de commander facilement des produits de première nécessité (nourriture, vêtements, produits divers) depuis leur mobile, avec paiement sécurisé via Mobile Money (Airtel Money / Moov Money), et de se faire livrer à domicile rapidement.

### Objectifs principaux
- ✅ Faciliter l'achat en ligne pour une population à faible accessibilité aux commerces physiques
- ✅ Réduire les frictions pour les magasins : paiement garanti, gestion simple des commandes, aucun marchandage ni crédit
- ✅ Offrir aux livreurs indépendants une opportunité de revenus via une plateforme structurée
- ✅ Créer un système gagnant-gagnant pour tous les acteurs : client, magasin, livreur et plateforme

---

## 🔄 2. FONCTIONNEMENT DU SERVICE

1. Le client choisit un magasin et sélectionne des produits
2. Le client paye à l'avance via Mobile Money 
3. Le magasin reçoit la commande immédiatement avec confirmation de paiement
4. Un livreur disponible est automatiquement assigné pour récupérer la commande et la livrer à l'adresse du client
5. Le magasin reçoit le paiement net après déduction de la commission de la plateforme
6. Le client peut suivre sa commande en temps réel et confirmer la livraison

---

## 👥 3. ACTEURS ET RÔLES

| Acteur | Rôle clé |
|--------|----------|
| **Client** | Parcours catalogue, commande, paie, suit livraison |
| **Magasin** | Prépare commandes, reçoit paiement garanti, gère catalogue |
| **Livreur** | Reçoit assignation, effectue livraison, confirme livraison |
| **Admin GABOSHOP** | Supervise transactions, rapports, gestion des commissions |

---

## 🏗️ 4. ARCHITECTURE BACKEND (Django + DRF)

### 📦 Modules / Apps Django

#### 1️⃣ **users**
Gère tous les types d'utilisateurs + authentification.

**Modèles:**

```python
# User (CustomUser)
- téléphone (login principal)
- email
- rôle: CLIENT, GERANT, LIVREUR, ADMIN
- verified
- date_joined

# ClientProfile
- user (OneToOne)
- adresse_principale
- adresses_supplementaires (JSONField ou relation)

# GerantProfile
- user (OneToOne)
- magasin (OneToOne)
- date_debut_activite

# LivreurProfile
- user (OneToOne)
- disponible (bool)
- position_lat
- position_lng
- type_vehicule: moto / scooter / vélo
- cni
- permis
```

---

#### 2️⃣ **shops**
Tout ce qui concerne les magasins, catégories, produits.

**Modèles:**

```python
# Shop
- nom
- logo
- adresse
- latitude
- longitude
- gerant (OneToOne vers GerantProfile)
- statut: ouvert/fermé
- frais_service (DecimalField, optionnel)
- commission_rate (DecimalField, défaut 8%)

# Category
- nom
- magasin (ForeignKey)
- ordre (IntegerField, pour tri)

# Product
- nom
- prix
- stock
- image
- description
- magasin (ForeignKey)
- categorie (ForeignKey)
- actif (BooleanField)
- is_sponsored (BooleanField, default=False)
- sponsor_expiry (DateTimeField, null=True)
```

---

#### 3️⃣ **orders**
Commandes clients + panier + livraison.

**Modèles:**

```python
# Order
- client (ForeignKey)
- magasin (ForeignKey)
- total (DecimalField)
- statut: 
  * CREATED
  * PENDING_PAYMENT
  * PAID
  * ASSIGNED
  * ON_GOING
  * DELIVERED
  * CANCELLED
- adresse_livraison
- delivery_type: standard / express
- date_creation
- date_modification
- frais_livraison (DecimalField)
- frais_service (DecimalField)
- commission_plateforme (DecimalField)

# OrderItem
- commande (ForeignKey)
- produit (ForeignKey)
- prix_unitaire (DecimalField)
- quantite (IntegerField)
```

---

#### 4️⃣ **payments**
Paiements Mobile Money + carte bancaire.

**Modèles:**

```python
# Payment
- commande (OneToOne)
- montant (DecimalField)
- operateur: Airtel / Moov / CB
- reference_transaction
- statut:
  * PENDING
  * SUCCESS
  * FAILED
- date_creation
- date_validation
- webhook_data (JSONField)
```

**Webhook handlers:**
- Airtel Money webhook
- Moov Money webhook
- Carte bancaire callback

---

#### 5️⃣ **delivery**
Gestion des livreurs et assignation automatique.

**Modèles:**

```python
# DeliveryAssignment
- commande (OneToOne)
- livreur (ForeignKey)
- statut:
  * WAITING
  * ACCEPTED
  * IN_DELIVERY
  * DELIVERED
- heure_acceptation
- heure_livraison
- preuve_livraison (ImageField, optionnel)
- code_pin (CharField, pour validation)

# DeliveryFee
- zone (CharField)
- prix_standard (DecimalField)
- prix_express (DecimalField)
```

---

#### 6️⃣ **revenue** (nouveau module à créer)
Gestion des revenus et commissions.

**Modèles:**

```python
# Commission
- commande (OneToOne)
- taux_commission (DecimalField)
- montant_commission (DecimalField)
- montant_magasin (DecimalField)
- statut_paiement: PENDING / PAID
- date_paiement

# StoreSubscription
- store (ForeignKey)
- plan: STARTER / PRO / BUSINESS
- prix (DecimalField)
- date_debut
- date_fin
- actif (BooleanField)

# BannerAd
- image
- link
- store (ForeignKey)
- prix (DecimalField)
- date_debut
- date_fin
- actif (BooleanField)

# Cashback
- user (ForeignKey)
- montant (DecimalField)
- is_used (BooleanField)
- commande_origine (ForeignKey)
- date_creation
- date_utilisation
```

---

## 🚨 4.5. PROBLÉMATIQUES CRITIQUES & SOLUTIONS

### 📌 PROBLÈME 1 : Identifier la ville du client automatiquement
**Pourquoi c’est un problème ?**
GABOSHOP doit afficher uniquement les magasins de la ville du client. Un client à Libreville ne doit pas voir les magasins de Port-Gentil. Le numéro de téléphone seul ne suffit pas (+241 = Gabon entier).

**⭐ SOLUTION ADOPTÉE : Détection + Sélection de la ville**
1. **Détection automatique:** GPS (Mobile) ou IP (Web)
2. **Confirmation manuelle:** L'utilisateur confirme ou change sa ville (Libreville, Port-Gentil, Franceville, etc.)
3. **Filtrage:** Chaque produit, magasin et livreur est tagué avec une `VILLE`.

**Avantage:** Toujours les magasins disponibles autour du client, pas de commandes impossibles à livrer.

---

### 📌 PROBLÈME 2 : Les frais Mobile Money (Airtel / Moov)
**Pourquoi c’est un problème ?**
Les paiements Mobile Money ne sont pas gratuits. Si GABOSHOP paie ces frais (ex: 1500 FCFA sur 50.000 FCFA), la marge devient nulle ou négative.

**⭐ SOLUTION ADOPTÉE : Le client paie les frais MoMo**
Le calcul final est transparent :
`Total commande + Livraison + Frais MoMo + Frais service`

**Avantage:**
- GABOSHOP ne perd jamais d’argent
- Modèle standard des plateformes africaines (JumiaPay, Glovo, etc.)
- Rentable dès la première commande

---

## 🔗 5. RELATIONS ENTRE MODULES

```
GerantProfile (OneToOne) ↔ Shop (OneToOne)
Shop (OneToMany) → Category
Shop (OneToMany) → Product
Client (FK) → Order
Shop (FK) → Order
Order (OneToOne) ↔ Payment
Order (OneToOne) ↔ DeliveryAssignment
Order (OneToOne) ↔ Commission
```

---

## ⚙️ 6. WORKFLOW AUTOMATIQUE

### 🟩 Étape 1: Création de commande
**Endpoint:** `POST /api/orders/create/`

**Backend fait:**
1. Vérifie stock de chaque produit
2. Calcule sous-total panier
3. Calcule frais de livraison (selon zone + type)
4. Calcule frais de service (fixe ou %)
5. Calcule total final
6. Crée `Order` + `OrderItem`
7. Passe statut à `PENDING_PAYMENT`

---

### 🟨 Étape 2: Paiement Mobile Money
**Endpoint:** `POST /api/payments/initiate/`

**Backend fait:**
1. Crée `Payment` (statut `PENDING`)
2. Appelle API Mobile Money (Airtel/Moov)
3. Retourne URL de validation ou USSD

---

### 🟧 Étape 3: Webhook Mobile Money
**Opérateur → Backend**

**Traitement:**
1. Vérifie signature webhook
2. Met à jour `Payment.statut` → `SUCCESS`
3. Met à jour `Order.statut` → `PAID`
4. Crée `Commission` automatiquement
5. **Déclenche Celery Task:** assignation livreur
6. Envoie notification magasin (WhatsApp/SMS)

---

### 🟥 Étape 4: Assignation automatique livreur
**Celery Task:** `assign_nearest_available_delivery`

**Logique:**
1. Cherche livreurs avec:
   - `disponible = True`
   - Distance minimale du magasin (géolocalisation)
2. Trie par distance (algorithme haversine)
3. Crée `DeliveryAssignment`
4. Change `Order.statut` → `ASSIGNED`
5. Envoie notification livreur
6. Envoie notification client (livreur assigné)

---

### 🟦 Étape 5: Livraison en temps réel
**Dashboard livreur:**
- Liste livraisons assignées
- Acceptation/refus
- Changement statut:
  - `ACCEPTED` → `IN_DELIVERY` → `DELIVERED`
- Upload preuve livraison (photo)
- Code PIN validation

**Backend:**
- Signal `post_save` sur `DeliveryAssignment`
- Notifications client en temps réel

---

## 🖥️ 7. DASHBOARDS PAR RÔLE

### 👤 Dashboard Client
- Historique commandes
- Statut en temps réel
- Suivi livreur (GPS optionnel)
- Gestion profil
- Adresses enregistrées
- Cashback disponible

### 🏪 Dashboard Magasin/Gérant
- Liste produits + gestion stocks
- Commandes en attente/en cours
- Stats journalières ventes
- Gestion catalogue (catégories/produits)
- Modifier statut ouvert/fermé
- Rapport financier (commissions déduites)

### 🛵 Dashboard Livreur
- Commandes assignées
- Accepter/refuser livraison
- Changer statut livraison
- Gérer disponibilité
- Historique livraisons
- Revenus du jour/semaine

### 🛠️ Dashboard Admin
- Gestion utilisateurs (tous rôles)
- Gestion magasins (validation/suspension)
- Suivi transactions (paiements/commissions)
- Statistiques globales
- Supervision livreurs
- Gestion abonnements magasins
- Gestion publicités

---

## 💰 8. MODÈLE DE REVENUS

### ✅ À IMPLÉMENTER MAINTENANT (priorité 1)

#### 1. Commission par vente
- **Taux:** 8% par défaut (configurable par magasin)
- **Calcul:** Automatique dans `Order.calculate_commission()`
- **Table:** `Commission`

#### 2. Frais de livraison
- **Standard:** 2 000 FCFA
- **Express:** 3 500 FCFA
- **Coût livreur:** 1 200 FCFA
- **Marge plateforme:** 800 - 2 300 FCFA
- **Table:** `DeliveryFee`

#### 3. Frais de service
- **Montant:** 100 - 300 FCFA par commande
- **Champ:** `Order.frais_service`

---

### 🟨 À PRÉPARER MAINTENANT (structure seulement)

#### 4. Abonnements magasins

| Formule | Prix/mois | Avantages |
|---------|-----------|-----------|
| **Starter** | Gratuit | 20 produits max |
| **Pro** | 10 000 FCFA | Produits illimités, stats avancées |
| **Business** | 30 000 FCFA | Page personnalisée, support VIP |

**Table:** `StoreSubscription` (créer maintenant, logique plus tard)

#### 5. Produits sponsorisés
- **Prix:** 5 000 FCFA/semaine
- **Champ:** `Product.is_sponsored` + `sponsor_expiry`

#### 6. Livraison express
- **Champ:** `Order.delivery_type`
- **Supplément:** +1 500 FCFA pour la plateforme

#### 7. Publicités (bannières)
- **Prix:** 15 000 - 50 000 FCFA/mois
- **Table:** `BannerAd`

#### 8. Cashback
- **Montant:** 200 FCFA par commande (fidélisation)
- **Table:** `Cashback`

---

### 🟥 À AJOUTER PLUS TARD (phase 2)

9. **Statistiques anonymisées** (vente aux grands distributeurs)
10. **Partenariats Mobile Money** (cashback opérateur)
11. **Verticale restaurants** (menus, options, toppings)

---

## 🤖 9. AUTOMATISATIONS BACKEND (Celery)

### Tasks prioritaires

```python
# 1. Assignation automatique livreur
@shared_task
def assign_nearest_delivery(order_id):
    # Logique distance minimale + disponibilité
    pass

# 2. Vérification paiement (si webhook fail)
@shared_task
def check_payment_status(payment_id):
    pass

# 3. Notification WhatsApp/SMS
@shared_task
def send_order_notification(order_id, recipient_type):
    pass

# 4. Calcul commissions journalières
@periodic_task(run_every=crontab(hour=23, minute=59))
def calculate_daily_commissions():
    pass

# 5. Rapport quotidien ventes (email admin)
@periodic_task(run_every=crontab(hour=8, minute=0))
def send_daily_sales_report():
    pass

# 6. Expiration produits sponsorisés
@periodic_task(run_every=crontab(hour=0, minute=0))
def expire_sponsored_products():
    pass
```

---

## 🧱 10. STRUCTURE FINALE DU BACKEND

```
gaboshop/
├── users/
│   ├── models.py (User, ClientProfile, GerantProfile, LivreurProfile)
│   ├── serializers.py
│   ├── views.py
│   ├── permissions.py
│   └── urls.py
│
├── shops/
│   ├── models.py (Shop, Category, Product)
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
│
├── orders/
│   ├── models.py (Order, OrderItem)
│   ├── serializers.py
│   ├── views.py
│   ├── signals.py (post_save triggers)
│   └── urls.py
│
├── payments/
│   ├── models.py (Payment)
│   ├── services/
│   │   ├── airtel_money.py
│   │   └── moov_money.py
│   ├── webhooks.py
│   └── urls.py
│
├── delivery/
│   ├── models.py (DeliveryAssignment, DeliveryFee)
│   ├── tasks.py (Celery assignment logic)
│   ├── utils.py (géolocalisation distance)
│   └── urls.py
│
├── revenue/ (nouveau module)
│   ├── models.py (Commission, StoreSubscription, BannerAd, Cashback)
│   ├── serializers.py
│   ├── views.py
│   └── admin.py
│
├── notifications/
│   ├── services.py (WhatsApp, SMS)
│   └── tasks.py
│
├── core/
│   └── utils.py (helpers communs)
│
├── gaboshop/
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   ├── celery.py
│   ├── urls.py
│   └── wsgi.py
│
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
└── manage.py
```

---

## 📊 11. PRIORITÉS D'IMPLÉMENTATION

### ✅ PHASE 1 - MVP FONCTIONNEL (À FAIRE MAINTENANT)

**Backend:**
1. ✅ Modèles utilisateurs (User, profiles)
2. ✅ Modèles magasins (Shop, Category, Product)
3. ✅ Modèles commandes (Order, OrderItem)
4. ✅ Modèles paiements (Payment)
5. ✅ Modèles livraison (DeliveryAssignment, DeliveryFee)
6. ⚠️ Modèle revenue (Commission - à créer)
7. ⚠️ Logique calcul commissions (Order.calculate_commission)
8. ⚠️ Logique frais livraison (Order.calculate_delivery_fee)
9. ⚠️ Logique frais service (Order.calculate_service_fee)
10. ⚠️ Webhook handlers (Airtel Money, Moov Money)
11. ⚠️ Celery task assignation livreur
12. ⚠️ Notifications WhatsApp/SMS
13. ✅ Dashboards API (endpoints par rôle)
14. ⚠️ Permissions DRF strictes par rôle

**Frontend:**
15. ⚠️ Intégration API backend
16. ⚠️ Pages paiement Mobile Money
17. ⚠️ Suivi commande temps réel
18. ⚠️ Dashboard livreur mobile-friendly

---

### 🟨 PHASE 2 - REVENUS ADDITIONNELS

1. Créer modèles `StoreSubscription`, `BannerAd`, `Cashback`
2. Implémenter logique abonnements magasins
3. Interface admin gestion publicités
4. Système produits sponsorisés
5. Livraison express différenciée
6. Programme cashback client

---

### 🟥 PHASE 3 - SCALE & OPTIMISATION

1. Statistiques vendables (analytics avancés)
2. Partenariats Mobile Money
3. Verticale restaurants (menus dynamiques)
4. Optimisation géolocalisation livreurs
5. Machine Learning assignation intelligente
6. App mobile native (React Native)

---

## 🎯 12. POINTS FORTS DU SYSTÈME

✅ **Paiement prépayé et sécurisé** → aucune commande impayée  
✅ **Notification instantanée** → WhatsApp/SMS magasins et livreurs  
✅ **Gestion automatisée** → dashboards simples par rôle  
✅ **MVP lean** → pas besoin de flotte de livraison propre  
✅ **Multi-revenue streams** → 6 à 9 sources de revenus cumulées  
✅ **Scalable** → architecture modulaire Django  
✅ **Production-ready** → Docker, Celery, Redis, PostgreSQL

---

## 📝 13. PROCHAINES ACTIONS IMMÉDIATES

### Backend (priorité absolue)

1. **Créer module `revenue`**
   ```bash
   python manage.py startapp revenue
   ```

2. **Créer modèle `Commission`**
   - Lien OneToOne avec Order
   - Calcul automatique via signal post_save

3. **Ajouter champs à `Order`:**
   - `frais_livraison`
   - `frais_service`
   - `commission_plateforme`
   - `delivery_type` (standard/express)

4. **Créer méthodes de calcul:**
   ```python
   def calculate_delivery_fee(self):
       # Logique selon zone + type
   
   def calculate_service_fee(self):
       # 100-300 FCFA
   
   def calculate_commission(self):
       # 8% ou taux custom magasin
   
   def calculate_total(self):
       # Sous-total + frais
   ```

5. **Implémenter webhook handlers**
   - Airtel Money
   - Moov Money

6. **Créer Celery task assignation**
   ```python
   @shared_task
   def assign_nearest_delivery(order_id):
       # Algorithme distance + disponibilité
   ```

7. **Tester workflow complet:**
   - Commande → Paiement → Assignation → Livraison

---

### Frontend

1. **Intégrer paiement Mobile Money**
2. **Page suivi commande temps réel**
3. **Dashboard livreur responsive**
4. **Tests utilisateurs réels**

---

## 🚀 14. OBJECTIF FINAL

**Avoir un MVP fonctionnel permettant:**
- ✅ Parcourir magasins et produits
- ✅ Passer commande et payer
- ✅ Suivre les livraisons
- ✅ Notifier magasin et livreur
- ✅ Calculer automatiquement la commission et préparer le reversement
- ✅ Générer des revenus via 3 sources minimum (commission + livraison + service fee)

---

**Ce document est la référence complète pour l'implémentation de GABOSHOP.**  
Toutes les décisions techniques et business doivent s'aligner sur cette architecture.
