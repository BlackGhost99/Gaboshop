# Jour 1 — Circuits de paiement pour le lancement pilote

Décision du propriétaire : Gaboshop proposera les paiements directs **et** SingPay quand les conditions opérationnelles et réglementaires seront satisfaites. Aucune mise en service SingPay n'est autorisée par cette seule décision.

## Règles communes
- Le client choisit exactement **un circuit de paiement** par commande. Son choix, la part articles, la part livraison et le bénéficiaire doivent être visibles avant validation.
- Aucune simple déclaration du client ne vaut preuve d'un encaissement : le bénéficiaire ou SingPay doit confirmer.
- Les obligations de paiement exigées avant l'expédition doivent être soldées avant de lancer le livreur.
- La commission est calculée selon les articles/catégories et le plan réellement actif. La marge livraison et les frais du prestataire sont séparés.
- Une annulation n'est pas un remboursement. Le remboursement ne passe à « effectué » qu'après confirmation de la sortie d'argent par le payeur concerné.
- Les droits du consommateur, notamment les dispositions applicables de la loi gabonaise n°025/2021 sur la rétractation et ses exceptions, priment sur les règles internes.

## Matrice opérationnelle

| Code | Encaissement | Livraison | Vérification | Responsable pratique du remboursement |
|---|---|---|---|---|
| `direct_split` | Client verse les articles au commerce | Client règle séparément le livreur | Commerce et livreur confirment chacun leur part | Chaque personne qui a reçu l'argent restitue sa part due ; Gaboshop suit le dossier |
| `store_collects_all` | Client verse articles + livraison au commerce | Le commerce rémunère le livreur | Confirmation par le commerce, rapprochement du livreur | Le commerce prend en charge les fonds qu'il a encaissés |
| `courier_cash` | **Désactivé pour le pilote B2C** : aucun livreur Gaboshop ne collecte d'espèces | — | Le serveur refuse cette option au panier | Les anciens flux restent consultables pour l'historique |
| `platform_online` | Client paie Airtel/Moov via SingPay | Part commerçant/livreur selon circuit et contrat | Confirmation prestataire, jamais simple capture | Gaboshop coordonne avec le PSP ; confirmation réelle obligatoire pour annoncer le remboursement |

### Exemple : 70 000 FCFA d'articles + 2 000 FCFA de livraison
- Direct séparé : 70 000 reçus par le commerce, 2 000 par le livreur.
- Tout au commerce : 72 000 reçus par le commerce ; il règle ensuite le livreur.
- Espèces livreur : 72 000 collectés par le livreur, dont 70 000 à remettre au commerce.
- En ligne : 72 000 initialement encaissés via SingPay ; répartitions et frais réels à rapprocher séparément, sans taux PSP inventé.

Les commissions Gaboshop, la marge de livraison et les frais de paiement dépendent de la configuration et des accords réellement en vigueur : cet exemple n'établit aucun taux commercial.

## Conditions bloquantes pour activer SingPay en production
1. Confirmer par écrit le contrat, le rôle réglementaire du PSP, la possibilité de répartir les fonds d'une marketplace et les conditions d'éligibilité de Gaboshop.
2. Tester les paiements Airtel et Moov en conditions réelles à faible montant et identifier les références, erreurs, paiements différés et éventuels doubles paiements.
3. Définir la procédure de versement et son rapprochement quotidien, même si les transferts automatiques sont désactivés (`SINGPAY_ENABLE_TRANSFER=False` dans `render.yaml`).
4. Valider les remboursements partiels, complets, le traitement des litiges et l'impossibilité de déclarer un remboursement sans justificatif.
5. Examiner la règle `is_trusted` : certains commerces sont éligibles au versement dès la préparation, contrairement à la règle générale après réception. Le lancement exige une décision spécifique sur cet avantage.

## Configuration du pilote
- Par défaut : `direct_split`, sous réserve de la validation de l'administrateur.
- Autoriser simultanément `direct_split`, `store_collects_all`, `courier_cash` et `platform_online` seulement si les options correspondantes sont vérifiées.
- Les paiements directs Mobile Money exigent des instructions vérifiables du commerce ; les espèces au livreur exigent une livraison et une procédure de remise d'espèces.
- L'affichage B2C initial masquait les paiements directs lorsque SingPay était prêt. Correction réalisée **sur la branche de revue uniquement**, avec tests ; aucune activation en production.
- Vérifier les réglages réellement stockés en base : les valeurs du code ne prouvent pas les options en vigueur.

## Décisions du propriétaire encore nécessaires
1. Activer les **espèces au livreur** dès le début ou après une période de contrôle ?
2. Suspendre les versements anticipés aux commerces `is_trusted` pendant le pilote ?
3. Qui effectue le rapprochement quotidien des transactions et valide les remboursements ?
4. Confirmer les taux de commission, frais de service et marges de livraison effectivement appliqués.

Références : `payments/configuration.py`, `payments/direct_service.py`, `payments/store_payout_service.py`, `frontend/src/pages/legal/CGU.jsx`; Journal officiel du Gabon, loi n°025/2021 : https://journal-officiel.ga/18190-025-2021-/. Revue juridique locale requise avant publication des clauses définitives.
