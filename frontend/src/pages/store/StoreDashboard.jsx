import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

import StoreLayout from '../../components/StoreLayout';
import StatCard from '../../components/StatCard';
import LoadingSpinner from '../../components/LoadingSpinner';
import B2BProcurementEmbedded from '../../components/b2b/B2BProcurementEmbedded';
import { getStoreDashboard } from '../../services/dashboardService';
import { updateOrderStatus } from '../../services/orderService';
import { formatCurrency, formatDateTime, getOrderStatusBadge } from '../../utils/helpers';

const StoreDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState(null);
  const [error, setError] = useState(null);
  const [toast, setToast] = useState(null);
  const [actionLoading, setActionLoading] = useState({});
  const [activeTab, setActiveTab] = useState('overview'); // overview, supply

  const fetchDashboard = async () => {
    try {
      setLoading(true);
      const response = await getStoreDashboard();
      if (response.success) {
        setDashboardData(response.data);
      } else {
        setError('Impossible de charger les données');
      }
    } catch (err) {
      setError('Erreur lors du chargement des données');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const fetchWholesalers = async () => {
    try {
      setLoadingWholesalers(true);
      const response = await getWholesalers();
      if (response.success) {
        setWholesalers(response.data || []);
      } else {
        setWholesalers([]);
        console.error("Erreur chargement grossistes", response.error);
      }
    } catch (err) {
      console.error("Erreur chargement grossistes", err);
      setWholesalers([]);
    } finally {
      setLoadingWholesalers(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  useEffect(() => {
    if (!toast) return undefined;
    const timer = setTimeout(() => setToast(null), 2200);
    return () => clearTimeout(timer);
  }, [toast]);

  const getNextAction = (status) => {
    if (status === 'paid') return { label: 'Confirmer', next: 'confirmed' };
    if (status === 'confirmed') return { label: 'Préparer', next: 'preparing' };
    return null;
  };

  const handleAdvanceStatus = async (order) => {
    const action = getNextAction(order.status);
    if (!action) return;

    setActionLoading((prev) => ({ ...prev, [order.id]: true }));
    try {
      const res = await updateOrderStatus(order.id, action.next);
      if (res.success) {
        setToast({ type: 'success', message: `Commande #${order.id} → ${action.next}` });
        fetchDashboard();
      } else {
        const detail = res.error?.details;
        const msg = detail ? Object.values(detail).flat().join(' | ') : res.error?.message;
        setToast({ type: 'error', message: msg || 'Action impossible' });
      }
    } catch (err) {
      const detail = err?.error?.details || err?.details;
      const msg = detail ? Object.values(detail).flat().join(' | ') : err?.error?.message || err;
      setToast({ type: 'error', message: `Erreur: ${msg}` });
    } finally {
      setActionLoading((prev) => ({ ...prev, [order.id]: false }));
    }
  };

  if (loading) return <LoadingSpinner />;

  if (error) {
    return (
      <StoreLayout title="Erreur">
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      </StoreLayout>
    );
  }

  // Chart data: prefer weekly_revenue from API, otherwise fallback to demo
  const chartData = (dashboardData?.weekly_revenue && Array.isArray(dashboardData.weekly_revenue))
    ? dashboardData.weekly_revenue.map(d => ({ name: d.name, vente: d.revenue }))
    : [
        { name: 'Lun', vente: 15000 },
        { name: 'Mar', vente: 23000 },
        { name: 'Mer', vente: 18000 },
        { name: 'Jeu', vente: 32000 },
        { name: 'Ven', vente: 21000 },
        { name: 'Sam', vente: 45000 },
        { name: 'Dim', vente: dashboardData?.stats?.daily_revenue || 12000 },
      ];

  return (
    <>
      <StoreLayout
        title={`Dashboard - ${dashboardData?.store?.name || 'Magasin'}`}
        userName={dashboardData?.store?.name}
      >
        {dashboardData?.store?.store_type === 'wholesaler' && (
          <div className="bg-amber-100 border-l-4 border-amber-500 text-amber-700 p-4 mb-6 rounded shadow-sm">
            <p className="font-bold flex items-center gap-2">
              <span className="text-xl">🏭</span>
              MODE GROSSISTE ACTIVÉ
            </p>
            <p className="text-sm">
              Votre magasin est visible par les autres boutiques dans leur onglet "Approvisionnement".
              Gérez votre stock ici, il sera automatiquement disponible pour vos clients B2B.
            </p>
          </div>
        )}
        {dashboardData?.store?.store_type === 'industry' && (
          <div className="bg-blue-100 border-l-4 border-blue-500 text-blue-700 p-4 mb-6 rounded shadow-sm">
            <p className="font-bold flex items-center gap-2">
              <span className="text-xl">🏭</span>
              MODE INDUSTRIE / USINE
            </p>
            <p className="text-sm">
              Compte Industriel. Vos produits sont listés pour les commandes de gros volume.
            </p>
          </div>
        )}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 -mt-6 mb-8">
          <p className="text-gray-600">Gérez vos commandes et suivez vos performances</p>
          <div className="flex gap-3">
            {dashboardData?.store?.id && (
              <Link
                to={`/stores/${dashboardData.store.id}`}
                target="_blank"
                className="inline-flex items-center px-4 py-2 border border-indigo-600 text-indigo-600 rounded-md hover:bg-indigo-50 font-medium transition-colors"
              >
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
                Voir ma boutique
              </Link>
            )}
            <button
              onClick={() => setActiveTab('supply')}
              className={`px-4 py-2 rounded-md font-medium transition-colors ${activeTab === 'supply' ? 'bg-indigo-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-50'}`}
            >
              Approvisionnement (B2B)
            </button>
            <button
              onClick={() => setActiveTab('overview')}
              className={`px-4 py-2 rounded-md font-medium transition-colors ${activeTab === 'overview' ? 'bg-indigo-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-50'}`}
            >
              Vue d'ensemble
            </button>
          </div>
        </div>

        {activeTab === 'overview' && (
          <>
            {/* Charts Section */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
              <div className="lg:col-span-2 bg-white rounded-2xl shadow-lg p-6 border border-gray-100">
                <h3 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-2">
                  <span className="p-2 bg-indigo-100 text-indigo-600 rounded-lg">📊</span>
                  Évolution des ventes (Semaine)
                </h3>
                <div className="h-64 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                      <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#6b7280' }} dy={10} />
                      <YAxis axisLine={false} tickLine={false} tick={{ fill: '#6b7280' }} tickFormatter={(value) => `${value / 1000}k`} />
                      <Tooltip
                        cursor={{ fill: '#f3f4f6' }}
                        contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.1)' }}
                      />
                      <Bar dataKey="vente" fill="#6366f1" radius={[6, 6, 0, 0]} barSize={40} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Goal card removed per request */}
            </div>

            {/* Statistiques principales */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
              <StatCard
                title="Commandes du jour"
                value={dashboardData?.stats?.daily_orders_count || 0}
                icon={
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                }
                bgColor="bg-slate-600"
              />
              <StatCard
                title="Ventes du jour"
                value={formatCurrency(dashboardData?.stats?.daily_revenue || 0)}
                icon={
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                }
                bgColor="bg-emerald-500"
              />
              <StatCard
                title="Bénéfice net"
                value={formatCurrency(dashboardData?.stats?.daily_net_revenue || 0)}
                hint="Après commission"
                icon={
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                }
                bgColor="bg-teal-500"
              />
              <StatCard
                title="Commission du jour"
                value={formatCurrency(dashboardData?.stats?.daily_commission || 0)}
                icon={
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v8m0 0l3-3m-3 3l-3-3m9-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                }
                bgColor="bg-amber-500"
              />
            </div>

            {/* Forfait / abonnement */}
            <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 text-white rounded-2xl p-6 mb-8 shadow-lg flex flex-col md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-sm uppercase tracking-wide text-slate-300">Votre forfait</p>
                <h3 className="text-2xl font-bold">{dashboardData?.subscription?.plan_name || 'Forfait Essentiel'}</h3>
                <p className="text-slate-200 mt-1">Statut : {dashboardData?.subscription?.status || 'active'}</p>
                {dashboardData?.subscription?.end_date && (
                  <p className="text-slate-300 text-sm mt-1">Expire le {formatDateTime(dashboardData.subscription.end_date)}</p>
                )}
              </div>
              <div className="mt-4 md:mt-0 flex flex-wrap gap-3">
                <span className="bg-white/10 text-white px-4 py-2 rounded-full text-sm border border-white/20">Commission réduite</span>
                <span className="bg-white/10 text-white px-4 py-2 rounded-full text-sm border border-white/20">Support prioritaire</span>
                <span className="bg-white/10 text-white px-4 py-2 rounded-full text-sm border border-white/20">Promos mises en avant</span>
              </div>
            </div>

            {/* Commandes en attente */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-8">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-bold text-gray-900">Commandes en attente</h3>
                <button
                  onClick={fetchDashboard}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md text-sm font-medium"
                >
                  Rafraîchir
                </button>
              </div>

              {dashboardData?.pending_order_list?.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          N° Commande
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Client
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Date
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Montant
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Statut
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {dashboardData.pending_order_list.map((order) => {
                        const statusBadge = getOrderStatusBadge(order.status);
                        const action = getNextAction(order.status);
                        return (
                          <tr key={order.id} className="hover:bg-gray-50">
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                              #{order.id}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {order.client_name || 'Client'}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {formatDateTime(order.created_at)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">
                              {formatCurrency(order.total)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={`px-3 py-1 rounded-full text-xs font-medium ${statusBadge.className}`}>
                                {statusBadge.label}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm space-x-2">
                              <button className="text-indigo-400 cursor-not-allowed font-medium" disabled>
                                Voir
                              </button>
                              {action && (
                                <button
                                  onClick={() => handleAdvanceStatus(order)}
                                  className={`font-medium ${actionLoading[order.id] ? 'text-gray-400 cursor-wait' : 'text-green-600 hover:text-green-900'}`}
                                  disabled={!!actionLoading[order.id]}
                                >
                                  {action.label}
                                </button>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-12">
                  <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <p className="mt-4 text-gray-500">Aucune commande en attente</p>
                </div>
              )}
            </div>

            {/* Statistiques mensuelles */}
            <div className="bg-white rounded-lg shadow-md p-6">
              <h3 className="text-xl font-bold text-gray-900 mb-6">Performance du mois</h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="border-l-4 border-blue-500 pl-4">
                  <p className="text-sm text-gray-600">Commandes totales</p>
                  <p className="text-2xl font-bold text-gray-900">{dashboardData?.monthly_orders || 0}</p>
                </div>
                <div className="border-l-4 border-green-500 pl-4">
                  <p className="text-sm text-gray-600">Revenus totaux</p>
                  <p className="text-2xl font-bold text-gray-900">{formatCurrency(dashboardData?.monthly_revenue || 0)}</p>
                </div>
                <div className="border-l-4 border-purple-500 pl-4">
                  <p className="text-sm text-gray-600">Commission déduite</p>
                  <p className="text-2xl font-bold text-gray-900">{formatCurrency(dashboardData?.monthly_commission || 0)}</p>
                </div>
              </div>
            </div>
          </>
        )}

        {activeTab === 'supply' && (
          <B2BProcurementEmbedded />
        )}
      </StoreLayout>
      {toast && (
        <div className="fixed bottom-5 right-5 z-50">
          <div
            className={`px-4 py-3 rounded-lg shadow-xl border text-sm font-medium text-white ${toast.type === 'success' ? 'bg-green-600 border-green-500' : 'bg-red-600 border-red-500'}`}
          >
            {toast.message}
          </div>
        </div>
      )}
    </>
  );
};

export default StoreDashboard;
