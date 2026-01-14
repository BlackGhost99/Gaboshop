# Plan d'implémentation : Account Manager dédié pour plans Business B2B

## Vue d'ensemble

Implémentation d'un système d'Account Manager dédié permettant aux stores B2B avec plan Business d'avoir un contact privilégié pour le support, le suivi et l'accompagnement.

## Architecture

### 1. Modèle de données

**Fichier**: `b2b/models/account_manager.py` (nouveau fichier)

Créer un nouveau modèle `AccountManager` :
- `user` (ForeignKey vers User) - L'utilisateur qui est Account Manager
- `stores` (ManyToMany vers Store) - Les stores assignés
- `is_active` (BooleanField) - Si l'Account Manager est actif
- `specialization` (CharField) - Spécialisation (ex: "B2B Wholesalers", "High Volume")
- `phone` (CharField) - Téléphone de contact direct
- `email` (EmailField) - Email de contact
- `whatsapp` (CharField, optionnel) - WhatsApp Business
- `notes` (TextField) - Notes internes
- `created_at`, `updated_at` (DateTimeField)

**Fichier**: `stores/models.py`

Ajouter au modèle `Store` :
- `account_manager` (ForeignKey vers AccountManager, null=True, blank=True)
- Méthode `get_account_manager()` qui retourne l'Account Manager si le store a un plan Business B2B

### 2. Permissions et accès

**Fichier**: `b2b/permissions.py` (nouveau fichier ou extension)

Créer une permission `IsAccountManager` :
- Vérifie si l'utilisateur est un Account Manager actif
- Permet l'accès aux vues dédiées aux Account Managers

### 3. API Backend

**Fichier**: `api/v1/account_managers.py` (nouveau fichier)

Endpoints pour les Account Managers :
- `GET /api/v1/account-managers/` - Liste des Account Managers (admin uniquement)
- `GET /api/v1/account-managers/<id>/` - Détails d'un Account Manager
- `POST /api/v1/account-managers/` - Créer un Account Manager (admin)
- `PATCH /api/v1/account-managers/<id>/` - Modifier un Account Manager (admin)
- `POST /api/v1/account-managers/<id>/assign-store/<store_id>/` - Assigner un store
- `DELETE /api/v1/account-managers/<id>/unassign-store/<store_id>/` - Retirer un store

Endpoints pour les stores :
- `GET /api/v1/store/account-manager/` - Récupérer l'Account Manager du store actuel
- `GET /api/v1/store/account-manager/contact/` - Informations de contact de l'Account Manager

Endpoints pour les Account Managers (dashboard) :
- `GET /api/v1/account-managers/me/stores/` - Liste des stores assignés
- `GET /api/v1/account-managers/me/stores/<store_id>/stats/` - Statistiques d'un store
- `GET /api/v1/account-managers/me/stores/<store_id>/finance/` - Rapports financiers d'un store

**Fichier**: `api/v1/urls.py`

Ajouter les routes pour les endpoints Account Manager.

### 4. Serializers

**Fichier**: `b2b/serializers/account_manager.py` (nouveau fichier)

- `AccountManagerSerializer` - Serializer de base
- `AccountManagerDetailSerializer` - Avec stores assignés
- `StoreAccountManagerSerializer` - Vue store (informations de contact uniquement)
- `AccountManagerStoreSerializer` - Vue Account Manager (stats stores)

### 5. Services

**Fichier**: `b2b/services/account_manager.py` (nouveau fichier)

- `assign_account_manager_to_store(store, account_manager)` - Assigner un Account Manager
- `get_store_account_manager(store)` - Récupérer l'Account Manager d'un store
- `get_account_manager_stores(account_manager)` - Liste des stores d'un Account Manager
- `can_have_account_manager(store)` - Vérifie si le store peut avoir un Account Manager (plan Business B2B)

### 6. Admin Django

**Fichier**: `b2b/admin.py`

Ajouter `AccountManagerAdmin` avec :
- Interface pour assigner/désassigner des stores
- Filtres par spécialisation, statut
- Actions en masse

### 7. Frontend - Store Dashboard

**Fichier**: `frontend/src/components/AccountManagerCard.jsx` (nouveau fichier)

Composant affichant :
- Nom et photo de l'Account Manager
- Coordonnées (téléphone, email, WhatsApp)
- Bouton "Contacter mon Account Manager"
- Badge "Account Manager dédié" (Business B2B uniquement)

**Fichier**: `frontend/src/pages/store/StoreDashboard.jsx`

Ajouter la `AccountManagerCard` dans le dashboard si le store a un plan Business B2B.

**Fichier**: `frontend/src/services/accountManagerService.js` (nouveau fichier)

Services API :
- `getStoreAccountManager()`
- `getAccountManagerContact()`

### 8. Frontend - Admin Dashboard

**Fichier**: `frontend/src/pages/admin/AccountManagers.jsx` (nouveau fichier)

Page admin pour :
- Liste des Account Managers
- Créer/modifier des Account Managers
- Assigner/désassigner des stores
- Voir les statistiques par Account Manager

**Fichier**: `frontend/src/components/admin/AccountManagerModal.jsx` (nouveau fichier)

Modal pour créer/modifier un Account Manager.

### 9. Frontend - Account Manager Dashboard

**Fichier**: `frontend/src/pages/account-manager/AccountManagerDashboard.jsx` (nouveau fichier)

Dashboard pour les Account Managers avec :
- Liste des stores assignés
- Statistiques globales
- Accès rapide aux rapports financiers de chaque store
- Historique des interactions

### 10. Intégration avec le plan Business

**Fichier**: `stores/models.py`

Modifier `get_current_b2b_plan()` pour vérifier si le plan Business a `has_priority_support=True` (qui inclut Account Manager).

**Fichier**: `api/v1/dashboards.py`

Ajouter les informations de l'Account Manager dans la réponse du `StoreDashboardView` si le store a un plan Business B2B.

## Migration

**Fichier**: `b2b/migrations/XXXX_add_account_manager.py` (nouveau fichier)

- Créer le modèle `AccountManager`
- Ajouter le champ `account_manager` au modèle `Store`
- Créer des Account Managers initiaux si nécessaire

## Tests

- Vérifier qu'un store Business B2B peut voir son Account Manager
- Vérifier qu'un store non-Business ne peut pas avoir d'Account Manager
- Vérifier les permissions (seuls les admins peuvent créer/assigner)
- Vérifier que l'Account Manager peut voir ses stores assignés

## Ordre d'implémentation

1. Modèle `AccountManager` et migration
2. Services et permissions
3. API Backend (endpoints store)
4. Frontend Store Dashboard (affichage Account Manager)
5. API Backend (endpoints admin)
6. Frontend Admin Dashboard
7. API Backend (endpoints Account Manager)
8. Frontend Account Manager Dashboard
9. Tests et vérifications
