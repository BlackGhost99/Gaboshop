import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import {
  createStoreSubscription,
  updateStoreSubscription,
  getSubscriptionPlans
} from '../services/adminService';
import { getStoresListAdmin } from '../services/adminService';

/**
 * Modal pour créer/modifier un abonnement store (B2C)
 */
const StoreSubscriptionModal = ({ isOpen, onClose, subscription = null, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [plans, setPlans] = useState([]);
  const [stores, setStores] = useState([]);
  
  const [formData, setFormData] = useState({
    store_id: '',
    plan_id: '',
    end_date: '',
    auto_renew: true,
    status: 'active'
  });

  useEffect(() => {
    if (isOpen) {
      loadPlans();
      loadStores();
      if (subscription) {
        setFormData({
          store_id: subscription.store || '',
          plan_id: subscription.plan || '',
          end_date: subscription.end_date || '',
          auto_renew: subscription.auto_renew !== undefined ? subscription.auto_renew : true,
          status: subscription.status || 'active'
        });
      } else {
        // Calculate default end_date (30 days from now)
        const defaultEndDate = new Date();
        defaultEndDate.setDate(defaultEndDate.getDate() + 30);
        setFormData({
          store_id: '',
          plan_id: '',
          end_date: defaultEndDate.toISOString().split('T')[0],
          auto_renew: true,
          status: 'active'
        });
      }
    }
  }, [isOpen, subscription]);

  const loadPlans = async () => {
    try {
      const res = await getSubscriptionPlans();
      if (res?.success) {
        setPlans(res.data || []);
      }
    } catch (err) {
      console.error('Error loading plans:', err);
    }
  };

  const loadStores = async () => {
    try {
      const res = await getStoresListAdmin({ status: 'active' });
      if (res?.success) {
        setStores(res.data || []);
      }
    } catch (err) {
      console.error('Error loading stores:', err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      let res;
      if (subscription?.id) {
        res = await updateStoreSubscription(subscription.id, formData);
      } else {
        res = await createStoreSubscription(formData);
      }

      if (res?.success) {
        if (onSuccess) onSuccess(res.data); // Passer les données mises à jour
        onClose();
      } else {
        setError(res?.error || res?.errors || 'Erreur lors de l\'enregistrement');
      }
    } catch (err) {
      setError(err?.message || 'Erreur lors de l\'enregistrement');
    } finally {
      setLoading(false);
    }
  };

  const updateField = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  if (!isOpen) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={subscription ? 'Modifier l\'abonnement' : 'Créer un abonnement'}
      size="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
            {error}
          </div>
        )}

        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-1">Magasin *</label>
          <select
            value={formData.store_id}
            onChange={(e) => updateField('store_id', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            required
            disabled={!!subscription}
          >
            <option value="">Sélectionner un magasin</option>
            {stores.map(store => (
              <option key={store.id} value={store.id}>{store.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-1">Plan</label>
          <select
            value={formData.plan_id}
            onChange={(e) => updateField('plan_id', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Aucun plan (Free)</option>
            {plans.filter(p => p.is_active).map(plan => (
              <option key={plan.id} value={plan.id}>
                {plan.name} - {new Intl.NumberFormat('fr-FR').format(plan.price)} FCFA/mois
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-1">Date de fin *</label>
          <input
            type="date"
            value={formData.end_date}
            onChange={(e) => updateField('end_date', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-1">Statut</label>
          <select
            value={formData.status}
            onChange={(e) => updateField('status', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
          >
            <option value="active">Actif</option>
            <option value="cancelled">Annulé</option>
            <option value="expired">Expiré</option>
            <option value="pending_payment">Attente paiement</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="auto_renew"
            checked={formData.auto_renew}
            onChange={(e) => updateField('auto_renew', e.target.checked)}
            className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
          />
          <label htmlFor="auto_renew" className="text-sm text-gray-700">Renouvellement automatique</label>
        </div>

        <div className="flex gap-3 pt-4 border-t border-gray-200">
          <button
            type="submit"
            disabled={loading}
            className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Enregistrement...' : subscription ? 'Mettre à jour' : 'Créer'}
          </button>
          <button
            type="button"
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            Annuler
          </button>
        </div>
      </form>
    </Modal>
  );
};

export default StoreSubscriptionModal;

