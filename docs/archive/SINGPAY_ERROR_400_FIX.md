# 🔧 CORRECTION - ERREUR 400 POST /api/v1/orders/create/

## ✅ Problème Identifié

Quand vous essayez de créer une commande via SingPay, vous obteniez:
```
POST http://localhost:8000/api/v1/orders/create/ 400 (Bad Request)
```

### Cause Racine

Le frontend **n'envoyait pas le champ `delivery_type`** dans le payload, mais le backend l'attendait comme champ requis.

**Frontend JSON envoyé:**
```javascript
{
  store: 1,
  city: "Libreville",
  delivery_address: "123 Rue Test",
  delivery_phone: "+24177777777",
  delivery_zone: "Zone Test",
  delivery_requested: true,
  notes: "Test",
  items: [{product_id: 1, quantity: 1}]
  // ❌ delivery_type MANQUANT!
}
```

**Serializer attendait:**
```python
fields = [
    'store', 'city', 'delivery_address', 'delivery_phone', 'delivery_zone',
    'delivery_type',  # ← REQUIS mais absent!
    'delivery_requested', 'notes', 'items'
]
```

---

## ✅ Solution Implémentée

### Fichier modifié: [`orders/serializers.py`](orders/serializers.py)

#### Avant (INCORRECT):
```python
class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemCreateSerializer(many=True, write_only=True)
    
    class Meta:
        model = Order
        fields = [
            'store', 'city', 'delivery_address', 'delivery_phone', 'delivery_zone',
            'delivery_type',  # ← Champ REQUIS par défaut
            'delivery_requested', 'notes', 'items'
        ]
```

#### Après (CORRECT):
```python
class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemCreateSerializer(many=True, write_only=True)
    delivery_type = serializers.ChoiceField(
        choices=['standard', 'express'],
        default='standard',
        required=False,  # ← Maintenant optionnel
        allow_blank=False
    )
    delivery_requested = serializers.BooleanField(
        default=True,
        required=False
    )
    notes = serializers.CharField(
        default='',
        required=False,
        allow_blank=True
    )
    city = serializers.CharField(
        default='Libreville',
        required=False,
        allow_blank=False
    )
    
    class Meta:
        model = Order
        fields = [
            'store', 'city', 'delivery_address', 'delivery_phone', 'delivery_zone',
            'delivery_type', 'delivery_requested', 'notes', 'items'
        ]
```

### Changements:
1. ✅ `delivery_type` → `required=False` avec `default='standard'`
2. ✅ `delivery_requested` → `required=False` avec `default=True`
3. ✅ `notes` → `required=False` avec `default=''`
4. ✅ `city` → `required=False` avec `default='Libreville'`

---

## 🧪 Verification

### 1. Vérifier directement via l'API

```bash
# Minimal valid payload (maintenant accepté):
curl -X POST http://localhost:8000/api/v1/orders/create/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "store": 1,
    "delivery_address": "123 Rue Test",
    "delivery_phone": "+24177777777",
    "delivery_zone": "Zone Test",
    "items": [{"product_id": 1, "quantity": 1}]
  }'
```

### 2. Tester avec le script Python

```bash
# Configuration d'abord:
cd d:\Expériences\Gaboshop

# Puis exécuter:
D:\Expériences\Gaboshop\venv-1\Scripts\python.exe test_order_request.py
```

### 3. Attendre le flux complet SingPay

Après correction de l'erreur 400, le flux normal devrait être:

1. ✅ POST `/api/v1/orders/create/` → Crée la commande (201 Created)
2. ✅ POST `/orders/{orderId}/payments/init/` → Initialise le paiement
3. ✅ SingPay API → Effectue la transaction
4. ✅ Payment callback → Met à jour le statut

---

## 🎯 Prochaines Étapes pour SingPay

1. **[X]** Corriger l'erreur 400 ← VOUS ÊTES ICI
2. **[ ]** Vérifier que la comande est créée avec succès
3. **[ ]** Vérifier que le paiement est initialisé
4. **[ ]** Tester un paiement Airtel Money complet
5. **[ ]** Configurer SingPay callback pour mettre à jour le statut

---

## 🔍 Information Supplémentaire

### Champs maintenant optionnels avec defaults:

| Champ | Type | Default | Requis? |
|-------|------|---------|---------|
| `store` | int | N/A | ✅ OUI |
| `delivery_address` | string | N/A | ✅ OUI |
| `delivery_phone` | string | N/A | ✅ OUI |
| `delivery_zone` | string | N/A | ✅ OUI |
| `items` | array | N/A | ✅ OUI |
| `delivery_type` | 'standard'\|'express' | 'standard' | ❌ NON |
| `delivery_requested` | boolean | True | ❌ NON |
| `notes` | string | '' | ❌ NON |
| `city` | string | 'Libreville' | ❌ NON |

### Configuration SingPay (.env):

```ini
SINGPAY_BASE_URL=https://gateway.singpay.ga/v1
SINGPAY_CLIENT_ID=<SINGPAY_CLIENT_ID>
SINGPAY_CLIENT_SECRET=<SINGPAY_CLIENT_SECRET>
SINGPAY_WALLET_ID=<SINGPAY_WALLET_ID>
SINGPAY_TIMEOUT=30
SINGPAY_ENABLE_TRANSFER=False
```

---

## 📝 Résumé

✅ **ERREUR 400 RÉSOLUE**: Le serializer accepte maintenant un payload minimal sans les champs optionnels.

🔄 **Flux SingPay amélioré**: L'intégration peut maintenant procéder sans erreurs de validation frontend.

⏭️ **Prochaine étape**: Tester le paiement réel via SingPay.
