import { useCallback, useEffect, useState } from 'react';
import api from '../services/api';
import useVisibleInterval from './useVisibleInterval';

/** Carte d'une commande (GET /orders/<id>/tracking/), rafraîchie toutes les 10 s tant qu'elle est affichée :
 *  la course peut commencer pendant que l'écran est ouvert. Arrêt si la commande n'est plus accessible. */
export default function useOrderTracking(orderId, enabled = true) {
  const [tracking, setTracking] = useState(null);
  const [error, setError] = useState('');
  const [gone, setGone] = useState(false);

  const load = useCallback(() => {
    if (!orderId) return Promise.resolve();
    return api.get(`/orders/${orderId}/tracking/`).then((res) => {
      setTracking(res.data?.data || null);
      setError('');
    }).catch((err) => {
      setError(err?.response?.data?.error?.message || 'Carte indisponible pour le moment.');
      if ([403, 404].includes(err?.response?.status)) setGone(true);
    });
  }, [orderId]);

  useEffect(() => { if (enabled) load(); }, [enabled, load]);
  useVisibleInterval(load, 10000, enabled && !!orderId && !gone);
  return { tracking, error, reload: load };
}
