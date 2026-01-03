/**
 * Formate un montant en FCFA
 * @param {number} amount - Montant à formater
 * @returns {string} - Montant formaté
 */
export const formatCurrency = (amount) => {
  return new Intl.NumberFormat('fr-FR', {
    style: 'currency',
    currency: 'XAF',
    minimumFractionDigits: 0,
  }).format(amount).replace('XAF', 'FCFA');
};

/**
 * Formate une date
 * @param {string} dateString - Date au format ISO
 * @returns {string} - Date formatée
 */
export const formatDate = (dateString) => {
  return new Intl.DateTimeFormat('fr-FR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  }).format(new Date(dateString));
};

/**
 * Formate une date et heure
 * @param {string} dateString - Date au format ISO
 * @returns {string} - Date et heure formatées
 */
export const formatDateTime = (dateString) => {
  return new Intl.DateTimeFormat('fr-FR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(dateString));
};

/**
 * Retourne le badge de statut d'une commande
 * @param {string} status - Statut de la commande
 * @returns {object} - Objet avec label et classe CSS
 */
export const getOrderStatusBadge = (status) => {
  const s = status?.toLowerCase();
  const statusMap = {
    created: { label: 'Créée', className: 'bg-gray-200 text-gray-800' },
    pending_payment: { label: 'En attente de paiement', className: 'bg-yellow-100 text-yellow-800 border border-yellow-300' },
    paid: { label: 'Payée', className: 'bg-green-100 text-green-800 border border-green-300' },
    confirmed: { label: 'Confirmée', className: 'bg-blue-100 text-blue-800 border border-blue-300' },
    preparing: { label: 'En préparation', className: 'bg-orange-100 text-orange-800 border border-orange-300' },
    ready: { label: 'Prête', className: 'bg-emerald-100 text-emerald-800 border border-emerald-300' },
    assigned: { label: 'Livreur assigné', className: 'bg-purple-100 text-purple-800 border border-purple-300' },
    in_transit: { label: 'En livraison', className: 'bg-cyan-100 text-cyan-800 border border-cyan-300' },
    delivered: { label: 'Livrée', className: 'bg-green-600 text-white shadow-sm' },
    cancelled: { label: 'Annulée', className: 'bg-red-100 text-red-800 border border-red-300' },
    refunded: { label: 'Remboursée', className: 'bg-gray-100 text-gray-800 border border-gray-300' },
  };
  return statusMap[s] || { label: status, className: 'bg-gray-200 text-gray-800' };
};

/**
 * Retourne le badge de statut de livraison
 * @param {string} status - Statut de la livraison
 * @returns {object} - Objet avec label et classe CSS
 */
export const getDeliveryStatusBadge = (status) => {
  const statusMap = {
    WAITING: { label: 'En attente', className: 'bg-yellow-200 text-yellow-800' },
    ACCEPTED: { label: 'Acceptée', className: 'bg-blue-200 text-blue-800' },
    IN_DELIVERY: { label: 'En livraison', className: 'bg-indigo-200 text-indigo-800' },
    DELIVERED: { label: 'Livrée', className: 'bg-green-500 text-white' },
  };
  return statusMap[status] || { label: status, className: 'bg-gray-200 text-gray-800' };
};
