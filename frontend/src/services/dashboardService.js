import api from './api';

// Dashboard Client
export const getClientDashboard = async () => {
  const response = await api.get('/dashboard/client/');
  return response.data;
};

// Dashboard Store
export const getStoreDashboard = async () => {
  const response = await api.get('/dashboard/store/');
  return response.data;
};

// Dashboard Delivery
export const getDeliveryDashboard = async () => {
  const response = await api.get('/dashboard/delivery/');
  return response.data;
};

export const updateDeliveryProfile = async (formData) => {
  const response = await api.post('/dashboard/delivery/profile/update/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

// Authentification
export const login = async (phone, password) => {
  const response = await api.post('/auth/login/', { phone, password });
  return response.data;
};

export const register = async (payload) => {
  const response = await api.post('/auth/register/', payload);
  return response.data;
};

export const logout = () => {
  sessionStorage.removeItem('token');
  sessionStorage.removeItem('refresh_token');
  window.location.href = '/login';
};

// Commandes
export const getOrders = async () => {
  const response = await api.get('/orders/');
  const payload = response.data;
  // 1) Format standard { success, data }
  if (payload && typeof payload === 'object' && 'success' in payload) {
    // Si success est faux, renvoyer tel quel pour afficher l'erreur backend
    if (payload.success === false) return payload;
    if ('data' in payload) return { success: true, data: payload.data, meta: payload.meta };
  }

  // 2) Format paginé DRF par défaut { count, next, previous, results: [...] }
  if (payload && typeof payload === 'object' && 'results' in payload) {
    return {
      success: true,
      data: payload.results,
      meta: { count: payload.count, next: payload.next, previous: payload.previous },
    };
  }

  // 3) Tableau brut
  if (Array.isArray(payload)) {
    return { success: true, data: payload };
  }

  // Fallback défensif
  return { success: false, error: { message: 'Réponse inattendue du serveur', raw: payload } };
};

export const getOrderDetail = async (orderId) => {
  const response = await api.get(`/orders/${orderId}/`);
  return response.data;
};

export const confirmDelivery = async (orderId, payload = {}) => {
  try {
    const response = await api.post(`/orders/${orderId}/confirm-delivery/`, payload);
    return response.data;
  } catch (error) {
    console.error('Erreur confirmation réception:', error);
    return { 
      success: false, 
      error: error.response?.data?.error || { message: 'Erreur lors de la confirmation de réception' }
    };
  }
};

// Profil
export const getProfile = async () => {
  const response = await api.get('/users/profile/');
  return response.data;
};

export const updateProfile = async (data) => {
  const response = await api.patch('/users/profile/', data);
  return response.data;
};
