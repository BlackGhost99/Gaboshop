import React, { useEffect, useMemo, useState } from 'react';
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

const StoreOrders = () => {
  const [loading, setLoading] = useState(true);
  const [orders, setOrders] = useState([]);
  const [error, setError] = useState(null);
  const [activeFilter, setActiveFilter] = useState('pending');
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState({});

  const fetchOrders = async () => {
    try {
      setLoading(true);
      const res = await getOrders();
      if (res.success) {
        setOrders(res.data || []);
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
    }
  };

  useEffect(() => {
    fetchOrders();
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
    if (!filter || filter.statuses.length === 0) return orders;
    return orders.filter((o) => filter.statuses.includes(o.status));
  }, [orders, activeFilter]);

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

  const canCancel = (status) => !['delivered', 'cancelled', 'refunded'].includes(status);

  const nextAction = (order) => NEXT_STATUS[order.status] || null;

  const handleAdvance = async (order) => {
    const action = nextAction(order);
    if (!action) return;
    setActionLoading((prev) => ({ ...prev, [order.id]: true }));
    try {
      const res = await updateOrderStatus(order.id, action.to);
      if (res.success) {
        fetchOrders();
        if (detail?.id === order.id) setDetail({ ...detail, status: action.to });
      } else {
        const detailErr = res.error?.details;
        const msg = detailErr ? Object.values(detailErr).flat().join(' | ') : res.error?.message;
        setError(msg || 'Action impossible');
      }
    } catch (err) {
      const detailErr = err?.error?.details || err?.details;
      const msg = detailErr ? Object.values(detailErr).flat().join(' | ') : err?.error?.message || err?.message || err;
      setError(`Erreur: ${msg}`);
    } finally {
      setActionLoading((prev) => ({ ...prev, [order.id]: false }));
    }
  };

  const handleCancel = async (order) => {
    if (!canCancel(order.status)) return;
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

  if (loading) return <LoadingSpinner />;

  return (
    <StoreLayout title="Mes Commandes">
      <div className="bg-white shadow rounded-lg p-6">
        <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Vue globale</h3>
          <button
            onClick={fetchOrders}
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
              <span className="ml-2 text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-700">{counts[key] || 0}</span>
            </button>
          ))}
        </div>

        {filteredOrders.length === 0 ? (
          <div className="text-center py-12">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <p className="mt-4 text-gray-500">Aucune commande dans cette catégorie</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">N°</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Client</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Montant</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Articles</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredOrders.map((order) => (
                  <tr key={order.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">#{order.id}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{order.client_phone || order.client}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{formatDateTime(order.created_at)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">{formatCurrency(order.total_amount || order.total)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">{renderStatus(order.status)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{order.items?.length || order.items_count || 0}</td>
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
                      {canCancel(order.status) && (
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
        )}
      </div>

      {detail && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4" role="dialog" aria-modal="true">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full overflow-hidden">
            <div className="flex items-center justify-between px-5 py-3 border-b">
              <div>
                <p className="text-xs text-gray-500">Commande #{detail.id}</p>
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

              <div>
                <p className="font-semibold text-gray-900 mb-2">Articles</p>
                <div className="divide-y divide-gray-100 border border-gray-100 rounded-md">
                  {detail.items?.map((it) => (
                    <div key={it.id} className="flex justify-between items-center px-3 py-2 text-sm">
                      <div className="space-y-0.5">
                        <p className="font-medium text-gray-900">{it.product_name || it.product}</p>
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
              {detail && canCancel(detail.status) && (
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
