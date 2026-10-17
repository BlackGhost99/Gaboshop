import React from 'react';
import { Link } from 'react-router-dom';
import { formatCurrency, formatDateTime } from '../../utils/helpers';

/** Argent payé en ligne par les clients, gardé par Gaboshop jusqu'au versement au commerce. */
export default function HeldFundsCard({ funds }) {
  if (!funds) return null;
  const { total = 0, count = 0, items = [], frozen, trusted } = funds;
  return (
    <div className="mb-8 rounded-lg border border-emerald-200 bg-emerald-50 p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-bold text-emerald-900">Paiements en ligne reçus — part commerçant à reverser</p>
          <p className="text-sm text-emerald-800">
            Il s'agit des sommes attribuées à votre boutique après des commandes payées en ligne.
            Un versement ne sera indiqué comme effectué qu'après confirmation du transfert.
            {trusted ? ' Certaines commandes peuvent être éligibles plus tôt, sous réserve des vérifications.' : ''}
            {' '}Les délais et les étapes dépendent des validations et du prestataire de paiement.
          </p>
        </div>
        <div className="text-right">
          <p className="text-2xl font-bold text-emerald-900">{formatCurrency(total)}</p>
          <p className="text-xs text-emerald-700">{count} commande{count > 1 ? 's' : ''} en attente de versement</p>
        </div>
      </div>
      {frozen && (
        <p className="mt-3 rounded bg-amber-100 p-2 text-sm text-amber-900">
          Vos versements sont retenus le temps d’une vérification. Votre argent reste gardé par Gaboshop : contactez le support pour en savoir plus.
        </p>
      )}
      {items.length > 0 && (
        <ul className="mt-3 divide-y divide-emerald-100 rounded bg-white text-sm">
          {items.map((item) => (
            <li key={item.order_number} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
              <div className="min-w-0 flex-1">
                {item.order_id ? (
                  <Link to={`/store/orders?order=${item.order_id}`} className="font-semibold text-indigo-700 hover:underline">
                    {item.order_number}
                  </Link>
                ) : <span className="font-medium">{item.order_number}</span>}
                {item.created_at && <p className="text-xs text-gray-500">{formatDateTime(item.created_at)}</p>}
              </div>
              <span className="text-gray-600">{item.stage}</span>
              <span className="font-semibold">{formatCurrency(item.amount)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
