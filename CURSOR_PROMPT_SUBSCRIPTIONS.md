# 🎯 PROMPT CURSOR — ABONNEMENTS B2B & B2C (CONFIGURABLE BACKEND)

## 📋 Contexte projet

Nous développons **GABOSHOP**, une marketplace B2B/B2C.

**Objectif** : Implémenter un système d'abonnements B2B et B2C **entièrement piloté par configuration backend** (DB / settings), **sans logique codée en dur**.

Les valeurs (prix, pourcentages, frais, limites) doivent pouvoir **évoluer sans modifier le code**.

---

## 🔵 1. ABONNEMENTS B2B — BOUTIQUES CLIENTES (ACHETEUSES)

### 🎯 Finalité
Réduire les coûts variables des commandes B2B et générer un revenu fixe pour la plateforme.

### 📌 Plans (exemple — valeurs modifiables)

| Plan | Prix/mois | Commission B2B | Service Fee | Operator Fee | Livraison | Priorité |
|------|-----------|----------------|-------------|--------------|-----------|----------|
| **Free** | 0 FCFA | 10% | 1,000 FCFA | 3% | ✗ | Normale |
| **Pro** | 30,000 FCFA | 5% | 0 FCFA | 3% | ✓ | Haute |
| **Business** | 100,000 FCFA | 0% | 0 FCFA | 0% | ✓ | Maximale |

### ⚙️ Avantages à implémenter (tous configurables)

Pour chaque plan B2B Buyer, prévoir les **champs suivants** :

```python
# Champs financiers
commission_rate_b2b        # Decimal(5,4) ex: 0.1000 (10%), 0.0500 (5%), 0.0000 (0%)
service_fee_b2b            # Decimal(10,2) ex: 1000.00, 0.00
operator_fee_rate          # Decimal(5,4) ex: 0.0300 (3%), 0.0000 (0%)

# Champs fonctionnels
delivery_enabled           # Boolean - Accès à la livraison
priority_access_grossistes # Boolean - Voir grossistes en priorité
analytics_enabled          # Boolean - Accès aux statistiques
bulk_order_discount        # Boolean - Remises sur gros volumes

# Limites
max_monthly_orders         # Integer null=True - Limite commandes/mois (null = illimité)
max_suppliers              # Integer null=True - Nb max de grossistes (null = illimité)

# Tarification et affichage
monthly_price              # Decimal(10,2) - Prix mensuel
visible_benefits_label     # TextField - Texte affiché au frontend (JSON ou texte)
```

### 📌 Règles métier

1. **La boutique cliente paie le montant brut** (prix produits + frais)
2. **La commission est déduite avant payout du grossiste**
3. **Le grossiste ne paie jamais ces frais** (commission/service fee/operator fee)
4. **Le service fee s'applique uniquement si** `service_fee_b2b > 0`
5. **Calcul d'une commande B2B** :

```python
# Exemple : Commande de 100,000 FCFA avec plan Free
montant_produits = 100_000
commission = montant_produits * plan.commission_rate_b2b  # 10,000
service_fee = plan.service_fee_b2b                        # 1,000
operator_fee = montant_produits * plan.operator_fee_rate  # 3,000

total_client = montant_produits + service_fee             # 101,000 FCFA
payout_grossiste = montant_produits - commission - operator_fee  # 87,000 FCFA
revenue_plateforme = commission + service_fee + operator_fee     # 14,000 FCFA
```

---

## 🔵 2. ABONNEMENTS B2B — GROSSISTES (VENDEURS)

### 🎯 Finalité
Inciter les grossistes à utiliser la plateforme comme canal principal.

### 📌 Plans (exemple — valeurs modifiables)

| Plan | Prix/mois | Produits | Payout Delay | Badge | Analytics | Support |
|------|-----------|----------|--------------|-------|-----------|---------|
| **Free** | 0 FCFA | 50 | 30 jours | ✗ | ✗ | Basic |
| **Pro** | 25,000 FCFA | 500 | 7 jours | ✓ | ✓ | Priority |
| **Business** | 50,000 FCFA | Illimité | 2 jours | ✓ | ✓ | VIP 24/7 |

### ⚙️ Avantages configurables par plan grossiste

```python
# Visibilité et marketing
listing_priority           # Integer - Ordre d'affichage (0-10, plus élevé = prioritaire)
verified_badge             # Boolean - Badge "Grossiste Vérifié"
featured_in_catalog        # Boolean - Mis en avant dans les catalogues
catalog_boost_multiplier   # Decimal(5,2) - Multiplicateur de visibilité (1.0-5.0)

# Gestion financière
payout_delay_days          # Integer - Délai avant payout (ex: 30, 7, 2)
early_payout_enabled       # Boolean - Peut demander payout anticipé

# Limites fonctionnelles
max_products               # Integer null=True - Nb max produits B2B (null = illimité)
max_categories             # Integer null=True - Nb max catégories (null = illimité)
max_b2c_buyers             # Integer null=True - Nb max clients B2C (null = illimité)

# Outils et fonctionnalités
analytics_enabled          # Boolean - Accès analytics avancés
export_orders_enabled      # Boolean - Export Excel/CSV
api_access_enabled         # Boolean - Accès API REST
promo_tools_enabled        # Boolean - Créer promotions
bulk_pricing_enabled       # Boolean - Prix dégressifs par quantité

# Support
support_level              # CharField choices: 'basic', 'priority', 'vip'
dedicated_account_manager  # Boolean - Manager dédié

# Tarification
monthly_price              # Decimal(10,2)
visible_benefits_label     # TextField - Avantages affichés
```

### 📌 Règles métier

1. **Le grossiste ne paie JAMAIS de commission par commande**
2. **L'abonnement agit uniquement sur** :
   - Visibilité dans les catalogues
   - Outils de gestion
   - Rapidité de paiement (payout delay)
   - Limites fonctionnelles (produits, catégories)
3. **Revenue du grossiste** = Prix commande - (commission + operator fee du buyer)
4. **Pas de frais cachés** : Le grossiste sait exactement ce qu'il reçoit

---

## 🟢 3. ABONNEMENTS B2C — BOUTIQUES (VENTE AU CLIENT FINAL)

### 🎯 Finalité
Monétiser la visibilité et les outils, **sans impacter le client final**.

### 📌 Plans (exemple — valeurs modifiables)

| Plan | Prix/mois | Produits | Visibilité | Promo | Stats | Commission |
|------|-----------|----------|------------|-------|-------|------------|
| **Free** | 0 FCFA | 100 | Normale | ✗ | ✗ | 100% |
| **Pro** | 15,000 FCFA | 1,000 | Haute | ✓ | ✓ | 50% |
| **Business** | 40,000 FCFA | Illimité | Maximale | ✓ | ✓ | 0% |

### ⚙️ Avantages configurables par plan B2C

```python
# Visibilité et ranking
visibility_score           # Integer - Poids d'affichage (0-100)
homepage_featured          # Boolean - Affiché sur la page d'accueil
search_boost_multiplier    # Decimal(5,2) - Boost dans les recherches (1.0-5.0)
category_priority          # Boolean - Priorité dans sa catégorie

# Limites fonctionnelles
max_products               # Integer null=True - Nb max produits (null = illimité)
max_product_images         # Integer - Images par produit (ex: 3, 10, 50)
max_monthly_sales          # Integer null=True - Volume ventes/mois (null = illimité)

# Outils marketing
promo_tools_enabled        # Boolean - Créer promotions/réductions
banner_ads_enabled         # Boolean - Bannières publicitaires
email_campaigns_enabled    # Boolean - Campagnes email clients
loyalty_program_enabled    # Boolean - Programme de fidélité

# Analytics et reporting
stats_enabled              # Boolean - Statistiques de base
advanced_analytics_enabled # Boolean - Analytics avancés (conversion, etc.)
export_reports_enabled     # Boolean - Export rapports

# Support et formation
support_level              # CharField choices: 'basic', 'priority', 'vip'
training_included          # Boolean - Formation à la plateforme

# Commissions (multiplicateur sur taux de base)
b2c_commission_multiplier  # Decimal(5,4) ex: 1.0000 (Free), 0.5000 (Pro), 0.0000 (Business)
# Appliqué sur commission_rate de la catégorie produit
# Commission finale = commission_categorie * multiplier

# Tarification
monthly_price              # Decimal(10,2)
visible_benefits_label     # TextField
```

### 📌 Règles métier

1. **Les clients finaux ne souscrivent jamais** (abonnements réservés aux boutiques)
2. **Les frais de service client (500 FCFA) sont indépendants du plan**
3. **La commission B2C varie par produit** :
   - Alimentaire = 0% (toujours gratuit)
   - Autres catégories = `CategoryCommission.rate * plan.b2c_commission_multiplier`
4. **Calcul commission B2C** :

```python
# Exemple : Vêtement à 20,000 FCFA, commission catégorie = 8%
base_rate = 0.08  # Commission catégorie
multiplier = plan.b2c_commission_multiplier  # 1.0 (Free), 0.5 (Pro), 0.0 (Business)

commission_finale = 20_000 * base_rate * multiplier
# Free: 20k * 0.08 * 1.0 = 1,600 FCFA
# Pro: 20k * 0.08 * 0.5 = 800 FCFA
# Business: 20k * 0.08 * 0.0 = 0 FCFA
```

---

## 🧱 4. MODÉLISATION ATTENDUE (SANS CODE MÉTIER DUR)

### Proposer une structure backend permettant :

#### Table principale : `SubscriptionPlan`

```python
class SubscriptionPlan(models.Model):
    # Identification
    name = CharField(max_length=200)
    slug = SlugField(unique=True)
    scope = CharField(choices=[
        ('b2b_buyer', 'B2B - Boutique Cliente'),
        ('b2b_wholesaler', 'B2B - Grossiste'),
        ('b2c_store', 'B2C - Boutique'),
    ])
    
    # Tarification
    monthly_price = DecimalField(max_digits=10, decimal_places=2, default=0)
    yearly_price = DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Métadonnées
    description = TextField(blank=True)
    tagline = CharField(max_length=200, blank=True)
    is_active = BooleanField(default=True)
    is_popular = BooleanField(default=False)
    display_order = IntegerField(default=0)
    
    # Configuration JSON flexible
    # Tous les champs spécifiques au scope sont stockés ici
    features_config = JSONField(default=dict, blank=True)
    # Structure :
    # {
    #   "financial": {
    #     "commission_rate_b2b": 0.10,
    #     "service_fee_b2b": 1000.00,
    #     ...
    #   },
    #   "limits": {
    #     "max_products": 100,
    #     "max_monthly_orders": null,
    #     ...
    #   },
    #   "features": {
    #     "analytics_enabled": false,
    #     "api_access_enabled": false,
    #     ...
    #   },
    #   "visibility": {
    #     "listing_priority": 0,
    #     "search_boost_multiplier": 1.0,
    #     ...
    #   }
    # }
    
    # Avantages affichés au frontend
    visible_benefits = JSONField(default=list, blank=True)
    # [
    #   {"title": "Commission 10%", "category": "pricing", "highlight": true},
    #   {"title": "50 produits max", "category": "limits", "highlight": false},
    #   ...
    # ]
```

#### Table d'abonnement : `StoreSubscription`

```python
class StoreSubscription(models.Model):
    # Relations
    store = ForeignKey('stores.Store', on_delete=CASCADE, related_name='subscriptions')
    plan = ForeignKey(SubscriptionPlan, on_delete=PROTECT, related_name='subscriptions')
    scope = CharField(choices=same_as_above)  # Dupliqué pour performance
    
    # Dates et statut
    status = CharField(choices=[
        ('active', 'Actif'),
        ('cancelled', 'Annulé'),
        ('expired', 'Expiré'),
        ('pending_payment', 'En attente de paiement'),
    ], default='pending_payment')
    
    start_date = DateField(default=timezone.now)
    end_date = DateField(null=True, blank=True)
    valid_until = DateField(null=True, blank=True)  # Cache de end_date
    
    # Snapshot du plan au moment de la souscription
    plan_snapshot = JSONField(default=dict, blank=True)
    # Copie de features_config pour historique
    
    # Renouvellement
    auto_renew = BooleanField(default=True)
    
    # Métadonnées
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True)
```

#### Une table ou config avec distinction :

**Approche recommandée** : Table unique avec `scope` discriminant

**Avantages** :
- Flexibilité totale
- Ajout de nouveaux scopes sans migration
- Configuration JSON permet des champs spécifiques par scope
- Validation au niveau service, pas au niveau DB

---

## 🧠 5. SERVICES DE LECTURE (PAS DE LOGIQUE DUR)

### Service de calcul de commission B2B

```python
def calculate_b2b_order_costs(buyer_store, wholesaler_store, order_amount):
    """
    Calcule tous les frais d'une commande B2B
    Sans aucune constante codée en dur
    """
    # Récupérer l'abonnement B2B Buyer actif
    buyer_subscription = buyer_store.subscriptions.filter(
        scope='b2b_buyer',
        status='active'
    ).first()
    
    if not buyer_subscription:
        # Plan par défaut = Free
        buyer_plan = SubscriptionPlan.objects.get(
            scope='b2b_buyer',
            slug='b2b-free'
        )
    else:
        buyer_plan = buyer_subscription.plan
    
    # Lire la configuration
    config = buyer_plan.features_config.get('financial', {})
    
    commission_rate = Decimal(str(config.get('commission_rate_b2b', 0)))
    service_fee = Decimal(str(config.get('service_fee_b2b', 0)))
    operator_fee_rate = Decimal(str(config.get('operator_fee_rate', 0)))
    
    # Calculs
    commission = order_amount * commission_rate
    operator_fee = order_amount * operator_fee_rate
    
    return {
        'order_amount': order_amount,
        'commission': commission,
        'service_fee': service_fee,
        'operator_fee': operator_fee,
        'total_buyer': order_amount + service_fee,
        'payout_wholesaler': order_amount - commission - operator_fee,
        'platform_revenue': commission + service_fee + operator_fee,
    }
```

### Service de vérification de limites

```python
def can_perform_action(store, action_type, scope):
    """
    Vérifie si le store peut effectuer une action selon son plan
    """
    subscription = store.subscriptions.filter(
        scope=scope,
        status='active'
    ).first()
    
    if not subscription:
        # Plan Free par défaut
        plan = SubscriptionPlan.objects.get(scope=scope, slug=f'{scope}-free')
    else:
        plan = subscription.plan
    
    limits = plan.features_config.get('limits', {})
    
    if action_type == 'add_product':
        max_products = limits.get('max_products')
        if max_products is None:
            return True, "OK"
        
        current_count = store.products.filter(is_available=True).count()
        if current_count >= max_products:
            return False, f"Limite de {max_products} produits atteinte"
        return True, "OK"
    
    # Autres actions...
    return True, "OK"
```

### Service de calcul commission B2C

```python
def calculate_b2c_commission(store, product, sale_amount):
    """
    Calcule la commission B2C selon la catégorie et le plan du store
    """
    # Récupérer plan B2C du store
    subscription = store.subscriptions.filter(
        scope='b2c_store',
        status='active'
    ).first()
    
    if not subscription:
        plan = SubscriptionPlan.objects.get(scope='b2c_store', slug='b2c-free')
    else:
        plan = subscription.plan
    
    # Commission de base de la catégorie
    category_commission = CategoryCommission.objects.filter(
        category=product.category
    ).first()
    
    if not category_commission or category_commission.rate == 0:
        # Alimentaire = 0% toujours
        return Decimal('0')
    
    # Multiplicateur du plan
    config = plan.features_config.get('financial', {})
    multiplier = Decimal(str(config.get('b2c_commission_multiplier', 1.0)))
    
    # Calcul final
    commission = sale_amount * category_commission.rate * multiplier
    return commission
```

---

## 🧠 6. OBJECTIF FINAL

### ✅ Ce qui DOIT être possible :

1. **Activer / désactiver un avantage sans recoder**
   ```python
   plan.features_config['features']['analytics_enabled'] = True
   plan.save()
   ```

2. **Modifier un taux / prix sans déployer**
   ```python
   plan.features_config['financial']['commission_rate_b2b'] = 0.08
   plan.monthly_price = 35000
   plan.save()
   ```

3. **Ajouter un nouveau plan sans toucher à la logique métier**
   ```python
   SubscriptionPlan.objects.create(
       name="B2B Premium",
       scope="b2b_buyer",
       monthly_price=150000,
       features_config={
           "financial": {"commission_rate_b2b": 0.0, ...},
           "limits": {...},
           "features": {...}
       }
   )
   ```

4. **Le frontend ne fait qu'afficher les bénéfices exposés par l'API**
   ```json
   GET /api/v1/subscriptions/plans/?scope=b2b_buyer
   {
     "plans": [
       {
         "name": "B2B Free",
         "monthly_price": "0.00",
         "visible_benefits": [
           {"title": "Commission 10%", "highlight": true},
           {"title": "Service fee 1000 FCFA", "highlight": false}
         ]
       }
     ]
   }
   ```

---

## ✅ LIVRABLE ATTENDU DE CURSOR

### 1. Proposition de structure de données (models / config)
- ✅ Table `SubscriptionPlan` avec `features_config` JSON
- ✅ Table `StoreSubscription` avec `plan_snapshot`
- ✅ Distinction par `scope` (b2b_buyer / b2b_wholesaler / b2c_store)

### 2. Liste exhaustive des champs configurables par plan
- ✅ **B2B Buyer** : 8 champs financiers/fonctionnels
- ✅ **B2B Wholesaler** : 15 champs visibilité/outils/limites
- ✅ **B2C Store** : 17 champs visibilité/marketing/commissions

### 3. Exemple de lecture de configuration dans les services
- ✅ `calculate_b2b_order_costs()` - Sans constantes
- ✅ `can_perform_action()` - Lecture dynamique des limites
- ✅ `calculate_b2c_commission()` - Multiplicateur depuis config

### 4. Aucun calcul financier codé en dur
- ✅ Tous les taux lus depuis `features_config`
- ✅ Tous les prix/limites configurables
- ✅ Plans Free créés en DB, pas en code

---

## 🎨 EXEMPLE DE CONFIGURATION COMPLÈTE

### Plan B2B Buyer "Free"

```json
{
  "name": "B2B Free",
  "slug": "b2b-free",
  "scope": "b2b_buyer",
  "monthly_price": "0.00",
  "features_config": {
    "financial": {
      "commission_rate_b2b": 0.10,
      "service_fee_b2b": 1000.00,
      "operator_fee_rate": 0.03
    },
    "limits": {
      "max_monthly_orders": null,
      "max_suppliers": null
    },
    "features": {
      "delivery_enabled": false,
      "priority_access_grossistes": false,
      "analytics_enabled": false,
      "bulk_order_discount": false
    }
  },
  "visible_benefits": [
    {"title": "Commission 10%", "category": "pricing", "highlight": true},
    {"title": "Service fee 1,000 FCFA", "category": "pricing", "highlight": false},
    {"title": "Operator fee 3%", "category": "pricing", "highlight": false},
    {"title": "Commandes illimitées", "category": "limits", "highlight": false},
    {"title": "Interface simple", "category": "interface", "highlight": false}
  ]
}
```

---

👉 **Fin du prompt**

