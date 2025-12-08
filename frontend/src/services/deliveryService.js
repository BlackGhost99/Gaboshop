import api from './api';

export const getAssignedOrders = async () => {
  try {
    const response = await api.get('/dashboard/delivery/assigned-orders/');
    return response.data;
  } catch (error) {
    console.error('Erreur récupération commandes assignées:', error);
    return { success: false, data: { assigned_orders: [] } };
  }
};

export const acceptDelivery = async (deliveryId) => {
  try {
    const response = await api.post(`/dashboard/delivery/${deliveryId}/accept/`);
    return response.data;
  } catch (error) {
    console.error('Erreur acceptation commande:', error);
    const errorMsg = error.response?.data?.error || error.response?.data?.message || 'Erreur lors de l\'acceptation';
    console.error('Détails erreur backend:', error.response?.data);
    return { success: false, error: errorMsg };
  }
};

export const rejectDelivery = async (deliveryId) => {
  try {
    const response = await api.post(`/dashboard/delivery/${deliveryId}/reject/`);
    return response.data;
  } catch (error) {
    console.error('Erreur refus commande:', error);
    return { success: false, error: error.response?.data?.error || 'Erreur lors du refus' };
  }
};

export const startDelivery = async (deliveryId) => {
  try {
    const response = await api.post(`/dashboard/delivery/${deliveryId}/start/`);
    return response.data;
  } catch (error) {
    console.error('Erreur démarrage livraison:', error);
    return { success: false, error: error.response?.data?.error || 'Erreur lors du démarrage' };
  }
};

export const uploadProof = async (deliveryId, formData) => {
  try {
    const response = await api.post(`/dashboard/delivery/${deliveryId}/upload-proof/`, formData);
    return response.data;
  } catch (error) {
    console.error('Erreur upload preuve:', error);
    console.error('Détails erreur backend:', error.response?.data);
    return { 
      success: false, 
      error: error.response?.data?.error || 'Erreur lors de l\'upload de la preuve',
      validation_errors: error.response?.data?.validation_errors || {}
    };
  }
};

export const verifyPIN = async (deliveryId, pinCode) => {
  try {
    const response = await api.post(`/dashboard/delivery/${deliveryId}/verify-pin/`, { pin_code: pinCode });
    return response.data;
  } catch (error) {
    console.error('Erreur vérification PIN:', error);
    return { success: false, error: error.response?.data?.error || 'Erreur lors de la vérification du PIN' };
  }
};

export const completeDelivery = async (deliveryId, proofData = {}) => {
  try {
    const response = await api.post(`/dashboard/delivery/${deliveryId}/complete/`, proofData);
    return response.data;
  } catch (error) {
    console.error('Erreur confirmation livraison:', error);
    return { success: false, error: error.response?.data?.error || 'Erreur lors de la confirmation' };
  }
};

