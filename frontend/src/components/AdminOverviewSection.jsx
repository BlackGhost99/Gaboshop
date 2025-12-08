import React from 'react';

const AdminOverviewSection = ({ summary, loading }) => {
  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!summary) {
    return <div className="text-center py-10 text-gray-500">Aucune donnée disponible</div>;
  }

  const { kpis, charts, alerts, recent_orders, top_lists, system_status } = summary;

  // Helper for currency formatting
  const formatMoney = (amount) => {
    return (amount || 0).toLocaleString('fr-FR') + ' FCFA';
  };

  return (
    <div className="space-y-8">
      {/* 1. KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Orders */}
        <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-100">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs text-gray-500 uppercase font-semibold">Commandes (Jour)</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-1">{kpis?.orders?.today || 0}</h3>
            </div>
            <span className="bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full">
              {kpis?.orders?.month || 0} ce mois
            </span>
          </div>
          <div className="mt-4 flex justify-between text-xs text-gray-500">
            <span>⏳ {kpis?.orders?.pending || 0} en attente</span>
            <span>✅ {kpis?.orders?.delivered || 0} livrées</span>
          </div>
        </div>

        {/* Finance */}
        <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-100">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs text-gray-500 uppercase font-semibold">Ventes (Jour)</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-1">{formatMoney(kpis?.finance?.sales_today)}</h3>
            </div>
            <span className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded-full">
              +Commissions
            </span>
          </div>
          <div className="mt-4 flex justify-between text-xs text-gray-500">
            <span>📅 {formatMoney(kpis?.finance?.sales_month)} (Mois)</span>
            <span>💰 {formatMoney(kpis?.finance?.commissions_total)} (Com)</span>
          </div>
        </div>

        {/* Stores */}
        <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-100">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs text-gray-500 uppercase font-semibold">Magasins</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-1">{kpis?.stores?.total || 0}</h3>
            </div>
            <span className="bg-purple-100 text-purple-800 text-xs px-2 py-1 rounded-full">
              +{kpis?.stores?.new_month || 0} ce mois
            </span>
          </div>
          <div className="mt-4 text-xs text-gray-500">
            Partenaires actifs sur la plateforme
          </div>
        </div>

        {/* Users */}
        <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-100">
          <div className="flex justify-between items-start">
            <div>
              <p className="text-xs text-gray-500 uppercase font-semibold">Utilisateurs</p>
              <h3 className="text-2xl font-bold text-gray-900 mt-1">{kpis?.users?.clients_active || 0}</h3>
            </div>
            <span className="bg-orange-100 text-orange-800 text-xs px-2 py-1 rounded-full">
              Clients actifs
            </span>
          </div>
          <div className="mt-4 text-xs text-gray-500">
            🛵 {kpis?.users?.agents_active_today || 0} livreurs actifs aujourd'hui
          </div>
        </div>
      </div>

      {/* 2. Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sales Curve */}
        <div className="lg:col-span-2 bg-white p-6 rounded-lg shadow-sm border border-gray-100">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">📊 Courbe des ventes (30 jours)</h3>
          <div className="h-64 flex items-end space-x-1">
            {charts?.sales_curve?.map((day, index) => {
               const maxSales = Math.max(...(charts.sales_curve.map(d => d.sales) || [0]), 1);
               const height = (day.sales / maxSales) * 100;
               return (
                 <div key={index} className="flex-1 flex flex-col justify-end group relative">
                   <div 
                     className="bg-blue-500 hover:bg-blue-600 rounded-t transition-all duration-300"
                     style={{ height: `${height}%`, minHeight: '4px' }}
                   ></div>
                   {/* Tooltip */}
                   <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 hidden group-hover:block bg-gray-800 text-white text-xs rounded p-2 z-10 whitespace-nowrap">
                     <p>{day.date}</p>
                     <p>{formatMoney(day.sales)}</p>
                     <p>{day.count} commandes</p>
                   </div>
                 </div>
               );
            })}
          </div>
          <div className="flex justify-between mt-2 text-xs text-gray-400">
            <span>Il y a 30 jours</span>
            <span>Aujourd'hui</span>
          </div>
        </div>

        {/* Category Distribution (Pie Chart Simulation) */}
        <div className="bg-white p-6 rounded-lg shadow-sm border border-gray-100">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">🟦 Répartition (Top 5)</h3>
          <div className="space-y-4">
            {charts?.categories?.map((cat, index) => {
              const total = charts.categories.reduce((acc, curr) => acc + curr.value, 0) || 1;
              const percent = ((cat.value / total) * 100).toFixed(1);
              return (
                <div key={index}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="text-gray-600">{cat.name}</span>
                    <span className="font-semibold">{percent}%</span>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2">
                    <div 
                      className={`h-2 rounded-full ${['bg-blue-500', 'bg-green-500', 'bg-yellow-500', 'bg-purple-500', 'bg-red-500'][index % 5]}`} 
                      style={{ width: `${percent}%` }}
                    ></div>
                  </div>
                </div>
              );
            })}
            {(!charts?.categories || charts.categories.length === 0) && (
              <p className="text-sm text-gray-400 text-center py-4">Aucune donnée de catégorie</p>
            )}
          </div>
        </div>
      </div>

      {/* 3. Alerts & Notifications */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Low Stock */}
        <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-100 border-l-4 border-l-yellow-500">
          <h3 className="font-semibold text-gray-800 mb-3 flex items-center">
            ⚠️ Stock Faible
          </h3>
          <div className="space-y-3">
            {alerts?.low_stock?.map((p) => (
              <div key={p.id} className="flex justify-between items-center text-sm border-b border-gray-50 pb-2 last:border-0">
                <div>
                  <p className="font-medium text-gray-900">{p.name}</p>
                  <p className="text-xs text-gray-500">{p.store__name}</p>
                </div>
                <span className="text-red-600 font-bold bg-red-50 px-2 py-1 rounded text-xs">
                  {p.stock} restants
                </span>
              </div>
            ))}
            {(!alerts?.low_stock || alerts.low_stock.length === 0) && (
              <p className="text-sm text-gray-400">Aucune alerte de stock.</p>
            )}
          </div>
        </div>

        {/* Deactivated Stores */}
        <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-100 border-l-4 border-l-red-500">
          <h3 className="font-semibold text-gray-800 mb-3 flex items-center">
            🛑 Magasins Désactivés
          </h3>
          <div className="space-y-3">
            {alerts?.deactivated_stores?.map((s) => (
              <div key={s.id} className="flex justify-between items-center text-sm border-b border-gray-50 pb-2 last:border-0">
                <p className="font-medium text-gray-900">{s.name}</p>
                <span className="text-xs text-red-500 bg-red-50 px-2 py-1 rounded">Inactif</span>
              </div>
            ))}
             {(!alerts?.deactivated_stores || alerts.deactivated_stores.length === 0) && (
              <p className="text-sm text-gray-400">Tous les magasins sont actifs.</p>
            )}
          </div>
        </div>

        {/* Unvalidated Agents */}
        <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-100 border-l-4 border-l-blue-500">
          <h3 className="font-semibold text-gray-800 mb-3 flex items-center">
            👤 Livreurs à valider
          </h3>
          <div className="space-y-3">
            {alerts?.unvalidated_agents?.map((u) => (
              <div key={u.id} className="flex justify-between items-center text-sm border-b border-gray-50 pb-2 last:border-0">
                <div>
                  <p className="font-medium text-gray-900">{u.first_name} {u.last_name}</p>
                  <p className="text-xs text-gray-500">{u.phone}</p>
                </div>
                <button className="text-xs bg-blue-100 text-blue-600 px-2 py-1 rounded hover:bg-blue-200">
                  Voir
                </button>
              </div>
            ))}
            {(!alerts?.unvalidated_agents || alerts.unvalidated_agents.length === 0) && (
              <p className="text-sm text-gray-400">Aucun livreur en attente.</p>
            )}
          </div>
        </div>
      </div>

      {/* 4. Recent Orders Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-100 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center">
          <h3 className="font-semibold text-gray-800">🧾 Commandes Récentes</h3>
          <button className="text-sm text-blue-600 hover:text-blue-800">Voir tout</button>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm text-left">
            <thead className="bg-gray-50 text-gray-500 font-medium">
              <tr>
                <th className="px-6 py-3">ID</th>
                <th className="px-6 py-3">Client</th>
                <th className="px-6 py-3">Magasin</th>
                <th className="px-6 py-3">Montant</th>
                <th className="px-6 py-3">Statut</th>
                <th className="px-6 py-3">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {recent_orders?.map((order) => (
                <tr key={order.id} className="hover:bg-gray-50">
                  <td className="px-6 py-3 font-medium text-gray-900">#{order.order_number}</td>
                  <td className="px-6 py-3">{order.client__first_name} {order.client__last_name}</td>
                  <td className="px-6 py-3">{order.store__name}</td>
                  <td className="px-6 py-3 font-medium">{formatMoney(order.total_amount)}</td>
                  <td className="px-6 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      order.status === 'delivered' ? 'bg-green-100 text-green-800' :
                      order.status === 'cancelled' ? 'bg-red-100 text-red-800' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>
                      {order.status}
                    </span>
                  </td>
                  <td className="px-6 py-3 text-gray-500">
                    {new Date(order.created_at).toLocaleDateString('fr-FR')}
                  </td>
                </tr>
              ))}
              {(!recent_orders || recent_orders.length === 0) && (
                <tr>
                  <td colSpan="6" className="px-6 py-8 text-center text-gray-500">Aucune commande récente</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 5. Top Lists */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Top Products */}
        <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-100">
          <h3 className="font-semibold text-gray-800 mb-4">🥇 Top Produits Vendus</h3>
          <div className="space-y-3">
            {top_lists?.products?.map((p, idx) => (
              <div key={idx} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-3">
                  <span className="w-6 h-6 flex items-center justify-center bg-gray-100 rounded-full text-xs font-bold text-gray-600">
                    {idx + 1}
                  </span>
                  <div>
                    <p className="font-medium text-gray-900">{p.product__name}</p>
                    <p className="text-xs text-gray-500">{p.product__store__name}</p>
                  </div>
                </div>
                <span className="font-bold text-gray-700">{p.total_sold} ventes</span>
              </div>
            ))}
             {(!top_lists?.products || top_lists.products.length === 0) && (
              <p className="text-sm text-gray-400 text-center">Pas de données</p>
            )}
          </div>
        </div>

        {/* Top Stores */}
        <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-100">
          <h3 className="font-semibold text-gray-800 mb-4">🏆 Top Magasins Performants</h3>
          <div className="space-y-3">
            {top_lists?.stores?.map((s, idx) => (
              <div key={idx} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-3">
                  <span className="w-6 h-6 flex items-center justify-center bg-yellow-100 text-yellow-700 rounded-full text-xs font-bold">
                    {idx + 1}
                  </span>
                  <div>
                    <p className="font-medium text-gray-900">{s.name}</p>
                    <p className="text-xs text-gray-500">{s.order_count} commandes</p>
                  </div>
                </div>
                <span className="font-bold text-green-600">{formatMoney(s.revenue)}</span>
              </div>
            ))}
            {(!top_lists?.stores || top_lists.stores.length === 0) && (
              <p className="text-sm text-gray-400 text-center">Pas de données</p>
            )}
          </div>
        </div>
      </div>

      {/* 6. System Status & Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* System Status */}
        <div className="bg-gray-900 text-white p-6 rounded-lg shadow-sm">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            ⚙️ État du Système
          </h3>
          <div className="space-y-4 text-sm">
            <div className="flex justify-between items-center">
              <span className="text-gray-400">API Health</span>
              <span className="px-2 py-1 bg-green-500/20 text-green-400 rounded text-xs font-bold">OK</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-400">Erreurs API (24h)</span>
              <span className="font-mono">{system_status?.api_errors || 0}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-gray-400">Sync Mobile Money</span>
              <span className="text-xs text-gray-300">{system_status?.last_sync || 'N/A'}</span>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="md:col-span-2 bg-white p-6 rounded-lg shadow-sm border border-gray-100">
          <h3 className="font-semibold text-gray-800 mb-4">🚀 Actions Rapides</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <button className="p-3 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors flex flex-col items-center gap-2 text-sm font-medium">
              <span className="text-xl">➕</span>
              Ajouter Magasin
            </button>
            <button className="p-3 bg-green-50 text-green-700 rounded-lg hover:bg-green-100 transition-colors flex flex-col items-center gap-2 text-sm font-medium">
              <span className="text-xl">📦</span>
              Ajouter Produit
            </button>
            <button className="p-3 bg-purple-50 text-purple-700 rounded-lg hover:bg-purple-100 transition-colors flex flex-col items-center gap-2 text-sm font-medium">
              <span className="text-xl">🛵</span>
              Gérer Livreurs
            </button>
            <button className="p-3 bg-gray-50 text-gray-700 rounded-lg hover:bg-gray-100 transition-colors flex flex-col items-center gap-2 text-sm font-medium">
              <span className="text-xl">⚙️</span>
              Paramètres
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminOverviewSection;
