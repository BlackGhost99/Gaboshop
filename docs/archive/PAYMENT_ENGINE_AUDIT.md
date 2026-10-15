# Audit du moteur financier Gaboshop

## État initial constaté

- `payments.Payment` représentait un paiement unique par commande et ne pouvait pas distinguer produits, livraison et commission.
- le paiement cash était rejeté à l'entrée mais une branche historique pouvait encore le marquer comme réussi ;
- la fin de livraison déclenchait systématiquement un transfert SingPay au livreur ;
- la part livreur était calculée différemment selon les chemins (60 % ou 80 %) ;
- les reversements historiques supposaient que Gaboshop encaissait avant de payer le commerce ;
- les commissions étaient créées à l'état `paid`, ce qui ne couvre pas un commerce qui encaisse directement ;
- commande, paiement, commission et livraison étaient fortement liés par les signaux Django et le changement de statut global de la commande.

## Architecture retenue

Les anciennes tables restent en place pour les commandes et paiements existants. Les nouvelles commandes reçoivent un `PaymentArrangement` immuable qui mémorise le circuit choisi, les moyens de paiement, le taux de commission, les montants et une copie de la politique applicable.

Chaque mouvement attendu devient une `PaymentObligation` indépendante : produits, livraison, reversement livreur vers commerce, commission ou indemnité de course échouée. Les preuves (`PaymentReceipt`), remboursements/avoirs (`PaymentAdjustment`) et règlements groupés (`CommissionSettlement` + allocations) sont append-only et ne réécrivent pas les montants historiques.

## Circuits disponibles

- `direct_split` : produits vers commerce, livraison vers livreur ;
- `store_collects_all` : commerce encaisse, puis paie le livreur ;
- `courier_cash` : livreur collecte séparément produits et livraison, puis reverse les produits ;
- `platform_online` : Gaboshop encaisse via le compte marchand, seulement si SingPay est configuré.

La politique globale et les restrictions par commerce sont modifiables sans changement de code. Le lancement utilise par défaut la collecte cash par le livreur, avec suivi séparé de la dette de commission du commerce.

## Compatibilité et garde-fous

- une ancienne commande sans arrangement reste sérialisable ;
- les anciens modèles de paiement ne sont pas supprimés ;
- les nouveaux calculs utilisent `Decimal` ;
- les transferts automatiques sont désactivés pour les circuits manuels ;
- un paiement livreur déjà en traitement ou terminé ne peut pas être redéclenché ;
- preuve de livraison et statut livré sont requis avant un transfert automatique ;
- une déclaration cash reste en attente jusqu'à confirmation et reçoit un numéro de reçu ;
- les taux et montants de commission sont figés au moment de la commande.
- un déclarant ne peut ni confirmer ni refuser son propre reçu ou règlement cash ;
- les refus conservent le réviseur, la date et la justification ;
- l'assignation automatique, la réclamation libre et l'acceptation d'une course contrôlent le plafond cash du livreur ;
- les remboursements de l'ancien endpoint fournisseur créent aussi un ajustement dans le nouveau registre ;
- la synthèse `/api/v1/payments/financial-control/` expose dettes, retards, capacités et reçus en attente.

## Dépréciations

`Order.status == "paid"`, `SystemSettings.payment_before_order` et le paiement global historique restent disponibles pour compatibilité, mais ne doivent plus servir de source unique de vérité financière. La source de vérité des nouvelles commandes est l'arrangement et ses obligations.
