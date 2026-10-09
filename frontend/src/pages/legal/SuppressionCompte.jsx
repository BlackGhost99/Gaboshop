import React from 'react';
import { Link } from 'react-router-dom';
import LegalLayout, { Section, List } from '../../legal/LegalLayout';
import { useCompany } from '../../legal/legalInfo';

const linkClass = 'text-indigo-600 underline hover:text-indigo-500';

export default function SuppressionCompte() {
  const COMPANY = useCompany();
  return (
    <LegalLayout
      title="Supprimer votre compte et vos données"
      intro={`Cette page explique comment demander la suppression de votre compte ${COMPANY.brand} (client, commerce ou livreur) et des données associées.`}
    >
      <Section title="1. Depuis l'application">
        <p>
          Connectez-vous, ouvrez le menu puis <strong>Supprimer mon compte</strong>, ou allez directement sur{' '}
          <Link to="/supprimer-mon-compte" className="text-orange-600 underline">la page de suppression</Link>.
          Saisissez votre mot de passe et confirmez.
        </p>
      </Section>

      <Section title="2. Par e-mail">
        <p>Si l'option n'apparaît pas dans votre application, ou si vous n'avez plus accès à votre compte :</p>
        <List
          items={[
            <>envoyez un e-mail à <strong>{COMPANY.email}</strong>, de préférence depuis l'adresse e-mail liée à votre compte ;</>,
            "objet : « Suppression de compte » ;",
            "indiquez le numéro de téléphone de votre compte et votre nom ;",
            "nous pouvons vous contacter sur ce numéro pour confirmer que la demande vient bien de vous.",
          ]}
        />
      </Section>

      <Section title="3. Avant la suppression">
        <List
          items={[
            "Les commandes en cours doivent être terminées ou annulées.",
            "Commerces : les commissions dues doivent être réglées.",
            "Livreurs : l'argent encaissé pour le compte d'autrui doit être reversé.",
          ]}
        />
        <p>Les sommes encore dues restent exigibles après la suppression du compte.</p>
      </Section>

      <Section title="4. Ce qui est supprimé">
        <List
          items={[
            "votre profil : nom, téléphone, e-mail, mot de passe ;",
            "vos adresses de livraison ;",
            "vos messages à l'assistant intelligent ;",
            "pour un commerce : la boutique, ses produits et photos sont retirés de l'application ;",
            "pour un livreur : vos informations de véhicule et vos preuves de livraison (hors celles liées à un litige en cours).",
          ]}
        />
      </Section>

      <Section title="5. Ce qui est conservé, et combien de temps">
        <p>
          Certaines données doivent être gardées pour respecter la loi (comptabilité, fiscalité) ou pour gérer un litige :
        </p>
        <List
          items={[
            <>
              <strong>Historique des commandes, paiements et commissions</strong> : conservé <strong>10 ans</strong>, sous
              forme <strong>anonymisée</strong> (votre nom et vos coordonnées sont retirés).
            </>,
            <>
              <strong>Données liées à un litige ou une fraude en cours</strong> : conservées jusqu'à la fin du litige,
              puis supprimées.
            </>,
            <>
              <strong>Journaux techniques de sécurité</strong> : 12 mois au maximum.
            </>,
          ]}
        />
      </Section>

      <Section title="6. Délai">
        <p>
          Votre compte est désactivé dès la prise en compte de la demande, et vos données sont supprimées ou anonymisées{' '}
          <strong>dans un délai de 30 jours</strong> maximum. Nous vous confirmons la suppression par e-mail ou SMS.
        </p>
        <p>
          Pour en savoir plus, consultez la{' '}
          <Link to="/confidentialite" className={linkClass}>politique de confidentialité</Link>.
        </p>
      </Section>
    </LegalLayout>
  );
}
