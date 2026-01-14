import api from './api';

/**
 * Service pour les appels API IA
 */
export const aiService = {
  /**
   * Envoyer un message à l'IA
   */
  async sendMessage(message, frontendContext) {
    const response = await api.post('/ai/chat/', {
      message,
      frontend_context: frontendContext,
    });
    return response.data;
  },

  /**
   * Récupérer le contexte backend
   */
  async getContext() {
    const response = await api.get('/ai/context/');
    return response.data;
  },

  /**
   * Recherche intelligente de produits
   */
  async searchProducts(query) {
    const response = await api.get('/ai/search/products/', {
      params: { query },
    });
    return response.data;
  },

  /**
   * Préparer une commande
   */
  async prepareOrder(intent, storeId = null) {
    const response = await api.post('/ai/prepare-order/', {
      intent,
      store_id: storeId,
    });
    return response.data;
  },

  /**
   * Confirmer une action
   */
  async confirmAction(actionType, preparationData, additionalData = {}) {
    const response = await api.post('/ai/confirm-action/', {
      action_type: actionType,
      preparation_data: preparationData,
      ...additionalData,
    });
    return response.data;
  },
};

export default aiService;

