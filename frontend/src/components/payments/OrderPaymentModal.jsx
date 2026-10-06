import OrderPaymentPanel from './OrderPaymentPanel';

export default function OrderPaymentModal({ orderId, orderLabel, onClose, onChange }) {
  if (!orderId) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 sm:items-center sm:p-4" role="dialog" aria-modal="true">
      <div className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-t-2xl bg-white p-4 sm:rounded-2xl">
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-lg font-bold text-gray-900">Paiement {orderLabel ? `· ${orderLabel}` : ''}</h3>
          <button type="button" onClick={onClose} className="px-2 text-gray-500" aria-label="Fermer">✕</button>
        </div>
        <OrderPaymentPanel orderId={orderId} onChange={onChange} />
        <p className="mt-3 text-xs text-gray-500">Si rien ne s'affiche, cette commande n'a pas de paiement direct à suivre.</p>
      </div>
    </div>
  );
}
