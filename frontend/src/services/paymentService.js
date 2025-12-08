import api from './api';

// Initialise un paiement pour une commande donnée
export const initPayment = async (orderId, payload) => {
  try {
    const res = await api.post(`/orders/${orderId}/payments/init/`, payload);
    return res.data;
  } catch (error) {
    throw error.response?.data || error.message;
  }
};

// Simule la confirmation opérateur via le webhook interne (usage tests)
export const simulatePaymentSuccess = async (transactionId, amount) => {
  try {
    const res = await api.post('/payments/webhook/', {
      transaction_id: transactionId,
      status: 'success',
      amount,
    });
    return res.data;
  } catch (error) {
    throw error.response?.data || error.message;
  }
};
