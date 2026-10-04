import React, { useEffect, useState } from 'react';
import { useAIContext } from '../context/AIContext';
import api from '../services/api';

const AIAlertBanner = () => {
  const { pageContext } = useAIContext();
  const [alerts, setAlerts] = useState([]);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const response = await api.get('/ai/context/');
        if (response.data.success) {
          const alertsDetails = response.data.data.alerts_details || [];
          setAlerts(alertsDetails);
          setIsVisible(alertsDetails.length > 0);
        }
      } catch (error) {
        // Ignorer les erreurs silencieusement
      }
    };

    // Charger les alertes seulement pour store_manager et admin
    if (pageContext?.role === 'store_manager' || pageContext?.role === 'admin') {
      fetchAlerts();
      // Rafraîchir toutes les 5 minutes
      const interval = setInterval(fetchAlerts, 5 * 60 * 1000);
      return () => clearInterval(interval);
    }
  }, [pageContext]);

  if (!isVisible || alerts.length === 0) return null;

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'error':
        return 'bg-red-50 border-red-500 text-red-800';
      case 'warning':
        return 'bg-yellow-50 border-yellow-500 text-yellow-800';
      default:
        return 'bg-blue-50 border-blue-500 text-blue-800';
    }
  };

  return (
    <div className="fixed top-0 left-0 right-0 z-40 px-4 pt-4">
      <div className="max-w-7xl mx-auto space-y-2">
        {alerts.slice(0, 3).map((alert, idx) => (
          <div
            key={idx}
            className={`${getSeverityColor(alert.severity)} border-l-4 p-4 rounded-lg shadow-lg flex items-center justify-between`}
          >
            <div className="flex items-center gap-3">
              <span className="text-lg">
                {alert.severity === 'error' ? '⚠️' : 'ℹ️'}
              </span>
              <p className="text-sm font-medium">{alert.message}</p>
            </div>
            <button
              onClick={() => setIsVisible(false)}
              className="text-gray-500 hover:text-gray-700 ml-4"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AIAlertBanner;

