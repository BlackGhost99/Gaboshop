// Libellés communs aux écrans de paiement direct (sans agrégateur).
export const METHOD_LABELS = {
  cash: 'Espèces',
  airtel_money: 'Airtel Money',
  moov_money: 'Moov Money',
  bank_transfer: 'Virement bancaire',
};

export const ROLE_LABELS = {
  client: 'le client',
  store: 'le commerce',
  courier: 'le livreur',
  platform: 'Gaboshop',
};

export const KIND_LABELS = {
  products: 'Articles',
  delivery: 'Livraison',
  delivery_collection: 'Frais de livraison',
  courier_remittance: 'Espèces à remettre au commerce',
  commission: 'Commission Gaboshop',
  failed_trip: 'Course échouée',
};

export const RECEIPT_STATUS = {
  pending: { label: 'En attente de vérification', className: 'bg-amber-100 text-amber-800' },
  confirmed: { label: 'Confirmé', className: 'bg-green-100 text-green-800' },
  rejected: { label: 'Refusé', className: 'bg-red-100 text-red-700' },
};

export const newIdempotencyKey = () =>
  (window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`);

export const apiErrorMessage = (err, fallback) =>
  err?.response?.data?.error?.message || err?.error?.message || fallback;
