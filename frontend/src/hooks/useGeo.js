import { useEffect, useState } from 'react';
import api from '../services/api';

let geoPromise = null;
/** Le référentiel est chargé une fois par session (quelques centaines de lignes). */
export function loadGeo() {
  if (!geoPromise) {
    geoPromise = api.get('/geo/').then((res) => res.data?.data || null).catch(() => { geoPromise = null; return null; });
  }
  return geoPromise;
}

export default function useGeo() {
  const [geo, setGeo] = useState(null);
  useEffect(() => { let on = true; loadGeo().then((g) => { if (on) setGeo(g); }); return () => { on = false; }; }, []);
  return geo;
}

