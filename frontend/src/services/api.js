import axios from 'axios';
import authStorage from '../utils/authStorage';

// Configuration de base pour Axios
// Use VITE_API_URL when provided (development/production override),
// otherwise fall back to the relative path so Vite proxy continues to work.
const envBase = import.meta.env.VITE_API_URL;
const baseURL = envBase ? `${envBase.replace(/\/$/, '')}/api/v1` : '/api/v1';

const api = axios.create({
  baseURL,
  // Pas d'attente sans fin : 90 s couvrent le réveil du serveur gratuit (environ 1 min).
  timeout: 90000,
});

// Intercepteur pour ajouter le token JWT et gérer Content-Type
api.interceptors.request.use(
  (config) => {
    const token = authStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    
    // Si ce n'est pas un FormData, définir application/json
    // Si c'est un FormData, laisser axios le définir automatiquement
    if (!(config.data instanceof FormData)) {
      config.headers['Content-Type'] = 'application/json';
    }
    
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Intercepteur pour gérer les erreurs de réponse
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    
    // Capturer les erreurs importantes (401, 403, 404, 500)
    if (status && [401, 403, 404, 500].includes(status)) {
      const errorData = {
        status: status,
        endpoint: error.config?.url || '',
        method: error.config?.method || 'GET',
        details: error.response?.data,
        timestamp: new Date().toISOString(),
      };
      
      // Stocker dans localStorage pour accès par l'IA
      localStorage.setItem('last_api_error', JSON.stringify(errorData));
      
      // Déclencher un événement personnalisé pour notifier le contexte IA
      window.dispatchEvent(new CustomEvent('api-error', { detail: errorData }));
    }
    
    // Mot de passe faux à la connexion : pas une session expirée, la page affiche le message du serveur.
    const authCall = /\/auth\/(login|register)\/?$/.test(error.config?.url || '');
    if (status === 401 && !authCall) {
      // Token expiré ou invalide
      authStorage.removeItem('token');
      authStorage.removeItem('refresh_token');
      localStorage.removeItem('last_api_error');
      window.location.href = '/login';
    }
    
    return Promise.reject(error);
  }
);

export default api;
