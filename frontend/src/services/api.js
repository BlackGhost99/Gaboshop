import axios from 'axios';

// Configuration de base pour Axios
// Use VITE_API_URL when provided (development/production override),
// otherwise fall back to the relative path so Vite proxy continues to work.
const envBase = import.meta.env.VITE_API_URL;
const baseURL = envBase ? `${envBase.replace(/\/$/, '')}/api/v1` : '/api/v1';

const api = axios.create({
  baseURL,
});

// Intercepteur pour ajouter le token JWT et gérer Content-Type
api.interceptors.request.use(
  (config) => {
    const token = sessionStorage.getItem('token');
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
    if (error.response?.status === 401) {
      // Token expiré ou invalide
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
