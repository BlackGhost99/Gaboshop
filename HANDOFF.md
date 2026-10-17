# Gaboshop : passation pour une autre IA ou un développeur

Ce fichier dit ce qu'il faut savoir pour continuer le projet sans tout redécouvrir. Il ne contient ni mot de passe ni clé :
ils sont dans Render (variables d'environnement) et dans les secrets GitHub Actions. Ne jamais les écrire dans le code ou
dans une conversation.

Dernière mise à jour : 16 octobre 2026.

## 1. Le propriétaire et sa façon de travailler

- Il écrit en français, vite et sans formalités. Répondez en français, en mots simples et courts.
- Il ne veut plus avoir besoin de son PC : il envoie des demandes, l'IA code, pousse sur GitHub, et Render déploie.
- Il vérifie sur le site de test avant le vrai site.
- Il ne paie aucune API d'IA payante : l'assistant utilise une clé Groq gratuite.

## 2. Règles à respecter

1. **Site de test d'abord.** Travaillez sur la branche `staging`. Le propriétaire teste, puis on envoie sur `main`.
2. **Rien ne part sur `main` (le vrai site) sans son accord explicite**, surtout ce qui touche l'argent ou les prix.
3. **Aucun changement de prix ou de taux sur le vrai site sans son accord.**
4. **Jamais de secret dans le code, les commits ou le chat.**
5. **Ne jamais mettre `PAYMENTS_SIMULATED` ni `PAYMENTS_DISABLED` sur la prod.** Ils servent uniquement sur le site de test.
6. **Messages pros.** Une erreur dit clairement pourquoi et comment régler. Utilisez `notifications/messages.py` côté
   serveur, et `frontend/src/utils/feedback.js` (`notifyError`, `describeError`…) côté écran. Jamais `alert()`.
7. **Ne bloquez jamais un commerce faute de forfait.** Sans abonnement, il est au forfait Gratuit (20 produits).
8. **Tests :** `python manage.py test <apps>`, sans `--parallel`. Les tests qui créent des commandes appellent
   `cache.clear()` dans `setUp`.

## 3. Où tourne quoi

| Élément | Adresse / lieu |
|---|---|
| Code | github.com/BlackGhost99/Gaboshop |
| Vrai site (web) | https://gaboshop-web-welf.onrender.com (branche `main`) |
| Vraie API | https://gaboshop-api.onrender.com (admin Django : `/admin`) |
| Site de test (web) | https://gaboshop-web-staging-uvn1.onrender.com (branche `staging`, fichier `render-staging.yaml`) |
| API de test | https://gaboshop-api-staging-uvn1.onrender.com |
| Base de données prod | Supabase (variables DATABASE_HOST, DATABASE_NAME, DATABASE_USER, DATABASE_PASSWORD sur Render) |
| Base de test | Postgres gratuit de Render, séparée de la prod |
| Application Android | Construite à chaque push sur `main` : release `android-latest` (gaboshop.apk) |
| Play Store | Workflow « Version Play Store », AAB signé dans la release `android-playstore` |

Le Render gratuit s'endort : la première requête peut attendre environ 50 s. Son disque est effacé à chaque déploiement, c'est
pourquoi les images envoyées sont stockées en base (`core.StoredFile`, `core/storage.py`).

## 4. Outils GitHub Actions utiles

- **Vérifier les sites en ligne :** poussez un commit sur `refs/heads/site-check`. Le résultat se lit dans la release
  `site-check` (`.github/scripts/site_check.py`, liste SITES et MARKERS).
- **Sauvegarde chiffrée de la base chaque nuit :** `db-backup.yml`, conservée 30 jours. La phrase de passe est gardée
  par le propriétaire, hors de GitHub.
- **Tâches automatiques :** il n'y a pas de worker Celery sur Render. `scheduler.yml` appelle un point protégé toutes les
  10 minutes, de jour.

## 5. Ce qui existe (grandes lignes)

- **Rôles :** admin, commerce (B2C et B2B grossiste), client, livreur.
- **Paiement en ligne SingPay** (Airtel Money et Moov Money), en `payments/`. Les clés SingPay sont sur la vraie API.
  Gaboshop garde l'argent puis paie le commerce quand le client confirme la réception (`payments/store_payout_service.py`).
  SingPay prend 2,5 % par transaction.
- **Paiement direct** (espèces, ou Mobile Money vers le code marchand du commerce) :
  - le client saisit l'identifiant de transaction et le commerce confirme ;
  - à la livraison, l'espèce est validée par le code PIN ;
  - la commission due s'accumule en dette par commerce.
- **Commission :** le taux de la catégorie de produit, sinon celui du commerce. B2B à 3 %.
  Simulateur : Admin › « Combien gagne Gaboshop ? ».
- **Forfaits commerces :** Gratuit par défaut, Pro à 10 000 F, Business visible mais grisé « Bientôt disponible »
  (`is_available=False`). Code : `payments/default_plans.py`.
  - Une seule règle « ce forfait donne-t-il l'outil X ? » : `payments/plan_features.py` (`has`). Le serveur, les cartes
    et le tableau de bord la lisent. Une carte ne montre que ce que le code applique (`keep_free_text`).
  - Pro donne : plus de produits, page Statistiques, exports Excel/CSV et PDF, import de produits par fichier,
    alertes de stock, promotions (prix barré), badge « Pro ». Grossistes : pareil sans promotions ; un grossiste
    ne commande jamais chez un autre grossiste (`must_be_b2c_store`), donc aucune carte ne promet l'approvisionnement.
  - Les conseils « Passez au forfait X » viennent de `plan_for_sale` (`payments/plan_features.py`) : seulement un
    forfait en vente qui donne vraiment la chose. Le Gratuit n'affiche jamais de date de fin.
  - Piège : à l'expiration, un signal crée une ligne Gratuit valable 100 ans. Cherchez toujours l'abonnement actif
    avec `Store.get_active_subscription()` (ordre `payments.models.paid_first()`).
  - Le paiement d'un forfait par carte (CinetPay) est refusé : seulement Airtel Money et Moov Money.
- **Adresses :** Province › Ville › Arrondissement › Quartier, puis une zone phare facultative et un repère libre.
  - Le code est dans `delivery/geo_data.py`, `delivery/zones.py` et `api/v1/geo.py`. L'écran admin est dans Admin › Livraison › Adresses.
  - Les 9 provinces existent, mais seule Libreville est ouverte.
  - Le prix de livraison vient de la zone de prix du quartier (DeliveryZone, à régler dans l'onglet Tarifs).
  - Libreville suit la loi 020/2025 (migration delivery 0019) ; les secteurs partagés (PK10–PK12, Plaine Orety)
    restent sans arrondissement et sont proposés dans chaque arrondissement.
- **Grandes surfaces :** une catégorie de magasin peut avoir « Vend de tout » (`StoreCategory.sells_everything`).
- **Produits à tailles et couleurs :** le client choisit la taille et la couleur au panier (`products/options.py`).
  Le stock n'est pas suivi par taille.
- **Facture PDF Gaboshop** par commande : `orders/invoice.py`, à l'adresse `/orders/<id>/invoice/`.
- **Assistant IA :**
  - Code dans `api/v1/ai/`. Il s'adapte au rôle connecté et agit après un bouton « Confirmer ».
  - Il propose un mode voix.
  - Sans clé Groq, un moteur local répond.
  - État de l'assistant : `/api/v1/ai/assistant/status/`.
- **Notifications (boîte, alertes téléphone/ordinateur, annonces) :**
  - Une notification est enregistrée en base (`notifications/models.py`), avec un lien par rôle (`notifications/links.py`).
    La cloche, la page `/notifications` et la barre du bas (`MobileTabBar`) lisent le même compteur
    (`frontend/src/context/NotificationContext.jsx`, appel léger toutes les 20 s).
  - Alertes quand le site est fermé = Web Push (`notifications/push.py`, `public/sw.js`). Les clés VAPID se créent seules
    en base au premier besoin ; `VAPID_PUBLIC_KEY` / `VAPID_PRIVATE_KEY` dans Render les remplaceraient, `PUSH_ENABLED=0` coupe tout.
    Seules les adresses des vrais services d'alertes (Google, Mozilla, Apple, Windows) sont acceptées à l'inscription.
  - Admin › Annonces : un message à tous les clients, commerces, livreurs ou à l'admin seul (essai). Entre 21 h et 7 h
    (Libreville) l'alerte téléphone attend 7 h, sauf annonce « urgente » ; la tâche automatique `annonces_differees` l'envoie.
  - L'application Android (APK) n'a pas Web Push : elle voit la cloche, mais l'alerte application fermée demande Firebase
    (`PushSubscription.kind='fcm'` est prévu, rien n'est branché ; le propriétaire doit créer un projet Firebase).
  - iPhone : les alertes ne marchent que si le site est ajouté à l'écran d'accueil.
- **Anti-fraude :**
  - Un nouveau commerce est invisible tant que l'admin ne l'a pas validé.
  - Le « Gardien anti-fraude » est en place.
  - Les mots de passe faibles sont refusés, et un compte est bloqué après 10 échecs de connexion.

## 6. Reste à faire ou en attente du propriétaire

- **Carte livreur** façon Uber ou Gozem, pour suivre le client. Des coordonnées sont déjà prévues sur les quartiers, les
  zones phares et les livraisons.
- **Adresses :**
  - vérifier les quartiers et leurs arrondissements ;
  - créer les zones de prix de Libreville ;
  - les adresses des commerces n'utilisent pas encore ce référentiel.
- **Clés SMS ou e-mail** (Twilio ou Brevo) : c'est au propriétaire de les mettre dans Render. Sans elles, un mot de passe
  oublié ne peut pas être récupéré. Il le sait, inutile de le lui rappeler.
- **Société et cadre légal :**
  - les informations de la société sont à remplir ;
  - un avocat local doit valider les textes ;
  - il faut demander à SingPay si les versements aux commerces sont facturés.
- **Sponsoring et petits frais panier :** déjà codés, mais éteints dans Configuration.

## 7. Historique et décisions

- Chaque changement est expliqué dans son message de commit : lisez `git log`.
- Les rapports détaillés et la mémoire des décisions sont dans le projet Claude du propriétaire, pas dans ce dépôt :
  modèle économique, contrôles de sécurité, simulation Libreville. Demandez-les au propriétaire si besoin.
