# 🧪 TESTING GUIDE - Comment Tester Phase 1 en Frontend

Il existe **3 méthodes simples** pour tester l'implémentation Phase 1 (Status Validation & Audit Logging):

---

## ✅ Méthode 1: Console Browser (Recommandée - 2 minutes)

### 🎯 Objectif
Tester les validations directement depuis la console du navigateur.

### 📋 Étapes

**1. Ouvrir la Console**
```
Chrome/Edge:  Ctrl+Shift+I  →  Onglet "Console"
Firefox:      Ctrl+Shift+K  →  Console
Safari:       Cmd+Option+I  →  Console
```

**2. Copier-Coller le Code de Test**
```javascript
// Charger les tests
import('./src/utils/testPhase1Validation.js').then(module => {
  window.runPhase1Tests = module.runPhase1Tests;
  console.log('Tests chargés! Exécutez: runPhase1Tests()');
});

// Puis exécutez après 1 seconde
setTimeout(() => {
  if (window.runPhase1Tests) {
    window.runPhase1Tests();
  }
}, 1000);
```

**3. Résultats Visibles en Direct**
```
✓ Login delivery agent - Token: abc123xyz...
✓ Get assigned deliveries - Found 1 deliveries
✓ Accept delivery (valid) - Status: accepted
✓ Reject invalid transition - Correctly rejected with status 400
✓ Start delivery (in_transit) - Status: in_transit
✓ Complete delivery (delivered) - Status: delivered

╔════════════════════════════════════════════════════╗
║                   TEST SUMMARY                     ║
║ ✓ Passed: 6                                         ║
║ ✗ Failed: 0                                         ║
╚════════════════════════════════════════════════════╝
```

---

## 🎨 Méthode 2: Interface UI (Plus Facile - 1 minute)

### 🎯 Objectif  
Tester avec un panel graphique dans votre interface.

### 📋 Étapes

**1. Ajouter le TestPanel au Composant Principal**

Ouvrez `frontend/src/pages/DeliveryDashboard.jsx` ou votre page principale:

```jsx
import { TestPanel } from '../components/TestPanel';

export function DeliveryDashboard() {
  return (
    <div className="dashboard">
      {/* Votre contenu */}
      <DeliveryList />
      <AssignedOrders />
      
      {/* Ajouter le Test Panel */}
      <TestPanel />
    </div>
  );
}
```

**2. Interface Apparaît**
- Un bouton violet 🧪 apparaît en bas à droite
- Cliquez dessus pour ouvrir le panel

**3. Exécuter les Tests**
- Cliquez "▶️ Exécuter les tests"
- Observez les résultats en temps réel
- Chaque action est loggée

### 📊 Vous Verrez
```
╔════════════════════════════════════════════════════╗
║   🧪 Test Phase 1 - Status Validation            ║
╚════════════════════════════════════════════════════╝

[14:30:12] 🔍 Démarrage des tests Phase 1...
[14:30:13] 📝 Exécution de la suite de tests...
[14:30:14] ✓ Tests terminés: 6 réussis, 0 échoués

📊 Résumé des tests:
  ✓ Réussis: 6
  ✗ Échoués: 0
  Total: 6

✓ Login delivery agent - Token: abc123...
✓ Get assigned deliveries - Found 1 deliveries
✓ Accept delivery (valid) - Status: accepted
✓ Reject invalid transition - Correctly rejected
✓ Start delivery (in_transit) - Status: in_transit
✓ Complete delivery (delivered) - Status: delivered
```

---

## 🔌 Méthode 3: API Direct avec Curl (Pour Admins - 5 minutes)

### 🎯 Objectif
Tester les endpoints REST directement.

### 📋 Étapes Préalables

**1. S'Authentifier**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "driver@test.com",
    "password": "test123"
  }' | jq .
```

**Réponse:**
```json
{
  "token": "1234567890abcdef",
  "user": {
    "id": 5,
    "email": "driver@test.com",
    "first_name": "Driver",
    "user_type": "delivery_agent"
  }
}
```

Sauvegardez le token dans une variable:
```bash
TOKEN="1234567890abcdef"
```

**2. Récupérer les Livraisons**
```bash
curl http://localhost:8000/api/v1/dashboard/delivery/assigned-orders/ \
  -H "Authorization: Token $TOKEN" | jq .
```

**Réponse:**
```json
[
  {
    "id": 1,
    "status": "pending",
    "order_id": 5,
    "delivery_agent": "driver@test.com"
  }
]
```

Notez l'ID de livraison (ici: `1`)

### ✅ Test 1: Accepter une Livraison (Transition Valide)

```bash
DELIVERY_ID=1

curl -X POST http://localhost:8000/api/v1/dashboard/delivery/$DELIVERY_ID/accept/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' | jq .
```

**Résultat Attendu (200 OK):**
```json
{
  "success": true,
  "message": "Livraison acceptée avec succès",
  "data": {
    "delivery_id": 1,
    "order_id": 5,
    "status": "accepted"
  }
}
```

✅ **Status: 200** = Test réussi!

### ❌ Test 2: Essayer d'Accepter à Nouveau (Transition Invalide)

```bash
curl -X POST http://localhost:8000/api/v1/dashboard/delivery/$DELIVERY_ID/accept/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' | jq .
```

**Résultat Attendu (400 Bad Request):**
```json
{
  "success": false,
  "error": "Invalid status transition: cannot go from accepted to accepted"
}
```

❌ **Status: 400** = Validation fonctionne!

### ✅ Test 3: Démarrer la Livraison (Transition Valide)

```bash
curl -X POST http://localhost:8000/api/v1/dashboard/delivery/$DELIVERY_ID/start/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' | jq .
```

**Résultat Attendu (200 OK):**
```json
{
  "success": true,
  "message": "Livraison démarrée avec succès",
  "data": {
    "delivery_id": 1,
    "status": "in_transit"
  }
}
```

### ✅ Test 4: Compléter la Livraison (Transition Valide)

```bash
curl -X POST http://localhost:8000/api/v1/dashboard/delivery/$DELIVERY_ID/complete/ \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' | jq .
```

**Résultat Attendu (200 OK):**
```json
{
  "success": true,
  "message": "Livraison confirmée avec succès",
  "data": {
    "delivery_id": 1,
    "status": "delivered"
  }
}
```

---

## 🛡️ Méthode 4: Vérifier les Logs d'Audit (Admin)

### 🎯 Objectif
Visualiser les changements enregistrés dans la base de données.

### 📋 Étapes

**1. Aller à Django Admin**
```
http://localhost:8000/admin/
```

**2. Se Connecter**
- Email: admin@test.com (ou votre compte admin)
- Mot de passe: (votre mot de passe)

**3. Accéder aux Audit Logs**
- Section "CORE" 
- Cliquez sur "Audit Logs"

**4. Vous Verrez le Tableau:**

| Timestamp | Action | User | Object | Old → New | IP | Suspicious |
|-----------|--------|------|--------|-----------|----|-----------:|
| 2025-12-08 14:30 | delivery_status_change | driver@test.com | delivery#1 | pending → accepted | 127.0.0.1 | No |
| 2025-12-08 14:30 | order_status_change | driver@test.com | order#5 | assigned → in_transit | 127.0.0.1 | No |

**5. Filtrer par:**
- Action type
- Timestamp
- User
- Suspicious (pour voir les tentatives de fraude)

---

## 🐍 Méthode 5: Script Python (Automatisé)

### 🎯 Objectif
Exécuter une suite complète de tests en Python.

### 📋 Étapes

**1. Exécuter le Script**
```bash
cd c:\Users\Admin\source\repos\BlackGhost99\gaboshop
python test_phase1.py
```

**2. Résultats Affichés**
```
======================================================================
                  PHASE 1 ANTI-FRAUD IMPLEMENTATION TEST SUITE
======================================================================

======================================================================
                      TEST 1: Valid Status Transitions
======================================================================

1.1 Testing: Accept Delivery (pending → accepted)
✓ Accept delivery endpoint                          PASS - Status: 200
✓ Status updated to 'accepted'                      PASS - Status: accepted

1.2 Testing: Start Delivery (accepted → in_transit)
✓ Start delivery endpoint                           PASS - Status: 200
✓ Status updated to 'in_transit'                    PASS - Status: in_transit

1.3 Testing: Complete Delivery (in_transit → delivered)
✓ Complete delivery endpoint                        PASS - Status: 200
✓ Status updated to 'delivered'                     PASS - Status: delivered

======================================================================
                    TEST 2: Invalid Status Transitions
======================================================================

2.1 Testing: Invalid - Accept Already Accepted Delivery
✓ Reject double acceptance                          PASS - Status: 400

2.2 Testing: Suspicious Activity Logging
✓ Suspicious activity marked in audit log           PASS - Found 1 suspicious logs

======================================================================
                    TEST 3: Unauthorized Access Prevention
======================================================================

3.1 Testing: Unauthorized Driver Cannot Accept Others' Deliveries
✓ Reject unauthorized access                        PASS - Status: 403

3.2 Testing: Unauthorized Access Logged as Suspicious
✓ Unauthorized attempt flagged as suspicious        PASS - Found 1 suspicious logs

3.3 Testing: Security Details Captured
✓ IP address captured                               PASS - IP: 127.0.0.1
✓ Reason recorded                                   PASS - Reason: Unauthorized user attempted

======================================================================
                        TEST 4: Audit Trail Logging
======================================================================

4.1 Testing: Audit Log Creation on Status Change
✓ Audit log created on status change                PASS - Logs: 0 → 5

4.2 Testing: Audit Log Details
✓ Old status recorded                               PASS - Old: pending
✓ New status recorded                               PASS - New: accepted
✓ User recorded                                     PASS - User: driver@test.com
✓ IP address recorded                               PASS - IP: 127.0.0.1

======================================================================
                          TEST SUMMARY
======================================================================

Total Tests: 24
Passed: 24
Failed: 0
Success Rate: 100.0%

✓ ALL TESTS PASSED - Phase 1 is working correctly!
```

---

## 📋 Checklist Complète

### Phase 1 Validation
- [ ] **Transitions Valides** fonctionnent (200 OK)
  - [ ] pending → accepted
  - [ ] accepted → in_transit
  - [ ] in_transit → delivered

- [ ] **Transitions Invalides** sont rejetées (400 Bad Request)
  - [ ] Double acceptation
  - [ ] Changements incorrects

- [ ] **Accès Non Autorisé** est bloqué (403 Forbidden)
  - [ ] Autre livreur ne peut pas accepter
  - [ ] Admin peut voir et gérer

- [ ] **Audit Trail** enregistre tout
  - [ ] Changements de statut
  - [ ] Tentatives de fraude
  - [ ] IP address capturé
  - [ ] Timestamps précis

### Django Admin
- [ ] Audit Logs visibles dans admin
- [ ] Filtrage fonctionne
- [ ] Recherche fonctionne
- [ ] Logs marqués comme suspicious

### Performance
- [ ] Pas de ralentissements
- [ ] Requêtes rapides (< 200ms)
- [ ] Pas d'erreurs dans logs

---

## 🐛 Dépannage

### Erreur: "Token Invalide"
```bash
# Solution: Créez le compte de test
python manage.py shell
>>> from users.models import User
>>> User.objects.create_user(email='driver@test.com', password='test123', user_type='delivery_agent')
```

### Erreur: "404 Not Found"
```bash
# Vérifiez que les routes existent
curl http://localhost:8000/api/v1/dashboard/delivery/ -H "Authorization: Token $TOKEN"

# Vérifiez urls.py
python manage.py show_urls | grep delivery
```

### Erreur: "CORS Error"
```python
# Vérifiez settings.py
CORS_ALLOWED_ORIGINS = [
    'http://localhost:5174',
    'http://localhost:3000',
]
```

### Audit Logs Vides
```bash
# Vérifiez que core app est enregistrée
python manage.py shell
>>> from core.models import AuditLog
>>> AuditLog.objects.all().count()

# Vérifiez migrations
python manage.py migrate core
```

---

## 📊 Interprétation

### ✅ Tous les Tests Passent
**Phase 1 est prêt pour la production!**
- Validations fonctionnent ✓
- Audit trail enregistre ✓
- Fraude détectée ✓
- Performance OK ✓

### ⚠️ Quelques Tests Échouent
1. Vérifiez les messages d'erreur
2. Consultez `python manage.py runserver` output
3. Vérifiez les migrations

### ❌ Tous les Tests Échouent
1. Serveur Django tourne? `http://localhost:8000/api/v1/`
2. Core app enregistrée? `INSTALLED_APPS`
3. Migrations appliquées? `python manage.py migrate core`

---

**Choisissez la méthode qui vous convient le mieux! 🚀**
