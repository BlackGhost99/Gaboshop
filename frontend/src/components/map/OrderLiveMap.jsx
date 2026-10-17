import DeliveryMap from './DeliveryMap';
import useOrderTracking from '../../hooks/useOrderTracking';

/** Frise des étapes, sans carte : pour les commerces dont le forfait n'inclut pas le suivi en temps réel. */
function StatusSteps({ tracking }) {
  return (
    <div className="space-y-2 rounded-lg border border-gray-200 bg-gray-50 p-3">
      <p className="text-sm font-semibold text-gray-900">
        Suivi de la livraison{tracking.is_express ? ' · Express' : ''}
      </p>
      <ol className="space-y-1">
        {(tracking.steps || []).map((step) => (
          <li key={step.key} className="flex items-center gap-2 text-sm">
            <span
              aria-hidden="true"
              className={`inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[11px] font-bold ${
                step.done ? 'bg-green-600 text-white' : step.current ? 'bg-amber-500 text-white' : 'bg-gray-200 text-gray-500'
              }`}
            >
              {step.done ? '✓' : step.current ? '•' : ''}
            </span>
            <span className={step.done ? 'text-gray-700' : step.current ? 'font-semibold text-gray-900' : 'text-gray-400'}>
              {step.label}
              <span className="sr-only">{step.done ? ' (fait)' : step.current ? ' (en cours)' : ' (à venir)'}</span>
            </span>
          </li>
        ))}
      </ol>
      {tracking.message && <p className="text-xs text-gray-600">{tracking.message}</p>}
      {tracking.upgrade_note && <p className="text-xs font-medium text-amber-800">{tracking.upgrade_note}</p>}
    </div>
  );
}

/** Suivi en direct pour le client (ou le commerce, l'admin) : carte pendant la course si le forfait du commerce
 *  l'inclut ; sinon la frise des étapes. */
export default function OrderLiveMap({ orderId, viewer = 'client' }) {
  const { tracking, error } = useOrderTracking(orderId, !!orderId);
  if (error || !tracking) return null;
  if (tracking.live_tracking === false) return <StatusSteps tracking={tracking} />;
  if (!tracking.active) return null;
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
