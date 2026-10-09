import { useEffect, useState } from 'react';
import api from '../services/api';

const FALLBACK = ['Libreville'];
let cache = null;

// Villes actives, réglées dans l'espace admin (Réglages > Villes).
export default function useEnabledCities() {
  const [cities, setCities] = useState(cache || FALLBACK);
  useEffect(() => {
    if (cache) return undefined;
    let alive = true;
    api.get('/settings/')
      .then((res) => {
        const list = res?.data?.data?.enabled_cities;
        if (Array.isArray(list) && list.length) {
          cache = list;
          if (alive) setCities(list);
        }
      })
      .catch(() => {});
    return () => { alive = false; };
  }, []);
  return cities;
}
