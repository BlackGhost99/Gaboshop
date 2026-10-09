import React from 'react';
import { Link } from 'react-router-dom';
import LegalLayout, { Section, List } from '../../legal/LegalLayout';
import { useCompany } from '../../legal/legalInfo';

const linkClass = 'text-indigo-600 underline hover:text-indigo-500';

export default function Confidentialite() {
  const COMPANY = useCompany();
  return (
    <LegalLayout
      title="Politique de confidentialité"
      intro={`Cette politique explique quelles données personnelles ${COMPANY.brand} collecte, pourquoi, avec qui elles sont partagées, combien de temps elles sont gardées et quels sont vos droits. Elle s'applique à l'application mobile et au site ${COMPANY.brand}.`}
    >
      <Section title="1. Responsable du traitement et cadre légal">
        <p>
          Le responsable du traitement est {COMPANY.operator}.
          Contact : {COMPANY.contact}.
        </p>
        <p>
          Nous traitons vos données conformément à la <strong>loi n°001/2011 du 25 septembre 2011 relative à la protection
          des données à caractère personnel</strong> en République gabonaise. L'autorité de contrôle est la{' '}
          <strong>CNPDCP</strong> (Commission Nationale pour la Protection des Données à Caractère Personnel).
        </p>
      </Section>

      <Section title="2. Données que nous collectons">
        <p><strong>Pour tous les utilisateurs :</strong></p>
        <List
          items={[
            "nom et prénom, numéro de téléphone, adresse e-mail si vous la donnez, mot de passe (enregistré de façon chiffrée) ;",
            "adresses de livraison, quartier et zone de livraison ;",
            "historique des commandes et des paiements : montants, mode de paiement, références de transaction Mobile Money ;",
            "messages envoyés à l'assistant intelligent ;",
            "données techniques : type d'appareil, journaux de connexion, nécessaires à la sécurité et au bon fonctionnement.",
          ]}
        />
        <p>
          <strong>Nous ne demandons jamais votre code secret (PIN) Mobile Money.</strong> Seule la référence de la
          transaction est enregistrée. Si quelqu'un vous demande votre PIN au nom de {COMPANY.brand}, c'est une arnaque.
        </p>
        <p><strong>Pour les commerces :</strong> nom et informations de la boutique, coordonnées du gérant, adresse,
          code marchand Mobile Money, produits, prix et photos des produits, ventes et commissions.</p>
        <p><strong>Pour les livreurs :</strong> identité, coordonnées, type de véhicule et immatriculation, zone
          d'activité, livraisons effectuées, preuves de livraison (photos, codes de confirmation) et sommes encaissées
          pour le compte d'autrui.</p>
      </Section>

      <Section title="3. Microphone et commande vocale">
        <List
          items={[
            "Le microphone est utilisé uniquement lorsque vous appuyez sur le bouton micro. Il n'écoute jamais en arrière-plan.",
            "Votre voix est transformée en texte par le service de reconnaissance vocale de votre téléphone ou de votre navigateur (par exemple celui de Google ou d'Apple), selon leurs propres règles de confidentialité.",
            `Seul le texte obtenu est envoyé à l'assistant ${COMPANY.brand}. Nous ne recevons pas et ne conservons pas l'enregistrement audio.`,
          ]}
        />
      </Section>

      <Section title="4. Assistant intelligent et prestataire d'IA">
        <p>
          Pour répondre, l'assistant utilise un fournisseur externe d'intelligence artificielle :{' '}
          <strong>Groq, Inc. (États-Unis)</strong>. Lui sont transmis le texte de votre message et les informations du
          catalogue ou de votre compte nécessaires à la réponse (par exemple les produits recherchés ou l'état d'une
          commande). Évitez d'écrire dans l'assistant des informations sensibles qui ne sont pas utiles à votre demande.
        </p>
      </Section>

      <Section title="5. Hébergement et transferts hors du Gabon">
        <p>
          L'application et ses données sont hébergées par <strong>Render Services, Inc.</strong> (application et API) et{' '}
          <strong>Supabase, Inc.</strong> (base de données et fichiers). Leurs serveurs peuvent être situés hors du Gabon,
          notamment aux États-Unis ou en Europe. Ces transferts sont nécessaires au fonctionnement du service ; nous
          choisissons des prestataires qui appliquent des mesures de sécurité reconnues.
        </p>
      </Section>

      <Section title="6. Pourquoi nous utilisons vos données (finalités et bases légales)">
        <List
          items={[
            <><strong>Créer et gérer votre compte, traiter les commandes et les livraisons</strong> — exécution du contrat (les CGU).</>,
            <><strong>Suivre les paiements, les commissions et les sommes remises aux livreurs</strong> — exécution du contrat et obligations légales (comptabilité).</>,
            <><strong>Faire fonctionner l'assistant intelligent</strong> — exécution du contrat, à votre demande.</>,
            <><strong>Prévenir la fraude, sécuriser la plateforme, gérer les litiges</strong> — intérêt légitime de {COMPANY.brand} et des utilisateurs.</>,
            <><strong>Vous envoyer des informations ou offres</strong> — votre consentement, que vous pouvez retirer à tout moment.</>,
            <><strong>Répondre aux demandes des autorités</strong> — obligation légale.</>,
          ]}
        />
      </Section>

      <Section title="7. Avec qui vos données sont partagées">
        <List
          items={[
            "Le commerce voit le nom, le numéro de téléphone et l'adresse de livraison du client pour les commandes passées chez lui.",
            "Le livreur voit les informations nécessaires à la livraison : nom et téléphone du client, adresse, contenu et montant à encaisser le cas échéant.",
            "Le client voit le nom et le téléphone du commerce et du livreur liés à sa commande.",
            "Nos prestataires techniques (hébergement, IA) traitent les données uniquement pour notre compte.",
            "Les autorités, uniquement lorsque la loi l'exige.",
          ]}
        />
        <p><strong>Nous ne vendons jamais vos données personnelles.</strong></p>
      </Section>

      <Section title="8. Durée de conservation">
        <List
          items={[
            "Données du compte : tant que le compte est actif, puis 3 ans après la dernière activité ou la fermeture du compte (pour gérer d'éventuels litiges), sauf obligation contraire.",
            "Commandes, paiements, commissions et pièces comptables : 10 ans (obligations comptables et fiscales), sous forme anonymisée lorsque le compte est supprimé.",
            "Messages envoyés à l'assistant : 12 mois au maximum.",
            "Preuves de livraison : 1 an après la livraison.",
            "Journaux techniques de sécurité : 12 mois au maximum.",
          ]}
        />
      </Section>

      <Section title="9. Sécurité">
        <p>
          Nous protégeons vos données par des mesures adaptées : connexion chiffrée (HTTPS), mots de passe chiffrés,
          accès limité selon le rôle (client, commerce, livreur, administrateur), sauvegardes et surveillance des accès.
          Aucun système n'étant parfait, nous vous informerons, ainsi que la CNPDCP lorsque la loi le prévoit, en cas
          d'incident grave touchant vos données.
        </p>
      </Section>

      <Section title="10. Vos droits">
        <p>Conformément à la loi n°001/2011, vous disposez des droits suivants :</p>
        <List
          items={[
            "droit d'accès : savoir quelles données nous avons sur vous et en obtenir une copie ;",
            "droit de rectification : faire corriger des données inexactes ou incomplètes ;",
            "droit de suppression : demander l'effacement de vos données, sous réserve de nos obligations légales ;",
            "droit d'opposition : vous opposer, pour un motif légitime, à certains traitements, et à tout moment à la prospection commerciale.",
          ]}
        />
        <p>
          Pour exercer ces droits, écrivez à <strong>{COMPANY.contact}</strong> en indiquant le numéro de téléphone de votre
          compte. Nous pouvons vous demander de prouver votre identité. Nous répondons dans un délai d'un mois au plus.
          Si vous n'êtes pas satisfait de notre réponse, vous pouvez saisir la CNPDCP.
        </p>
      </Section>

      <Section title="11. Suppression de votre compte">
        <p>
          Vous pouvez demander la suppression de votre compte et de vos données à tout moment. La marche à suivre est
          expliquée sur la page <Link to="/suppression-compte" className={linkClass}>suppression du compte</Link>.
        </p>
      </Section>

      <Section title="12. Mineurs">
        <p>
          {COMPANY.brand} n'est pas destiné aux personnes de moins de 18 ans sans l'accord d'un parent ou tuteur légal. Si
          vous pensez qu'un mineur nous a transmis des données sans cet accord, contactez-nous pour que nous les supprimions.
        </p>
      </Section>

      <Section title="13. Modifications">
        <p>
          Cette politique peut être mise à jour. La date de dernière mise à jour figure en haut de la page. En cas de
          changement important, nous vous en informerons dans l'application.
        </p>
        <p>
          Voir aussi les <Link to="/cgu" className={linkClass}>conditions générales</Link> et les{' '}
          <Link to="/mentions-legales" className={linkClass}>mentions légales</Link>.
        </p>
      </Section>
    </LegalLayout>
  );
}
