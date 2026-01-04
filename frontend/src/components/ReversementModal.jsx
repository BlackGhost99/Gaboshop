import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import {
  createReversement,
  updateReversement
} from '../services/adminService';
import { getStoresListAdmin } from '../services/adminService';

/**
 * Modal pour créer/modifier un reversement
 */
const ReversementModal = ({ isOpen, onClose, reversement = null, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [stores, setStores] = useState([]);
  
  const [formData, setFormData] = useState({
    store_id: '',
    period_start: '',
    period_end: '',
    transaction_reference: '',
    status: 'pending'
  });

  useEffect(() => {
    if (isOpen) {
      loadStores();
      if (reversement) {
        setFormData({
          store_id: reversement.store || '',
          period_start: reversement.period_start || '',
          period_end: reversement.period_end || '',
          transaction_reference: reversement.transaction_reference || '',
          status: reversement.status || 'pending'
        });
      } else {
        setFormData({
          store_id: '',
          period_start: '',
          period_end: '',
          transaction_reference: '',
          status: 'pending'
        });
      }
    }
  }, [isOpen, reversement]);

  const loadStores = async () => {
    try {
      const res = await getStoresListAdmin();
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
      if (reversement) {
        // Update: only status and transaction_reference can be updated
        res = await updateReversement(reversement.id, {
          status: formData.status,
          transaction_reference: formData.transaction_reference
        });
      } else {
        // Create
        res = await createReversement({
          store_id: formData.store_id,
          period_start: formData.period_start,
          period_end: formData.period_end
        });
      }

      if (res?.success) {
        if (onSuccess) onSuccess();
        onClose();
      } else {
        setError(res?.error || 'Erreur lors de la sauvegarde');
      }
    } catch (err) {
      setError(err?.message || 'Erreur lors de la sauvegarde');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return '—';
    return new Date(dateString).toLocaleDateString('fr-FR');
  };

  const formatPrice = (price) => {
    return new Intl.NumberFormat('fr-FR').format(price) + ' FCFA';
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={reversement ? 'Modifier le reversement' : 'Créer un reversement'}
      size="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
            {error}
          </div>
        )}

        {!reversement ? (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Magasin *</label>
              <select
                value={formData.store_id}
                onChange={(e) => setFormData({ ...formData, store_id: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                required
              >
                <option value="">Sélectionner un magasin</option>
                {stores.map(store => (
                  <option key={store.id} value={store.id}>{store.name}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Date début *</label>
              <input
                type="date"
                value={formData.period_start}
                onChange={(e) => setFormData({ ...formData, period_start: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Date fin *</label>
              <input
                type="date"
                value={formData.period_end}
                onChange={(e) => setFormData({ ...formData, period_end: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                required
              />
            </div>
          </>
        ) : (
          <>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Statut</label>
              <select
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              >
                <option value="pending">En attente</option>
                <option value="processing">En traitement</option>
                <option value="completed">Complété</option>
                <option value="failed">Échoué</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Référence transaction</label>
              <input
                type="text"
                value={formData.transaction_reference}
                onChange={(e) => setFormData({ ...formData, transaction_reference: e.target.value })}
                placeholder="Référence de transaction (optionnel)"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div className="bg-gray-50 p-4 rounded-lg space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Magasin:</span>
                <span className="font-semibold">{reversement.store_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Période:</span>
                <span className="font-semibold">{formatDate(reversement.period_start)} - {formatDate(reversement.period_end)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Montant net:</span>
                <span className="font-semibold text-indigo-600">{formatPrice(reversement.net_amount)}</span>
              </div>
            </div>
          </>
        )}

        <div className="flex justify-end gap-3 pt-4">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
            disabled={loading}
          >
            Annuler
          </button>
          <button
            type="submit"
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
            disabled={loading}
          >
            {loading ? 'Enregistrement...' : (reversement ? 'Enregistrer' : 'Créer')}
          </button>
        </div>
      </form>
    </Modal>
  );
};

export default ReversementModal;

