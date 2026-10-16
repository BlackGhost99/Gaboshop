import { useCallback, useEffect, useState } from 'react';
import api from '../services/api';
import useVisibleInterval from './useVisibleInterval';

/** Carte d'une commande (GET /orders/<id>/tracking/), rafraîchie toutes les 10 s pendant la course. */
export default function useOrderTracking(orderId, enabled = true) {
  const [tracking, setTracking] = useState(null);
  const [error, setError] = useState('');

  const load = useCallback(() => {
    if (!orderId) return Promise.resolve();
    return api.get(`/orders/${orderId}/tracking/`).then((res) => {
      setTracking(res.data?.data || null);
      setError('');
    }).catch((err) => {
      setError(err?.response?.data?.error?.message || 'Carte indisponible pour le moment.');
    });
  }, [orderId]);

  useEffect(() => { if (enabled) load(); }, [enabled, load]);
  useVisibleInterval(load, 10000, enabled && !!orderId && tracking?.active !== false);
  return { tracking, error, reload: load };
}
