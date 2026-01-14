import React, { useState, useEffect } from 'react';
import B2CCategoryModal from './B2CCategoryModal';
import B2CProductPricingModal from './B2CProductPricingModal';
import StoreB2CModal from './StoreB2CModal';
import ConfirmModal from './ConfirmModal';
import Modal from './Modal';
import {
  getB2CProfiles,
  getB2CCategories,
  createB2CCategory,
  updateB2CCategory,
  deleteB2CCategory,
  getB2CProductPricings,
  updateB2CProductPrice,
  getB2COrders
} from '../services/adminService';

/**
 * Section Admin pour gérer B2C (Profils, Catégories, Prix, Commandes)
 */
const AdminB2CManagementSection = () => {
  const [activeSubTab, setActiveSubTab] = useState('profiles');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Profils B2C
  const [b2cProfiles, setB2cProfiles] = useState([]);
  const [selectedStoreForB2C, setSelectedStoreForB2C] = useState(null);

  // Catégories B2C
  const [b2cCategories, setB2cCategories] = useState([]);
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [editingCategory, setEditingCategory] = useState(null);
  const [confirmDeleteCategory, setConfirmDeleteCategory] = useState(null);

  // Prix B2C
  const [b2cPricings, setB2cPricings] = useState([]);
  const [selectedStoreForPricing, setSelectedStoreForPricing] = useState(null);
  const [showPricingModal, setShowPricingModal] = useState(false);
  const [editingPricing, setEditingPricing] = useState(null);

  // Commandes B2C
  const [b2cOrders, setB2cOrders] = useState([]);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [orderFilters, setOrderFilters] = useState({
    store_id: '',
    status: '',
    date_from: '',
    date_to: '',
    search: ''
  });

  // Load B2C profiles on mount and when switching to pricing tab
  useEffect(() => {
    if (activeSubTab === 'pricing' && b2cProfiles.length === 0) {
      getB2CProfiles().then(res => {
        if (res?.success) setB2cProfiles(res.data || []);
      });
    }
  }, [activeSubTab]);

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSubTab, selectedStoreForPricing]);
  
  // Recharger quand les filtres changent
  useEffect(() => {
    if (activeSubTab === 'orders') {
      loadData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderFilters]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      if (activeSubTab === 'profiles') {
        const res = await getB2CProfiles();
        if (res?.success) setB2cProfiles(res.data || []);
      } else if (activeSubTab === 'categories') {
        const res = await getB2CCategories();
        if (res?.success) setB2cCategories(res.data || []);
      } else if (activeSubTab === 'pricing') {
        if (selectedStoreForPricing) {
          const res = await getB2CProductPricings(selectedStoreForPricing);
          if (res?.success) {
            const products = Array.isArray(res.data?.products)
              ? res.data.products
              : (Array.isArray(res.data) ? res.data : []);
            setB2cPricings(products);
          } else {
            setB2cPricings([]);
          }
        } else {
          setB2cPricings([]);
        }
      } else if (activeSubTab === 'orders') {
        const res = await getB2COrders(orderFilters);
        if (res?.success) setB2cOrders(res.data || []);
      }
    } catch (err) {
      setError(err?.message || 'Erreur lors du chargement');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteCategory = async () => {
    if (!confirmDeleteCategory) return;
    try {
      const res = await deleteB2CCategory(confirmDeleteCategory);
      if (res?.success) {
        setSuccess('Catégorie supprimée avec succès');
        loadData();
      } else {
        setError(res?.error || 'Erreur lors de la suppression');
      }
    } catch (err) {
      setError(err?.message || 'Erreur lors de la suppression');
    }
    setConfirmDeleteCategory(null);
  };

  const formatPrice = (price) => {
    return new Intl.NumberFormat('fr-FR').format(price) + ' FCFA';
  };

  const formatDate = (dateString) => {
    if (!dateString) return '—';
    return new Date(dateString).toLocaleDateString('fr-FR');
  };

  const subTabs = [
    { id: 'profiles', label: 'Profils B2C' },
    { id: 'categories', label: 'Catégories B2C' },
    { id: 'pricing', label: 'Prix B2C' },
    { id: 'orders', label: 'Commandes B2C' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Gestion B2C</h2>
      </div>

      {/* Messages */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm flex justify-between items-center">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-600 hover:text-red-800">✕</button>
        </div>
      )}
      {success && (
        <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded text-sm flex justify-between items-center">
          <span>{success}</span>
          <button onClick={() => setSuccess(null)} className="text-green-600 hover:text-green-800">✕</button>
        </div>
      )}

      {/* Sub-tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex space-x-8">
          {subTabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveSubTab(tab.id)}
              className={`py-4 px-1 border-b-2 font-medium text-sm ${
                activeSubTab === tab.id
                  ? 'border-indigo-500 text-indigo-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Content */}
      {loading && (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
          <p className="mt-2 text-gray-600">Chargement...</p>
        </div>
      )}

      {/* Profils B2C */}
      {!loading && activeSubTab === 'profiles' && (
        <div className="space-y-4">
          <div className="bg-white shadow-sm rounded-lg border border-gray-100 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Magasin</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Catégorie</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ville</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">B2C</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">B2B</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {b2cProfiles.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="px-6 py-8 text-center text-gray-500">
                      Aucun magasin B2C trouvé
                    </td>
                  </tr>
                ) : (
                  b2cProfiles.map(store => (
                    <tr key={store.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {store.name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {store.category_name || '—'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {store.city || '—'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                          store.is_b2c !== false ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                        }`}>
                          {store.is_b2c !== false ? 'Actif' : 'Inactif'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                          store.is_b2b ? 'bg-purple-100 text-purple-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {store.is_b2b ? 'Actif' : 'Inactif'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                          store.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                        }`}>
                          {store.is_active ? 'Actif' : 'Inactif'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          onClick={() => setSelectedStoreForB2C(store)}
                          className="text-indigo-600 hover:text-indigo-900"
                        >
                          Gérer B2C
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Catégories B2C */}
      {!loading && activeSubTab === 'categories' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button
              onClick={() => {
                setEditingCategory(null);
                setShowCategoryModal(true);
              }}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-semibold"
            >
              + Créer une catégorie
            </button>
          </div>
          <div className="bg-white shadow-sm rounded-lg border border-gray-100 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Nom</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Magasin</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ordre</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {b2cCategories.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="px-6 py-8 text-center text-gray-500">
                      Aucune catégorie trouvée
                    </td>
                  </tr>
                ) : (
                  b2cCategories.map(category => (
                    <tr key={category.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {category.name}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {category.description || '—'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {category.store_name || 'Global'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {category.order || 0}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          onClick={() => {
                            setEditingCategory(category);
                            setShowCategoryModal(true);
                          }}
                          className="text-indigo-600 hover:text-indigo-900 mr-4"
                        >
                          Modifier
                        </button>
                        <button
                          onClick={() => setConfirmDeleteCategory(category.id)}
                          className="text-red-600 hover:text-red-900"
                        >
                          Supprimer
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Prix B2C */}
      {!loading && activeSubTab === 'pricing' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Sélectionner un magasin B2C</label>
              <select
                value={selectedStoreForPricing || ''}
                onChange={(e) => {
                  const storeId = e.target.value ? parseInt(e.target.value) : null;
                  setSelectedStoreForPricing(storeId);
                  if (storeId) {
                    setTimeout(() => loadData(), 100);
                  }
                }}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Sélectionner un magasin</option>
                {b2cProfiles.map(store => (
                  <option key={store.id} value={store.id}>{store.name}</option>
                ))}
              </select>
            </div>
          </div>
          {selectedStoreForPricing && (
            <div className="bg-white shadow-sm rounded-lg border border-gray-100 overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Produit</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Catégorie</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Prix B2C</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Prix comparé</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Stock</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type marché</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {!Array.isArray(b2cPricings) || b2cPricings.length === 0 ? (
                    <tr>
                      <td colSpan="7" className="px-6 py-8 text-center text-gray-500">
                        Aucun produit B2C trouvé
                      </td>
                    </tr>
                  ) : (
                    b2cPricings.map(product => (
                      <tr key={product.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {product.name}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {product.category_name || '—'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {formatPrice(product.price)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {product.compare_price ? formatPrice(product.compare_price) : '—'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {product.stock || 0}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                            product.market_type === 'both' ? 'bg-blue-100 text-blue-800' :
                            product.market_type === 'b2c' ? 'bg-green-100 text-green-800' :
                            'bg-gray-100 text-gray-800'
                          }`}>
                            {product.market_type === 'both' ? 'B2C & B2B' :
                             product.market_type === 'b2c' ? 'B2C' :
                             product.market_type || '—'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                          <button
                            onClick={() => {
                              setEditingPricing(product);
                              setShowPricingModal(true);
                            }}
                            className="text-indigo-600 hover:text-indigo-900"
                          >
                            Modifier prix
                          </button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Commandes B2C */}
      {!loading && activeSubTab === 'orders' && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-4">
            <input
              type="text"
              placeholder="Rechercher (n° commande, client)..."
              value={orderFilters.search}
              onChange={(e) => setOrderFilters({ ...orderFilters, search: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            />
            <select
              value={orderFilters.status}
              onChange={(e) => setOrderFilters({ ...orderFilters, status: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">Tous les statuts</option>
              <option value="pending">En attente</option>
              <option value="preparing">En préparation</option>
              <option value="ready">Prête</option>
              <option value="assigned">Assignée</option>
              <option value="in_transit">En transit</option>
              <option value="delivered">Livrée</option>
              <option value="cancelled">Annulée</option>
            </select>
            <input
              type="date"
              placeholder="Date début"
              value={orderFilters.date_from}
              onChange={(e) => setOrderFilters({ ...orderFilters, date_from: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            />
            <input
              type="date"
              placeholder="Date fin"
              value={orderFilters.date_to}
              onChange={(e) => setOrderFilters({ ...orderFilters, date_to: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div className="bg-white shadow-sm rounded-lg border border-gray-100 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">N° Commande</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Client</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Magasin</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Montant</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {b2cOrders.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="px-6 py-8 text-center text-gray-500">
                      Aucune commande B2C trouvée
                    </td>
                  </tr>
                ) : (
                  b2cOrders.map(order => (
                    <tr key={order.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {order.order_number || `#${order.id}`}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {order.client_name || order.client?.first_name || '—'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {order.store_name || '—'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatPrice(order.total_amount || order.total || 0)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(order.created_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                          order.status === 'delivered' ? 'bg-green-100 text-green-800' :
                          order.status === 'cancelled' ? 'bg-red-100 text-red-800' :
                          order.status === 'ready' ? 'bg-blue-100 text-blue-800' :
                          'bg-yellow-100 text-yellow-800'
                        }`}>
                          {order.status_display || order.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          onClick={() => setSelectedOrder(order)}
                          className="text-indigo-600 hover:text-indigo-900"
                        >
                          Détail
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modals */}
      <StoreB2CModal
        isOpen={selectedStoreForB2C !== null}
        onClose={() => setSelectedStoreForB2C(null)}
        store={selectedStoreForB2C}
        onSuccess={() => {
          loadData();
          setSelectedStoreForB2C(null);
        }}
      />

      <B2CCategoryModal
        isOpen={showCategoryModal}
        onClose={() => {
          setShowCategoryModal(false);
          setEditingCategory(null);
        }}
        category={editingCategory}
        onSuccess={() => {
          loadData();
          setSuccess('Catégorie enregistrée avec succès');
        }}
      />

      <B2CProductPricingModal
        isOpen={showPricingModal}
        onClose={() => {
          setShowPricingModal(false);
          setEditingPricing(null);
        }}
        product={editingPricing}
        onSuccess={() => {
          loadData();
          setSuccess('Prix mis à jour avec succès');
        }}
      />

      <ConfirmModal
        isOpen={!!confirmDeleteCategory}
        onClose={() => setConfirmDeleteCategory(null)}
        title="Supprimer la catégorie"
        message="Êtes-vous sûr de vouloir supprimer cette catégorie ? Cette action est irréversible."
        onConfirm={handleDeleteCategory}
        variant="danger"
      />

      {/* Order Detail Modal */}
      {selectedOrder && (
        <Modal
          isOpen={!!selectedOrder}
          onClose={() => setSelectedOrder(null)}
          title={`Commande B2C ${selectedOrder.order_number || `#${selectedOrder.id}`}`}
          size="lg"
        >
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500">Client</p>
                <p className="font-semibold">{selectedOrder.client_name || selectedOrder.client?.first_name || '—'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Magasin</p>
                <p className="font-semibold">{selectedOrder.store_name || '—'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Montant total</p>
                <p className="font-semibold">{formatPrice(selectedOrder.total_amount || selectedOrder.total || 0)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Statut</p>
                <p className="font-semibold">{selectedOrder.status_display || selectedOrder.status}</p>
              </div>
            </div>
            {selectedOrder.items && selectedOrder.items.length > 0 && (
              <div>
                <p className="text-sm font-semibold mb-2">Articles</p>
                <div className="border border-gray-200 rounded-lg overflow-hidden">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Produit</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Quantité</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Prix unitaire</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Total</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {selectedOrder.items.map((item, idx) => (
                        <tr key={idx}>
                          <td className="px-4 py-2 text-sm">{item.product_name || item.product?.name || '—'}</td>
                          <td className="px-4 py-2 text-sm">{item.quantity}</td>
                          <td className="px-4 py-2 text-sm">{formatPrice(item.unit_price || item.price || 0)}</td>
                          <td className="px-4 py-2 text-sm font-semibold">{formatPrice(item.subtotal || (item.quantity * (item.unit_price || item.price || 0)))}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </Modal>
      )}
    </div>
  );
};

export default AdminB2CManagementSection;
