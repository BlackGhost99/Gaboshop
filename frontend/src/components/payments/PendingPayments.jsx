import { useCallback, useEffect, useState } from 'react';
import api from '../../services/api';
import useVisibleInterval from '../../hooks/useVisibleInterval';
import { ReviewReceipt } from './OrderPaymentPanel';
import { KIND_LABELS } from './paymentLabels';

// Paiements déclarés par des clients (ou des commerces acheteurs en B2B) qui attendent ma vérification.
export default function PendingPayments({ title = 'Paiements à vérifier' }) {
  const [items, setItems] = useState([]);

  const load = useCallback(async () => {
    try {
      const res = await api.get('/payments/receipts/pending/');
      setItems(res.data?.data || []);
    } catch {
      // On réessaie au prochain passage.
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(load, 0);
    return () => clearTimeout(timer);
  }, [load]);
  useVisibleInterval(load, 20000);

  if (!items.length) return null;

  return (
    <div className="mb-6 rounded-2xl border-2 border-amber-300 bg-white p-4 shadow">
      <h3 className="text-lg font-bold text-gray-900">
        🔔 {title} ({items.length})
      </h3>
      <p className="text-sm text-gray-600">
        Comparez avec le SMS Mobile Money reçu : montant, ID de transaction et motif (numéro de commande).
      </p>
      <div className="mt-2 space-y-2 text-sm">
        {items.map((r) => (
          <ReviewReceipt
            key={r.id}
            receipt={r}
            onDone={load}
            context={(
              <p className="font-semibold text-gray-900">
                Commande {r.order_number}{r.is_b2b ? ' (B2B)' : ''} · {KIND_LABELS[r.kind] || 'Paiement'} · par {r.declared_by}
                {r.declared_by_phone && r.declared_by !== r.declared_by_phone ? ` (${r.declared_by_phone})` : ''}
              </p>
            )}
          />
        ))}
      </div>
    </div>
  );
}
