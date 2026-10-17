import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../../services/api';
import { formatCurrency, formatDateTime } from '../../utils/helpers';
import { KIND_LABELS, METHOD_LABELS } from './paymentLabels';

const ORDER_STATUS = {
  pending_payment: 'En attente de paiement', created: 'Créée',
  paid: 'Payée', confirmed: 'Confirmée', preparing: 'En préparation',
  ready: 'Prête', assigned: 'Livreur attribué',
  in_transit: 'En livraison', delivered: 'Livrée',
  cancelled: 'Annulée', refunded: 'Remboursée',
};
const FLOW_LABELS = {
  direct_split: 'Paiement direct séparé',
  store_collects_all: 'Paiement au commerce',
  courier_cash: 'Espèces collectées par le livreur',
  platform_online: 'Paiement en ligne SingPay',
};

function DebtRow({ item, review = false }) {
  return (
    <li className="border-b border-gray-100 last:border-0 px-4 py-3 text-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1 space-y-1">
          <Link className="font-bold text-indigo-700 underline-offset-2 hover:underline" to={`/store/orders?order=${item.order_id}`}>
            Commande {item.order_number || `#${item.order_id}`}
          </Link>
          <p className="text-gray-600">
            {formatDateTime(item.created_at)}
            {' · '}{ORDER_STATUS[item.order_status] || item.order_status}
          </p>
          <p className="font-medium text-gray-800">
            {KIND_LABELS[item.kind] || item.kind}
            {' · '}{METHOD_LABELS[item.payment_method] || FLOW_LABELS[item.payment_flow] || item.payment_flow}
          </p>
          <p className="text-gray-700">
            {item.items?.length
              ? item.items.map((line) => `${line.name} × ${line.quantity}`).join(' · ')
              : 'Articles indisponibles dans cet historique'}
          </p>
        </div>
        <div className="shrink-0 text-right">
          <p className="text-lg font-bold text-gray-900">{formatCurrency(item.remaining)}</p>
          <p className={`text-xs font-semibold ${review ? 'text-amber-700' : 'text-red-700'}`}>
            {review ? 'À examiner — non réclamé' : item.status === 'overdue' ? 'En retard' : 'À régler'}
          </p>
        </div>
      </div>
      <details className="mt-2 rounded-md bg-gray-50 p-2">
        <summary className="cursor-pointer font-semibold text-indigo-700">Comprendre ce montant</summary>
        <dl className="mt-2 grid grid-cols-2 gap-2 text-xs text-gray-700 sm:grid-cols-3">
          <div><dt>Articles vendus</dt><dd className="font-bold">{formatCurrency(item.items_total)}</dd></div>
          <div><dt>Livraison facturée</dt><dd className="font-bold">{formatCurrency(item.delivery_fee)}</dd></div>
          <div><dt>Commande totale</dt><dd className="font-bold">{formatCurrency(item.order_total)}</dd></div>
          <div><dt>Part Gaboshop initiale</dt><dd className="font-bold">{formatCurrency(item.amount)}</dd></div>
          <div><dt>Déjà réglé à Gaboshop</dt><dd className="font-bold">{formatCurrency(item.paid_to_platform)}</dd></div>
          <div><dt>Avoirs / remboursements</dt><dd className="font-bold">{formatCurrency(item.credited)}</dd></div>
          <div><dt>Reste à régler</dt><dd className="font-bold">{formatCurrency(item.remaining)}</dd></div>
          <div><dt>Échéance prévue</dt><dd className="font-bold">{item.due_at ? formatDateTime(item.due_at) : 'Non définie'}</dd></div>
          <div><dt>Circuit de paiement</dt><dd className="font-bold">{FLOW_LABELS[item.payment_flow] || item.payment_flow}</dd></div>
        </dl>
        <Link to={`/store/orders?order=${item.order_id}`} className="mt-3 inline-block text-sm font-semibold text-indigo-700 hover:underline">
          Voir la vente et ses articles →
        </Link>
      </details>
    </li>
  );
}

/** Dettes commerciales identifiées, séparées des écritures comptables à régulariser. */
export default function MyPlatformDebt() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    api.get('/payments/debts/mine/')
      .then((res) => { setData(res.data?.data || null); setError(false); })
      .catch(() => { setData(null); setError(true); });
  }, []);

  const due = data?.items || [];
  const review = data?.review?.items || [];
  if (error) return (
    <p className="mb-6 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
      Le relevé Gaboshop est momentanément indisponible. Aucun montant ne peut être confirmé ici.
    </p>
  );
  if (!data || (due.length === 0 && review.length === 0)) return null;

  const overdue = Number(data.overdue) > 0;
  const contact = data.pay_to?.whatsapp || data.pay_to?.phone;
  return (
    <section className="mb-8 space-y-3" aria-label="Relevé Gaboshop">
      <div className={`rounded-xl border p-4 shadow-sm ${overdue ? 'border-red-200 bg-red-50' : 'border-amber-200 bg-amber-50'}`}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-gray-900">Relevé des sommes dues à Gaboshop</h2>
            <p className="max-w-2xl text-sm text-gray-700">
              Uniquement les commandes livrées. Pour chaque vente, vérifiez les articles,
              le circuit de paiement, les montants déjà réglés et les avoirs.
            </p>
            {contact && <p className="mt-1 text-sm text-gray-700">Pour régler ou contester : {contact}</p>}
            {overdue && <p className="mt-1 text-sm font-semibold text-red-700">Une partie des sommes dues est en retard.</p>}
          </div>
          <div className="text-right">
            <p className="text-xs font-semibold text-gray-700">Solde à régler sur ventes livrées</p>
            <p className="text-2xl font-bold text-gray-900">{formatCurrency(data.total_due)}</p>
          </div>
        </div>
        {due.length ? <ul className="mt-3 rounded-lg bg-white"><>{due.map((item) => (
          <DebtRow key={item.obligation_id} item={item} />
        ))}</></ul> : <p className="mt-3 text-sm font-medium text-green-800">Aucune somme exigible sur les commandes livrées.</p>}
      </div>
      {review.length > 0 && (
        <div className="rounded-xl border border-amber-300 bg-white p-4 shadow-sm">
          <h3 className="font-bold text-amber-900">Écritures à vérifier — non incluses dans le montant à régler</h3>
          <p className="mt-1 text-sm text-gray-700">
            Ces lignes concernent des commandes non livrées, annulées ou en attente. Elles restent
            traçables pour vérification avec Gaboshop ; ne les réglez pas sans rapprochement.
          </p>
          <p className="mt-2 text-sm font-semibold">Montant comptable à examiner : {formatCurrency(data.review.total_due)}</p>
          <details className="mt-3">
            <summary className="cursor-pointer text-sm font-semibold text-indigo-700">
              Afficher les {review.length} écriture(s)
            </summary>
            <ul className="mt-2 rounded-lg border border-amber-100">
              {review.map((item) => <DebtRow key={item.obligation_id} item={item} review />)}
            </ul>
          </details>
        </div>
      )}
    </section>
  );
}
