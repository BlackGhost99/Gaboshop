import { getSystemSettings } from '../services/adminService';

/**
 * Hook personnalisé pour accéder aux paramètres système.
 * Charge les paramètres au montage du composant et les met en cache.
 */
import { useState, useEffect } from 'react';

export const useSystemSettings = () => {
  const [settings, setSettings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const loadSettings = async () => {
      try {
        const response = await getSystemSettings();
        if (response.success) {
          setSettings(response.data);
        } else {
          setError('Erreur lors du chargement des paramètres');
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    loadSettings();
  }, []);

  return { settings, loading, error };
};

/**
 * Contexte global pour les paramètres système.
 * Permet d'accéder aux paramètres depuis n'importe quel composant.
 */
import React, { createContext, useContext } from 'react';

const SystemSettingsContext = createContext(null);

export const SystemSettingsProvider = ({ children }) => {
  const { settings, loading, error } = useSystemSettings();

  return (
    <SystemSettingsContext.Provider value={{ settings, loading, error }}>
      {children}
    </SystemSettingsContext.Provider>
  );
};

export const useSettings = () => {
  const context = useContext(SystemSettingsContext);
  if (!context) {
    throw new Error('useSettings doit être utilisé dans SystemSettingsProvider');
  }
  return context;
};

/**
 * Fonctions utilitaires pour accéder aux paramètres spécifiques
 */

// Calcul du prix de livraison basé sur la distance
export const calculateDeliveryPrice = (distanceKm, settings) => {
  if (!settings) return 0;
  return distanceKm * settings.price_per_km;
};

// Calcul de la commission sur une vente
export const calculateCommission = (amount, settings, categoryCommission = null) => {
  if (!settings) return 0;
  const rate = categoryCommission || settings.commission_global;
  return (amount * rate) / 100;
};

// Calcul des frais de paiement mobile
export const calculatePaymentFee = (amount, paymentMethod, settings) => {
  if (!settings) return 0;
  
  let feeRate = 0;
  if (paymentMethod === 'moov_money') {
    feeRate = settings.moov_money_fee;
  } else if (paymentMethod === 'airtel_money') {
    feeRate = settings.airtel_money_fee;
  }
  
  return (amount * feeRate) / 100;
};

// Vérifier si les commandes sont ouvertes à l'heure actuelle
export const areOrdersOpen = (settings) => {
  if (!settings) return true;
  
  const now = new Date();
  const currentTime = now.getHours() * 60 + now.getMinutes();
  
  const [openHour, openMin] = settings.order_opening_time.split(':').map(Number);
  const [closeHour, closeMin] = settings.order_closing_time.split(':').map(Number);
  
  const openingTime = openHour * 60 + openMin;
  const closingTime = closeHour * 60 + closeMin;
  
  return currentTime >= openingTime && currentTime <= closingTime;
};

// Vérifier si une ville est activée
export const isCityEnabled = (city, settings) => {
  if (!settings) return false;
  return settings.enabled_cities.includes(city);
};
