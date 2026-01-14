import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import api from '../services/api';

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

  // Détecter le contexte de la page automatiquement
  useEffect(() => {
    const detectPageContext = () => {
      const path = location.pathname;
      const context = {
        page: path.split('/').filter(Boolean).join('_') || 'home',
        route: path,
        is_authenticated: !!sessionStorage.getItem('token'),
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
      const storeId = sessionStorage.getItem('store_id');
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
  const sendMessage = useCallback(async (message) => {
    if (!message.trim()) return;

    const userMessage = {
      id: Date.now(),
      type: 'user',
      text: message,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const frontendContext = {
        ...pageContext,
        last_api_error: lastError,
      };

      const response = await api.post('/ai/chat/', {
        message: message,
        frontend_context: frontendContext,
      });

      if (response.data.success) {
        const aiMessage = {
          id: Date.now() + 1,
          type: 'bot',
          text: response.data.data.message,
          timestamp: new Date().toISOString(),
        };
        setMessages(prev => [...prev, aiMessage]);
      } else {
        throw new Error(response.data.error?.message || 'Erreur lors de la communication avec l\'IA');
      }
    } catch (error) {
      reportError(error);
      const errorMessage = {
        id: Date.now() + 1,
        type: 'bot',
        text: error.response?.data?.error?.message || 'Désolé, une erreur s\'est produite. Veuillez réessayer.',
        timestamp: new Date().toISOString(),
        isError: true,
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [pageContext, lastError, reportError]);

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

