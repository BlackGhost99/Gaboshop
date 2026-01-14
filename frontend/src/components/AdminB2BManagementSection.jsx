import React, { useState, useEffect } from 'react';
import B2BCategoryModal from './B2BCategoryModal';
import ConfirmModal from './ConfirmModal';
import {
  getB2BCategories,
  createB2BCategory,
  updateB2BCategory,
  deleteB2BCategory,
  getB2BOrders,
  updateB2BOrderStatus,
  getB2BProductPricings,
  createB2BProductPricing,
  updateB2BProductPricing,
  deleteB2BProductPricing,
  getB2BProfile,
  createB2BProfile,
  updateB2BProfile,
  activateB2BProfile,
  deactivateB2BProfile
} from '../services/adminService';
import { getStoresListAdmin } from '../services/adminService';

/**
 * Section Admin pour gérer B2B (Profils, Catégories, Prix, Commandes)
 */
const AdminB2BManagementSection = () => {
  const [activeSubTab, setActiveSubTab] = useState('profiles');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Profils B2B
  const [b2bProfiles, setB2bProfiles] = useState([]);
  const [editingProfile, setEditingProfile] = useState(null);
  const [showProfileModal, setShowProfileModal] = useState(false);

  // Catégories B2B
  const [b2bCategories, setB2bCategories] = useState([]);
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [editingCategory, setEditingCategory] = useState(null);
  const [confirmDeleteCategory, setConfirmDeleteCategory] = useState(null);

  // Prix B2B
  const [b2bPricings, setB2bPricings] = useState([]);
  const [selectedStoreForPricing, setSelectedStoreForPricing] = useState(null);
  const [showPricingModal, setShowPricingModal] = useState(false);
  const [editingPricing, setEditingPricing] = useState(null);

  // Commandes B2B
  const [b2bOrders, setB2bOrders] = useState([]);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [orderFilters, setOrderFilters] = useState({
    store_id: '',
    source_store_id: '',
    status: '',
    date_from: '',
    date_to: '',
    search: ''
  });

  useEffect(() => {
    loadData();
  }, [activeSubTab, selectedStoreForPricing, orderFilters]);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      if (activeSubTab === 'profiles') {
        // Load B2B stores and their profiles
        // Include stores that have is_b2b=True OR have a B2B profile
        const storesRes = await getStoresListAdmin({ status: 'active' });
        if (storesRes?.success) {
          const b2bStores = (storesRes.data || []).filter(s => s.is_b2b || s.has_b2b_profile);
          const profilesWithData = await Promise.all(
            b2bStores.map(async (store) => {
              try {
                const profileRes = await getB2BProfile(store.id);
                return {
                  ...store,
                  profile: profileRes?.exists ? profileRes.data : null
                };
              } catch {
                return { ...store, profile: null };
              }
            })
          );
          setB2bProfiles(profilesWithData);
        }
      } else if (activeSubTab === 'categories') {
        const res = await getB2BCategories();
        if (res?.success) setB2bCategories(res.data || []);
      } else if (activeSubTab === 'pricing') {
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/3034891a-d8c4-4be8-b0a8-8720a23ed625',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'AdminB2BManagementSection.jsx:93',message:'loadData pricing tab entry',data:{activeSubTab,selectedStoreForPricing,b2bPricingsType:typeof b2bPricings,b2bPricingsIsArray:Array.isArray(b2bPricings),b2bPricingsValue:b2bPricings},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A,B,C,D,E'})}).catch(()=>{});
        // #endregion
        if (selectedStoreForPricing) {
          const res = await getB2BProductPricings(selectedStoreForPricing);
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/3034891a-d8c4-4be8-b0a8-8720a23ed625',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'AdminB2BManagementSection.jsx:96',message:'API response received',data:{resSuccess:res?.success,resDataType:typeof res?.data,resDataIsArray:Array.isArray(res?.data),resDataPricingsType:typeof res?.data?.pricings,resDataPricingsIsArray:Array.isArray(res?.data?.pricings),resDataKeys:res?.data?Object.keys(res.data):null,resData:res?.data},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A,B,E'})}).catch(()=>{});
          // #endregion
          // L'API retourne { success: true, data: { pricings: [...], products_without_pricing: [...] } }
          if (res?.success) {
            // S'assurer que res.data.pricings est un tableau
            const pricings = Array.isArray(res.data?.pricings) 
              ? res.data.pricings 
              : (Array.isArray(res.data) ? res.data : []);
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/3034891a-d8c4-4be8-b0a8-8720a23ed625',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'AdminB2BManagementSection.jsx:102',message:'Before setB2bPricings',data:{pricingsType:typeof pricings,pricingsIsArray:Array.isArray(pricings),pricingsLength:pricings?.length,pricingsValue:pricings},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A,B,E'})}).catch(()=>{});
            // #endregion
            setB2bPricings(pricings);
          } else {
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/3034891a-d8c4-4be8-b0a8-8720a23ed625',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'AdminB2BManagementSection.jsx:104',message:'API success=false, setting empty array',data:{resError:res?.error},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
            // #endregion
            setB2bPricings([]);
          }
        } else {
          // #region agent log
          fetch('http://127.0.0.1:7242/ingest/3034891a-d8c4-4be8-b0a8-8720a23ed625',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'AdminB2BManagementSection.jsx:107',message:'No selectedStoreForPricing, setting empty array',data:{},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
          // #endregion
          setB2bPricings([]);
        }
      } else if (activeSubTab === 'orders') {
        const res = await getB2BOrders(orderFilters);
        if (res?.success) setB2bOrders(res.data || []);
      }
    } catch (err) {
      // #region agent log
      fetch('http://127.0.0.1:7242/ingest/3034891a-d8c4-4be8-b0a8-8720a23ed625',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'AdminB2BManagementSection.jsx:114',message:'Exception in loadData',data:{errorMessage:err?.message,errorStack:err?.stack,activeSubTab,b2bPricingsType:typeof b2bPricings,b2bPricingsIsArray:Array.isArray(b2bPricings),b2bPricingsValue:b2bPricings},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
      // #endregion
      setError(err?.message || 'Erreur lors du chargement');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteCategory = async () => {
    if (!confirmDeleteCategory) return;
    try {
      const res = await deleteB2BCategory(confirmDeleteCategory);
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

  const handleToggleProfile = async (storeId, isActive) => {
    try {
      let res;
      if (isActive) {
        res = await deactivateB2BProfile(storeId);
      } else {
        res = await activateB2BProfile(storeId);
      }
      if (res?.success) {
        setSuccess(`Profil ${isActive ? 'désactivé' : 'activé'} avec succès`);
        loadData();
      } else {
        setError(res?.error || 'Erreur lors de la modification');
      }
    } catch (err) {
      setError(err?.message || 'Erreur lors de la modification');
    }
  };

  const handleUpdateOrderStatus = async (orderId, newStatus) => {
    try {
      const res = await updateB2BOrderStatus(orderId, newStatus);
      if (res?.success) {
        setSuccess('Statut de commande mis à jour');
        loadData();
      } else {
        setError(res?.error || 'Erreur lors de la mise à jour');
      }
    } catch (err) {
      setError(err?.message || 'Erreur lors de la mise à jour');
    }
  };

  const formatPrice = (price) => {
    return new Intl.NumberFormat('fr-FR').format(price) + ' FCFA';
  };

  const formatDate = (dateString) => {
    if (!dateString) return '—';
    return new Date(dateString).toLocaleDateString('fr-FR');
  };

  const subTabs = [
    { id: 'profiles', label: 'Profils B2B' },
    { id: 'categories', label: 'Catégories B2B' },
    { id: 'pricing', label: 'Prix B2B' },
    { id: 'orders', label: 'Commandes B2B' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Gestion B2B</h2>
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

      {/* Profils B2B */}
      {!loading && activeSubTab === 'profiles' && (
        <div className="space-y-4">
          <div className="bg-white shadow-sm rounded-lg border border-gray-100 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Magasin</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Montant min</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Visible à tous</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {b2bProfiles.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="px-6 py-8 text-center text-gray-500">
                      Aucun magasin B2B trouvé
                    </td>
                  </tr>
                ) : (
                  b2bProfiles.map(store => (
                    <tr key={store.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {store.name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {store.profile ? formatPrice(store.profile.minimum_order_amount) : '—'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                          store.profile?.visible_to_all ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {store.profile?.visible_to_all ? 'Oui' : 'Non'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                          store.profile?.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                        }`}>
                          {store.profile?.is_active ? 'Actif' : 'Inactif'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        {store.profile ? (
                          <>
                            <button
                              onClick={() => {
                                setEditingProfile({ ...store.profile, store_id: store.id });
                                setShowProfileModal(true);
                              }}
                              className="text-indigo-600 hover:text-indigo-900 mr-4"
                            >
                              Modifier
                            </button>
                            <button
                              onClick={() => handleToggleProfile(store.id, store.profile.is_active)}
                              className={`${store.profile.is_active ? 'text-red-600 hover:text-red-900' : 'text-green-600 hover:text-green-900'}`}
                            >
                              {store.profile.is_active ? 'Désactiver' : 'Activer'}
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => {
                              setEditingProfile({ store_id: store.id });
                              setShowProfileModal(true);
                            }}
                            className="text-indigo-600 hover:text-indigo-900"
                          >
                            Créer profil
                          </button>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Catégories B2B */}
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
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {b2bCategories.length === 0 ? (
                  <tr>
                    <td colSpan="4" className="px-6 py-8 text-center text-gray-500">
                      Aucune catégorie trouvée
                    </td>
                  </tr>
                ) : (
                  b2bCategories.map(category => (
                    <tr key={category.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {category.name}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {category.description || '—'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                          category.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {category.is_active ? 'Actif' : 'Inactif'}
                        </span>
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

      {/* Prix B2B */}
      {!loading && activeSubTab === 'pricing' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2">Sélectionner un magasin B2B</label>
              <select
                value={selectedStoreForPricing || ''}
                onChange={(e) => setSelectedStoreForPricing(e.target.value ? parseInt(e.target.value) : null)}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Sélectionner un magasin</option>
                {b2bProfiles.map(store => (
                  <option key={store.id} value={store.id}>{store.name}</option>
                ))}
              </select>
            </div>
            {selectedStoreForPricing && (
              <button
                onClick={() => {
                  setEditingPricing(null);
                  setShowPricingModal(true);
                }}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-semibold"
              >
                + Ajouter un prix
              </button>
            )}
          </div>
          {selectedStoreForPricing && (
            <div className="bg-white shadow-sm rounded-lg border border-gray-100 overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Produit</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Prix B2B</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Quantité min</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Quantité max</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {(() => {
                    // #region agent log
                    fetch('http://127.0.0.1:7242/ingest/3034891a-d8c4-4be8-b0a8-8720a23ed625',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'AdminB2BManagementSection.jsx:433',message:'Render check b2bPricings',data:{b2bPricingsType:typeof b2bPricings,b2bPricingsIsArray:Array.isArray(b2bPricings),b2bPricingsValue:b2bPricings,b2bPricingsLength:b2bPricings?.length,checkResult:!Array.isArray(b2bPricings) || b2bPricings.length === 0},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
                    // #endregion
                    return !Array.isArray(b2bPricings) || b2bPricings.length === 0;
                  })() ? (
                    <tr>
                      <td colSpan="6" className="px-6 py-8 text-center text-gray-500">
                        Aucun prix trouvé
                      </td>
                    </tr>
                  ) : (
                    (() => {
                      // #region agent log
                      fetch('http://127.0.0.1:7242/ingest/3034891a-d8c4-4be8-b0a8-8720a23ed625',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'AdminB2BManagementSection.jsx:440',message:'Before b2bPricings.map',data:{b2bPricingsType:typeof b2bPricings,b2bPricingsIsArray:Array.isArray(b2bPricings),b2bPricingsValue:b2bPricings,b2bPricingsLength:b2bPricings?.length},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
                      // #endregion
                      return b2bPricings.map(pricing => (
                      <tr key={pricing.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {pricing.product_name || '—'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {formatPrice(pricing.b2b_price)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {pricing.min_quantity || '—'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {pricing.max_quantity || 'Illimité'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                            pricing.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                          }`}>
                            {pricing.is_active ? 'Actif' : 'Inactif'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                          <button
                            onClick={() => {
                              setEditingPricing(pricing);
                              setShowPricingModal(true);
                            }}
                            className="text-indigo-600 hover:text-indigo-900 mr-4"
                          >
                            Modifier
                          </button>
                          <button
                            onClick={async () => {
                              if (window.confirm('Supprimer ce prix ?')) {
                                try {
                                  const res = await deleteB2BProductPricing(pricing.id);
                                  if (res?.success) {
                                    setSuccess('Prix supprimé avec succès');
                                    loadData();
                                  }
                                } catch (err) {
                                  setError(err?.message || 'Erreur lors de la suppression');
                                }
                              }
                            }}
                            className="text-red-600 hover:text-red-900"
                          >
                            Supprimer
                          </button>
                        </td>
                      </tr>
                    ));
                    })()
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Commandes B2B */}
      {!loading && activeSubTab === 'orders' && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-4">
            <input
              type="text"
              placeholder="Rechercher (n° commande, magasin)..."
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
              <option value="created">Créée</option>
              <option value="confirmed">Confirmée</option>
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
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Grossiste</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Acheteur</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Montant</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {b2bOrders.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="px-6 py-8 text-center text-gray-500">
                      Aucune commande trouvée
                    </td>
                  </tr>
                ) : (
                  b2bOrders.map(order => (
                    <tr key={order.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {order.order_number}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {order.store_name || '—'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {order.source_store_name || '—'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatPrice(order.total_amount)}
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
                          className="text-indigo-600 hover:text-indigo-900 mr-4"
                        >
                          Détail
                        </button>
                        {order.status !== 'delivered' && order.status !== 'cancelled' && (
                          <select
                            value={order.status}
                            onChange={(e) => handleUpdateOrderStatus(order.id, e.target.value)}
                            className="text-sm border border-gray-300 rounded px-2 py-1"
                          >
                            <option value="created">Créée</option>
                            <option value="confirmed">Confirmée</option>
                            <option value="preparing">En préparation</option>
                            <option value="ready">Prête</option>
                            <option value="assigned">Assignée</option>
                            <option value="in_transit">En transit</option>
                            <option value="delivered">Livrée</option>
                            <option value="cancelled">Annulée</option>
                          </select>
                        )}
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
      <B2BCategoryModal
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
          title={`Commande B2B ${selectedOrder.order_number}`}
          size="lg"
        >
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500">Grossiste</p>
                <p className="font-semibold">{selectedOrder.store_name}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Acheteur</p>
                <p className="font-semibold">{selectedOrder.source_store_name}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Montant total</p>
                <p className="font-semibold">{formatPrice(selectedOrder.total_amount)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Statut</p>
                <p className="font-semibold">{selectedOrder.status_display}</p>
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
                          <td className="px-4 py-2 text-sm">{item.product_name}</td>
                          <td className="px-4 py-2 text-sm">{item.quantity}</td>
                          <td className="px-4 py-2 text-sm">{formatPrice(item.unit_price)}</td>
                          <td className="px-4 py-2 text-sm font-semibold">{formatPrice(item.subtotal)}</td>
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

export default AdminB2BManagementSection;

