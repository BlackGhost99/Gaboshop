# 🛠️ CORRECTION REQUISES - SINGPAY

## 📋 CHECK-LIST CORRECTIONS

### CORRECTION 1: WEBHOOK UNIQUE (PRIORITÉ HAUTE)

**Problème**: Deux implémentations de webhooks créent confusion

**Fichiers affectés**:
- `payments/webhooks.py` - Webhooks simples (OLD)
- `api/v1/payments.py` - PaymentWebhookView (NEW)

**Solution**: 

✅ **GARDER**: `PaymentWebhookView` de `api/v1/payments.py`
❌ **RETIRER**: `payments/webhooks.py` (ou archiver)

**Pourquoi**:
1. Gère plusieurs formats de réponse
2. A AuditLog pour traçabilité
3. Peut chercher Payment par reference en fallback

**Action**:
```python
# Dans payments/urls.py - COMMENTER/SUPPRIMER:
# path('webhooks/airtel/', webhooks.airtel_money_webhook, name='webhook_airtel'),
# path('webhooks/moov/', webhooks.moov_money_webhook, name='webhook_moov'),
```

**URL UNIQUE à utiliser**:
```
POST /api/v1/orders/{order_id}/payments/webhook/
```

---

### CORRECTION 2: VALIDATION RÉPONSE SINGPAY

**Fichier**: `payments/services.py` → `_call_airtel_money_api()` et `_call_moov_money_api()`

**Problème**: Extraction transaction_id fait trop d'hypothèses

**Code actuel** (FRAGILE):
```python
transaction_id = (
    tx.get("airtel_money_id")
    or tx.get("id")
    or tx.get("_id")
    or response.get("transaction_id")
    or f"AIRTEL_{order.id}_{int(timezone.now().timestamp())}"
)
```

**Risque**: Si none des clés existent → utilise timestamp généré → webhook mal matché

**Solution - Ajouter logs**:
```python
# Après appel Singpay
import logging
logger = logging.getLogger(__name__)

logger.debug(f"Singpay response keys: {response.keys()}")
logger.debug(f"Transaction keys: {tx.keys()}")
logger.debug(f"Status keys: {status_payload.keys()}")

# Si transaction_id is None:
if not transaction_id:
    logger.error(f"⚠️ transaction_id is None! Response: {response}")
```

---

### CORRECTION 3: ENRICHIR GESTION ERREURS

**Fichier**: `payments/services.py` → `_build_singpay_error_message()`

**Actuel**:
```python
if "wallet not accepted" in lowered or "status: pending" in lowered:
    message += " | Action requise: activer/valider le wallet..."
```

**À AJOUTER** après testing:
```python
error_mapping = {
    "invalid_amount": "Montant invalide (min 1000 FCFA, max 2000000 FCFA)",
    "invalid_phone": "Numéro téléphone invalide pour Gabon",
    "wallet_disabled": "Wallet désactivé chez Singpay",
    "timeout": "Timeout Singpay. Rééssayez.",
    "rate_limit": "Trop de requêtes. Attendez 60s.",
}
```

---

### CORRECTION 4: AJOUTER SIMULATION MODE (OPTIONNEL)

**Fichier**: `Gaboshop/settings.py`

**À AJOUTER**:
```python
# Sandbox Singpay Simulation
# Mettre True pour tests locaux sans vrais appels Singpay
SINGPAY_SIMULATION_MODE = False  # À False pour tests sandbox réels

# Si True, utiliser ce mode:
if SINGPAY_SIMULATION_MODE:
    # Retourner réponses simulées (dev/local)
    pass
else:
    # Appels réels Singpay (sandbox/prod)
    pass
```

**Utilisation dans code**:
```python
# Dans payments/services.py
if getattr(settings, 'SINGPAY_SIMULATION_MODE', False):
    logger.info("⚠️ MODE SIMULATION - Pas d'appel réel Singpay")
    return PaymentService._get_fallback_response(...)
```

---

### CORRECTION 5: CLARIFIER WORKFLOW STATUTS ORDER

**Fichier**: `orders/models.py`

**Clarifier les transitions**:
```python
class Order(models.Model):
    STATUS_CHOICES = (
        # Avant paiement
        ('created', 'Créée'),              # Initiale
        ('pending_payment', 'En attente de paiement'),  # Après API paiement
        
        # Après paiement
        ('paid', 'Payée'),                 # Webhook succès
        ('confirmed', 'Confirmée'),        # = paid (alias?)
        
        # Autres
        ('preparing', 'En préparation'),
        ('ready', 'Prête'),
        ('in_transit', 'En livraison'),
        ('delivered', 'Livrée'),
        ('cancelled', 'Annulée'),
        ('refunded', 'Remboursée'),
    )
```

**À clarifier**:
- Quelle différence entre `paid` et `confirmed` ?
- Voir si les deux sont nécessaires ou consolider

---

### CORRECTION 6: LOGGING DÉTAILLÉ

**Ajouter à `payments/services.py`**:

```python
import logging
logger = logging.getLogger(__name__)

class PaymentService:
    
    @staticmethod
    def init_mobile_money_payment(order, phone_number, operator):
        logger.info(f"🔵 PAIEMENT INIT - Order: {order.id}, Operator: {operator}, Phone: {phone_number[:5]}***")
        
        # ... code ...
        
        logger.info(f"🟢 PAIEMENT SUCCESS - Order: {order.id}, TxID: {payment.transaction_id}")
        
        # En cas d'erreur:
        except Exception as e:
            logger.error(f"🔴 PAIEMENT ERROR - Order: {order.id}, Error: {str(e)}", exc_info=True)
```

---

## 🚀 PLAN D'EXÉCUTION

### Phase 1: Préparer les corrections (30 min)

- [ ] Lire et comprendre ce document
- [ ] Tester script `test_singpay_integration.py`
- [ ] Identifier points spécifiques au YOUR code

### Phase 2: Appliquer corrections (1h)

- [ ] CORRECTION 1: Webhook unique
- [ ] CORRECTION 2: Validation réponse
- [ ] CORRECTION 3: Gestion erreurs
- [ ] CORRECTION 4: Simulation mode
- [ ] CORRECTION 5: Statuts clarifiés
- [ ] CORRECTION 6: Logs détaillés

### Phase 3: Tester (1-2h)

- [ ] Exécuter `python test_singpay_integration.py`
- [ ] Vérifier logs
- [ ] Valider avec Singpay

---

## ✅ VALIDATION AVANT TESTS LIVE

Avant de passer à production, vérifier:

```python
# 1. Config OK
✓ SINGPAY_CLIENT_ID configuré
✓ SINGPAY_CLIENT_SECRET configuré
✓ SINGPAY_WALLET_ID configuré
✓ SINGPAY_BASE_URL = https://gateway.singpay.ga/v1

# 2. Webhook OK
✓ Url unique définie chez Singpay
✓ Pas de doublon (old vs new)

# 3. Logs OK
✓ Logs détaillés à chaque étape
✓ Traces erreurs claires

# 4. Tests OK
✓ test_singpay_integration.py passe
✓ BD en état cohérent
✓ Webhooks reçus correctement
```

---

## 📞 QUESTIONS POUR SINGPAY

Quand communiquer:

1. **Format Callback**: Quelle structure JSON exactement ?
   - Inclure sample dans ticket support Singpay

2. **Signature**: Comment signer webhooks ?
   - HMAC-SHA256 dans quel header ?

3. **Timeout**: Accepte-t-on 30s ?

4. **Retry**: Vous reessayez combien de fois ?

5. **Format Error**: Codes d'erreur spécifiques ?
   - Pour enrichir `_build_singpay_error_message()`

---

## 📊 MÉTRIQUES DE SUCCÈS

Après corrections:

```
✅ Config Singpay valide: 100%
✅ Phone formatting: 100%
✅ API Payment Init: Success rate > 95%
✅ Webhook handling: 100% des payements confirmés
✅ Error handling: < 1% non-handled errors
✅ Logs: Tous les steps tracés
```

---

## 🎯 NEXT STEPS

1. **Immédiat**: Lire corrections + valider avec vous
2. **Demain**: Appliquer corrections (1-2h de dev)
3. **J+1**: Exécuter tests (1h)
4. **J+2**: Contact Singpay si besoin clarifications
5. **J+3**: Tests avec compte LIVE

---

**Date**: 2026-06-22  
**Status**: 🟡 PRÊT POUR CORRECTIONS
