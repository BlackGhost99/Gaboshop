# 🚀 GUIDE EXÉCUTION TESTS SINGPAY

## 📋 AVANT DE COMMENCER

**Checklist préalable**:
- [ ] Django installé et configuré
- [ ] Compte Singpay actif (sandbox)
- [ ] Config `.env` avec credentials
- [ ] BD migrations à jour

---

## ÉTAPE 1: PRÉPARER L'ENVIRONNEMENT

### 1.1 Vérifier Python + Django

```powershell
cd s:\Brice\Gaboshop
python --version
# Output: Python 3.10+ ✓

python manage.py --version
# Output: Django 4.x+ ✓
```

### 1.2 Vérifier les migrations

```powershell
python manage.py migrate --check
# Doit dire: No migrations pending ✓
```

### 1.3 Vérifier config Singpay

```powershell
python manage.py shell
>>> from django.conf import settings
>>> print(settings.SINGPAY_BASE_URL)
https://gateway.singpay.ga/v1  ✓
>>> print(settings.SINGPAY_CLIENT_ID)
<SINGPAY_CLIENT_ID> ✓
```

---

## ÉTAPE 2: EXÉCUTER SCRIPT DE TEST

### 2.1 Lancer le script complet

```powershell
cd s:\Brice\Gaboshop
python test_singpay_integration.py
```

**Résultat attendu**:
```
════════════════════════════════════════════════════════════════════════════════
🧪 TEST SINGPAY INTEGRATION
Date: 2026-06-22T...
Sandbox Singpay: ACTIVE

════════════════════════════════════════════════════════════════════════════════
SETUP - Préparation des données
════════════════════════════════════════════════════════════════════════════════
✅ User récupéré: testclient
✅ Store récupéré: Test Store Singpay
✅ Category créée: Test Category
✅ Produit créé: TEST-SINGPAY-001

════════════════════════════════════════════════════════════════════════════════
TEST 1 - Validation Config Singpay
════════════════════════════════════════════════════════════════════════════════
✅ SINGPAY_BASE_URL: https://gateway.singpay.ga/v1
✅ SINGPAY_CLIENT_ID: <SINGPAY_CLIENT_ID>
✅ SINGPAY_WALLET_ID: <SINGPAY_WALLET_ID>
✅ SINGPAY_TIMEOUT: 30

... (suite des tests)
```

### 2.2 Interpréter les résultats

#### ✅ SUCCÈS - Tout fonctionne
```
✅ Commande créée: #123456
✅ Airtel Money - Réponse valide
✅ Moov Money - Réponse valide
✅ Webhook traité
✅ TESTS COMPLÉTÉS
```

**Action**: Passer au test de paiement réel ✓

#### ⚠️ AVERTISSEMENT - Config OK, API test échoue
```
⚠️ AVERTISSEMENT: Config manquante: [...] 
❌ Airtel Money - Erreur API: SingPay HTTP 400
```

**Action**: Vérifier avec Singpay si account sandbox est activé pour ce CLIENT_ID

#### ❌ ERREUR - Problème code
```
❌ Erreur création commande: Store n'est pas actif
❌ Exception: Permission denied
```

**Action**: Lire le traceback complet et corriger

---

## ÉTAPE 3: TESTER VIA API DIRECTEMENT

### 3.1 Démarrer Django en dev

```powershell
cd s:\Brice\Gaboshop
python manage.py runserver
# Output: Starting development server at http://127.0.0.1:8000/
```

### 3.2 Créer commande via API

**Terminal 2** - Créer commande test:

```powershell
# 1. Récupérer token d'auth
$token = (curl -X POST http://localhost:8000/api/get-token/ `
  -H "Content-Type: application/json" `
  -d '{"username":"testclient","password":"testpass123"}' | `
  ConvertFrom-Json).token

# 2. Créer commande
curl -X POST http://localhost:8000/api/v1/orders/create/ `
  -H "Authorization: Token $token" `
  -H "Content-Type: application/json" `
  -d '{
    "items": [
      {"product_id": 1, "quantity": 1, "unit_price": 15000}
    ],
    "delivery_address": "123 Rue Test, Libreville",
    "delivery_phone": "+24177777777",
    "delivery_zone": "TEST"
  }'

# Output:
# {
#   "success": true,
#   "data": {
#     "order": {
#       "id": 123,
#       "order_number": "ORD-123456",
#       "total_amount": 17000,
#       "status": "created"
#     }
#   }
# }
```

**Copier l'order_id** (ex: 123)

### 3.3 Initier paiement Airtel Money

```powershell
$order_id = 123  # From previous step

curl -X POST "http://localhost:8000/api/v1/orders/$order_id/payments/init/" `
  -H "Authorization: Token $token" `
  -H "Content-Type: application/json" `
  -d '{
    "payment_method": "airtel_money",
    "phone_number": "+24177777777",
    "operator": "airtel"
  }'

# Output expected:
# {
#   "success": true,
#   "message": "Paiement initialisé.",
#   "data": {
#     "payment": {
#       "id": 456,
#       "transaction_id": "PAY-123456-20260622101234",
#       "amount": 17000
#     },
#     "next_steps": {
#       "message": "Un prompt de paiement apparaitra sur votre mobile Airtel",
#       "action": "Verifiez votre telephone et entrez votre PIN"
#     }
#   }
# }
```

**Copier transaction_id** (ex: PAY-123456-20260622101234)

### 3.4 Simuler webhook de confirmation

```powershell
$transaction_id = "PAY-123456-20260622101234"

curl -X POST "http://localhost:8000/api/v1/orders/$order_id/payments/webhook/" `
  -H "Content-Type: application/json" `
  -d "{
    \"transaction_id\": \"$transaction_id\",
    \"status\": \"SUCCESS\",
    \"amount\": 17000,
    \"transaction\": {
      \"airtel_money_id\": \"AM_456\",
      \"result\": \"SUCCESS\"
    },
    \"status_payload\": {
      \"success\": true,
      \"code\": \"00\"
    }
  }"

# Output expected:
# {
#   "success": true,
#   "message": "Paiement confirme."
# }
```

### 3.5 Vérifier statuts finaux

```powershell
curl -X GET "http://localhost:8000/api/v1/orders/$order_id/" `
  -H "Authorization: Token $token"

# Output:
# {
#   "data": {
#     "order": {
#       "status": "confirmed",  ← DOIT ÊTRE "confirmed" ou "paid"
#       "total_amount": 17000,
#       "payment": {
#         "status": "success"   ← DOIT ÊTRE "success"
#       }
#     }
#   }
# }
```

---

## ÉTAPE 4: TESTER CAS D'ERREUR

### 4.1 Erreur: Phone invalide

```powershell
curl -X POST "http://localhost:8000/api/v1/orders/$order_id/payments/init/" `
  -H "Authorization: Token $token" `
  -H "Content-Type: application/json" `
  -d '{
    "payment_method": "airtel_money",
    "phone_number": "123",  # ← INVALIDE
    "operator": "airtel"
  }'

# Output expected:
# {
#   "success": false,
#   "error": {
#     "message": "Numéro de téléphone Gabon invalide..."
#   }
# }
```

### 4.2 Erreur: Opérateur non supporté

```powershell
curl -X POST "http://localhost:8000/api/v1/orders/$order_id/payments/init/" `
  -H "Authorization: Token $token" `
  -H "Content-Type: application/json" `
  -d '{
    "payment_method": "visa",  # ← NON SUPPORTÉ
    "operator": "visa"
  }'

# Output expected:
# {
#   "success": false,
#   "error": {
#     "message": "Seuls les paiements Mobile Money (Airtel/Moov) sont autorisés."
#   }
# }
```

### 4.3 Erreur: Commande introuvable

```powershell
curl -X POST "http://localhost:8000/api/v1/orders/99999/payments/init/" `
  -H "Authorization: Token $token" `
  -H "Content-Type: application/json" `
  -d '{
    "payment_method": "airtel_money",
    "phone_number": "+24177777777",
    "operator": "airtel"
  }'

# Output expected:
# {
#   "success": false,
#   "error": {
#     "code": 404,
#     "message": "Commande non trouvée ou déjà payée."
#   }
# }
```

---

## ÉTAPE 5: VÉRIFIER LES LOGS

### 5.1 Logs Django

```powershell
# Dans le terminal de Django, chercher:
💳 Paiement AIRTEL initialisé: PAY-123456... | +24177777777 | 17000F CFA

# Ou en cas d'erreur:
❌ Erreur initiation paiement airtel: ...
```

### 5.2 Logs BD

```powershell
python manage.py shell
>>> from payments.models import Payment
>>> p = Payment.objects.latest('id')
>>> print(f"ID: {p.id}")
>>> print(f"Status: {p.status}")
>>> print(f"Transaction ID: {p.transaction_id}")
>>> print(f"Webhook data: {p.webhook_data}")
```

---

## ÉTAPE 6: TESTER MOOV MONEY (PAREIL)

```powershell
# Créer nouvelle commande
# Paiement init avec operator='moov'
# Vérifier webhook
```

---

## 📊 TABLEAU RÉSUMÉ

| Étape | Action | ✅ Success | ❌ Problème |
|-------|--------|-----------|-----------|
| 1 | Config Singpay | Logs valides | Config manquante |
| 2 | Créer commande | Order créée | BD error |
| 3 | Init Airtel | Payment créé | API error |
| 4 | Webhook | Status=success | Webhook non reçu |
| 5 | Vérifier statuts | Order=confirmed | Order=pending_payment |
| 6 | Init Moov | Payment créé | API error |
| 7 | Cas d'erreur | Erreur retournée | Erreur non gérée |

---

## 🐛 TROUBLESHOOTING

### Problème: "SINGPAY_BASE_URL manquant"
```
❌ Config SingPay manquante: ['SINGPAY_BASE_URL']

Résolution:
1. Vérifier .env: SINGPAY_BASE_URL=...
2. Redémarrer Django: python manage.py runserver
```

### Problème: "wallet not accepted"
```
❌ Erreur Airtel Money API: SingPay error - wallet not accepted | Action requise: activer/valider le wallet...

Résolution:
1. Contacter Singpay support
2. Vérifier account est activé pour CLIENT_ID
3. Vérifier wallet status dans dashboard Singpay
```

### Problème: "Payment not found"
```
❌ Webhook failed: Payment not found

Résolution:
1. Vérifier transaction_id matches DB
2. Vérifier Payment record créé par PaymentInitView
3. Vérifier ordre des appels (init AVANT webhook)
```

### Problème: "Order status stays pending_payment"
```
Order ne change pas de status après webhook

Résolution:
1. Vérifier PaymentWebhookView est appelé
2. Vérifier webhook_data est reçu
3. Vérifier statuts conditions (is_success logic)
4. Check logs: "Webhook traité?" ou erreur?
```

---

## ✅ CHECKLIST VALIDATION

Après tous les tests:

- [ ] Config Singpay chargée ✓
- [ ] Commande créée ✓
- [ ] Payment init Airtel ✓
- [ ] Payment init Moov ✓
- [ ] Webhook confirmation reçu ✓
- [ ] Order status = confirmed ✓
- [ ] Payment status = success ✓
- [ ] Cas d'erreur gérés ✓
- [ ] Logs complets ✓

**SI TOUT ✓**: Prêt pour tests LIVE avec Singpay 🎉

---

## 📞 SI ERREURS PERSISTANTES

**Ouvrir ticket Singpay support** avec:
1. CLIENT_ID: <SINGPAY_CLIENT_ID>
2. Erreur exacte: (copier-coller)
3. Request payload: (inclure JSON)
4. Response payload: (inclure JSON)
5. Timestamp: 2026-06-22 HH:MM:SS UTC

---

**Date**: 2026-06-22  
**Version**: 1.0  
**Status**: PRÊT POUR TESTS
