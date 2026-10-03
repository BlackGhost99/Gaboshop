export const PAYMENT_METHOD_LABELS = {
  cash: 'Espèces',
  airtel_money: 'Airtel Money',
  moov_money: 'Moov Money',
  bank_transfer: 'Virement bancaire',
};

export const PAYMENT_FLOW_LABELS = {
  direct_split: 'Commerce et livreur payés séparément',
  store_collects_all: 'Le commerce encaisse la totalité',
  courier_cash: 'Le livreur collecte les espèces',
  platform_online: 'Paiement en ligne via Gaboshop',
};

export const validatePaymentPolicy = (policy) => {
  if (!policy) return 'La configuration des paiements doit être chargée.';
  if (!policy.enabled_flows?.length) return 'Activez au moins un circuit de paiement.';
  if (!policy.enabled_flows.includes(policy.default_flow)) return 'Le circuit par défaut doit être actif.';
  if (!policy.enabled_methods?.length) return 'Activez au moins un moyen de paiement.';
  if (policy.enabled_flows.includes('courier_cash') && !policy.enabled_methods.includes('cash')) {
    return 'La collecte par le livreur nécessite les espèces.';
  }
  if (!Number.isInteger(Number(policy.commission_settlement_days)) || Number(policy.commission_settlement_days) < 1) {
    return 'Le délai de règlement doit être un nombre entier de jours, au moins égal à 1.';
  }
  for (const field of ['merchant_debt_limit', 'courier_cash_limit']) {
    if (policy[field] === '' || !Number.isFinite(Number(policy[field])) || Number(policy[field]) < 0) {
      return 'Les plafonds doivent être des montants positifs ou nuls.';
    }
  }
  return '';
};

export const paymentErrorMessage = (error) => {
  const data = error?.response?.data || error;
  const detail = data?.error?.details || data?.details;
  if (detail && typeof detail === 'object') return Object.values(detail).flat().join(' · ');
  return data?.error?.message || data?.message || (typeof data === 'string' ? data : 'Impossible de traiter le paiement.');
};
