# 🧪 Comment Tester Phase 1: Status Validation

Il y a 3 façons de tester l'implémentation Phase 1 anti-fraude:

## 1️⃣ Test Console (Le Plus Simple) - Recommandé pour les développeurs

### Étape 1: Ouvrir la console du navigateur
- **Chrome/Edge**: `Ctrl+Shift+I` → Onglet "Console"
- **Firefox**: `Ctrl+Shift+K` → Console
- **Safari**: `Cmd+Option+I` → Console

### Étape 2: Importer et exécuter les tests
Collez ceci dans la console:

```javascript
// Importer le module de test
import { runPhase1Tests } from './src/utils/testPhase1Validation.js';

// Exécuter les tests
await runPhase1Tests();
```

### Résultat attendu:
```
✓ Login delivery agent
✓ Get assigned deliveries
✓ Accept delivery (valid)
✓ Reject invalid transition
✓ Start delivery (in_transit)
✓ Complete delivery (delivered)
✓ Audit logs endpoint accessible

Résumé:
  ✓ Réussis: 7
  ✗ Échoués: 0
```

---

## 2️⃣ Test Panel UI (Interface Graphique) - Plus Facile

### Étape 1: Ajouter le composant au layout
Ouvrez `frontend/src/pages/DeliveryDashboard.jsx` (ou votre page principale):

```jsx
import { TestPanel } from '../components/TestPanel';

export function DeliveryDashboard() {
  return (
    <div>
      {/* Votre contenu existant */}
      <div>Dashboard Content...</div>
      
      {/* Ajouter le Test Panel */}
      <TestPanel />
    </div>
  );
}
```

### Étape 2: Utiliser le panel
1. Un bouton violet 🧪 apparaît en bas à droite
2. Cliquez dessus pour ouvrir le panel de test
3. Cliquez sur "▶️ Exécuter les tests"
4. Observez les résultats en temps réel

### Vous verrez:
- 📝 Logs détaillés de chaque test
- 📊 Résumé des résultats (réussis/échoués)
- 📈 Détails de chaque action testée

---

## 3️⃣ Test Curl/API Direct (Pour les Administrateurs)

### Pré-requis:
Vous avez besoin d'un token d'authentification

### Obtenir un token:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "driver@test.com",
    "password": "test123"
  }'
```

Réponse:
```json
{
  "token": "abc123xyz...",
  "user": { ... }
}
```

### Test 1: Vérifier les livraisons assignées
```bash
curl http://localhost:8000/api/v1/dashboard/delivery/assigned-orders/ \
  -H "Authorization: Token abc123xyz..."
```

### Test 2: Accepter une livraison (Transition valide)
```bash
curl -X POST http://localhost:8000/api/v1/dashboard/delivery/1/accept/ \
  -H "Authorization: Token abc123xyz..." \
  -H "Content-Type: application/json" \
  -d '{}'
```

✓ Réponse attendue: **200 OK**
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

### Test 3: Essayer d'accepter à nouveau (Transition invalide)
```bash
curl -X POST http://localhost:8000/api/v1/dashboard/delivery/1/accept/ \
  -H "Authorization: Token abc123xyz..." \
  -H "Content-Type: application/json" \
  -d '{}'
```

✗ Réponse attendue: **400 BAD REQUEST**
```json
{
  "success": false,
  "error": "Invalid status transition: cannot go from accepted to accepted"
}
```

### Test 4: Démarrer la livraison (Transition valide)
```bash
curl -X POST http://localhost:8000/api/v1/dashboard/delivery/1/start/ \
  -H "Authorization: Token abc123xyz..." \
  -H "Content-Type: application/json" \
  -d '{}'
```

✓ Réponse attendue: **200 OK**

### Test 5: Compléter la livraison (Transition valide)
```bash
curl -X POST http://localhost:8000/api/v1/dashboard/delivery/1/complete/ \
  -H "Authorization: Token abc123xyz..." \
  -H "Content-Type: application/json" \
  -d '{}'
```

✓ Réponse attendue: **200 OK**

---

## 4️⃣ Vérifier les Logs d'Audit (Django Admin)

### Étape 1: Accéder à Django Admin
1. Allez à: `http://localhost:8000/admin/`
2. Connectez-vous avec un compte admin

### Étape 2: Voir les Audit Logs
1. Cherchez "Audit Logs" dans la section "CORE"
2. Vous verrez tous les changements enregistrés:

| Timestamp | Action | User | Object | Old → New | IP | Suspicious |
|-----------|--------|------|--------|-----------|----|-----------:|
| 2025-12-08 14:30 | delivery_status_change | driver@test.com | delivery#1 | pending → accepted | 127.0.0.1 | ✓ |

### Étape 3: Filtrer les logs suspects
1. Cliquez sur "Is Suspicious" pour voir les tentatives de fraude
2. Recherchez par adresse IP pour identifier les comportements suspects
3. Consultez les notes pour les détails de l'investigation

---

## 📋 Checklist de Validation

Voici ce que chaque test doit valider:

### ✓ Authentification
- [ ] Login avec driver@test.com fonctionne
- [ ] Token est généré correctement
- [ ] Token est accepté pour les appels API

### ✓ Transitions Valides
- [ ] pending → accepted (Accepter) ✓ 200
- [ ] accepted → in_transit (Démarrer) ✓ 200
- [ ] in_transit → delivered (Terminer) ✓ 200

### ✓ Transitions Invalides
- [ ] accepted → accepted (Double acceptation) ✗ 400
- [ ] in_transit → pending (Reculer) ✗ 400
- [ ] delivered → in_transit (Reculer) ✗ 400

### ✓ Sécurité
- [ ] Autre livreur ne peut pas accepter une livraison ✗ 403
- [ ] Tentative de fraude marquée comme suspicious ✓
- [ ] IP enregistrée pour chaque action ✓
- [ ] User agent capturé ✓

### ✓ Audit Trail
- [ ] Chaque action crée un log d'audit ✓
- [ ] Old status enregistré correctement ✓
- [ ] New status enregistré correctement ✓
- [ ] Raison/Notes enregistrées ✓

---

## 🐛 Dépannage

### Erreur: "Token invalide"
```
Solution: Connectez-vous d'abord, puis utilisez le token fourni
```

### Erreur: "Livraison non trouvée"
```
Solution: Créez d'abord une livraison ou utilisez un ID existant
Vérifiez avec: GET /api/v1/dashboard/delivery/assigned-orders/
```

### Erreur: "CORS error"
```
Solution: Assurez-vous que CORS est configuré dans settings.py
CORS_ALLOWED_ORIGINS = ['http://localhost:5174']
```

### Erreur: "405 Method Not Allowed"
```
Solution: Vérifiez que la route utilise le bon verbe HTTP (POST, GET, etc.)
```

---

## 📊 Interprétation des Résultats

### Tous les tests passent ✓
Phase 1 est correctement implémentée! Vous pouvez procéder à Phase 2.

### Quelques tests échouent
1. Vérifiez les messages d'erreur détaillés
2. Consultez les logs Django (`python manage.py runserver` output)
3. Vérifiez que le endpoint existe dans `api/v1/urls.py`

### Tous les tests échouent
1. Vérifiez que le serveur Django tourne (`http://localhost:8000/api/v1/...`)
2. Vérifiez que `core` app est enregistrée dans `INSTALLED_APPS`
3. Vérifiez que migrations ont été appliquées (`python manage.py migrate core`)

---

## 📝 Notes Importantes

### Pour le Développement:
- Les tests utilisent `driver@test.com` - créez cet utilisateur s'il n'existe pas
- Les tests utilisent l'ID de livraison `1` - adaptez selon vos données
- Exécutez les tests après chaque modification importante

### Pour la Production:
- Ne laissez pas le Test Panel actif en production
- Utilisez les Audit Logs pour les investigations de fraude
- Configurez des alertes pour les actions marquées `is_suspicious=True`

### Architecture de Sécurité:
```
Request → Validation → Permission Check → State Transition Check
    ↓              ↓              ↓              ↓
   401          400            403            400
Unauthorized   Bad Request    Forbidden    Bad Request
    
    → Audit Logging → Database → Admin Review
```

---

**✓ Phase 1 est maintenant testable via 3 méthodes différentes!**
