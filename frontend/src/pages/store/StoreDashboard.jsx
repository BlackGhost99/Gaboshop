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
  const [showAllB2BOrders, setShowAllB2BOrders] = useState(false); // Pour afficher toutes les commandes B2B

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

  // Auto-refresh pour traçabilité B2B quand sur l'onglet supply
  useEffect(() => {
    if (activeTab === 'supply') {
      // Rafraîchir toutes les 30 secondes pour voir les mises à jour de statut
      const interval = setInterval(() => {
        fetchDashboard();
      }, 30000); // 30 secondes
      
      return () => clearInterval(interval);
    }
  }, [activeTab]);

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

        {/* Alertes Souscription */}
        {dashboardData?.subscription && (
          <>
            {/* Alerte expiration imminente (< 7 jours) */}
            {dashboardData.subscription.days_until_expiry !== undefined && dashboardData.subscription.days_until_expiry < 7 && dashboardData.subscription.days_until_expiry > 0 && (
              <div className="bg-orange-100 border-l-4 border-orange-500 text-orange-800 p-5 mb-6 rounded-lg shadow-md">
                <div className="flex items-start gap-3">
                  <svg className="w-7 h-7 text-orange-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                  <div className="flex-1">
                    <p className="font-bold text-lg mb-2">⚠️ Votre abonnement expire bientôt !</p>
                    <p className="text-sm mb-3">
                      Votre plan <strong>{dashboardData.subscription.plan_name}</strong> expire dans <strong className="text-orange-900">{dashboardData.subscription.days_until_expiry} jour{dashboardData.subscription.days_until_expiry > 1 ? 's' : ''}</strong>.
                      Renouvelez-le maintenant pour conserver tous vos avantages.
                    </p>
                    <Link
                      to="/store/subscription"
                      className="inline-flex items-center gap-2 bg-orange-600 hover:bg-orange-700 text-white px-6 py-2 rounded-lg font-semibold transition-colors shadow-md"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                      </svg>
                      Renouveler maintenant
                    </Link>
                  </div>
                </div>
              </div>
            )}

            {/* Alerte plan expiré */}
            {dashboardData.subscription.status === 'expired' || (dashboardData.subscription.days_until_expiry !== undefined && dashboardData.subscription.days_until_expiry <= 0) && (
              <div className="bg-red-100 border-l-4 border-red-500 text-red-800 p-5 mb-6 rounded-lg shadow-lg">
                <div className="flex items-start gap-3">
                  <svg className="w-7 h-7 text-red-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <div className="flex-1">
                    <p className="font-bold text-lg mb-2">❌ Votre abonnement a expiré</p>
                    <p className="text-sm mb-3">
                      Votre plan <strong>{dashboardData.subscription.plan_name}</strong> a expiré. 
                      Vous avez été automatiquement basculé sur le plan Free avec des limitations.
                      Renouvelez dès maintenant pour récupérer tous vos avantages.
                    </p>
                    <Link
                      to="/store/subscription"
                      className="inline-flex items-center gap-2 bg-red-600 hover:bg-red-700 text-white px-6 py-2 rounded-lg font-bold transition-colors shadow-md"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      Renouveler mon abonnement
                    </Link>
                  </div>
                </div>
              </div>
            )}

            {/* Encouragement upgrade si Free */}
            {dashboardData.subscription.plan_type === 'free' && !dashboardData.subscription.status === 'expired' && (
              <div className="bg-indigo-50 border-l-4 border-indigo-500 text-indigo-800 p-5 mb-6 rounded-lg shadow-sm">
                <div className="flex items-start gap-3">
                  <svg className="w-7 h-7 text-indigo-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                  <div className="flex-1">
                    <p className="font-bold text-lg mb-2">✨ Passez au plan Business !</p>
                    <p className="text-sm mb-3">
                      Débloquez l'accès B2B, commissions réduites (0% alimentaire, 2% autre), analytics avancés et bien plus encore.
                    </p>
                    <Link
                      to="/store/subscription"
                      className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-6 py-2 rounded-lg font-semibold transition-colors shadow-md"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z" />
                      </svg>
                      Découvrir les plans
                    </Link>
                  </div>
                </div>
              </div>
            )}
          </>
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

            {/* Commandes Client (B2C) */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-8">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-bold text-gray-900">Commandes Clients (B2C)</h3>
                <button
                  onClick={fetchDashboard}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md text-sm font-medium"
                >
                  Rafraîchir
                </button>
              </div>

              {dashboardData?.b2c_pending_orders?.length > 0 ? (
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
                      {dashboardData.b2c_pending_orders.map((order) => {
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
                  <p className="mt-4 text-gray-500">Aucune commande client en attente</p>
                </div>
              )}
            </div>

            {/* Commandes B2B Reçues (si grossiste) */}
            {dashboardData?.b2b_incoming_orders?.length > 0 && (
              <div className="bg-indigo-50 rounded-lg shadow-md p-6 mb-8 border border-indigo-200">
                <div className="flex justify-between items-center mb-6">
                  <h3 className="text-xl font-bold text-indigo-900 flex items-center gap-2">
                    <span className="text-2xl">🏭</span>
                    Commandes B2B Reçues (Magasins)
                  </h3>
                </div>

                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-indigo-200">
                    <thead className="bg-indigo-100">
                      <tr>
                        <th className="px-6 py-3 text-left text-xs font-bold text-indigo-700 uppercase tracking-wider">
                          N°
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-bold text-indigo-700 uppercase tracking-wider">
                          Magasin Acheteur
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-bold text-indigo-700 uppercase tracking-wider">
                          Date
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-bold text-indigo-700 uppercase tracking-wider">
                          Total
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-bold text-indigo-700 uppercase tracking-wider">
                          Statut
                        </th>
                        <th className="px-6 py-3 text-left text-xs font-bold text-indigo-700 uppercase tracking-wider">
                          Actions
                        </th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-indigo-100">
                      {dashboardData.b2b_incoming_orders.map((order) => {
                        const statusBadge = getOrderStatusBadge(order.status);
                        const action = getNextAction(order.status);
                        return (
                          <tr key={order.id} className="hover:bg-indigo-50">
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-indigo-900">
                              #{order.id}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700 font-semibold">
                              {order.source_store_name || 'Magasin'}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                              {formatDateTime(order.created_at)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-indigo-700">
                              {formatCurrency(order.total)}
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={`px-3 py-1 rounded-full text-xs font-bold ${statusBadge.className}`}>
                                {statusBadge.label}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm space-x-2">
                              {action && (
                                <button
                                  onClick={() => handleAdvanceStatus(order)}
                                  className={`font-bold px-3 py-1 rounded border-2 ${actionLoading[order.id] ? 'text-gray-400' : 'text-green-700 border-green-600 hover:bg-green-50'}`}
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
              </div>
            )}

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
          <div className="space-y-8">
            {/* Mes commandes d'approvisionnement (B2B Sortantes) */}
            {dashboardData?.b2b_outgoing_orders?.length > 0 && (
              <div className="bg-gradient-to-br from-white to-indigo-50 rounded-lg shadow-lg p-6 border-2 border-indigo-200">
                <div className="flex justify-between items-center mb-6">
                  <h3 className="text-2xl font-bold text-indigo-900 flex items-center gap-3">
                    <div className="bg-indigo-600 rounded-full p-3">
                      <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                      </svg>
                    </div>
                    Mes Commandes d'Approvisionnement
                  </h3>
                  <button
                    onClick={fetchDashboard}
                    className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg font-semibold flex items-center gap-2 shadow-md transition-all"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Actualiser
                  </button>
                </div>
                <div className="overflow-x-auto bg-white rounded-lg shadow">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-indigo-100">
                      <tr>
                        <th className="px-6 py-4 text-left text-xs font-bold text-indigo-800 uppercase tracking-wider">Commande</th>
                        <th className="px-6 py-4 text-left text-xs font-bold text-indigo-800 uppercase tracking-wider">Fournisseur</th>
                        <th className="px-6 py-4 text-left text-xs font-bold text-indigo-800 uppercase tracking-wider">Date</th>
                        <th className="px-6 py-4 text-left text-xs font-bold text-indigo-800 uppercase tracking-wider">Articles</th>
                        <th className="px-6 py-4 text-left text-xs font-bold text-indigo-800 uppercase tracking-wider">Montant</th>
                        <th className="px-6 py-4 text-left text-xs font-bold text-indigo-800 uppercase tracking-wider">État</th>
                        <th className="px-6 py-4 text-left text-xs font-bold text-indigo-800 uppercase tracking-wider">Livraison</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-100">
                      {(showAllB2BOrders ? dashboardData.b2b_outgoing_orders : dashboardData.b2b_outgoing_orders.slice(0, 5)).map((order) => {
                        const statusBadge = getOrderStatusBadge(order.status);
                        const isDelivered = order.status === 'delivered';
                        const isInProgress = ['confirmed', 'preparing', 'ready', 'assigned', 'in_transit'].includes(order.status);
                        
                        return (
                          <tr key={order.id} className={`hover:bg-indigo-50 transition-colors ${isDelivered ? 'bg-green-50' : ''}`}>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="flex items-center gap-2">
                                <div className={`w-2 h-2 rounded-full ${isDelivered ? 'bg-green-500' : isInProgress ? 'bg-blue-500 animate-pulse' : 'bg-gray-400'}`}></div>
                                <span className="text-sm font-bold text-indigo-700">#{order.order_number || order.id}</span>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <div className="flex items-center gap-2">
                                <div className="bg-indigo-100 rounded-full p-2">
                                  <svg className="w-4 h-4 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                                  </svg>
                                </div>
                                <span className="text-sm text-gray-900 font-semibold">{order.wholesaler_name}</span>
                              </div>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-xs text-gray-600">{formatDateTime(order.created_at)}</td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 rounded-full text-xs font-semibold text-gray-700">
                                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                                </svg>
                                {order.items_count} article{order.items_count > 1 ? 's' : ''}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-gray-900">{formatCurrency(order.total)}</td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              <span className={`px-3 py-1 rounded-full text-xs font-bold ${statusBadge.className} shadow-sm`}>
                                {statusBadge.label}
                              </span>
                            </td>
                            <td className="px-6 py-4 whitespace-nowrap">
                              {isDelivered ? (
                                <div className="flex items-center gap-1 text-green-700">
                                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                  </svg>
                                  <span className="text-xs font-bold">Reçu</span>
                                </div>
                              ) : isInProgress ? (
                                <div className="flex items-center gap-1 text-blue-700">
                                  <svg className="w-5 h-5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                  </svg>
                                  <span className="text-xs font-bold">En cours</span>
                                </div>
                              ) : (
                                <div className="flex items-center gap-1 text-gray-500">
                                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                  </svg>
                                  <span className="text-xs font-bold">En attente</span>
                                </div>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
                
                {/* Bouton Voir plus / Voir moins */}
                {dashboardData.b2b_outgoing_orders.length > 5 && (
                  <div className="mt-4 flex justify-center">
                    <button
                      onClick={() => setShowAllB2BOrders(!showAllB2BOrders)}
                      className="inline-flex items-center gap-2 px-6 py-3 bg-white border-2 border-indigo-300 text-indigo-700 rounded-lg hover:bg-indigo-50 font-semibold transition-all shadow-sm hover:shadow-md"
                    >
                      {showAllB2BOrders ? (
                        <>
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                          </svg>
                          Voir moins
                        </>
                      ) : (
                        <>
                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                          </svg>
                          Voir plus ({dashboardData.b2b_outgoing_orders.length - 5} commandes)
                        </>
                      )}
                    </button>
                  </div>
                )}
                
                <div className="mt-4 p-4 bg-indigo-50 rounded-lg border border-indigo-200">
                  <p className="text-sm text-indigo-800 font-medium flex items-center gap-2">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    Vos produits sont automatiquement ajoutés à votre inventaire dès la livraison confirmée
                  </p>
                </div>
              </div>
            )}

            <B2BProcurementEmbedded />
          </div>
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
