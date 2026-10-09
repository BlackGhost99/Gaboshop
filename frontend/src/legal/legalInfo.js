import { useEffect, useState } from 'react';
import api from '../services/api';

/**
 * Informations légales de Gaboshop.
 * Remplacer les valeurs entre crochets ici : elles sont reprises
 * automatiquement dans toutes les pages légales.
 */
export const COMPANY = {
  brand: 'Gaboshop',
  name: '[RAISON SOCIALE]',
  legalForm: '[FORME JURIDIQUE]',
  rccm: '[NUMÉRO RCCM]',
  nif: '[NIF]',
  address: '[ADRESSE DU SIÈGE]',
  city: 'Libreville, Gabon',
  publicationDirector: '[DIRECTEUR DE LA PUBLICATION]',
  email: '[EMAIL DE CONTACT]',
  phone: '[TÉLÉPHONE]',
  updatedAt: '6 octobre 2026',
};

export const LEGAL_PAGES = [
  { path: '/cgu', label: 'CGU / CGV' },
  { path: '/confidentialite', label: 'Confidentialité' },
  { path: '/mentions-legales', label: 'Mentions légales' },
  { path: '/suppression-compte', label: 'Suppression du compte' },
];

// Les informations de l'entreprise et du support se règlent dans l'espace admin (Réglages > Entreprise et support).
// Les valeurs ci-dessus servent seulement tant qu'elles n'y sont pas remplies.
let cachedSettings = null;
let pending = null;

function loadSettings() {
  if (!pending) {
    pending = api.get('/settings/')
      .then((res) => { cachedSettings = res?.data?.data || {}; return cachedSettings; })
      .catch(() => { pending = null; return {}; });
  }
  return pending;
}

function merge(settings) {
  const s = settings || {};
  return {
    ...COMPANY,
    name: s.company_name || COMPANY.name,
    legalForm: s.company_legal_form || COMPANY.legalForm,
    rccm: s.company_rccm || COMPANY.rccm,
    nif: s.company_nif || COMPANY.nif,
    address: s.company_address || COMPANY.address,
    city: s.company_city || COMPANY.city,
    publicationDirector: s.publication_director || COMPANY.publicationDirector,
    email: s.support_email || COMPANY.email,
    phone: s.support_phone || COMPANY.phone,
    whatsapp: s.support_whatsapp || '',
  };
}

export function useCompany() {
  const [company, setCompany] = useState(() => merge(cachedSettings));
  useEffect(() => {
    if (cachedSettings) return undefined;
    let alive = true;
    loadSettings().then((s) => { if (alive) setCompany(merge(s)); });
    return () => { alive = false; };
  }, []);
  return company;
}
