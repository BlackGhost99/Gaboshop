import React from 'react';
import { Link } from 'react-router-dom';
import LegalLayout, { Section, List } from '../../legal/LegalLayout';
import { useCompany } from '../../legal/legalInfo';

const linkClass = 'text-indigo-600 underline hover:text-indigo-500';

export default function MentionsLegales() {
  const COMPANY = useCompany();
  return (
    <LegalLayout title="Mentions légales">
      <Section title="1. Éditeur">
        <p>Le site et l'application {COMPANY.brand} sont édités par :</p>
        <List
          items={[
            <>Raison sociale : <strong>{COMPANY.name}</strong></>,
            <>Forme juridique : {COMPANY.legalForm}</>,
            <>RCCM : {COMPANY.rccm}</>,
            <>NIF : {COMPANY.nif}</>,
            <>Siège social : {COMPANY.address}, {COMPANY.city}</>,
            <>Directeur de la publication : {COMPANY.publicationDirector}</>,
            <>E-mail : {COMPANY.email}</>,
            <>Téléphone : {COMPANY.phone}</>,
          ]}
        />
      </Section>

      <Section title="2. Hébergement">
        <List
          items={[
            <>
              Application et API : <strong>Render Services, Inc.</strong>, San Francisco, Californie, États-Unis —{' '}
              <a href="https://render.com" target="_blank" rel="noopener noreferrer" className={linkClass}>render.com</a>
            </>,
            <>
              Base de données et fichiers : <strong>Supabase, Inc.</strong>, États-Unis —{' '}
              <a href="https://supabase.com" target="_blank" rel="noopener noreferrer" className={linkClass}>supabase.com</a>
            </>,
          ]}
        />
      </Section>

      <Section title="3. Propriété intellectuelle">
        <p>
          Le nom {COMPANY.brand}, le logo, le design, les textes et le code de l'application sont la propriété de{' '}
          {COMPANY.name} ou de ses partenaires. Toute reproduction ou utilisation sans autorisation écrite est interdite.
        </p>
        <p>
          Les photos, descriptions et marques des produits publiés par les commerces restent la propriété de ces commerces
          ou de leurs titulaires. Chaque commerce garantit qu'il a le droit de les utiliser et autorise {COMPANY.brand} à
          les afficher dans l'application pour promouvoir ses produits.
        </p>
      </Section>

      <Section title="4. Contact et informations complémentaires">
        <p>
          Pour toute question ou pour signaler un contenu illicite : {COMPANY.email}.
        </p>
        <p>
          Voir aussi les <Link to="/cgu" className={linkClass}>conditions générales</Link> et la{' '}
          <Link to="/confidentialite" className={linkClass}>politique de confidentialité</Link>.
        </p>
      </Section>
    </LegalLayout>
  );
}
