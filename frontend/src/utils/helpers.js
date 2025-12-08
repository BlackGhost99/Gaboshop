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
  const statusMap = {
    CREATED: { label: 'Créée', className: 'bg-gray-200 text-gray-800' },
    PENDING_PAYMENT: { label: 'En attente de paiement', className: 'bg-yellow-200 text-yellow-800' },
    PAID: { label: 'Payée', className: 'bg-green-200 text-green-800' },
    ASSIGNED: { label: 'Assignée', className: 'bg-blue-200 text-blue-800' },
    ON_GOING: { label: 'En cours', className: 'bg-indigo-200 text-indigo-800' },
    DELIVERED: { label: 'Livrée', className: 'bg-green-500 text-white' },
    CANCELLED: { label: 'Annulée', className: 'bg-red-200 text-red-800' },
  };
  return statusMap[status] || { label: status, className: 'bg-gray-200 text-gray-800' };
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
