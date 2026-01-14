import React, { useState, useEffect, useCallback } from 'react';
import SubscriptionPlanModal from './SubscriptionPlanModal';
import B2BSubscriptionPlanModal from './B2BSubscriptionPlanModal';
import StoreSubscriptionModal from './StoreSubscriptionModal';
import B2BStoreSubscriptionModal from './B2BStoreSubscriptionModal';
import ConfirmModal from './ConfirmModal';
import {
  getSubscriptionPlans,
  deleteSubscriptionPlan,
  getB2BSubscriptionPlans,
  deleteB2BSubscriptionPlan,
  getStoreSubscriptions,
  getB2BStoreSubscriptions,
  updateStoreSubscription,
  updateB2BStoreSubscription
} from '../services/adminService';

/**
 * Section Admin pour gérer les plans d'abonnement et abonnements
 */
const AdminSubscriptionsSection = () => {
  const [activeSubTab, setActiveSubTab] = useState('b2c_plans');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Plans B2C
  const [b2cPlans, setB2cPlans] = useState([]);
  const [showB2CPlanModal, setShowB2CPlanModal] = useState(false);
  const [editingB2CPlan, setEditingB2CPlan] = useState(null);
  const [confirmDeleteB2CPlan, setConfirmDeleteB2CPlan] = useState(null);

  // Plans B2B
  const [b2bPlans, setB2bPlans] = useState([]);
  const [showB2BPlanModal, setShowB2BPlanModal] = useState(false);
  const [editingB2BPlan, setEditingB2BPlan] = useState(null);
  const [confirmDeleteB2BPlan, setConfirmDeleteB2BPlan] = useState(null);

  // Abonnements B2C
  const [storeSubscriptions, setStoreSubscriptions] = useState([]);
  const [showStoreSubModal, setShowStoreSubModal] = useState(false);
  const [editingStoreSub, setEditingStoreSub] = useState(null);
  const [storeSubFilters, setStoreSubFilters] = useState({
    store_id: '',
    plan_id: '',
    status: '',
    search: ''
  });

  // Abonnements B2B
  const [b2bStoreSubscriptions, setB2bStoreSubscriptions] = useState([]);
  const [showB2BStoreSubModal, setShowB2BStoreSubModal] = useState(false);
  const [editingB2BStoreSub, setEditingB2BStoreSub] = useState(null);
  const [b2bStoreSubFilters, setB2bStoreSubFilters] = useState({
    store_id: '',
    plan_id: '',
    status: '',
    search: ''
  });

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      if (activeSubTab === 'b2c_plans') {
        const res = await getSubscriptionPlans();
        if (res?.success) setB2cPlans(res.data || []);
      } else if (activeSubTab === 'b2b_plans') {
        const res = await getB2BSubscriptionPlans();
        if (res?.success) setB2bPlans(res.data || []);
      } else if (activeSubTab === 'store_subscriptions') {
        const res = await getStoreSubscriptions(storeSubFilters);
        if (res?.success) setStoreSubscriptions(res.data || []);
      } else if (activeSubTab === 'b2b_store_subscriptions') {
        const res = await getB2BStoreSubscriptions(b2bStoreSubFilters);
        if (res?.success) setB2bStoreSubscriptions(res.data || []);
      }
    } catch (err) {
      setError(err?.message || 'Erreur lors du chargement');
    } finally {
      setLoading(false);
    }
  }, [activeSubTab, storeSubFilters, b2bStoreSubFilters]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Recharger les données quand les filtres changent (avec debounce pour la recherche)
  useEffect(() => {
    if (activeSubTab === 'store_subscriptions') {
      const timeoutId = setTimeout(() => {
        loadData();
      }, storeSubFilters.search ? 500 : 0); // Debounce de 500ms pour la recherche
      return () => clearTimeout(timeoutId);
    }
  }, [storeSubFilters, activeSubTab, loadData]);

  useEffect(() => {
    if (activeSubTab === 'b2b_store_subscriptions') {
      const timeoutId = setTimeout(() => {
        loadData();
      }, b2bStoreSubFilters.search ? 500 : 0); // Debounce de 500ms pour la recherche
      return () => clearTimeout(timeoutId);
    }
  }, [b2bStoreSubFilters, activeSubTab, loadData]);

  const handleDeleteB2CPlan = async () => {
    if (!confirmDeleteB2CPlan) return;
    try {
      const res = await deleteSubscriptionPlan(confirmDeleteB2CPlan);
      if (res?.success) {
        setSuccess('Plan supprimé avec succès');
        loadData();
      } else {
        setError(res?.error || 'Erreur lors de la suppression');
      }
    } catch (err) {
      setError(err?.message || 'Erreur lors de la suppression');
    }
    setConfirmDeleteB2CPlan(null);
  };

  const handleDeleteB2BPlan = async () => {
    if (!confirmDeleteB2BPlan) return;
    try {
      const res = await deleteB2BSubscriptionPlan(confirmDeleteB2BPlan);
      if (res?.success) {
        setSuccess('Plan supprimé avec succès');
        loadData();
      } else {
        setError(res?.error || 'Erreur lors de la suppression');
      }
    } catch (err) {
      setError(err?.message || 'Erreur lors de la suppression');
    }
    setConfirmDeleteB2BPlan(null);
  };

  const formatPrice = (price) => {
    return new Intl.NumberFormat('fr-FR').format(price) + ' FCFA';
  };

  const formatDate = (dateString) => {
    if (!dateString) return '—';
    return new Date(dateString).toLocaleDateString('fr-FR');
  };

  const subTabs = [
    { id: 'b2c_plans', label: 'Plans B2C' },
    { id: 'b2b_plans', label: 'Plans B2B' },
    { id: 'store_subscriptions', label: 'Abonnements B2C' },
    { id: 'b2b_store_subscriptions', label: 'Abonnements B2B' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Gestion des Abonnements</h2>
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

      {/* Plans B2C */}
      {!loading && activeSubTab === 'b2c_plans' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button
              onClick={() => {
                setEditingB2CPlan(null);
                setShowB2CPlanModal(true);
              }}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-semibold"
            >
              + Créer un plan B2C
            </button>
          </div>
          <div className="bg-white shadow-sm rounded-lg border border-gray-100 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Nom</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Prix</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">S'applique à</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {b2cPlans.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="px-6 py-8 text-center text-gray-500">
                      Aucun plan trouvé
                    </td>
                  </tr>
                ) : (
                  b2cPlans.map(plan => (
                    <tr key={plan.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{plan.name}</div>
                        {plan.slug && <div className="text-xs text-gray-500">{plan.slug}</div>}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                          {plan.plan_type}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatPrice(plan.price)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {plan.applies_to || 'b2c'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                          plan.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {plan.is_active ? 'Actif' : 'Inactif'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          onClick={() => {
                            setEditingB2CPlan(plan);
                            setShowB2CPlanModal(true);
                          }}
                          className="text-indigo-600 hover:text-indigo-900 mr-4"
                        >
                          Modifier
                        </button>
                        <button
                          onClick={() => setConfirmDeleteB2CPlan(plan.id)}
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

      {/* Plans B2B */}
      {!loading && activeSubTab === 'b2b_plans' && (
        <div className="space-y-4">
          <div className="flex justify-end">
            <button
              onClick={() => {
                setEditingB2BPlan(null);
                setShowB2BPlanModal(true);
              }}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-semibold"
            >
              + Créer un plan B2B
            </button>
          </div>
          <div className="bg-white shadow-sm rounded-lg border border-gray-100 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Nom</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Prix</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {b2bPlans.length === 0 ? (
                  <tr>
                    <td colSpan="5" className="px-6 py-8 text-center text-gray-500">
                      Aucun plan trouvé
                    </td>
                  </tr>
                ) : (
                  b2bPlans.map(plan => (
                    <tr key={plan.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">{plan.name}</div>
                        {plan.tagline && <div className="text-xs text-gray-500">{plan.tagline}</div>}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="px-2 py-1 text-xs font-semibold rounded-full bg-purple-100 text-purple-800">
                          {plan.plan_type}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatPrice(plan.price)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                          plan.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {plan.is_active ? 'Actif' : 'Inactif'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          onClick={() => {
                            setEditingB2BPlan(plan);
                            setShowB2BPlanModal(true);
                          }}
                          className="text-indigo-600 hover:text-indigo-900 mr-4"
                        >
                          Modifier
                        </button>
                        <button
                          onClick={() => setConfirmDeleteB2BPlan(plan.id)}
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

      {/* Store Subscriptions */}
      {!loading && activeSubTab === 'store_subscriptions' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <div className="flex gap-4">
              <input
                type="text"
                placeholder="Rechercher..."
                value={storeSubFilters.search}
                onChange={(e) => setStoreSubFilters({ ...storeSubFilters, search: e.target.value })}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              />
              <select
                value={storeSubFilters.status}
                onChange={(e) => setStoreSubFilters({ ...storeSubFilters, status: e.target.value })}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Tous les statuts</option>
                <option value="active">Actif</option>
                <option value="cancelled">Annulé</option>
                <option value="expired">Expiré</option>
                <option value="pending_payment">Attente paiement</option>
              </select>
            </div>
            <button
              onClick={() => {
                setEditingStoreSub(null);
                setShowStoreSubModal(true);
              }}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-semibold"
            >
              + Créer un abonnement
            </button>
          </div>
          <div className="bg-white shadow-sm rounded-lg border border-gray-100 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Magasin</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Plan</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Début</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fin</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {storeSubscriptions.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="px-6 py-8 text-center text-gray-500">
                      Aucun abonnement trouvé
                    </td>
                  </tr>
                ) : (
                  storeSubscriptions.map(sub => (
                    <tr key={sub.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {sub.store_name || '—'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {sub.plan_name_display || sub.plan_name || '—'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(sub.start_date)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(sub.end_date)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                          sub.status === 'active' ? 'bg-green-100 text-green-800' :
                          sub.status === 'expired' ? 'bg-red-100 text-red-800' :
                          sub.status === 'cancelled' ? 'bg-gray-100 text-gray-800' :
                          'bg-yellow-100 text-yellow-800'
                        }`}>
                          {sub.status === 'active' ? 'Actif' :
                           sub.status === 'expired' ? 'Expiré' :
                           sub.status === 'cancelled' ? 'Annulé' :
                           'Attente paiement'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          onClick={() => {
                            setEditingStoreSub(sub);
                            setShowStoreSubModal(true);
                          }}
                          className="text-indigo-600 hover:text-indigo-900"
                        >
                          Modifier
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

      {/* B2B Store Subscriptions */}
      {!loading && activeSubTab === 'b2b_store_subscriptions' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <div className="flex gap-4">
              <input
                type="text"
                placeholder="Rechercher..."
                value={b2bStoreSubFilters.search}
                onChange={(e) => setB2bStoreSubFilters({ ...b2bStoreSubFilters, search: e.target.value })}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              />
              <select
                value={b2bStoreSubFilters.status}
                onChange={(e) => setB2bStoreSubFilters({ ...b2bStoreSubFilters, status: e.target.value })}
                className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">Tous les statuts</option>
                <option value="active">Actif</option>
                <option value="cancelled">Annulé</option>
                <option value="expired">Expiré</option>
                <option value="pending_payment">Attente paiement</option>
              </select>
            </div>
            <button
              onClick={() => {
                setEditingB2BStoreSub(null);
                setShowB2BStoreSubModal(true);
              }}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-semibold"
            >
              + Créer un abonnement B2B
            </button>
          </div>
          <div className="bg-white shadow-sm rounded-lg border border-gray-100 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Magasin</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Plan</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Début</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fin</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {b2bStoreSubscriptions.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="px-6 py-8 text-center text-gray-500">
                      Aucun abonnement trouvé
                    </td>
                  </tr>
                ) : (
                  b2bStoreSubscriptions.map(sub => (
                    <tr key={sub.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {sub.store_name || '—'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {sub.plan_name_display || sub.plan_name || '—'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(sub.start_date)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(sub.end_date)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                          sub.status === 'active' ? 'bg-green-100 text-green-800' :
                          sub.status === 'expired' ? 'bg-red-100 text-red-800' :
                          sub.status === 'cancelled' ? 'bg-gray-100 text-gray-800' :
                          'bg-yellow-100 text-yellow-800'
                        }`}>
                          {sub.status === 'active' ? 'Actif' :
                           sub.status === 'expired' ? 'Expiré' :
                           sub.status === 'cancelled' ? 'Annulé' :
                           'Attente paiement'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button
                          onClick={() => {
                            setEditingB2BStoreSub(sub);
                            setShowB2BStoreSubModal(true);
                          }}
                          className="text-indigo-600 hover:text-indigo-900"
                        >
                          Modifier
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
      <SubscriptionPlanModal
        isOpen={showB2CPlanModal}
        onClose={() => {
          setShowB2CPlanModal(false);
          setEditingB2CPlan(null);
        }}
        planId={editingB2CPlan?.id}
        onSuccess={() => {
          loadData();
          setSuccess('Plan enregistré avec succès');
        }}
      />

      <B2BSubscriptionPlanModal
        isOpen={showB2BPlanModal}
        onClose={() => {
          setShowB2BPlanModal(false);
          setEditingB2BPlan(null);
        }}
        planId={editingB2BPlan?.id}
        onSuccess={() => {
          loadData();
          setSuccess('Plan enregistré avec succès');
        }}
      />

      <StoreSubscriptionModal
        isOpen={showStoreSubModal}
        onClose={() => {
          setShowStoreSubModal(false);
          setEditingStoreSub(null);
        }}
        subscription={editingStoreSub}
        onSuccess={async (updatedData) => {
          setSuccess('Abonnement enregistré avec succès');
          // Mettre à jour immédiatement l'état avec les données reçues
          if (updatedData && editingStoreSub?.id) {
            setStoreSubscriptions(prev =>
              prev.map(sub => sub.id === editingStoreSub.id
                ? { ...sub, ...updatedData }
                : sub
              )
            );
          }
          // Recharger les données depuis le backend pour s'assurer de la cohérence
          await loadData();
        }}
      />

      <B2BStoreSubscriptionModal
        isOpen={showB2BStoreSubModal}
        onClose={() => {
          setShowB2BStoreSubModal(false);
          setEditingB2BStoreSub(null);
        }}
        subscription={editingB2BStoreSub}
        onSuccess={async (updatedData) => {
          setSuccess('Abonnement enregistré avec succès');
          // Mettre à jour immédiatement l'état avec les données reçues
          if (updatedData && editingB2BStoreSub?.id) {
            setB2bStoreSubscriptions(prev =>
              prev.map(sub => sub.id === editingB2BStoreSub.id
                ? { ...sub, ...updatedData }
                : sub
              )
            );
          }
          // Recharger les données depuis le backend pour s'assurer de la cohérence
          await loadData();
        }}
      />

      <ConfirmModal
        isOpen={!!confirmDeleteB2CPlan}
        onClose={() => setConfirmDeleteB2CPlan(null)}
        title="Supprimer le plan"
        message="Êtes-vous sûr de vouloir supprimer ce plan ? Cette action est irréversible."
        onConfirm={handleDeleteB2CPlan}
        variant="danger"
      />

      <ConfirmModal
        isOpen={!!confirmDeleteB2BPlan}
        onClose={() => setConfirmDeleteB2BPlan(null)}
        title="Supprimer le plan"
        message="Êtes-vous sûr de vouloir supprimer ce plan ? Cette action est irréversible."
        onConfirm={handleDeleteB2BPlan}
        variant="danger"
      />
    </div>
  );
};

export default AdminSubscriptionsSection;

