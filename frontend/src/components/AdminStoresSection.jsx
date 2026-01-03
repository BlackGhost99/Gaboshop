import { useState, useMemo } from 'react';

const AdminStoresSection = ({
  storesListAdmin,
  storesFilter,
  setStoresFilter,
  loadStoresData,
  setShowAddStore,
  setEditingStore,
  viewStoreDetail,
  handleDeactivateStore,
  handleActivateStore,
  handleDeleteStore,
  handleActivateB2B,
  handleDeactivateB2B,
  handleCreateB2BProfile,
  b2bLoading = {},
  storeCategories,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedStores, setSelectedStores] = useState([]);

  // Calculate stats on the fly
  const stats = useMemo(() => {
    const total = storesListAdmin.length;
    const active = storesListAdmin.filter(s => s.is_active).length;
    const inactive = total - active;
    // Assuming we might have these fields later, or just placeholder for now
    const newThisMonth = storesListAdmin.filter(s => {
      if (!s.created_at) return false;
      const date = new Date(s.created_at);
      const now = new Date();
      return date.getMonth() === now.getMonth() && date.getFullYear() === now.getFullYear();
    }).length;

    return { total, active, inactive, newThisMonth };
  }, [storesListAdmin]);

  const handleSearch = (value) => {
    setSearchTerm(value);
    setStoresFilter({ ...storesFilter, search: value });
  };

  const toggleStoreSelection = (storeId) => {
    setSelectedStores((prev) =>
      prev.includes(storeId)
        ? prev.filter((id) => id !== storeId)
        : [...prev, storeId]
    );
  };

  const toggleSelectAll = () => {
    if (selectedStores.length === storesListAdmin.length) {
      setSelectedStores([]);
    } else {
      setSelectedStores(storesListAdmin.map((s) => s.id));
    }
  };

  return (
    <div className="space-y-6">
      {/* KPI Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-100">
          <p className="text-xs text-gray-500 mb-1">Total Magasins</p>
          <p className="text-2xl font-bold text-gray-900">{stats.total}</p>
        </div>
        <div className="bg-green-50 p-4 rounded-lg border border-green-200">
          <p className="text-xs text-green-700 mb-1">Actifs</p>
          <p className="text-2xl font-bold text-green-800">{stats.active}</p>
        </div>
        <div className="bg-red-50 p-4 rounded-lg border border-red-200">
          <p className="text-xs text-red-700 mb-1">Inactifs</p>
          <p className="text-2xl font-bold text-red-800">{stats.inactive}</p>
        </div>
        <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
          <p className="text-xs text-blue-700 mb-1">Nouveaux (Mois)</p>
          <p className="text-2xl font-bold text-blue-800">{stats.newThisMonth}</p>
        </div>
      </div>

      {/* Filtres */}
      <div className="bg-white shadow-sm rounded-lg p-4 border border-gray-100">
        <h3 className="font-semibold mb-3 text-sm">🔍 Recherche et Filtres</h3>
        <div className="grid grid-cols-1 md:grid-cols-6 gap-3">
          <input
            type="text"
            placeholder="Chercher un magasin..."
            value={searchTerm}
            onChange={(e) => handleSearch(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded text-sm md:col-span-2"
          />

          <select
            value={storesFilter.category}
            onChange={(e) => setStoresFilter({ ...storesFilter, category: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded text-sm"
          >
            <option value="">Toutes catégories</option>
            {storeCategories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>

          <select
            value={storesFilter.city}
            onChange={(e) => setStoresFilter({ ...storesFilter, city: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded text-sm"
          >
            <option value="">Toutes villes</option>
            <option value="Libreville">Libreville</option>
            <option value="Port-Gentil">Port-Gentil</option>
            <option value="Franceville">Franceville</option>
          </select>

          <select
            value={storesFilter.status}
            onChange={(e) => setStoresFilter({ ...storesFilter, status: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded text-sm"
          >
            <option value="all">Tous statuts</option>
            <option value="active">Actifs</option>
            <option value="inactive">Inactifs</option>
          </select>

          <button
            onClick={loadStoresData}
            className="px-3 py-2 bg-indigo-600 text-white rounded text-sm font-semibold hover:bg-indigo-700"
          >
            Appliquer
          </button>
        </div>
      </div>

      {/* Bouton Ajouter */}
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">Liste des Magasins ({storesListAdmin.length})</h2>
        <button
          onClick={() => setShowAddStore(true)}
          className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-semibold hover:bg-indigo-700"
        >
          ➕ Ajouter un Magasin
        </button>
      </div>

      {/* Tableau Magasins */}
      <div className="bg-white shadow-sm rounded-lg border border-gray-100 overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left">
                <input
                  type="checkbox"
                  checked={selectedStores.length === storesListAdmin.length && storesListAdmin.length > 0}
                  onChange={toggleSelectAll}
                  className="rounded"
                />
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Logo</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Magasin</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Catégorie</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ville</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Gérant</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Statut</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">B2B</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Créé le</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {storesListAdmin.map((store) => (
              <tr key={store.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <input
                    type="checkbox"
                    checked={selectedStores.includes(store.id)}
                    onChange={() => toggleStoreSelection(store.id)}
                    className="rounded"
                  />
                </td>
                <td className="px-4 py-3">
                  <div className="h-10 w-10 bg-gray-200 rounded-full flex items-center justify-center text-gray-400 text-xs font-bold">
                    {store.name.substring(0, 2).toUpperCase()}
                  </div>
                </td>
                <td className="px-4 py-3 text-sm font-medium text-gray-900">{store.name}</td>
                <td className="px-4 py-3 text-sm text-gray-500">{store.category_name || '—'}</td>
                <td className="px-4 py-3 text-sm text-gray-500">{store.city}</td>
                <td className="px-4 py-3 text-sm text-gray-500">{store.manager_name || '—'}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 text-xs rounded-full ${store.is_active ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                    {store.is_active ? 'Actif' : 'Inactif'}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {store.is_b2b ? (
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-1 text-xs rounded-full bg-purple-50 text-purple-700">
                        B2B
                      </span>
                      {store.b2b_profile?.is_active ? (
                        <span className="px-2 py-1 text-xs rounded-full bg-green-50 text-green-700">
                          Actif
                        </span>
                      ) : (
                        <span className="px-2 py-1 text-xs rounded-full bg-gray-50 text-gray-700">
                          Inactif
                        </span>
                      )}
                    </div>
                  ) : (
                    <span className="text-xs text-gray-400">—</span>
                  )}
                </td>
                <td className="px-4 py-3 text-sm text-gray-500">
                  {store.created_at ? new Date(store.created_at).toLocaleDateString('fr-FR') : '-'}
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => viewStoreDetail(store.id)}
                      className="p-1.5 text-blue-600 hover:text-blue-900 hover:bg-blue-50 rounded"
                      title="Voir détails"
                    >
                      🔍
                    </button>
                    <button
                      onClick={() => setEditingStore(store)}
                      className="p-1.5 text-indigo-600 hover:text-indigo-900 hover:bg-indigo-50 rounded"
                      title="Modifier"
                    >
                      ✏️
                    </button>
                    {store.is_active ? (
                      <button
                        onClick={() => handleDeactivateStore(store.id)}
                        className="p-1.5 text-orange-600 hover:text-orange-900 hover:bg-orange-50 rounded"
                        title="Désactiver"
                      >
                        🚫
                      </button>
                    ) : (
                      <button
                        onClick={() => handleActivateStore(store.id)}
                        className="p-1.5 text-green-600 hover:text-green-900 hover:bg-green-50 rounded"
                        title="Activer"
                      >
                        ✅
                      </button>
                    )}
                    <button
                      onClick={() => handleDeleteStore(store.id, false)}
                      className="p-1.5 text-red-600 hover:text-red-900 hover:bg-red-50 rounded"
                      title="Supprimer"
                    >
                      🗑️
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {storesListAdmin.length === 0 && (
              <tr>
                <td colSpan="10" className="px-6 py-8 text-center text-gray-500">
                  Aucun magasin trouvé
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default AdminStoresSection;
