import { useEffect, useState } from 'react';
import api from '../../services/api';
import { formatCurrency } from '../../utils/helpers';
import { KIND_LABELS } from './paymentLabels';

/** Ce que le commerce ou le livreur doit à Gaboshop après des commandes payées en direct ou en espèces. */
export default function MyPlatformDebt() {
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get('/payments/debts/mine/').then((res) => setData(res.data?.data)).catch(() => setData(null));
  }, []);

  if (!data || Number(data.total_due) <= 0) return null;
  const overdue = Number(data.overdue) > 0;
  const contact = data.pay_to?.whatsapp || data.pay_to?.phone;
  return (
    <div className={`mb-8 rounded-lg border p-4 shadow-sm ${overdue ? 'border-red-200 bg-red-50' : 'border-amber-200 bg-amber-50'}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-bold text-gray-900">À régler à Gaboshop</p>
          <p className="text-sm text-gray-700">
            Sur les commandes payées en direct ou en espèces, l’argent ne passe pas par Gaboshop : sa part reste à lui remettre.
            {contact ? ` Contactez Gaboshop au ${contact} pour la régler.` : ' Contactez le support Gaboshop pour la régler.'}
          </p>
          {overdue && <p className="mt-1 text-sm font-semibold text-red-700">Une partie est en retard : au-delà du plafond, les nouvelles commandes en direct sont bloquées.</p>}
        </div>
        <p className="text-2xl font-bold text-gray-900">{formatCurrency(data.total_due)}</p>
      </div>
      <ul className="mt-3 divide-y divide-gray-100 rounded bg-white text-sm">
        {data.items.map((item) => (
          <li key={item.obligation_id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
            <span className="font-medium">{item.order_number}</span>
            <span className="text-gray-600">{KIND_LABELS[item.kind] || item.kind}</span>
            <span className="font-semibold">{formatCurrency(item.remaining)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
