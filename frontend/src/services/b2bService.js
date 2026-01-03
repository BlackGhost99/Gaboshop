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
		const response = await api.get('/b2b/wholesalers/');
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
		const response = await api.get(`/b2b/wholesalers/${id}/`);
		return response.data;
	} catch (error) {
		console.error('Erreur lors de la récupération du grossiste:', error);
		throw error;
	}
};

/**
 * Récupère le catalogue complet d'un grossiste (infos + catégories + produits)
 * @param {number} id - ID du grossiste
 * @param {Object} params - Paramètres de filtrage (category_id, search, page, page_size)
 * @returns {Promise} Catalogue complet
 */
export const getWholesalerCatalog = async (id, params = {}) => {
	try {
		const queryParams = new URLSearchParams();
		Object.entries(params).forEach(([key, value]) => {
			if (value !== null && value !== undefined) {
				queryParams.append(key, value);
			}
		});
		
		const queryString = queryParams.toString();
		const url = `/b2b/wholesalers/${id}/catalog/${queryString ? `?${queryString}` : ''}`;
		const response = await api.get(url);
		return response.data;
	} catch (error) {
		console.error('Erreur lors de la récupération du catalogue B2B:', error);
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
		const url = `/b2b/wholesalers/${wholesalerId}/products/${queryString ? `?${queryString}` : ''}`;
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
		const response = await api.get(`/b2b/wholesalers/${wholesalerId}/categories/`);
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
		const response = await api.post('/b2b/orders/', orderData);
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
		const response = await api.get('/b2b/my-orders/');
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
		// #region agent log
		fetch('http://127.0.0.1:7242/ingest/fced817a-6879-4b38-979a-ae3f1398a171', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sessionId: 'debug-session', runId: 'prefix', hypothesisId: 'A', location: 'b2bService.js:getStoreB2BProfile', message: 'call getStoreB2BProfile', data: { storeId, baseURL: api?.defaults?.baseURL, path: `/b2b/profiles/${storeId}/` }, timestamp: Date.now() }) }).catch(() => {});
		// #endregion
		const response = await api.get(`/b2b/profiles/${storeId}/`);
		return response.data;
	} catch (error) {
		// Si 404, c'est normal (profil n'existe pas encore) - ne pas logger comme erreur
		if (error.response?.status === 404) {
			// #region agent log
			fetch('http://127.0.0.1:7242/ingest/fced817a-6879-4b38-979a-ae3f1398a171', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sessionId: 'debug-session', runId: 'prefix', hypothesisId: 'D', location: 'b2bService.js:getStoreB2BProfile', message: 'profile missing 404', data: { storeId, status: error.response?.status }, timestamp: Date.now() }) }).catch(() => {});
			// #endregion
			// Tentative sans trailing slash pour détecter un souci de configuration APPEND_SLASH
			try {
				const altResponse = await api.get(`/b2b/profiles/${storeId}`);
				// #region agent log
				fetch('http://127.0.0.1:7242/ingest/fced817a-6879-4b38-979a-ae3f1398a171', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sessionId: 'debug-session', runId: 'prefix', hypothesisId: 'E', location: 'b2bService.js:getStoreB2BProfile', message: 'alt path success', data: { storeId, path: `/b2b/profiles/${storeId}`, status: altResponse?.status }, timestamp: Date.now() }) }).catch(() => {});
				// #endregion
				return altResponse.data;
			} catch (altErr) {
				// #region agent log
				fetch('http://127.0.0.1:7242/ingest/fced817a-6879-4b38-979a-ae3f1398a171', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sessionId: 'debug-session', runId: 'prefix', hypothesisId: 'E', location: 'b2bService.js:getStoreB2BProfile', message: 'alt path failed', data: { storeId, status: altErr?.response?.status }, timestamp: Date.now() }) }).catch(() => {});
				// #endregion
			}
			// Retourner une réponse structurée pour indiquer que le profil n'existe pas
			return {
				success: false,
				error: {
					code: 404,
					message: 'Aucun profil B2B trouvé pour ce magasin'
				}
			};
		}
		// Pour les autres erreurs, logger et throw
		// #region agent log
		fetch('http://127.0.0.1:7242/ingest/fced817a-6879-4b38-979a-ae3f1398a171', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sessionId: 'debug-session', runId: 'prefix', hypothesisId: 'A', location: 'b2bService.js:getStoreB2BProfile', message: 'profile fetch error', data: { storeId, status: error.response?.status }, timestamp: Date.now() }) }).catch(() => {});
		// #endregion
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
		// #region agent log
		fetch('http://127.0.0.1:7242/ingest/fced817a-6879-4b38-979a-ae3f1398a171', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sessionId: 'debug-session', runId: 'prefix', hypothesisId: 'B', location: 'b2bService.js:createStoreB2BProfile', message: 'call create profile', data: { storeId, body: { ...data }, baseURL: api?.defaults?.baseURL, path: '/b2b/profiles/' }, timestamp: Date.now() }) }).catch(() => {});
		// #endregion
		const response = await api.post('/b2b/profiles/', {
			store_id: storeId,
			...data,
		});
		return response.data;
	} catch (error) {
		// #region agent log
		fetch('http://127.0.0.1:7242/ingest/fced817a-6879-4b38-979a-ae3f1398a171', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sessionId: 'debug-session', runId: 'prefix', hypothesisId: 'B', location: 'b2bService.js:createStoreB2BProfile', message: 'create profile error', data: { storeId, status: error.response?.status }, timestamp: Date.now() }) }).catch(() => {});
		// #endregion
		// Tentative sans trailing slash
		try {
			const altResponse = await api.post('/b2b/profiles', {
				store_id: storeId,
				...data,
			});
			// #region agent log
			fetch('http://127.0.0.1:7242/ingest/fced817a-6879-4b38-979a-ae3f1398a171', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sessionId: 'debug-session', runId: 'prefix', hypothesisId: 'E', location: 'b2bService.js:createStoreB2BProfile', message: 'alt create success', data: { storeId, path: '/b2b/profiles', status: altResponse?.status }, timestamp: Date.now() }) }).catch(() => {});
			// #endregion
			return altResponse.data;
		} catch (altErr) {
			// #region agent log
			fetch('http://127.0.0.1:7242/ingest/fced817a-6879-4b38-979a-ae3f1398a171', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sessionId: 'debug-session', runId: 'prefix', hypothesisId: 'E', location: 'b2bService.js:createStoreB2BProfile', message: 'alt create failed', data: { storeId, status: altErr?.response?.status }, timestamp: Date.now() }) }).catch(() => {});
			// #endregion
		}
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
		const response = await api.put(`/b2b/profiles/${storeId}/update/`, data);
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
		// #region agent log
		fetch('http://127.0.0.1:7242/ingest/fced817a-6879-4b38-979a-ae3f1398a171', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sessionId: 'debug-session', runId: 'prefix', hypothesisId: 'C', location: 'b2bService.js:activateStoreB2B', message: 'call activate', data: { storeId, body: { ...data }, baseURL: api?.defaults?.baseURL, path: `/b2b/profiles/${storeId}/activate/` }, timestamp: Date.now() }) }).catch(() => {});
		// #endregion
		const response = await api.patch(`/b2b/profiles/${storeId}/activate/`, data);
		return response.data;
	} catch (error) {
		// #region agent log
		fetch('http://127.0.0.1:7242/ingest/fced817a-6879-4b38-979a-ae3f1398a171', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sessionId: 'debug-session', runId: 'prefix', hypothesisId: 'C', location: 'b2bService.js:activateStoreB2B', message: 'activate error', data: { storeId, status: error.response?.status }, timestamp: Date.now() }) }).catch(() => {});
		// #endregion
		// Tentative sans trailing slash
		try {
			const altResponse = await api.patch(`/b2b/profiles/${storeId}/activate`, data);
			// #region agent log
			fetch('http://127.0.0.1:7242/ingest/fced817a-6879-4b38-979a-ae3f1398a171', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sessionId: 'debug-session', runId: 'prefix', hypothesisId: 'E', location: 'b2bService.js:activateStoreB2B', message: 'alt activate success', data: { storeId, path: `/b2b/profiles/${storeId}/activate`, status: altResponse?.status }, timestamp: Date.now() }) }).catch(() => {});
			// #endregion
			return altResponse.data;
		} catch (altErr) {
			// #region agent log
			fetch('http://127.0.0.1:7242/ingest/fced817a-6879-4b38-979a-ae3f1398a171', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sessionId: 'debug-session', runId: 'prefix', hypothesisId: 'E', location: 'b2bService.js:activateStoreB2B', message: 'alt activate failed', data: { storeId, status: altErr?.response?.status }, timestamp: Date.now() }) }).catch(() => {});
			// #endregion
		}
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
		const response = await api.patch(`/b2b/profiles/${storeId}/deactivate/`);
		return response.data;
	} catch (error) {
		console.error('Erreur lors de la désactivation du profil B2B:', error);
		throw error;
	}
};

// ==================== B2B PRICING MANAGEMENT ====================

/**
 * Récupère les prix B2B d'un store (Admin)
 * @param {number} storeId - ID du store
 * @returns {Promise} Liste des prix B2B + produits sans prix
 */
export const getB2BPricingList = async (storeId) => {
	try {
		const response = await api.get(`/b2b/pricing/${storeId}/`);
		return response.data;
	} catch (error) {
		console.error('Erreur lors de la récupération des prix B2B:', error);
		throw error;
	}
};

/**
 * Crée un prix B2B pour un produit (Admin)
 * @param {Object} data - Données du prix B2B
 * @returns {Promise} Prix B2B créé
 */
export const createB2BPricing = async (data) => {
	try {
		const response = await api.post('/b2b/pricing/', data);
		return response.data;
	} catch (error) {
		console.error('Erreur lors de la création du prix B2B:', error);
		throw error;
	}
};

/**
 * Met à jour un prix B2B (Admin)
 * @param {number} pricingId - ID du pricing
 * @param {Object} data - Données à mettre à jour
 * @returns {Promise} Prix B2B mis à jour
 */
export const updateB2BPricing = async (pricingId, data) => {
	try {
		const response = await api.put(`/b2b/pricing/${pricingId}/`, data);
		return response.data;
	} catch (error) {
		console.error('Erreur lors de la mise à jour du prix B2B:', error);
		throw error;
	}
};

/**
 * Supprime un prix B2B (Admin)
 * @param {number} pricingId - ID du pricing
 * @returns {Promise} Confirmation de suppression
 */
export const deleteB2BPricing = async (pricingId) => {
	try {
		const response = await api.delete(`/b2b/pricing/${pricingId}/delete/`);
		return response.data;
	} catch (error) {
		console.error('Erreur lors de la suppression du prix B2B:', error);
		throw error;
	}
};

/**
 * Crée des prix B2B en masse pour un store (Admin)
 * @param {number} storeId - ID du store
 * @param {number} discountPercent - Pourcentage de remise (ex: 10 pour -10%)
 * @returns {Promise} Résultat de la création en masse
 */
export const bulkCreateB2BPricing = async (storeId, discountPercent = 10) => {
	try {
		const response = await api.post('/b2b/pricing/bulk/', {
			store_id: storeId,
			discount_percent: discountPercent,
		});
		return response.data;
	} catch (error) {
		console.error('Erreur lors de la création en masse des prix B2B:', error);
		throw error;
	}
};
