import api from './api';

export const createOrder = async (payload) => {
  try {
    const res = await api.post('/orders/create/', payload);
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
