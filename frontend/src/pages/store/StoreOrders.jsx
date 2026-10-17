import React, { useEffect, useMemo, useState } from 'react';
import { openInvoice } from '../../utils/invoice';
import OrderLiveMap from '../../components/map/OrderLiveMap';
import { describeOptions } from '../../utils/productOptions';
import { notifyError, notifySuccess } from '../../utils/feedback';
import StoreLayout from '../../components/StoreLayout';
import LoadingSpinner from '../../components/LoadingSpinner';
import { getOrders, getOrderDetail } from '../../services/dashboardService';
import { updateOrderStatus } from '../../services/orderService';
import { formatCurrency, formatDateTime } from '../../utils/helpers';

const STATUS_MAP = {
  created: { label: 'Créée', className: 'bg-gray-200 text-gray-800' },
  pending_payment: { label: 'En attente de paiement', className: 'bg-yellow-100 text-yellow-800' },
  paid: { label: 'Payée', className: 'bg-green-100 text-green-800' },
  confirmed: { label: 'Confirmée', className: 'bg-blue-100 text-blue-800' },
  preparing: { label: 'En préparation', className: 'bg-indigo-100 text-indigo-800' },
  ready: { label: 'Prête', className: 'bg-purple-100 text-purple-800' },
  assigned: { label: 'Livreur assigné', className: 'bg-teal-100 text-teal-800' },
  in_transit: { label: 'En livraison', className: 'bg-cyan-100 text-cyan-800' },
  delivered: { label: 'Livrée', className: 'bg-green-500 text-white' },
  cancelled: { label: 'Annulée', className: 'bg-red-100 text-red-800' },
  refunded: { label: 'Remboursée', className: 'bg-red-200 text-red-800' },
};

const FILTERS = {
  pending: { label: 'Commandes en attente', statuses: ['paid', 'confirmed'] },
  preparing: { label: 'Commandes en préparation', statuses: ['preparing'] },
  ready: { label: 'Commandes prêtes', statuses: ['ready'] },
  delivered: { label: 'Commandes livrées', statuses: ['delivered'] },
  returns: { label: 'Retours / annulées', statuses: ['cancelled', 'refunded'] },
  all: { label: 'Toutes', statuses: [] },
};

const NEXT_STATUS = {
  paid: { label: 'Préparer', to: 'preparing' },
  confirmed: { label: 'Préparer', to: 'preparing' },
  preparing: { label: 'Prête', to: 'ready' },
};

const ADVANCE_DETAILS = {
  preparing: 'Le client est prévenu que vous préparez sa commande.',
  ready: 'Le client est prévenu ; un livreur Gaboshop va venir la chercher.',
  in_transit: 'Le client est prévenu que vous arrivez. Il confirmera la réception dans son application.',
};

const PAYMENT_FLOW_NAMES = {
  direct_split: 'Paiement direct : commerce et livreur',
  store_collects_all: 'Paiement intégral au commerce',
  courier_cash: 'Espèces encaissées par un livreur',
  platform_online: 'Paiement SingPay',
};
const PAYMENT_METHOD_NAMES = {
  cash: 'Espèces', airtel_money: 'Airtel Money', moov_money: 'Moov Money',
  bank_transfer: 'Virement',
};
const ROLE_NAMES = { client: 'Client', store: 'Commerce', courier: 'Livreur', platform: 'Gaboshop' };
const DEBT_KIND_NAMES = {
  products: 'Articles', delivery: 'Livraison', delivery_collection: 'Frais de livraison',
  courier_remittance: 'Fonds remis au commerce', commission: 'Commission Gaboshop',
  delivery_margin: 'Marge livraison Gaboshop', failed_trip: 'Course non aboutie',
};
const orderArticlePreview = (order) => (order.items || [])
  .map((item) => `${item.product_name || 'Article'} × ${item.quantity}`)
  .join(' · ');

const StoreOrders = () => {
  const [loading, setLoading] = useState(true);
  const [orders, setOrders] = useState([]);
  const [error, setError] = useState(null);
  const [activeFilter, setActiveFilter] = useState('all');
  const [search, setSearch] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [untilDate, setUntilDate] = useState('');
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState({});
  const [page, setPage] = useState(1);
  const [nextPage, setNextPage] = useState(false);
  const [totalCount, setTotalCount] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);

  const fetchOrders = async (pageNumber = 1) => {
    try {
      if (pageNumber === 1) setLoading(true);
      else setLoadingMore(true);
      const res = await getOrders({
        page: pageNumber, search: search.trim(),
        date_from: fromDate, date_to: untilDate,
        status: FILTERS[activeFilter]?.statuses?.join(',') || '',
      });
      if (res.success) {
        setOrders((previous) => pageNumber === 1 ? (res.data || []) : [...previous, ...(res.data || [])]);
        setNextPage(Boolean(res.meta?.next));
        setTotalCount(res.meta?.count ?? (res.data || []).length);
        setPage(pageNumber);
        setError(null);
      } else {
        const detail = res.error?.details;
        const msg = detail ? Object.values(detail).flat().join(' | ') : res.error?.message;
        setError(msg || 'Impossible de charger les commandes');
      }
    } catch (err) {
      const detail = err?.error?.details || err?.details;
      const msg = detail ? Object.values(detail).flat().join(' | ') : err?.error?.message || err?.message || err;
      setError(`Erreur: ${msg}`);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  useEffect(() => {
    // Rechercher aussi dans les pages anciennes de la base, pas seulement les 20 visibles.
    const task = setTimeout(() => fetchOrders(1), 300);
    return () => clearTimeout(task);
  }, [search, fromDate, untilDate, activeFilter]);

  useEffect(() => {
    // Accès depuis une notification ou depuis une ligne du relevé Gaboshop.
    const wanted = new URLSearchParams(window.location.search).get('order');
    if (wanted) openDetail(wanted);
  }, []);

  const counts = useMemo(() => {
    const base = { pending: 0, preparing: 0, ready: 0, delivered: 0, returns: 0, all: orders.length };
    orders.forEach((o) => {
      if (FILTERS.pending.statuses.includes(o.status)) base.pending += 1;
      if (FILTERS.preparing.statuses.includes(o.status)) base.preparing += 1;
      if (FILTERS.ready.statuses.includes(o.status)) base.ready += 1;
      if (FILTERS.delivered.statuses.includes(o.status)) base.delivered += 1;
      if (FILTERS.returns.statuses.includes(o.status)) base.returns += 1;
    });
    return base;
  }, [orders]);

  const filteredOrders = useMemo(() => {
    const filter = FILTERS[activeFilter];
    const query = search.trim().toLocaleLowerCase('fr');
    return orders.filter((order) => {
      if (filter?.statuses?.length && !filter.statuses.includes(order.status)) return false;
      if (query && ![
        order.order_number, order.client_phone, order.status_display,
        orderArticlePreview(order),
      ].some((value) => String(value || '').toLocaleLowerCase('fr').includes(query))) return false;
      const day = order.created_at ? String(order.created_at).slice(0, 10) : '';
      if (fromDate && day < fromDate) return false;
      if (untilDate && day > untilDate) return false;
      return true;
    });
  }, [orders, activeFilter, search, fromDate, untilDate]);

  const renderStatus = (status) => {
    const cfg = STATUS_MAP[status] || { label: status, className: 'bg-gray-100 text-gray-800' };
    return <span className={`px-3 py-1 rounded-full text-xs font-semibold ${cfg.className}`}>{cfg.label}</span>;
  };

  const openDetail = async (orderId) => {
    setDetailLoading(true);
    try {
      const res = await getOrderDetail(orderId);
      if (res.success) {
        setDetail(res.data || res);
      } else {
        const detail = res.error?.details;
        const msg = detail ? Object.values(detail).flat().join(' | ') : res.error?.message;
        setError(msg || 'Impossible de charger le détail');
      }
    } catch (err) {
      const detail = err?.error?.details || err?.details;
      const msg = detail ? Object.values(detail).flat().join(' | ') : err?.error?.message || err?.message || err;
      setError(`Erreur: ${msg}`);
    } finally {
      setDetailLoading(false);
    }
  };

  // Payée et en route vers le client : seul l'admin peut encore l'annuler (et rembourser).
  const canCancel = (order) => Boolean(order) && order.store_can_cancel !== false
    && !['delivered', 'cancelled', 'refunded'].includes(order.status);

  // Option « tout au commerce » : le commerce livre lui-même, puis le client confirme la réception.
  const nextAction = (order) => {
    if (order.delivered_by_store && order.status === 'ready') return { label: 'Je pars livrer', to: 'in_transit' };
    return NEXT_STATUS[order.status] || null;
  };

  const handleAdvance = async (order) => {
    const action = nextAction(order);
    if (!action) return;
    setActionLoading((prev) => ({ ...prev, [order.id]: true }));
    try {
      const res = await updateOrderStatus(order.id, action.to);
      if (res.success) {
        fetchOrders();
        if (detail?.id === order.id) setDetail({ ...detail, status: action.to });
        notifySuccess(`Commande #${order.order_number} : ${action.label.toLowerCase()}`, ADVANCE_DETAILS[action.to] || '');
      } else {
        notifyError(res, { action: action.label });
      }
    } catch (err) {
      notifyError(err, { action: action.label });
    } finally {
      setActionLoading((prev) => ({ ...prev, [order.id]: false }));
    }
  };

  const handleCancel = async (order) => {
    if (!canCancel(order)) return;
    if (!window.confirm(`Annuler la commande #${order.id} ?`)) return;
    setActionLoading((prev) => ({ ...prev, [order.id]: true }));
    try {
      const res = await updateOrderStatus(order.id, 'cancelled');
      if (res.success) {
        fetchOrders();
      } else {
        const detail = res.error?.details;
        const msg = detail ? Object.values(detail).flat().join(' | ') : res.error?.message;
        setError(msg || 'Annulation impossible');
      }
    } catch (err) {
      const detail = err?.error?.details || err?.details;
      const msg = detail ? Object.values(detail).flat().join(' | ') : err?.error?.message || err?.message || err;
      setError(`Erreur: ${msg}`);
    } finally {
      setActionLoading((prev) => ({ ...prev, [order.id]: false }));
    }
  };

  if (loading && orders.length === 0) return <LoadingSpinner />;

  return (
    <StoreLayout title="Mes Commandes">
      <div className="bg-white shadow rounded-lg p-4 sm:p-6">
        <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Vue globale</h3>
          <button
            onClick={() => fetchOrders(1)}
            className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md text-sm font-medium"
          >
            Rafraîchir
          </button>
        </div>

        {error && (
          <div className="mb-4 bg-red-100 border border-red-300 text-red-700 px-4 py-2 rounded">
            {error}
          </div>
        )}

        <div className="flex flex-wrap gap-2 mb-6">
          {Object.entries(FILTERS).map(([key, cfg]) => (
            <button
              key={key}
              onClick={() => setActiveFilter(key)}
              className={`px-4 py-2 rounded-full text-sm font-medium border ${
                activeFilter === key ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-gray-700 border-gray-200'
              }`}
            >
              {cfg.label}
              
            </button>
          ))}
        </div>

        <div className="mb-5 grid gap-3 rounded-lg border border-gray-200 bg-gray-50 p-3 sm:grid-cols-[minmax(0,1fr)_auto_auto_auto]">
          <label className="text-xs font-semibold text-gray-700">
            Rechercher une vente
            <input value={search} onChange={(event) => setSearch(event.target.value)}
              placeholder="N° commande, téléphone, nom d'article"
              className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm" />
          </label>
          <label className="text-xs font-semibold text-gray-700">Depuis
            <input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)}
              className="mt-1 block rounded-md border border-gray-300 bg-white px-2 py-2 text-sm" />
          </label>
          <label className="text-xs font-semibold text-gray-700">Jusqu'au
            <input type="date" value={untilDate} onChange={(e) => setUntilDate(e.target.value)}
              className="mt-1 block rounded-md border border-gray-300 bg-white px-2 py-2 text-sm" />
          </label>
          <button type="button" onClick={() => { setSearch(''); setFromDate(''); setUntilDate(''); setActiveFilter('all'); }}
            className="self-end rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700">
            Tout afficher
          </button>
        </div>
        <p className="mb-3 text-sm text-gray-600">
          {filteredOrders.length} sur {totalCount} commande(s) correspondant aux critères.
          {loading ? ' Actualisation en cours…' : ''} Cliquez sur une vente pour son relevé détaillé.
        </p>

        {filteredOrders.length === 0 ? (
          <div className="text-center py-12">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="mt-4 text-gray-500">Aucune commande dans cette catégorie</p>
          </div>
        ) : (
          <>
          <div className="md:hidden space-y-3">
            {filteredOrders.map((order) => (
              <div key={order.id} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-base font-semibold text-gray-900">{order.order_number || `#${order.id}`}</p>
                    <p className="text-sm text-gray-700">{order.client_phone || order.client}</p>
                    <p className="text-xs text-gray-500">{formatDateTime(order.created_at)}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-base font-semibold text-gray-900">{formatCurrency(order.total_amount || order.total)}</p>
                    <p className="text-xs text-gray-600 max-w-[160px] break-words">{orderArticlePreview(order) || 'Articles non renseignés'}</p>
                  </div>
                </div>
                <div className="mt-2 text-sm">{renderStatus(order.status)}</div>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button
                    onClick={() => openDetail(order.id)}
                    className="flex-1 min-w-[90px] px-3 py-2 rounded-md border border-indigo-200 text-indigo-700 text-sm font-medium"
                  >
                    Voir
                  </button>
                  {nextAction(order) && (
                    <button
                      onClick={() => handleAdvance(order)}
                      disabled={!!actionLoading[order.id]}
                      className={`flex-1 min-w-[90px] px-3 py-2 rounded-md bg-green-600 text-white text-sm font-medium ${actionLoading[order.id] ? 'cursor-wait opacity-60' : ''}`}
                    >
                      {nextAction(order).to === 'ready' ? 'Marquer prête' : nextAction(order).label}
                    </button>
                  )}
                  {canCancel(order) && (
                    <button
                      onClick={() => handleCancel(order)}
                      disabled={!!actionLoading[order.id]}
                      className={`flex-1 min-w-[90px] px-3 py-2 rounded-md border border-red-200 text-red-600 text-sm font-medium ${actionLoading[order.id] ? 'cursor-wait opacity-60' : ''}`}
                    >
                      Annuler
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
          <div className="hidden md:block overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">N°</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Client</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Montant</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Articles achetés</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredOrders.map((order) => (
                  <tr key={order.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">{order.order_number || `#${order.id}`}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{order.client_phone || order.client}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{formatDateTime(order.created_at)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">{formatCurrency(order.total_amount || order.total)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">{renderStatus(order.status)}</td>
                    <td className="px-6 py-4 text-sm text-gray-700 max-w-[260px]">
                      <p className="font-medium break-words">{orderArticlePreview(order) || 'Articles non renseignés'}</p>
                      <p className="text-xs text-gray-500">{order.items?.reduce((count, item) => count + Number(item.quantity || 0), 0) || 0} unité(s)</p>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm space-x-2 flex items-center">
                      <button
                        className="text-indigo-600 hover:text-indigo-900"
                        onClick={() => openDetail(order.id)}
                        title="Voir"
                        aria-label="Voir"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.477 0 8.268 2.943 9.542 7-1.274 4.057-5.065 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                      </button>
                      {nextAction(order) && (
                        <button
                          onClick={() => handleAdvance(order)}
                          disabled={!!actionLoading[order.id]}
                          className={`text-green-600 hover:text-green-800 ${actionLoading[order.id] ? 'cursor-wait opacity-60' : ''}`}
                          title={nextAction(order).label}
                          aria-label={nextAction(order).label}
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                        </button>
                      )}
                      {canCancel(order) && (
                        <button
                          onClick={() => handleCancel(order)}
                          disabled={!!actionLoading[order.id]}
                          className={`text-red-600 hover:text-red-900 ${actionLoading[order.id] ? 'cursor-wait opacity-60' : ''}`}
                          title="Annuler"
                          aria-label="Annuler"
                        >
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {nextPage && (
            <div className="mt-4 text-center">
              <button type="button" disabled={loadingMore} onClick={() => fetchOrders(page + 1)}
                className="rounded-md border border-indigo-300 px-5 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-50 disabled:opacity-50">
                {loadingMore ? 'Chargement…' : 'Charger des commandes plus anciennes'}
              </button>
            </div>
          )}
          </>
        )}
      </div>

      {detail && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" role="dialog" aria-modal="true">
          <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3 border-b">
              <div>
                <p className="text-xs text-gray-500">Commande {detail.order_number || `#${detail.id}`}</p>
                <h3 className="text-lg font-semibold text-gray-900">{detail.store_name || 'Commande'}</h3>
              </div>
              <button className="text-gray-500 hover:text-gray-800" onClick={() => setDetail(null)}>✕</button>
            </div>

            <div className="px-5 py-4 space-y-4 max-h-[70vh] overflow-y-auto">
              <div className="grid grid-cols-2 gap-4 text-sm text-gray-700">
                <div>
                  <p className="font-semibold">Client</p>
                  <p>{detail.client_phone || detail.client}</p>
                </div>
                <div>
                  <p className="font-semibold">Date</p>
                  <p>{formatDateTime(detail.created_at)}</p>
                </div>
                <div>
                  <p className="font-semibold">Adresse</p>
                  <p>{detail.delivery_address}</p>
                  <p className="text-xs text-gray-500">{detail.city} · {detail.delivery_zone}</p>
                </div>
                <div>
                  <p className="font-semibold">Total</p>
                  <p>{formatCurrency(detail.total_amount || detail.total)}</p>
                </div>
              </div>

              <div className="rounded-lg border border-indigo-100 bg-indigo-50 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h4 className="font-bold text-gray-900">Fiche de vente — {detail.order_number}</h4>
                  {renderStatus(detail.status)}
                </div>
                <div className="mt-3 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                  <div><p className="text-xs text-gray-600">Création de la commande</p><p className="font-semibold">{formatDateTime(detail.created_at)}</p></div>
                  <div><p className="text-xs text-gray-600">Confirmée</p><p className="font-semibold">{detail.confirmed_at ? formatDateTime(detail.confirmed_at) : 'Non confirmée'}</p></div>
                  <div><p className="text-xs text-gray-600">Livrée</p><p className="font-semibold">{detail.delivered_at ? formatDateTime(detail.delivered_at) : 'Non livrée / non renseignée'}</p></div>
                  <div><p className="text-xs text-gray-600">Dernière mise à jour</p><p className="font-semibold">{detail.updated_at ? formatDateTime(detail.updated_at) : 'Indisponible'}</p></div>
                </div>
                <p className="mt-3 text-xs text-gray-600">
                  Ces dates proviennent des enregistrements réels de la commande.
                  L'identité de l'employé ayant préparé ou encaissé la vente n'est pas encore historisée :
                  elle ne peut pas être reconstituée automatiquement.
                </p>
              </div>

              <section className="rounded-lg border border-gray-200 p-4">
                <h4 className="font-bold text-gray-900">Récapitulatif du montant facturé</h4>
                <dl className="mt-2 space-y-1 text-sm">
                  {[
                    ['Articles', detail.items_total],
                    ['Frais de livraison', detail.delivery_fee],
                    ['Frais opérateur', detail.operator_fee],
                    ['Autres frais de paiement', detail.payment_fees],
                    ['Taxes', detail.tax_amount],
                  ].filter(([, amount]) => Number(amount || 0) !== 0).map(([label, amount]) => (
                    <div key={label} className="flex justify-between gap-3"><dt>{label}</dt><dd>{formatCurrency(amount)}</dd></div>
                  ))}
                  {Number(detail.forfait_discount || 0) > 0 && (
                    <div className="flex justify-between gap-3 text-green-700"><dt>Réduction forfait livraison</dt><dd>-{formatCurrency(detail.forfait_discount)}</dd></div>
                  )}
                  <div className="flex justify-between gap-3 border-t pt-2 font-bold"><dt>Total de la commande</dt><dd>{formatCurrency(detail.total_amount)}</dd></div>
                </dl>
              </section>

              <section className="rounded-lg border border-gray-200 p-4">
                <h4 className="font-bold text-gray-900">Paiement et traçabilité financière</h4>
                {detail.payment_arrangement ? (
                  <>
                    <p className="mt-2 text-sm text-gray-800">
                      <strong>Circuit :</strong> {PAYMENT_FLOW_NAMES[detail.payment_arrangement.flow] || detail.payment_arrangement.flow}
                      {' · '}<strong>Moyen :</strong> {PAYMENT_METHOD_NAMES[detail.payment_arrangement.method] || detail.payment_arrangement.method}
                    </p>
                    <p className="mt-1 text-sm text-gray-700">
                      Commission calculée lors de la commande : <strong>{formatCurrency(detail.payment_arrangement.commission_amount)}</strong>
                      {' '}— ce n'est pas nécessairement une somme exigible si la commande n'est pas livrée.
                    </p>
                    <div className="mt-3 space-y-2">
                      {(detail.payment_arrangement.obligations || []).map((debt) => (
                        <div key={debt.id} className="rounded-md bg-gray-50 p-3 text-sm">
                          <div className="flex flex-wrap justify-between gap-2 font-semibold text-gray-900">
                            <span>{DEBT_KIND_NAMES[debt.kind] || debt.kind}</span>
                            <span>{formatCurrency(debt.amount)}</span>
                          </div>
                          <p className="text-xs text-gray-600">
                            {ROLE_NAMES[debt.payer] || debt.payer} → {ROLE_NAMES[debt.payee] || debt.payee}
                            {' · '}État : {debt.status}
                            {' · '}Reçu : {formatCurrency(debt.received_amount)}
                            {' · '}Restant : {formatCurrency(debt.remaining_amount)}
                          </p>
                          {(debt.adjustments || []).length > 0 && (
                            <ul className="mt-2 space-y-1 border-t pt-2 text-xs text-gray-700">
                              {debt.adjustments.map((adjustment) => (
                                <li key={adjustment.id} className="rounded bg-amber-50 px-2 py-1">
                                  {adjustment.type === 'refund' ? 'Remboursement enregistré'
                                    : adjustment.type === 'commission_credit' ? 'Avoir sur commission'
                                    : 'Correction financière'}
                                  {' — '}{formatCurrency(adjustment.amount)}
                                  {' · '}{adjustment.status === 'confirmed' ? 'Confirmé' : 'À vérifier'}
                                  {adjustment.created_at ? ` · ${formatDateTime(adjustment.created_at)}` : ''}
                                  {adjustment.reference ? ` · Réf. ${adjustment.reference}` : ''}
                                  {adjustment.reason ? ` · Motif : ${adjustment.reason}` : ''}
                                </li>
                              ))}
                            </ul>
                          )}
                          {(debt.receipts || []).length > 0 && (
                            <ul className="mt-2 space-y-1 border-t pt-2 text-xs text-gray-700">
                              {debt.receipts.map((receipt) => (
                                <li key={receipt.id}>
                                  Reçu {receipt.receipt_number || `#${receipt.id}`} — {formatCurrency(receipt.amount)}
                                  {' · '}{receipt.status === 'confirmed' ? 'Confirmé' : receipt.status === 'rejected' ? 'Refusé' : 'En attente'}
                                  {receipt.reference ? ` · Réf. ${receipt.reference}` : ''}
                                  {receipt.created_at ? ` · ${formatDateTime(receipt.created_at)}` : ''}
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      ))}
                    </div>
                    {['cancelled', 'pending_payment', 'refunded'].includes(detail.status) && (
                      <p className="mt-3 rounded-md bg-amber-50 p-2 text-sm text-amber-900">
                        Attention : cette commande n'est pas une vente livrée. Un montant comptable affiché ici
                        doit être rapproché avec Gaboshop avant tout règlement ou remboursement.
                      </p>
                    )}
                  </>
                ) : (
                  <p className="mt-2 text-sm text-gray-600">Aucun détail de règlement historique disponible pour cette commande.</p>
                )}
              </section>

              {detail.notes && (
                <div className="rounded-lg border border-gray-200 bg-gray-50 p-3 text-sm">
                  <p className="font-bold">Instructions / notes de commande</p>
                  <p className="mt-1 whitespace-pre-wrap">{detail.notes}</p>
                </div>
              )}
              {detail.client_problem_reported_at && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-900">
                  <p className="font-bold">Réclamation client signalée le {formatDateTime(detail.client_problem_reported_at)}</p>
                  <p className="mt-1 whitespace-pre-wrap">{detail.client_problem || 'Motif non renseigné'}</p>
                </div>
              )}

              {['ready', 'assigned', 'in_transit'].includes(detail.status) && <OrderLiveMap orderId={detail.id} viewer="store" />}

              <button
                type="button"
                onClick={() => openInvoice(detail.id, detail.order_number)}
                className="inline-flex items-center gap-2 rounded-md border border-indigo-200 bg-indigo-50 px-3 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-100"
              >
                📄 Facture (PDF)
              </button>

              <div>
                <p className="font-semibold text-gray-900 mb-2">Articles</p>
                <div className="divide-y divide-gray-100 border border-gray-100 rounded-md">
                  {detail.items?.map((it) => (
                    <div key={it.id} className="flex justify-between items-center px-3 py-2 text-sm">
                      <div className="space-y-0.5">
                        <p className="font-medium text-gray-900">{it.product_name || it.product}</p>
                        {describeOptions(it.options) && <p className="text-xs font-semibold text-indigo-700">{describeOptions(it.options)}</p>}
                        <p className="text-xs text-gray-500">{formatCurrency(it.unit_price)} · Qté {it.quantity}</p>
                      </div>
                      <p className="text-sm font-semibold text-gray-900">{formatCurrency(it.subtotal || it.unit_price * it.quantity)}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="px-5 py-3 border-t bg-gray-50 flex justify-end gap-2 text-sm">
              {detail && nextAction(detail) && (
                <button
                  onClick={() => handleAdvance(detail)}
                  disabled={!!actionLoading[detail.id]}
                  className={`px-4 py-2 rounded-md border text-white ${actionLoading[detail.id] ? 'bg-green-300' : 'bg-green-600 hover:bg-green-700 border-green-600'}`}
                  title={nextAction(detail).label}
                >
                  {nextAction(detail).label}
                </button>
              )}
              {detail && canCancel(detail) && (
                <button
                  onClick={() => handleCancel(detail)}
                  disabled={!!actionLoading[detail.id]}
                  className={`px-4 py-2 rounded-md border text-white ${actionLoading[detail.id] ? 'bg-red-300' : 'bg-red-600 hover:bg-red-700 border-red-600'}`}
                >
                  Annuler la commande
                </button>
              )}
              <button className="px-4 py-2 rounded-md border border-gray-200 text-gray-700" onClick={() => setDetail(null)}>
                Fermer
              </button>
            </div>
          </div>
        </div>
      )}
    </StoreLayout>
  );
};

export default StoreOrders;
