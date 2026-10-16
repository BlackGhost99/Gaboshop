import { useEffect, useMemo } from 'react';
import { MapContainer, Marker, Polyline, Popup, TileLayer, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const LIBREVILLE = [0.4162, 9.4673];

// Pastilles emoji : pas d'image à charger (fonctionne aussi dans l'application Android).
const pin = (emoji, bg) => L.divIcon({
  className: '',
  html: `<div style="background:${bg};width:34px;height:34px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:18px;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.4)">${emoji}</div>`,
  iconSize: [34, 34],
  iconAnchor: [17, 17],
});
const ICONS = { store: pin('🏪', '#4f46e5'), client: pin('📍', '#dc2626'), courier: pin('🛵', '#16a34a'), me: pin('🛵', '#16a34a') };

const toLatLng = (p) => (p && Number.isFinite(p.lat) && Number.isFinite(p.lng) ? [p.lat, p.lng] : null);

function FitBounds({ points }) {
  const map = useMap();
  const key = points.map((p) => p.join(',')).join('|');
  useEffect(() => {
    if (points.length === 1) map.setView(points[0], 15);
    else if (points.length > 1) map.fitBounds(points, { padding: [36, 36], maxZoom: 16 });
  }, [map, key]); // eslint-disable-line react-hooks/exhaustive-deps
  return null;
}

/** Carte de course : commerce 🏪, client 📍, livreur 🛵, et le trajet restant.
 *  `tracking` : réponse de /orders/<id>/tracking/ ; `myPosition` : [lat, lng] du livreur sur son téléphone. */
export default function DeliveryMap({ tracking, myPosition = null, height = 260, viewer = 'client' }) {
  const store = toLatLng(tracking?.store?.position);
  const client = toLatLng(tracking?.destination?.position);
  const courier = myPosition || toLatLng(tracking?.courier?.position);
  const points = useMemo(() => [store, client, courier].filter(Boolean), [store, client, courier]);
  const next = tracking?.carrying ? client : store;
  const route = courier && next ? [courier, next] : null;
  const directions = tracking?.directions || {};

  return (
    <div className="space-y-2">
      <div className="relative z-0 w-full overflow-hidden rounded-xl border border-gray-200" style={{ height }}>
        <MapContainer center={points[0] || LIBREVILLE} zoom={13} style={{ height: '100%', width: '100%' }} scrollWheelZoom={false}>
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          />
          <FitBounds points={points} />
          {store && <Marker position={store} icon={ICONS.store}><Popup>{tracking?.store?.name || 'Commerce'}</Popup></Marker>}
          {client && <Marker position={client} icon={ICONS.client}><Popup>{viewer === 'client' ? 'Vous' : 'Client'}</Popup></Marker>}
          {courier && (
            <Marker position={courier} icon={myPosition ? ICONS.me : ICONS.courier}>
              <Popup>{myPosition ? 'Vous êtes ici' : (tracking?.courier?.name || 'Livreur')}</Popup>
            </Marker>
          )}
          {route && <Polyline positions={route} pathOptions={{ color: '#16a34a', dashArray: '6 8', weight: 4 }} />}
        </MapContainer>
      </div>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-600">
        <span>🏪 Commerce</span><span>📍 {viewer === 'client' ? 'Vous' : 'Client'}</span><span>🛵 Livreur</span>
        {tracking?.remaining_km != null && <span className="font-semibold text-gray-800">· {tracking.remaining_km} km restants</span>}
        {tracking?.eta_minutes != null && <span className="font-semibold text-green-700">· arrivée dans ~{tracking.eta_minutes} min</span>}
      </div>
      {viewer === 'client' && tracking?.courier && !tracking.courier.live && (
        <p className="text-xs text-amber-700">Position du livreur pas encore reçue ou trop ancienne : elle se met à jour dès que son téléphone la partage.</p>
      )}
      {!client && (
        <p className="text-xs text-amber-700">
          {viewer === 'client' ? "Pas de position GPS pour votre adresse : le livreur s'aide de votre quartier et de votre repère."
            : "Pas de position GPS du client : suivez l'adresse et appelez-le."}
        </p>
      )}
      {viewer === 'courier' && (directions.google || directions.waze) && (
        <div className="flex flex-wrap gap-2">
          {directions.google && (
            <a href={directions.google} target="_blank" rel="noreferrer" className="rounded-md bg-slate-900 px-3 py-2 text-xs font-semibold text-white">
              🧭 Itinéraire {tracking?.carrying ? 'vers le client' : 'vers le commerce'} (Google Maps)
            </a>
          )}
          {directions.waze && (
            <a href={directions.waze} target="_blank" rel="noreferrer" className="rounded-md border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-800">
              Waze
            </a>
          )}
        </div>
      )}
    </div>
  );
}
