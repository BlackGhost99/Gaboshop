/**
 * Service API pour le module B2B
 */

import api from './api';

/**
 * Récupère la liste des grossistes disponibles
 * @returns {Promise} Liste des grossistes
 */
export const getWholesalers = async () => {
	try {
		const response = await api.get('/api/v1/b2b/wholesalers/');
		return response.data;
	} catch (error) {
		console.error('Erreur lors de la récupération des grossistes:', error);
		throw error;
	}
};

/**
 * Récupère les détails d'un grossiste
 * @param {number} id - ID du grossiste
 * @returns {Promise} Détails du grossiste
 */
export const getWholesalerDetail = async (id) => {
	try {
		const response = await api.get(`/api/v1/b2b/wholesalers/${id}/`);
		return response.data;
	} catch (error) {
		console.error('Erreur lors de la récupération du grossiste:', error);
		throw error;
	}
};

/**
 * Récupère les produits B2B d'un grossiste
 * @param {number} wholesalerId - ID du grossiste
 * @param {Object} filters - Filtres optionnels (category_id, search, quantity)
 * @returns {Promise} Liste des produits B2B
 */
export const getB2BProducts = async (wholesalerId, filters = {}) => {
	try {
		const params = new URLSearchParams();
		if (filters.category_id) {
			params.append('category_id', filters.category_id);
		}
		if (filters.search) {
			params.append('search', filters.search);
		}
		if (filters.quantity) {
			params.append('quantity', filters.quantity);
		}
		
		const queryString = params.toString();
		const url = `/api/v1/b2b/wholesalers/${wholesalerId}/products/${queryString ? `?${queryString}` : ''}`;
		const response = await api.get(url);
		return response.data;
	} catch (error) {
		console.error('Erreur lors de la récupération des produits B2B:', error);
		throw error;
	}
};

/**
 * Récupère les catégories B2B d'un grossiste
 * @param {number} wholesalerId - ID du grossiste
 * @returns {Promise} Liste des catégories B2B
 */
export const getB2BCategories = async (wholesalerId) => {
	try {
		const response = await api.get(`/api/v1/b2b/wholesalers/${wholesalerId}/categories/`);
		return response.data;
	} catch (error) {
		console.error('Erreur lors de la récupération des catégories B2B:', error);
		throw error;
	}
};

/**
 * Crée une commande B2B
 * @param {Object} orderData - Données de la commande
 * @param {number} orderData.wholesaler_id - ID du grossiste
 * @param {Array} orderData.items - Items de la commande [{product_id, quantity}]
 * @param {string} orderData.delivery_type - Type de livraison (standard/express)
 * @param {string} orderData.notes - Notes optionnelles
 * @param {string} orderData.delivery_address - Adresse de livraison
 * @param {string} orderData.delivery_phone - Téléphone de livraison
 * @param {string} orderData.delivery_zone - Zone de livraison
 * @param {string} orderData.city - Ville (défaut: Libreville)
 * @returns {Promise} Commande créée
 */
export const createB2BOrder = async (orderData) => {
	try {
		const response = await api.post('/api/v1/b2b/orders/', orderData);
		return response.data;
	} catch (error) {
		console.error('Erreur lors de la création de la commande B2B:', error);
		throw error;
	}
};

/**
 * Récupère les commandes B2B du magasin connecté
 * @returns {Promise} Liste des commandes B2B
 */
export const getMyB2BOrders = async () => {
	try {
		const response = await api.get('/api/v1/b2b/my-orders/');
		return response.data;
	} catch (error) {
		console.error('Erreur lors de la récupération des commandes B2B:', error);
		throw error;
	}
};

// ==================== ADMIN FUNCTIONS ====================

/**
 * Récupère le profil B2B d'un store (Admin)
 * @param {number} storeId - ID du store
 * @returns {Promise} Profil B2B
 */
export const getStoreB2BProfile = async (storeId) => {
	try {
		const response = await api.get(`/api/v1/b2b/profiles/${storeId}/`);
		return response.data;
	} catch (error) {
		console.error('Erreur lors de la récupération du profil B2B:', error);
		throw error;
	}
};

/**
 * Crée un profil B2B pour un store (Admin)
 * @param {number} storeId - ID du store
 * @param {Object} data - Données du profil B2B
 * @param {number} data.minimum_order_amount - Montant minimum de commande
 * @param {boolean} data.visible_to_all - Visible par tous les magasins B2C
 * @param {boolean} data.is_active - Profil actif
 * @returns {Promise} Profil B2B créé
 */
export const createStoreB2BProfile = async (storeId, data) => {
	try {
		const response = await api.post('/api/v1/b2b/profiles/', {
			store_id: storeId,
			...data,
		});
		return response.data;
	} catch (error) {
		console.error('Erreur lors de la création du profil B2B:', error);
		throw error;
	}
};

/**
 * Met à jour le profil B2B d'un store (Admin)
 * @param {number} storeId - ID du store
 * @param {Object} data - Données à mettre à jour
 * @returns {Promise} Profil B2B mis à jour
 */
export const updateStoreB2BProfile = async (storeId, data) => {
	try {
		const response = await api.put(`/api/v1/b2b/profiles/${storeId}/update/`, data);
		return response.data;
	} catch (error) {
		console.error('Erreur lors de la mise à jour du profil B2B:', error);
		throw error;
	}
};

/**
 * Active le profil B2B d'un store (Admin)
 * @param {number} storeId - ID du store
 * @param {Object} data - Données optionnelles (minimum_order_amount, visible_to_all)
 * @returns {Promise} Profil B2B activé
 */
export const activateStoreB2B = async (storeId, data = {}) => {
	try {
		const response = await api.patch(`/api/v1/b2b/profiles/${storeId}/activate/`, data);
		return response.data;
	} catch (error) {
		console.error('Erreur lors de l\'activation du profil B2B:', error);
		throw error;
	}
};

/**
 * Désactive le profil B2B d'un store (Admin)
 * @param {number} storeId - ID du store
 * @returns {Promise} Profil B2B désactivé
 */
export const deactivateStoreB2B = async (storeId) => {
	try {
		const response = await api.patch(`/api/v1/b2b/profiles/${storeId}/deactivate/`);
		return response.data;
	} catch (error) {
		console.error('Erreur lors de la désactivation du profil B2B:', error);
		throw error;
	}
};

