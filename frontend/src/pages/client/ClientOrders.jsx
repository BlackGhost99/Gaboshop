import React, { useEffect, useMemo, useState } from 'react';
import ClientLayout from '../../components/ClientLayout';
import LoadingSpinner from '../../components/LoadingSpinner';
import { getOrders, getOrderDetail, confirmDelivery } from '../../services/dashboardService';
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
  active: { label: 'En cours', statuses: ['created', 'pending_payment', 'paid', 'confirmed', 'preparing', 'ready', 'assigned', 'in_transit'] },
  delivered: { label: 'Livrées', statuses: ['delivered'] },
  cancelled: { label: 'Annulées / Remboursées', statuses: ['cancelled', 'refunded'] },
  all: { label: 'Toutes', statuses: [] },
};

const ClientOrders = () => {
  const [loading, setLoading] = useState(true);
  const [orders, setOrders] = useState([]);
  const [error, setError] = useState(null);
  const [activeFilter, setActiveFilter] = useState('active');
  const [detail, setDetail] = useState(null);
  const [confirming, setConfirming] = useState(false);
  const [showPinModal, setShowPinModal] = useState(false);
  const [pinInput, setPinInput] = useState('');
  const [pendingOrderId, setPendingOrderId] = useState(null);
  const [pinError, setPinError] = useState('');

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
        setError(msg || 'Impossible de charger vos commandes');
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

  // Polling automatique pour mettre à jour les commandes toutes les 5 secondes
  useEffect(() => {
    const interval = setInterval(() => {
      fetchOrders();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  // Auto-afficher la popup d'acceptation avec PIN quand la livraison est acceptée
  useEffect(() => {
    if (detail?.status === 'in_transit' && !showPinModal && detail?.client_confirmation_pending) {
      // Afficher automatiquement la popup pour demander le PIN au client
      setPendingOrderId(detail.id);
      setShowPinModal(true);
      setPinInput('');
    }
  }, [detail?.status, detail?.client_confirmation_pending, detail?.id, showPinModal]);

  // Polling du détail de la commande ouverte toutes les 2 secondes
  useEffect(() => {
    if (!detail?.id) return;
    
    const interval = setInterval(async () => {
      try {
        const res = await getOrderDetail(detail.id);
        if (res.success) {
          setDetail(res.data || res);
        }
      } catch {
        // Silencieux : c'est juste un refresh
      }
    }, 2000);
    
    return () => clearInterval(interval);
  }, [detail?.id]);

  const counts = useMemo(() => {
    const base = { active: 0, delivered: 0, cancelled: 0, all: orders.length };
    orders.forEach((o) => {
      if (FILTERS.active.statuses.includes(o.status)) base.active += 1;
      if (FILTERS.delivered.statuses.includes(o.status)) base.delivered += 1;
      if (FILTERS.cancelled.statuses.includes(o.status)) base.cancelled += 1;
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
      /* no-op */
    }
  };

  const handleConfirmDelivery = async (orderId) => {
    // Pour les ordres en statut 'delivered', afficher la popup PIN
    const order = detail;
    if (order?.status === 'delivered' && order?.client_confirmation_pending) {
      // Montrer modale PIN
      setPendingOrderId(orderId);
      setShowPinModal(true);
      setPinInput('');
      return;
    }

    // Pas de PIN requis, confirmer directement (cas rare)
    await performConfirmDelivery(orderId, '');
  };

  const performConfirmDelivery = async (orderId, pinCode) => {
    setConfirming(true);
    setPinError('');
    try {
      const payload = {};
      if (pinCode) {
        payload.pin_code = pinCode;
      }

      const res = await confirmDelivery(orderId, payload);
      if (res.success) {
        alert('✓ Réception confirmée avec succès !');
        setDetail(null);
        setShowPinModal(false);
        setPinInput('');
        setPinError('');
        fetchOrders(); // Rafraîchir la liste
      } else {
        const msg = res.error?.message || 'Erreur lors de la confirmation';
        setPinError(`❌ ${msg}`);
      }
    } catch (err) {
      setPinError(`❌ Erreur: ${err.message}`);
    } finally {
      setConfirming(false);
    }
  };

  const handleSubmitPin = async () => {
    if (!pinInput.trim()) {
      setPinError('Veuillez entrer le code PIN');
      return;
    }
    if (pinInput.length < 4) {
      setPinError('Le code PIN doit contenir au moins 4 chiffres');
      return;
    }
    await performConfirmDelivery(pendingOrderId, pinInput);
  };

  if (loading) return <ClientLayout title="Mes commandes"><LoadingSpinner /></ClientLayout>;

  return (
    <ClientLayout title="Mes commandes">
      <div className="bg-white shadow rounded-lg p-6">
        <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Historique et suivi</h3>
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
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Magasin</th>
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
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{order.store_name || order.store}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{formatDateTime(order.created_at)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">{formatCurrency(order.total_amount || order.total)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">{renderStatus(order.status)}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{order.items?.length || order.items_count || 0}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
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
                  <p className="font-semibold">Magasin</p>
                  <p>{detail.store_name || detail.store}</p>
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

            <div className="px-5 py-3 border-t bg-gray-50 flex justify-between items-center text-sm">
              <div>
                {detail.status === 'delivered' && !showPinModal && (
                  <button
                    onClick={() => handleConfirmDelivery(detail.id)}
                    disabled={confirming}
                    className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {confirming ? 'Confirmation...' : '✓ Confirmer la réception'}
                  </button>
                )}
              </div>
              <button className="px-4 py-2 rounded-md border border-gray-200 text-gray-700 hover:bg-gray-50" onClick={() => setDetail(null)}>
                Fermer
              </button>
            </div>
          </div>
        </div>
      )}

      {/* PIN Modal */}
      {showPinModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-lg p-6 w-96">
            <div className="text-center mb-6">
              <div className="text-4xl mb-2">📦</div>
              <h3 className="text-lg font-semibold text-gray-800">
                Livraison arrivée !
              </h3>
              <p className="text-sm text-gray-600 mt-2">
                Votre livraison est arrivée. Le livreur vous a fourni un code PIN à 6 chiffres pour confirmer la réception.
              </p>
            </div>

            <input
              type="text"
              maxLength="6"
              placeholder="0000"
              value={pinInput}
              onChange={(e) => {
                setPinInput(e.target.value.replace(/\D/g, ''));
                setPinError('');
              }}
              className="w-full px-4 py-2 border border-gray-300 rounded-md text-center text-2xl font-mono font-bold focus:outline-none focus:ring-2 focus:ring-blue-500 mb-4"
              autoFocus
            />
            {pinError && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-700 rounded-md text-sm">
                {pinError}
              </div>
            )}

            <div className="flex gap-3">
              <button
                onClick={handleSubmitPin}
                disabled={confirming || pinInput.length < 4}
                className="flex-1 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-md font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {confirming ? 'Vérification...' : 'Confirmer la réception'}
              </button>
              <button
                onClick={() => {
                  setShowPinModal(false);
                  setPinInput('');
                  setPendingOrderId(null);
                  setPinError('');
                }}
                className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-md font-semibold hover:bg-gray-50"
              >
                Annuler
              </button>
            </div>
          </div>
        </div>
      )}
    </ClientLayout>
  );
};

export default ClientOrders;
