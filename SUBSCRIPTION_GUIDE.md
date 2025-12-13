# 🎯 Système de Gestion des Forfaits en Temps Réel - Guide d'Implémentation

## 📋 Vue d'ensemble

Ce système implémente une **gestion de forfaits professionnelle et automatisée** comme Shopify, Odoo ou Wix. Chaque action du commerçant est contrôlée par son forfait en temps réel.

---

## 🏗️ Architecture

### 1. **Modèles Django**
- `SubscriptionPlan` : Définit les capacités (Starter, Pro, Business)
- `StoreSubscription` : Suivi du forfait actif pour chaque magasin
- `Store` : Enrichi avec méthodes pour vérifier les permissions

### 2. **Service de Vérification (`subscription_check.py`)**
- `SubscriptionChecker` : Classe centralisée pour vérifier les permissions
- Décorateur `@check_subscription_permission()` : Protège les vues/APIs

### 3. **Tâches Automatisées (`tasks.py`)**
- Vérification quotidienne des expirations
- Notifications automatiques (expiration, rappels)
- Renouvellement automatique (si activé)

### 4. **API REST (`subscription.py`)**
- Endpoints pour afficher le statut du forfait
- Vérification de permissions
- Comparaison des plans disponibles

---

## 🚀 Comment utiliser le système

### Scénario 1 : Empêcher l'ajout d'un produit si le forfait est dépassé

#### Dans une Vue Django ClassBased

```python
from rest_framework.views import APIView
from payments.subscription_check import SubscriptionChecker, check_subscription_permission

class ProductCreateView(APIView):
    @check_subscription_permission('add_product')
    def post(self, request):
        # Si on arrive ici, la permission est OK
        # Sinon, PermissionDenied est levée automatiquement
        return Response({'success': True})
```

#### Dans une Vue Classique

```python
from django.shortcuts import render
from django.core.exceptions import PermissionDenied
from payments.subscription_check import SubscriptionChecker

def add_product(request):
    store = request.user.store
    
    # Vérifier la permission
    try:
        SubscriptionChecker.check_can_add_product(store)
    except PermissionDenied as e:
        # Message d'erreur clair au commerçant
        return render(request, 'error.html', {'error': str(e)})
    
    # Code pour ajouter le produit...
    return redirect('store_dashboard')
```

#### Via API REST

Le frontend appelle :
```javascript
GET /api/v1/dashboard/subscription/check-permission/?action=add_product
```

Réponse si OK :
```json
{
  "success": true,
  "allowed": true,
  "action": "add_product",
  "message": "L'action \"add_product\" est autorisée pour votre forfait"
}
```

Réponse si KO :
```json
{
  "success": true,
  "allowed": false,
  "action": "add_product",
  "error": "Votre forfait Starter ne permet que 20 produits. Vous en avez déjà 20."
}
```

---

### Scénario 2 : Afficher le statut du forfait au commerçant

#### Frontend appelle

```javascript
async function loadSubscriptionStatus() {
  const response = await fetch('/api/v1/dashboard/subscription/status/');
  const data = await response.json();
  
  // Afficher les informations
  console.log(data.subscription); // Statut du forfait
  console.log(data.plan); // Détails du plan
  console.log(data.features); // Quelles fonctionnalités sont actives
  console.log(data.limits); // Limites actuelles
}
```

Réponse :
```json
{
  "success": true,
  "subscription": {
    "id": 5,
    "plan_name": "Pro",
    "plan_type": "pro",
    "is_active": true,
    "is_expired": false,
    "status": "active",
    "start_date": "2025-12-01",
    "end_date": "2025-12-31",
    "days_until_expiry": 22,
    "auto_renew": true
  },
  "plan": {
    "name": "Pro",
    "price": 25000,
    "description": "Pour les magasins qui veulent croître"
  },
  "features": {
    "max_products": null,
    "current_products": 45,
    "can_add_more_products": true,
    "has_statistics": true,
    "has_custom_page": true,
    "can_sponsor_products": true,
    "has_priority_support": true,
    "priority_listing": 2
  },
  "limits": {
    "products": {
      "current": 45,
      "max": null,
      "can_add_more": true,
      "message": "Produits illimités"
    }
  },
  "all_features": [
    "Produits illimités",
    "Statistiques et rapports de ventes",
    "Page personnalisée",
    "Produits sponsorisés",
    "Meilleure visibilité sur la plateforme",
    "Support VIP"
  ]
}
```

---

### Scénario 3 : Accès aux statistiques bloqué si forfait insuffisant

#### Dans une Vue Django

```python
from payments.subscription_check import SubscriptionChecker
from django.core.exceptions import PermissionDenied

def statistics_view(request):
    store = request.user.store
    
    # Vérifier que le magasin a le droit aux stats
    try:
        SubscriptionChecker.check_can_access_statistics(store)
    except PermissionDenied as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=403)
    
    # Afficher les statistiques...
    return JsonResponse({...})
```

---

### Scénario 4 : Webhook de paiement Flutterwave

```python
from payments.models import SubscriptionPlan, StoreSubscription
from django.utils import timezone
from datetime import timedelta

def handle_flutterwave_webhook(request):
    payload = json.loads(request.body)
    
    if payload['status'] == "successful":
        store_id = payload['meta']['store_id']
        plan_name = payload['meta']['plan']  # "pro", "business"
        
        store = Store.objects.get(id=store_id)
        plan = SubscriptionPlan.objects.get(slug=plan_name)
        
        # Créer/Mettre à jour l'abonnement
        subscription, created = StoreSubscription.objects.update_or_create(
            store=store,
            defaults={
                'plan': plan,
                'plan_name': plan.name,
                'monthly_fee': plan.price,
                'status': 'active',
                'start_date': timezone.now().date(),
                'end_date': timezone.now().date() + timedelta(days=30),
                'auto_renew': True
            }
        )
        
        return JsonResponse({'success': True})
```

---

## 📅 Tâches CRON Automatiques

### Configuration dans `celery_beat` (si vous utilisez Celery)

```python
# settings.py

CELERY_BEAT_SCHEDULE = {
    'check-expired-subscriptions': {
        'task': 'payments.tasks.check_expired_subscriptions',
        'schedule': crontab(hour=0, minute=0),  # Chaque jour à minuit
    },
    'send-expiry-reminders': {
        'task': 'payments.tasks.send_subscription_expiry_reminder',
        'schedule': crontab(hour=9, minute=0),  # Chaque jour à 9h
    },
}
```

### Ou avec APScheduler

```python
# Dans une command Django

from django.core.management.base import BaseCommand
from payments.tasks import check_expired_subscriptions

class Command(BaseCommand):
    def handle(self, *args, **options):
        result = check_expired_subscriptions()
        self.stdout.write(f"✅ {result['message']}")
```

---

## 🎯 Différences de Plan

### 🟦 Starter (Gratuit ou très bon marché)
- ✅ 20 produits max
- ❌ Pas de statistiques
- ❌ Pas de personnalisation
- ❌ Pas de produits sponsorisés
- ❌ Support basique

### 🟩 Pro (25 000 FCFA/mois)
- ✅ Produits illimités
- ✅ Statistiques avancées
- ✅ Personnalisation de boutique
- ✅ Produits sponsorisés
- ✅ Support VIP
- ✅ Meilleure visibilité

### 🟧 Business (50 000 FCFA/mois)
- ✅ Tout de Pro +
- ✅ Bannière personnalisée
- ✅ Support dédié
- ✅ Priorité maximale dans les résultats
- ✅ Intégrations avancées

---

## 💾 Structure des Données

### StoreSubscription
```python
{
  "id": 5,
  "store": 12,
  "plan": 2,  # FK vers SubscriptionPlan
  "status": "active",  # active, expired, suspended, pending_payment
  "start_date": "2025-12-01",
  "end_date": "2025-12-31",
  "auto_renew": true,
  "created_at": "2025-12-01T10:00:00Z",
  "updated_at": "2025-12-01T10:00:00Z"
}
```

### SubscriptionPlan
```python
{
  "id": 2,
  "name": "Pro",
  "slug": "pro",
  "plan_type": "pro",
  "price": 25000,  # FCFA/mois
  "max_products": null,  # null = illimité
  "can_sponsor_products": true,
  "has_statistics": true,
  "has_custom_page": true,
  "has_priority_support": true,
  "priority_listing": 2,  # Plus = plus visible
  "description": "Pour les magasins qui veulent croître",
  "is_active": true
}
```

---

## 🔥 Points Clés à Retenir

1. **Toujours utiliser `SubscriptionChecker`** pour les vérifications
2. **Les permissions sont vérifiées en temps réel** : pas de cache
3. **Les expirations sont gérées automatiquement** par Celery
4. **Chaque action sensible doit être protégée** : ajouter produit, stats, perso, sponsor
5. **Messages d'erreur clairs** : dites pourquoi on refuse, pas juste "non autorisé"
6. **Dashboard** : montrez les limites actuelles (ex: "15/20 produits")

---

## 🚨 Erreurs Courantes

❌ **Mauvais** : Vérifier le forfait via le champ `subscription_plan` du Store (obsolète)
```python
if store.subscription_plan == 'pro':  # ❌ NON!
    pass
```

✅ **Bon** : Utiliser le système temps réel
```python
if store.is_subscription_active():  # ✅ OUI!
    plan = store.get_current_plan()
    if plan.has_statistics:
        pass
```

---

## 📞 Support

Pour toute question sur l'implémentation, consulter :
- `payments/subscription_check.py` - Service de vérification
- `api/v1/subscription.py` - Endpoints API
- `payments/tasks.py` - Tâches automatisées
- `stores/models.py` - Méthodes de Store

