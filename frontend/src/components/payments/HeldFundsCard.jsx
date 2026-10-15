import React from 'react';
import { formatCurrency } from '../../utils/helpers';

/** Argent payé en ligne par les clients, gardé par Gaboshop jusqu'au versement au commerce. */
export default function HeldFundsCard({ funds }) {
  if (!funds) return null;
  const { total = 0, count = 0, items = [], frozen, trusted } = funds;
  return (
    <div className="mb-8 rounded-lg border border-emerald-200 bg-emerald-50 p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-bold text-emerald-900">🔒 Votre argent en sécurité chez Gaboshop</p>
          <p className="text-sm text-emerald-800">
            {trusted
              ? 'Quand un client paie en ligne, Gaboshop garde l’argent puis vous le verse sur votre Mobile Money dès que vous préparez la commande.'
              : 'Quand un client paie en ligne, Gaboshop garde l’argent puis vous le verse sur votre Mobile Money dès que le client confirme la réception, ou automatiquement 48 h après la livraison s’il ne la confirme pas.'}
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
              <span className="font-medium">{item.order_number}</span>
              <span className="text-gray-600">{item.stage}</span>
              <span className="font-semibold">{formatCurrency(item.amount)}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
