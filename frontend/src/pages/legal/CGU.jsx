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
          Aujourd'hui, {COMPANY.brand} <strong>n'encaisse pas l'argent des commandes</strong> : il n'y a pas encore
          d'agrégateur de paiement intégré. Le client paie directement le commerce, ou le livreur à la livraison :
        </p>
        <List
          items={[
            <><strong>En espèces</strong> au commerce ;</>,
            <><strong>Par Mobile Money</strong> (Airtel Money ou Moov Money), sur le code marchand du commerce affiché dans l'application ;</>,
            <><strong>En espèces au livreur</strong>, au moment de la livraison, lorsque le commerce accepte ce mode de paiement.</>,
          ]}
        />
        <p>
          Pour un paiement Mobile Money, le client doit <strong>saisir dans l'application la référence de la transaction</strong>{' '}
          (reçue par SMS). {COMPANY.brand} ne vous demandera jamais votre code secret (PIN) Mobile Money : ne le communiquez
          à personne.
        </p>
        <p>
          <strong>Une commande n'est préparée qu'une fois que le commerce a confirmé avoir reçu le paiement</strong>, ou,
          pour un paiement en espèces, au moment de la livraison.
        </p>
        <p>
          Déclarer un paiement qui n'a pas été fait (fausse référence, faux reçu, etc.) est une fraude. Elle entraîne la
          suspension du compte et peut faire l'objet de poursuites.
        </p>
      </Section>

      <Section title="6. Livraison">
        <List
          items={[
            "Les frais de livraison sont affichés avant la validation de la commande. Ils dépendent de la zone de livraison.",
            "La commande est remise par un livreur indépendant, à l'adresse indiquée par le client. Les délais sont donnés à titre indicatif.",
            "À la livraison, le client communique au livreur un code de confirmation (PIN de livraison) affiché dans son application. Ce code prouve que la commande a bien été remise : ne le donnez qu'une fois le colis reçu et vérifié.",
            "Le client doit être joignable et présent (ou désigner quelqu'un) à l'adresse indiquée. En cas d'absence, des frais peuvent rester dus.",
          ]}
        />
      </Section>

      <Section title="7. Annulation, retours et remboursements">
        <p>
          Les annulations, échanges, retours et remboursements sont gérés <strong>par le commerce</strong>, selon ses
          propres conditions et la loi gabonaise. Le client doit signaler tout problème (produit manquant, abîmé ou non
          conforme) rapidement, de préférence dès la livraison.
        </p>
        <p>
          En cas de désaccord, le client ou le commerce peut contacter {COMPANY.brand} à {COMPANY.contact}.{' '}
          {COMPANY.brand} joue alors un rôle de médiateur pour trouver une solution amiable, sans être tenu de rembourser
          à la place du commerce.
        </p>
      </Section>

      <Section title="8. Commission due par les commerces">
        <p>
          Les commerces doivent à {COMPANY.brand} une <strong>commission sur les ventes réalisées via l'application</strong>.
          Le taux applicable est affiché dans l'espace du commerce. Le commerce doit régler la commission dans le délai
          indiqué. À défaut, son compte peut être suspendu jusqu'au paiement complet.
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
