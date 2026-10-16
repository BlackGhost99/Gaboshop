import DeliveryMap from './DeliveryMap';
import useOrderTracking from '../../hooks/useOrderTracking';

/** Suivi en direct pour le client (ou le commerce, l'admin) : visible seulement pendant la course. */
export default function OrderLiveMap({ orderId, viewer = 'client' }) {
  const { tracking, error } = useOrderTracking(orderId, !!orderId);
  if (error || !tracking?.active) return null;
  const courier = tracking.courier;
  return (
    <div className="space-y-2 rounded-lg border border-green-200 bg-green-50 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm font-semibold text-green-900">
          🛵 {tracking.carrying
            ? (viewer === 'client' ? 'Votre colis est en route' : 'Le livreur est en route vers le client')
            : (viewer === 'client' ? 'Le livreur va chercher votre colis' : 'Le livreur arrive au commerce')}
        </p>
        {courier?.phone && (
          <a href={`tel:${courier.phone}`} className="rounded-md bg-green-700 px-3 py-1.5 text-xs font-semibold text-white">
            📞 Appeler {courier.name}
          </a>
        )}
      </div>
      <DeliveryMap tracking={tracking} viewer={viewer} height={240} />
    </div>
  );
}
