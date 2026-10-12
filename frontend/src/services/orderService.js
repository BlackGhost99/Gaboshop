import api from './api';

// requestId : le même pour chaque renvoi d'un même panier, pour ne jamais créer deux commandes.
export const createOrder = async (payload, requestId) => {
  try {
    const res = await api.post('/orders/create/', payload, requestId ? { headers: { 'Idempotency-Key': requestId } } : undefined);
    return res.data;
  } catch (error) {
    throw error.response?.data || error.message;
  }
};

export const updateOrderStatus = async (orderId, status) => {
  try {
    const res = await api.patch(`/orders/${orderId}/status/`, { status });
    return res.data;
  } catch (error) {
    throw error.response?.data || error.message;
  }
};
