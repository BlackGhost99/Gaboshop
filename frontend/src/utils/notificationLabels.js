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

const TYPE_LABELS = { order: 'Commande', delivery: 'Livraison', payment: 'Paiement', warning: 'Alerte', info: 'Info' };

// Étiquette de la notification : « Échec » ou « Réussi » quand le niveau est connu, sinon son type.
export const typeLabel = (notification) => {
  const level = notification?.metadata?.level;
  if (level === 'error') return 'Échec';
  if (level === 'success') return 'Réussi';
  return TYPE_LABELS[notification?.notif_type] || 'Info';
};
