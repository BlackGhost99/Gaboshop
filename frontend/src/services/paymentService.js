import api from './api';

export const getPaymentOptions = async (storeId, deliveryRequested = true) => {
  const response = await api.get('/payments/options/', { params: { store_id: storeId, delivery_requested: deliveryRequested } });
  return response.data;
};

export const getPaymentArrangement = async (orderId) => {
  const response = await api.get(`/payments/arrangements/order/${orderId}/`);
  return response.data;
};

export const recordPaymentReceipt = async (payload) => {
  const response = await api.post('/payments/receipts/', payload);
  return response.data;
};

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
