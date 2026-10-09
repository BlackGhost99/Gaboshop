import { useEffect, useState } from 'react';
import api from '../services/api';

/**
 * Informations légales de Gaboshop, réglées dans l'espace admin (Réglages > Entreprise et support).
 * Un champ vide n'est jamais affiché : pas de faux RCCM ni de NIF provisoire.
 */
export const COMPANY = {
  brand: 'Gaboshop',
  name: '',
  legalForm: '',
  rccm: '',
  nif: '',
  address: '',
  city: 'Libreville, Gabon',
  publicationDirector: '',
  email: '',
  phone: '',
  whatsapp: '',
  updatedAt: '9 octobre 2026',
};

export const LEGAL_PAGES = [
  { path: '/cgu', label: 'CGU / CGV' },
  { path: '/confidentialite', label: 'Confidentialité' },
  { path: '/mentions-legales', label: 'Mentions légales' },
  { path: '/suppression-compte', label: 'Suppression du compte' },
];

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
  const company = {
    ...COMPANY,
    brand: s.company_trade_name || COMPANY.brand,
    name: s.company_name || '',
    legalForm: s.company_legal_form || '',
    rccm: s.company_rccm || '',
    nif: s.company_nif || '',
    address: s.company_address || '',
    city: s.company_city || COMPANY.city,
    publicationDirector: s.publication_director || '',
    email: s.support_email || '',
    phone: s.support_phone || '',
    whatsapp: s.support_whatsapp || '',
  };
  // Tant que l'entreprise n'est pas immatriculée (pas de RCCM), on le dit clairement.
  company.registered = Boolean(company.rccm);
  company.status = company.registered ? '' : 'Entreprise en cours de formalisation au Gabon';
  // « Gaboshop (Jean Dupont, Entreprise individuelle (EI)), Quartier X, Libreville, Gabon »
  const identity = [company.name, company.legalForm].filter(Boolean).join(', ');
  const place = [company.address, company.city].filter(Boolean).join(', ');
  company.operator = company.registered || identity
    ? `${company.brand}${identity ? ` (${identity})` : ''}${place ? `, ${place}` : ''}`
    : `${company.brand}, ${company.status.charAt(0).toLowerCase()}${company.status.slice(1)}${place ? `, ${place}` : ''}`;
  company.contact = company.email || company.phone || company.whatsapp || 'le formulaire de contact de l’application';
  return company;
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
