import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import api from '../services/api';
import authStorage from '../utils/authStorage';
import { readCart, addToCart, removeFromCart, savePendingCartItem } from '../utils/session';

const AIContext = createContext(null);

export const useAIContext = () => {
  const context = useContext(AIContext);
  if (!context) {
    throw new Error('useAIContext must be used within AIContextProvider');
  }
  return context;
};

export const AIContextProvider = ({ children }) => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [lastError, setLastError] = useState(null);
  const [pageContext, setPageContext] = useState(null);
  const location = useLocation();
  const navigate = useNavigate();

  // Détecter le contexte de la page automatiquement
  useEffect(() => {
    const detectPageContext = () => {
      const path = location.pathname;
      const context = {
        page: path.split('/').filter(Boolean).join('_') || 'home',
        route: path,
        is_authenticated: !!authStorage.getItem('token'),
      };

      // Détecter le rôle depuis le token ou la route
      if (path.includes('/client/')) {
        context.role = 'client';
      } else if (path.includes('/store/')) {
        context.role = 'store_manager';
      } else if (path.includes('/delivery/')) {
        context.role = 'delivery_agent';
      } else if (path.includes('/admin/')) {
        context.role = 'admin';
      }

      // Récupérer store_id si disponible (depuis localStorage ou autre)
      const storeId = authStorage.getItem('store_id');
      if (storeId) {
        context.store_id = parseInt(storeId);
      }

      setPageContext(context);
    };

    detectPageContext();
  }, [location.pathname]);

  // Capturer les erreurs API automatiquement
  const reportError = useCallback((error) => {
    if (error?.response) {
      const errorData = {
        status: error.response.status,
        endpoint: error.config?.url || '',
        details: error.response.data,
        timestamp: new Date().toISOString(),
      };
      setLastError(errorData);
      
      // Stocker dans localStorage pour persistance
      localStorage.setItem('last_api_error', JSON.stringify(errorData));
    }
  }, []);

  // Envoyer un message à l'IA
  const addBotMessage = useCallback((text, extra = {}) => {
    setMessages(prev => [...prev, {
      id: Date.now() + Math.random(),
      type: 'bot',
      text,
      timestamp: new Date().toISOString(),
      ...extra,
    }]);
  }, []);

  // Exécute sur l'appareil les actions décidées par l'assistant
  const runActions = useCallback((actions) => {
    let needsLogin = false;
    (actions || []).forEach((action) => {
      if (action.type === 'add_to_cart' && action.product) {
        addToCart(action.product, action.quantity, action.size);
      } else if (action.type === 'remove_from_cart') {
        removeFromCart(action.product_id);
      } else if (action.type === 'login_required' && action.product) {
        savePendingCartItem(action.product);
        needsLogin = true;
      } else if (action.type === 'navigate' && action.path?.startsWith('/')) {
        navigate(action.path);
      }
    });
    return needsLogin;
  }, [navigate]);

  // Envoyer un message à l'assistant (adapté au rôle de l'utilisateur côté serveur)
  // `extra.problem` : le problème que l'application vient d'afficher, pour que l'IA l'explique.
  const sendMessage = useCallback(async (message, extra = {}) => {
    if (!message.trim()) return;

    setMessages(prev => [...prev, {
      id: Date.now(),
      type: 'user',
      text: message,
      timestamp: new Date().toISOString(),
    }]);
    setIsLoading(true);

    try {
      const history = messages.slice(-8).map((m) => ({ role: m.type, text: m.text }));
      const response = await api.post('/ai/assistant/', {
        message,
        history,
        cart: readCart(),
        page: location.pathname,
        ...(extra.problem ? { problem: extra.problem } : {}),
      });
      const data = response.data?.data || {};
      const needsLogin = runActions(data.actions);
      const replyText = data.message || "Je n'ai pas compris, pouvez-vous reformuler ?";
      addBotMessage(replyText, {
        products: Array.isArray(data.products) ? data.products : [],
        confirmations: Array.isArray(data.confirmations) ? data.confirmations : [],
        loginPrompt: needsLogin,
        cartChanged: (data.actions || []).some((a) => a.type === 'add_to_cart'),
      });
      return replyText;
    } catch (error) {
      reportError(error);
      const tooMany = error.response?.status === 429;
      const errorText = tooMany
        ? 'Beaucoup de messages en peu de temps. Patientez une minute puis réessayez.'
        : "Je n'arrive pas à joindre le serveur. Vérifiez votre connexion et réessayez.";
      addBotMessage(errorText, { isError: true });
      return errorText;
    } finally {
      setIsLoading(false);
    }
  }, [location.pathname, messages, reportError, runActions, addBotMessage]);

  // Confirme une modification proposée par l'assistant (prix, stock…)
  const confirmAction = useCallback(async (token) => {
    try {
      const response = await api.post('/ai/assistant/confirm/', { token });
      const done = response.data?.data || {};
      addBotMessage(done.message || "C'est fait.", done.path ? { link: { path: done.path, label: 'Ouvrir' } } : {});
      return true;
    } catch (error) {
      addBotMessage(error.response?.data?.error?.message || "La modification n'a pas pu être faite.", { isError: true });
      return false;
    }
  }, [addBotMessage]);

  // Récupérer le contexte backend
  const getContext = useCallback(async () => {
    try {
      const response = await api.get('/ai/context/');
      if (response.data.success) {
        return response.data.data;
      }
      return null;
    } catch (error) {
      reportError(error);
      return null;
    }
  }, [reportError]);

  // Charger la dernière erreur depuis localStorage au montage
  useEffect(() => {
    const storedError = localStorage.getItem('last_api_error');
    if (storedError) {
      try {
        setLastError(JSON.parse(storedError));
      } catch (e) {
        // Ignorer les erreurs de parsing
      }
    }

    // Écouter les événements d'erreur API
    const handleApiError = (event) => {
      setLastError(event.detail);
    };

    window.addEventListener('api-error', handleApiError);
    return () => {
      window.removeEventListener('api-error', handleApiError);
    };
  }, []);

  const value = {
    messages,
    isLoading,
    lastError,
    pageContext,
    sendMessage,
    confirmAction,
    addBotMessage,
    getContext,
    reportError,
    clearMessages: () => setMessages([]),
    clearError: () => {
      setLastError(null);
      localStorage.removeItem('last_api_error');
    },
  };

  return <AIContext.Provider value={value}>{children}</AIContext.Provider>;
};

