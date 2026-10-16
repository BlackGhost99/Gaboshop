// Libellés des notifications (statuts de commande, types).

export const ORDER_STATUS_LABELS = {
  created: 'Enregistrée',
  pending_payment: 'En attente de paiement',
  paid: 'Payée',
  confirmed: 'Confirmée',
  preparing: 'En préparation',
  ready: 'Prête',
  assigned: 'Confiée à un livreur',
  in_transit: 'En route',
  delivered: 'Livrée',
  cancelled: 'Annulée',
  refunded: 'Remboursée',
  delayed: 'En retard',
};

export const statusLabel = (code) => ORDER_STATUS_LABELS[code] || code;

const TYPE_LABELS = { order: 'Commande', delivery: 'Livraison', payment: 'Paiement', warning: 'Alerte', announcement: 'Annonce', info: 'Info' };

// Étiquette de la notification : « Échec » ou « Réussi » quand le niveau est connu, sinon son type.
export const typeLabel = (notification) => {
  const level = notification?.metadata?.level;
  if (level === 'error') return 'Échec';
  if (level === 'success') return 'Réussi';
  return TYPE_LABELS[notification?.notif_type] || 'Info';
};

// --- Présentation dans la boîte de réception ---

const TYPE_ICONS = { order: '📦', delivery: '🚚', payment: '💰', warning: '⚠️', announcement: '📣', info: 'ℹ️' };

export const typeIcon = (notification) => {
  const level = notification?.metadata?.level;
  if (level === 'error') return '❌';
  if (level === 'success') return '✅';
  return TYPE_ICONS[notification?.notif_type] || 'ℹ️';
};

// Teinte de la pastille : rouge pour un échec, vert pour une réussite, sinon selon le type.
export const typeTone = (notification) => {
  const level = notification?.metadata?.level;
  if (level === 'error') return 'bg-red-100 text-red-700';
  if (level === 'success') return 'bg-green-100 text-green-700';
  const map = {
    order: 'bg-slate-100 text-slate-700',
    delivery: 'bg-emerald-100 text-emerald-700',
    payment: 'bg-amber-100 text-amber-700',
    warning: 'bg-amber-100 text-amber-800',
    announcement: 'bg-indigo-100 text-indigo-700',
  };
  return map[notification?.notif_type] || 'bg-gray-100 text-gray-700';
};

const DAY_MS = 24 * 3600 * 1000;
const startOfDay = (date) => new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();

// « à l'instant », « il y a 5 min », « il y a 3 h », « hier », « 12 oct. »
export const timeAgo = (value, now = new Date()) => {
  const date = new Date(value);
  const seconds = Math.max(0, Math.round((now - date) / 1000));
  if (seconds < 60) return 'à l’instant';
  if (seconds < 3600) return `il y a ${Math.floor(seconds / 60)} min`;
  const days = Math.round((startOfDay(now) - startOfDay(date)) / DAY_MS);
  if (days === 0) return `il y a ${Math.floor(seconds / 3600)} h`;
  if (days === 1) return 'hier';
  if (days < 7) return `il y a ${days} jours`;
  return new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'short' }).format(date);
};

// Titre du groupe : « Aujourd'hui », « Hier », « Cette semaine », puis le mois.
export const dayGroup = (value, now = new Date()) => {
  const date = new Date(value);
  const days = Math.round((startOfDay(now) - startOfDay(date)) / DAY_MS);
  if (days <= 0) return 'Aujourd’hui';
  if (days === 1) return 'Hier';
  if (days < 7) return 'Cette semaine';
  const label = new Intl.DateTimeFormat('fr-FR', { month: 'long', year: 'numeric' }).format(date);
  return label.charAt(0).toUpperCase() + label.slice(1);
};

export const FILTERS = [
  { id: 'all', label: 'Toutes' },
  { id: 'unread', label: 'Non lues' },
  { id: 'order', label: 'Commandes' },
  { id: 'delivery', label: 'Livraisons' },
  { id: 'payment', label: 'Paiements' },
  { id: 'announcement', label: 'Annonces' },
];
