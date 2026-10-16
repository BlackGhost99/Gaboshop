import React from 'react';
import { Link } from 'react-router-dom';
import LegalLayout, { Section, List } from '../../legal/LegalLayout';
import { useCompany } from '../../legal/legalInfo';

const linkClass = 'text-indigo-600 underline hover:text-indigo-500';

export default function CGU() {
  const COMPANY = useCompany();
  return (
    <LegalLayout
      title="Conditions générales d'utilisation et de vente"
      intro={`Les présentes conditions (les « CGU ») encadrent l'utilisation de l'application et du site ${COMPANY.brand}, une place de marché en ligne qui met en relation, à Libreville et au Gabon, des clients, des commerces et des livreurs indépendants. En créant un compte ou en passant une commande, vous acceptez ces conditions.`}
    >
      <Section title="1. Qui fait quoi ?">
        <p>
          Le service est exploité par {COMPANY.operator}. Voir les <Link to="/mentions-legales" className={linkClass}>mentions légales</Link>.
        </p>
        <List
          items={[
            <><strong>Le client</strong> : la personne qui achète des produits via l'application.</>,
            <><strong>Le commerce</strong> : la boutique qui vend ses produits sur {COMPANY.brand}.</>,
            <><strong>Le livreur</strong> : une personne indépendante qui livre les commandes.</>,
            <><strong>{COMPANY.brand}</strong> : la plateforme qui met ces personnes en relation et administre le service.</>,
          ]}
        />
      </Section>

      <Section title="2. Rôle de Gaboshop : un intermédiaire">
        <p>
          {COMPANY.brand} n'est pas le vendeur des produits. <strong>Le vendeur est le commerce.</strong> Le contrat de vente
          est conclu directement entre le client et le commerce.
        </p>
        <p>
          Le commerce est seul responsable de ses produits : description, photos, prix, disponibilité du stock, qualité,
          conformité, garantie et service après-vente. {COMPANY.brand} fournit l'outil technique (catalogue, commandes,
          suivi, livraison) et peut aider à résoudre les litiges, mais ne garantit pas les produits vendus par les commerces.
        </p>
      </Section>

      <Section title="3. Comptes utilisateurs">
        <p>Il existe trois types de comptes : client, commerce et livreur.</p>
        <List
          items={[
            "Vous devez donner des informations exactes et à jour (nom, numéro de téléphone, adresse, informations de la boutique ou du véhicule).",
            "Votre compte est personnel. Gardez votre mot de passe secret : toute action faite depuis votre compte est considérée comme faite par vous.",
            "Prévenez-nous rapidement si vous pensez que quelqu'un utilise votre compte sans votre accord.",
            `${COMPANY.brand} peut vérifier les informations des commerces et des livreurs et refuser ou suspendre un compte si elles sont fausses ou incomplètes.`,
          ]}
        />
      </Section>

      <Section title="4. Commandes">
        <List
          items={[
            "Le client choisit ses produits, vérifie son panier, l'adresse de livraison et le montant total (produits + frais de livraison), puis valide sa commande.",
            "La commande est transmise au commerce, qui l'accepte ou la refuse (par exemple si un produit n'est plus en stock).",
            "La vente est définitive lorsque le commerce a confirmé la commande et, pour un paiement à l'avance, la réception du paiement.",
            "Les prix sont indiqués en francs CFA (FCFA). Ils sont fixés par le commerce, qui doit les tenir à jour.",
          ]}
        />
      </Section>

      <Section title="5. Paiement">
        <p>
          Plusieurs circuits de paiement peuvent être proposés selon le commerce, la commande et les options
          effectivement activées lors de la validation du panier. Le client voit avant de confirmer sa commande
          le montant à payer, les frais de livraison et le bénéficiaire du paiement.
        </p>
        <List
          items={[
            <>Paiement direct au commerce : en espèces, par Mobile Money ou par un autre moyen proposé à l'écran de commande.</>,
            <>Paiement au livreur ou paiement intégral au commerce : uniquement lorsque cette option est effectivement proposée au panier.</>,
            <>Paiement en ligne via un prestataire, lorsque ce service est activé : le paiement est initié depuis {COMPANY.brand},
              puis son statut est vérifié auprès du prestataire. Les parts dues au commerce, au livreur et à la plateforme
              font l'objet d'un suivi distinct.</>,
          ]}
        />
        <p>
          Les modes et frais disponibles peuvent varier selon la commande. Pour un paiement Mobile Money réalisé
          directement au commerce ou à un livreur, une référence ou une preuve peut être demandée pour vérifier
          le règlement. Une déclaration de paiement ne constitue pas, à elle seule, une confirmation de réception.
          Ne communiquez jamais votre code secret (PIN) Mobile Money à qui que ce soit.
        </p>
        <p>
          Le démarrage de la préparation et de la livraison dépend du mode choisi et des confirmations
          requises. Un paiement initié, mais non confirmé, ne vaut pas paiement reçu.
          Les reversements aux bénéficiaires sont soumis aux vérifications financières et aux conditions
          applicables au circuit sélectionné ; leur automatisation n'est pas garantie.
        </p>
      </Section>

      <Section title="6. Livraison">
        <List
          items={[
            "Les frais de livraison sont affichés avant la validation de la commande. Ils dépendent de la zone de livraison.",
            "La livraison peut être assurée par un livreur partenaire de Gaboshop ou par le commerce lorsque ce mode est proposé. Les délais communiqués sont indicatifs ; tout retard important peut être signalé au support.",
            "Lorsqu'un code de confirmation de livraison est demandé, le client ne le communique qu'après réception et contrôle du colis. Les modalités peuvent différer lorsque le commerce livre lui-même.",
            "Le client doit être joignable et présent (ou désigner quelqu'un) à l'adresse indiquée. En cas d'absence, des frais peuvent rester dus.",
          ]}
        />
      </Section>

      <Section title="7. Annulation, rétractation, retours et remboursements">
        <p>
          Une commande peut faire l'objet d'une demande d'annulation avant sa livraison. Les suites données
          dépendent notamment de la préparation, de la prise en charge du colis, du paiement reçu et des
          éventuels frais déjà engagés. Une annulation de commande ne constitue pas une preuve de remboursement.
        </p>
        <p>
          Pour les contrats à distance avec les consommateurs, le droit de rétractation prévu par la loi
          gabonaise n°025/2021 s'applique, lorsqu'il est ouvert, dans un délai de quatorze jours calendaires :
          à compter de la livraison du bien ou de la conclusion du contrat de service. Des exceptions légales
          existent, notamment pour certains biens périssables, personnalisés ou descellés pour des raisons
          d'hygiène. Le commerce et {COMPANY.brand} ne peuvent supprimer un droit impératif par leurs propres conditions.
        </p>
        <p>
          Lorsqu'un remboursement est dû, son montant, son délai, le traitement des frais de livraison et le
          moyen de remboursement doivent respecter la loi applicable. Dans les cas prévus par celle-ci, les
          paiements reçus, frais de livraison compris, sont remboursés au plus tard sous quatorze jours
          calendaires suivant l'information de la rétractation, avec les règles légales relatives au retour du bien.
        </p>
        <p>
          Si le client a payé directement le commerce, celui-ci reste l'interlocuteur du règlement et du
          remboursement dû. Si un paiement est passé par un prestataire en ligne, son remboursement doit être
          vérifié et suivi dans le circuit concerné ; aucune opération ne sera présentée comme exécutée
          avant sa confirmation. Une réclamation peut être adressée à {COMPANY.brand} via {COMPANY.contact}
          afin d'en assurer le suivi avec le commerce et le prestataire, sans préjudice des droits du consommateur.
        </p>
      </Section>

      <Section title="8. Commission due par les commerces">
        <p>
          Les commissions applicables à une vente dépendent des catégories de produits et, lorsqu'il existe,
          du forfait professionnel concerné. Elles sont calculées selon les règles et montants affichés
          dans l'espace du commerce. Selon le circuit de paiement, elles peuvent être retenues sur le
          versement au commerce ou faire l'objet d'une dette à régler dans le délai indiqué.
          En cas d'impayé vérifié, le compte peut faire l'objet de mesures prévues par les présentes conditions.
        </p>
      </Section>

      <Section title="9. Interdiction de contourner la plateforme">
        <p>
          Il est interdit aux commerces et aux clients d'utiliser {COMPANY.brand} pour se trouver, puis de conclure la
          vente <strong>en dehors de l'application</strong> afin d'éviter la commission (par exemple : inviter un client
          rencontré via l'application à commander directement par téléphone pour ne pas payer de commission).
        </p>
        <p>
          En cas de contournement constaté, le compte concerné peut être suspendu ou fermé, et{' '}
          <strong>la commission reste due</strong> sur les ventes concernées.
        </p>
      </Section>

      <Section title="10. Obligations des livreurs">
        <List
          items={[
            "Le livreur est indépendant. Il est responsable de son véhicule, de ses papiers, de son assurance et du respect du code de la route.",
            "Il transporte les commandes avec soin et les remet uniquement au client (ou à la personne désignée), contre le code de confirmation.",
            "L'argent encaissé pour le compte d'autrui (paiement en espèces à la livraison) doit être reversé intégralement et dans les délais au commerce ou à la personne indiquée dans l'application. Tout manquement entraîne la suspension du compte et peut faire l'objet de poursuites.",
            "Les photos et preuves de livraison doivent être exactes.",
          ]}
        />
      </Section>

      <Section title="11. Assistant intelligent (IA)">
        <p>
          L'application propose un assistant intelligent qui répond aux questions et aide à effectuer certaines actions.
          Ses réponses sont générées automatiquement et <strong>peuvent contenir des erreurs</strong> : vérifiez les
          informations importantes (prix, disponibilité, montants).
        </p>
        <p>
          Toute action qui modifie vos données (passer ou annuler une commande, modifier un produit, etc.){' '}
          <strong>vous est toujours présentée pour confirmation</strong> avant d'être exécutée. Voir la{' '}
          <Link to="/confidentialite" className={linkClass}>politique de confidentialité</Link> pour l'utilisation de vos messages.
        </p>
      </Section>

      <Section title="12. Contenus et produits interdits">
        <p>Il est interdit de publier, vendre ou commander via {COMPANY.brand} :</p>
        <List
          items={[
            "des produits illégaux au Gabon : drogues, armes et munitions, médicaments sans autorisation, espèces protégées, produits volés ou de contrefaçon ;",
            "des produits dangereux, périmés ou non conformes ;",
            "des contenus trompeurs, injurieux, discriminatoires, violents, pornographiques ou portant atteinte aux droits d'autrui (photos ou marques copiées sans autorisation) ;",
            "tout moyen de fraude, de spam ou de piratage de l'application.",
          ]}
        />
        <p>{COMPANY.brand} peut retirer sans préavis tout produit ou contenu contraire à ces règles.</p>
      </Section>

      <Section title="13. Responsabilité">
        <List
          items={[
            `${COMPANY.brand} fait de son mieux pour que le service fonctionne, mais ne peut garantir une disponibilité sans interruption (pannes, maintenance, réseau internet ou mobile).`,
            `${COMPANY.brand} n'est pas responsable des produits vendus par les commerces, ni des paiements effectués directement entre client, commerce et livreur, ni des retards dus à des événements extérieurs (intempéries, circulation, coupures, etc.).`,
            `La responsabilité de ${COMPANY.brand}, si elle est engagée, est limitée aux dommages directs et prouvés, dans les limites prévues par la loi gabonaise.`,
          ]}
        />
      </Section>

      <Section title="14. Suspension et fermeture de compte">
        <p>
          {COMPANY.brand} peut suspendre ou fermer un compte, après avertissement lorsque c'est possible, en cas de
          non-respect de ces conditions, de fraude, de fausse déclaration de paiement, de commission impayée, de
          contournement de la plateforme ou de comportement abusif. Les sommes dues restent exigibles.
        </p>
        <p>
          Vous pouvez fermer votre compte à tout moment : voir la page{' '}
          <Link to="/suppression-compte" className={linkClass}>suppression du compte</Link>.
        </p>
      </Section>

      <Section title="15. Modification des conditions">
        <p>
          Ces conditions peuvent évoluer (par exemple lors de l'ajout d'un paiement en ligne). La date de mise à jour est
          indiquée en haut de cette page. En cas de changement important, vous serez informé dans l'application. Continuer
          à utiliser {COMPANY.brand} après la mise à jour vaut acceptation des nouvelles conditions.
        </p>
      </Section>

      <Section title="16. Droit applicable et litiges">
        <p>
          Ces conditions sont soumises au <strong>droit gabonais</strong>. En cas de litige, les parties chercheront
          d'abord une solution amiable. À défaut, les <strong>tribunaux compétents de Libreville</strong> seront saisis.
        </p>
        <p>
          Contact : {[COMPANY.email, COMPANY.phone].filter(Boolean).join(' · ') || COMPANY.contact}
        </p>
      </Section>
    </LegalLayout>
  );
}
