import { useState } from 'react';

/** « Partager ma position » : le livreur voit le point exact de livraison sur sa carte. Facultatif. */
export default function ShareLocationButton({ value, onChange }) {
  const [state, setState] = useState('');
  const shared = value?.latitude != null && value?.longitude != null;

  const share = () => {
    if (!navigator.geolocation) { setState('Localisation non disponible sur cet appareil.'); return; }
    setState('Recherche de votre position…');
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        onChange({ latitude: Number(pos.coords.latitude.toFixed(6)), longitude: Number(pos.coords.longitude.toFixed(6)) });
        setState(pos.coords.accuracy > 200 ? `Position approximative (à ${Math.round(pos.coords.accuracy)} m près) : précisez bien votre repère.` : '');
      },
      () => setState('Position refusée ou introuvable : autorisez la localisation, ou continuez avec votre quartier et votre repère.'),
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 },
    );
  };

  return (
    <div className="md:col-span-2 flex flex-wrap items-center gap-2 text-xs">
      {shared ? (
        <>
          <span className="rounded-full bg-green-100 px-2 py-1 font-semibold text-green-800">📍 Position GPS partagée avec le livreur</span>
          <button type="button" className="text-gray-500 underline" onClick={() => { onChange({ latitude: null, longitude: null }); setState(''); }}>Retirer</button>
        </>
      ) : (
        <button type="button" onClick={share} className="rounded-md border border-indigo-200 bg-indigo-50 px-3 py-1.5 font-semibold text-indigo-700">
          📍 Je suis à l’adresse de livraison : partager ma position
        </button>
      )}
      {state && <span className="text-gray-600">{state}</span>}
    </div>
  );
}
