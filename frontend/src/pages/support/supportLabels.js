export const CATEGORIES = [
  ['order', 'Commande'],
  ['payment', 'Paiement'],
  ['delivery', 'Livraison'],
  ['plan', 'Forfait'],
  ['account', 'Compte'],
  ['technical', 'Problème technique'],
  ['other', 'Autre'],
];

export const STATUS_LABELS = { open: 'Ouvert', in_progress: 'En cours', resolved: 'Résolu' };
export const STATUS_TONES = {
  open: 'bg-amber-100 text-amber-800',
  in_progress: 'bg-blue-100 text-blue-800',
  resolved: 'bg-emerald-100 text-emerald-800',
};

export const PRIORITY_LABELS = { dedie: 'Ligne dédiée', prioritaire: 'Prioritaire', standard: 'Standard' };
export const PRIORITY_TONES = {
  dedie: 'bg-purple-100 text-purple-800',
  prioritaire: 'bg-red-100 text-red-800',
  standard: 'bg-gray-100 text-gray-700',
};
