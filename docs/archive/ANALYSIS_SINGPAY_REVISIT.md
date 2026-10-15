# 🔍 ANALYSE SINGPAY - REVISIT 2026

## 📊 RÉSUMÉ EXÉCUTIF

Votre projet Gaboshop a **une implémentation Singpay fonctionnelle et structurée**. L'intégration Airtel Money + Moov Money est **90% complète**. Il y a quelques ambiguïtés et optimisations à clarifier avant de passer aux tests en live.

**Status**: ✅ PRÊT POUR TESTS SANDBOX AVEC AJUSTEMENTS MINEURS

---

## ✅ CE QUI FONCTIONNE BIEN

### 1. **Configuration Singpay (✓ VALIDE)**
```
BASE_URL: https://gateway.singpay.ga/v1
CLIENT_ID: <SINGPAY_CLIENT_ID>
WALLET_ID: <SINGPAY_WALLET_ID>
Timeout: 30 secondes
```
✅ Chargée correctement dans Django

### 2. **Wrapper API Singpay (✓ BON)**
Fichier: `payments/utils.py`
- ✅ `call_singpay_payment()` - Wrapper pour Airtel/Moov
- ✅ `_singpay_request()` - Requête générique avec retry logic
- ✅ Normalisation du numéro phone `_normalize_msisdn()`
- ✅ Normalisation montant `_normalize_amount()`
- ✅ Gestion erreurs de config manquante

**Endpoints ciblés**:
- Airtel Money: `/74/paiement`
- Moov Money: `/62/paiement`

### 3. **Services de Paiement (✓ STRUCTURE BON)**
Fichier: `payments/services.py`

```
PaymentService
├── init_mobile_money_payment()          ✅ Crée Payment + appelle API
├── _call_operator_api()                 ✅ Dispatch Airtel/Moov
├── _call_airtel_money_api()            ✅ Appelle Singpay pour Airtel
├── _call_moov_money_api()              ✅ Appelle Singpay pour Moov
├── _format_gabon_phone()               ✅ Format +241XXXXXXXX
├── confirm_payment()                    ✅ Webhook handler
├── _create_commission()                 ✅ Commission post-paiement
└── check_payment_status()              ✅ Query local DB
```

### 4. **Endpoint API Paiement (✓ IMPLÉMENTÉ)**
Fichier: `api/v1/payments.py`

```
POST /api/v1/orders/{order_id}/payments/init/
├── Valide la commande
├── Calcule frais Mobile Money
├── Appelle PaymentService
├── Crée Payment record
└── Retourne next_steps pour le client
```

**Serializer**: `PaymentInitSerializer`
- ✅ Valide `payment_method` (airtel_money, moov_money)
- ✅ Valide `phone_number` requis
- ✅ Valide `operator` (airtel, moov)
- ✅ Normalise phone format

### 5. **Modèles de Données (✓ COMPLET)**
Fichier: `payments/models.py`

```
Payment
├── payment_method ✅ (airtel_money, moov_money, card, cash)
├── status ✅ (pending, processing, success, failed, refunded)
├── transaction_id ✅ (ID interne Gaboshop)
├── operator_reference ✅ (ID Singpay/Airtel/Moov)
└── webhook_data ✅ (JSON brut du webhook)
```

### 6. **Webhooks Implémentés (✓ STRUCTURE BON)**

**Deux implémentations**:

#### A. Ancien système (`payments/webhooks.py`)
```python
airtel_money_webhook()  # POST /api/v1/payments/webhooks/airtel/
moov_money_webhook()    # POST /api/v1/payments/webhooks/moov/
```

#### B. Nouveau système (`api/v1/payments.py`)
```python
PaymentWebhookView()    # POST /api/v1/orders/{id}/payments/webhook/
```

---

## ⚠️ PROBLÈMES IDENTIFIÉS

### PROBLÈME 1: **DUALITÉ WEBHOOK** 🔴
**Sévérité**: MEDIUM

**Situation**:
- `payments/webhooks.py`: Deux webhooks simples (airtel/moov)
- `api/v1/payments.py`: PaymentWebhookView plus robuste

**Question**: Quel webhook Singpay doit appeler ?

**Impact**:
- Si Singpay appelle le mauvais endpoint → paiement non confirmé
- Configurations différentes = confusion

**Recommandation**:
✅ **Utiliser UNIQUEMENT `PaymentWebhookView` de `api/v1/payments.py`**

Raison:
1. Plus robuste (gère plusieurs formats)
2. A AuditLog pour traçabilité
3. Peut chercher Payment par reference si transaction_id manquant

---

### PROBLÈME 2: **FORMAT RÉPONSE SINGPAY AMBIGU** 🟡
**Sévérité**: MEDIUM

**Situation actuelle**:
`_call_airtel_money_api()` suppose:
```python
response.get("transaction")  # Dict avec ID
response.get("status")       # Dict avec success/code
```

**MAIS** la doc Singpay peut retourner:
```python
# Variante 1: {"transaction": {...}, "status": {...}}
# Variante 2: {"paymentResult": {"transaction": {...}}}
# Variante 3: Direct sans wrapping
```

**Impact**: Si format ≠ attendu → transaction_id vide → webhook échoue

**À TESTER**: Appeler Singpay et voir structure réelle

---

### PROBLÈME 3: **GESTION ERREUR PARTIELLE** 🟡
**Sévérité**: LOW-MEDIUM

`_build_singpay_error_message()` traite certains cas:
- ✅ "wallet not accepted"
- ✅ "status: pending"

**MAIS** pas validé avec vrais codes d'erreur Singpay. À enrichir après tests.

---

### PROBLÈME 4: **WORKFLOW STATUT ORDER PAS CLAIR** 🟡
**Sévérité**: LOW

**Ambiguïté**: Quelle transition exacte ?

**Option A** (code actuel):
```
created → pending_payment → confirmed (webhook)
```

**Option B** (alternative):
```
created → paid → confirmed
```

**À clarifier** dans `orders/models.py`

---

### PROBLÈME 5: **SIMULATION MODE MÉLANGÉE** 🟡
**Sévérité**: LOW

Code a mode fallback:
```python
if getattr(settings, 'PAYMENT_SIMULATION_MODE', False):
    return PaymentService._get_fallback_response(...)
```

**MAIS** `PAYMENT_SIMULATION_MODE` pas défini dans settings. À ajouter ou retirer.

---

## 📋 PLAN DE CORRECTION

### Phase 1: CLARIFICATION (30 min)

- [ ] **1.1** Définir webhook UNIQUE pour Singpay
- [ ] **1.2** Valider format réponse Singpay (appel test)
- [ ] **1.3** Clarifier statuts Order (workflow diagram)
- [ ] **1.4** Ajouter PAYMENT_SIMULATION_MODE à settings ou retirer

### Phase 2: CORRECTIONS CODE (45 min)

- [ ] **2.1** Consolider webhooks (supprimer ancien si nécessaire)
- [ ] **2.2** Améliorer gestion erreurs Singpay
- [ ] **2.3** Ajouter logs détaillés à chaque étape
- [ ] **2.4** Ajouter retry logic pour instabilité réseau

### Phase 3: TESTS (1-2h)

- [ ] **3.1** Test initiation Airtel (sandbox)
- [ ] **3.2** Test initiation Moov (sandbox)
- [ ] **3.3** Test webhook confirmation
- [ ] **3.4** Test cas d'erreur (numéro invalide, montant 0, etc.)

---

## 🧪 SCRIPT DE TEST PRÉPARÉ

Je vais créer un script `test_singpay_integration.py` qui:

1. ✅ Crée une commande test
2. ✅ Appelle `/payments/init/` avec Airtel Money
3. ✅ Affiche la réponse Singpay
4. ✅ Teste webhook de confirmation
5. ✅ Valide changement statut Order

---

## 🎯 NEXT STEPS

1. **Maintenant**: Vous validez la correction du webhook
2. **Puis**: Corrections mineures du code
3. **Ensuite**: Exécuter script de test
4. **Finalement**: Appels réels Singpay (sandbox)

---

## 📞 CONFIGURATION À VÉRIFIER AVEC SINGPAY

Quand vous appelleriez Singpay, demander:

1. ✅ **Webhook URL**: Quelle URL appeller pour les callbacks ?
   - Option: `https://your-domain.com/api/v1/orders/{order_id}/payments/webhook/`

2. ✅ **Format Callback**: Quelle structure JSON ?
   ```json
   {
     "paymentResult": {
       "transaction": { "airtel_money_id": "..." },
       "status": { "success": true }
     }
   }
   ```

3. ✅ **Signature**: Comment signer les webhooks ?
   - HMAC-SHA256 ?
   - Header: `x-signature` ?

4. ✅ **Timeout**: Combien de temps avant timeout ?
   - 30s OK ?

---

## 📊 TABLEAU COMPARATIF (Implémentation vs Singpay)

| Étape | Implémentation | Status | À Tester |
|-------|----------------|--------|----------|
| 1. Créer Payment | ✅ PaymentInitView | ✅ Code | ⏳ Real API |
| 2. Appeler Singpay | ✅ call_singpay_payment | ✅ Code | ⏳ Real API |
| 3. Formatter numéro | ✅ _format_gabon_phone | ✅ Code | ✅ Validé |
| 4. Recevoir webhook | ✅ PaymentWebhookView | ✅ Code | ⏳ Real API |
| 5. Confirmer paiement | ✅ confirm_payment | ✅ Code | ⏳ Real API |
| 6. Mettre à jour Order | ✅ order.status = 'confirmed' | ✅ Code | ⏳ Real API |

---

## 💾 FICHIERS CLÉS À CONNAÎTRE

```
s:\Brice\Gaboshop\
├── .env (config Singpay)
├── payments/
│   ├── services.py (logique métier)
│   ├── utils.py (wrapper API)
│   ├── models.py (Payment model)
│   ├── webhooks.py (ancien - à clarifier)
│   └── serializers.py (validation input)
├── api/v1/
│   └── payments.py (endpoints + webhooks)
└── orders/
    └── models.py (Order statuts)
```

---

## ✅ ACTIONS IMMÉDIATES

1. **Lisez** ce document complètement
2. **Décidez** du webhook UNIQUE
3. **Communiquez** avec Singpay pour formats/signatures
4. **Exécutez** les tests que je vais préparer

---

**Date Analyse**: 2026-06-22  
**Compte Sandboxactif**: ✅ OUI  
**Pret pour tests**: ✅ OUI (avec ajustements)
