import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import ConfirmModal from './ConfirmModal';
import {
  getReversements,
  createReversement,
  updateReversement
} from '../services/adminService';
import { getStoresListAdmin } from '../services/adminService';

/**
 * Section Admin pour gérer les reversements
 */
const AdminReversementsSection = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const [reversements, setReversements] = useState([]);
  const [selectedReversement, setSelectedReversement] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [reversementToDelete, setReversementToDelete] = useState(null);

  const [filters, setFilters] = useState({
    store_id: '',
    status: '',
    date_from: '',
    date_to: ''
  });

  const [formData, setFormData] = useState({
    store_id: '',
    period_start: '',
    period_end: '',
    transaction_reference: ''
  });

  const [stores, setStores] = useState([]);

  useEffect(() => {
    loadStores();
  }, []);

  useEffect(() => {
    loadReversements();
  }, [filters]);

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

  const loadReversements = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getReversements(filters);
      if (res?.success) {
        setReversements(res.data || []);
      } else {
        setError(res?.error || 'Erreur lors du chargement');
      }
    } catch (err) {
      setError(err?.message || 'Erreur lors du chargement');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setFormData({
      store_id: '',
      period_start: '',
      period_end: '',
      transaction_reference: ''
    });
    setSelectedReversement(null);
    setIsModalOpen(true);
  };

  const handleEdit = (reversement) => {
    setFormData({
      store_id: reversement.store,
      period_start: reversement.period_start,
      period_end: reversement.period_end,
      transaction_reference: reversement.transaction_reference || ''
    });
    setSelectedReversement(reversement);
    setIsModalOpen(true);
  };

  const handleSave = async () => {
    setError(null);
    setSuccess(null);
    try {
      let res;
      if (selectedReversement) {
        // Update: only status and transaction_reference can be updated
        res = await updateReversement(selectedReversement.id, {
          status: formData.status || selectedReversement.status,
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
        setSuccess(selectedReversement ? 'Reversement mis à jour' : 'Reversement créé');
        setIsModalOpen(false);
        loadReversements();
      } else {
        setError(res?.error || 'Erreur lors de la sauvegarde');
      }
    } catch (err) {
      setError(err?.message || 'Erreur lors de la sauvegarde');
    }
  };

  const handleStatusChange = async (reversement, newStatus) => {
    setError(null);
    setSuccess(null);
    try {
      const res = await updateReversement(reversement.id, {
        status: newStatus
      });
      if (res?.success) {
        setSuccess(`Statut mis à jour: ${getStatusLabel(newStatus)}`);
        loadReversements();
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

  const getStatusLabel = (status) => {
    const labels = {
      'pending': 'En attente',
      'processing': 'En traitement',
      'completed': 'Complété',
      'failed': 'Échoué'
    };
    return labels[status] || status;
  };

  const getStatusColor = (status) => {
    const colors = {
      'pending': 'bg-yellow-100 text-yellow-800',
      'processing': 'bg-blue-100 text-blue-800',
      'completed': 'bg-green-100 text-green-800',
      'failed': 'bg-red-100 text-red-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Gestion des Reversements</h2>
        <button
          onClick={handleCreate}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
        >
          + Créer un reversement
        </button>
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

      {/* Filters */}
      <div className="bg-white p-4 rounded-lg border border-gray-200">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <select
            value={filters.store_id}
            onChange={(e) => setFilters({ ...filters, store_id: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Tous les magasins</option>
            {stores.map(store => (
              <option key={store.id} value={store.id}>{store.name}</option>
            ))}
          </select>
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Tous les statuts</option>
            <option value="pending">En attente</option>
            <option value="processing">En traitement</option>
            <option value="completed">Complété</option>
            <option value="failed">Échoué</option>
          </select>
          <input
            type="date"
            placeholder="Date début"
            value={filters.date_from}
            onChange={(e) => setFilters({ ...filters, date_from: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
          />
          <input
            type="date"
            placeholder="Date fin"
            value={filters.date_to}
            onChange={(e) => setFilters({ ...filters, date_to: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
          />
        </div>
      </div>

      {/* Table */}
      {loading && (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
          <p className="mt-2 text-gray-600">Chargement...</p>
        </div>
      )}

      {!loading && (
        <div className="bg-white shadow-sm rounded-lg border border-gray-100 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Magasin</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Période</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Commandes</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">CA Brut</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Commissions</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Net</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Référence</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {reversements.length === 0 ? (
                <tr>
                  <td colSpan="9" className="px-6 py-8 text-center text-gray-500">
                    Aucun reversement trouvé
                  </td>
                </tr>
              ) : (
                reversements.map(reversement => (
                  <tr key={reversement.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {reversement.store_name || '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(reversement.period_start)} - {formatDate(reversement.period_end)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {reversement.total_orders}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatPrice(reversement.total_sales)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatPrice(reversement.total_commissions)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-indigo-600">
                      {formatPrice(reversement.net_amount)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(reversement.status)}`}>
                        {getStatusLabel(reversement.status)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {reversement.transaction_reference || '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex justify-end gap-2">
                        {reversement.status === 'pending' && (
                          <button
                            onClick={() => handleStatusChange(reversement, 'processing')}
                            className="text-blue-600 hover:text-blue-900"
                          >
                            Traiter
                          </button>
                        )}
                        {reversement.status === 'processing' && (
                          <button
                            onClick={() => handleStatusChange(reversement, 'completed')}
                            className="text-green-600 hover:text-green-900"
                          >
                            Compléter
                          </button>
                        )}
                        <button
                          onClick={() => handleEdit(reversement)}
                          className="text-indigo-600 hover:text-indigo-900"
                        >
                          Modifier
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Create/Edit Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={selectedReversement ? 'Modifier le reversement' : 'Créer un reversement'}
        size="md"
      >
        <div className="space-y-4">
          {!selectedReversement ? (
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
                  value={formData.status || selectedReversement.status}
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
                  <span className="font-semibold">{selectedReversement.store_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Période:</span>
                  <span className="font-semibold">{formatDate(selectedReversement.period_start)} - {formatDate(selectedReversement.period_end)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Montant net:</span>
                  <span className="font-semibold text-indigo-600">{formatPrice(selectedReversement.net_amount)}</span>
                </div>
              </div>
            </>
          )}
          <div className="flex justify-end gap-3 pt-4">
            <button
              onClick={() => setIsModalOpen(false)}
              className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
            >
              Annuler
            </button>
            <button
              onClick={handleSave}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
            >
              {selectedReversement ? 'Enregistrer' : 'Créer'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default AdminReversementsSection;

