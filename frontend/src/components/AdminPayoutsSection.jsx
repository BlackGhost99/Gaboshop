import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import ConfirmModal from './ConfirmModal';
import {
  getPayouts,
  createPayout,
  updatePayout
} from '../services/adminService';
import { getAdminUsers } from '../services/adminService';

/**
 * Section Admin pour gérer les payouts généraux
 */
const AdminPayoutsSection = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const [payouts, setPayouts] = useState([]);
  const [selectedPayout, setSelectedPayout] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const [filters, setFilters] = useState({
    user_id: '',
    payout_type: '',
    status: '',
    date_from: '',
    date_to: ''
  });

  const [formData, setFormData] = useState({
    user_id: '',
    order_id: '',
    payout_type: 'delivery',
    amount: '',
    reason: '',
    flutterwave_payout_id: ''
  });

  const [users, setUsers] = useState([]);

  useEffect(() => {
    loadUsers();
  }, []);

  useEffect(() => {
    loadPayouts();
  }, [filters]);

  const loadUsers = async () => {
    try {
      // Load delivery agents and store managers
      const [agentsRes, managersRes] = await Promise.all([
        getAdminUsers('delivery_agent'),
        getAdminUsers('store_manager')
      ]);
      const allUsers = [
        ...(agentsRes?.data || []),
        ...(managersRes?.data || [])
      ];
      setUsers(allUsers);
    } catch (err) {
      console.error('Error loading users:', err);
    }
  };

  const loadPayouts = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getPayouts(filters);
      if (res?.success) {
        setPayouts(res.data || []);
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
      user_id: '',
      order_id: '',
      payout_type: 'delivery',
      amount: '',
      reason: '',
      flutterwave_payout_id: ''
    });
    setSelectedPayout(null);
    setIsModalOpen(true);
  };

  const handleEdit = (payout) => {
    setFormData({
      user_id: payout.user,
      order_id: payout.order || '',
      payout_type: payout.payout_type,
      amount: payout.amount,
      reason: payout.reason || '',
      flutterwave_payout_id: payout.flutterwave_payout_id || ''
    });
    setSelectedPayout(payout);
    setIsModalOpen(true);
  };

  const handleSave = async () => {
    setError(null);
    setSuccess(null);
    try {
      if (!formData.user_id || !formData.amount) {
        setError('Veuillez remplir tous les champs obligatoires');
        return;
      }

      const payload = {
        user: formData.user_id,
        payout_type: formData.payout_type,
        amount: parseFloat(formData.amount),
        reason: formData.reason
      };

      if (formData.order_id) {
        payload.order = formData.order_id;
      }
      if (formData.flutterwave_payout_id) {
        payload.flutterwave_payout_id = formData.flutterwave_payout_id;
      }

      let res;
      if (selectedPayout) {
        res = await updatePayout(selectedPayout.id, payload);
      } else {
        res = await createPayout(payload);
      }
      if (res?.success) {
        setSuccess(selectedPayout ? 'Payout mis à jour' : 'Payout créé');
        setIsModalOpen(false);
        loadPayouts();
      } else {
        setError(res?.error || 'Erreur lors de la sauvegarde');
      }
    } catch (err) {
      setError(err?.message || 'Erreur lors de la sauvegarde');
    }
  };

  const handleStatusChange = async (payout, newStatus) => {
    setError(null);
    setSuccess(null);
    try {
      const res = await updatePayout(payout.id, { status: newStatus });
      if (res?.success) {
        setSuccess(`Statut mis à jour: ${getStatusLabel(newStatus)}`);
        loadPayouts();
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
      'paid': 'Payé',
      'failed': 'Échec',
      'cancelled': 'Annulé'
    };
    return labels[status] || status;
  };

  const getStatusColor = (status) => {
    const colors = {
      'pending': 'bg-yellow-100 text-yellow-800',
      'processing': 'bg-blue-100 text-blue-800',
      'paid': 'bg-green-100 text-green-800',
      'failed': 'bg-red-100 text-red-800',
      'cancelled': 'bg-gray-100 text-gray-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getPayoutTypeLabel = (type) => {
    const labels = {
      'delivery': 'Paiement Livreur',
      'merchant': 'Paiement Commerçant',
      'refund': 'Remboursement'
    };
    return labels[type] || type;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Gestion des Payouts</h2>
        <button
          onClick={handleCreate}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
        >
          + Créer un payout
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
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <input
            type="number"
            placeholder="ID Utilisateur"
            value={filters.user_id}
            onChange={(e) => setFilters({ ...filters, user_id: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
          />
          <select
            value={filters.payout_type}
            onChange={(e) => setFilters({ ...filters, payout_type: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Tous les types</option>
            <option value="delivery">Paiement Livreur</option>
            <option value="merchant">Paiement Commerçant</option>
            <option value="refund">Remboursement</option>
          </select>
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Tous les statuts</option>
            <option value="pending">En attente</option>
            <option value="processing">En traitement</option>
            <option value="paid">Payé</option>
            <option value="failed">Échec</option>
            <option value="cancelled">Annulé</option>
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
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Utilisateur</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">N° Commande</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Montant</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date création</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Référence Flutterwave</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {payouts.length === 0 ? (
                <tr>
                  <td colSpan="8" className="px-6 py-8 text-center text-gray-500">
                    Aucun payout trouvé
                  </td>
                </tr>
              ) : (
                payouts.map(payout => (
                  <tr key={payout.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {payout.user_name || payout.user_phone || `User #${payout.user}`}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {getPayoutTypeLabel(payout.payout_type)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {payout.order_number || '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-indigo-600">
                      {formatPrice(payout.amount)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(payout.status)}`}>
                        {getStatusLabel(payout.status)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(payout.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 font-mono text-xs">
                      {payout.flutterwave_payout_id || '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex justify-end gap-2">
                        {payout.status === 'pending' && (
                          <button
                            onClick={() => handleStatusChange(payout, 'processing')}
                            className="text-blue-600 hover:text-blue-900"
                          >
                            Traiter
                          </button>
                        )}
                        {payout.status === 'processing' && (
                          <button
                            onClick={() => handleStatusChange(payout, 'paid')}
                            className="text-green-600 hover:text-green-900"
                          >
                            Marquer payé
                          </button>
                        )}
                        <button
                          onClick={() => handleEdit(payout)}
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
        title={selectedPayout ? 'Modifier le payout' : 'Créer un payout'}
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Utilisateur *</label>
            <select
              value={formData.user_id}
              onChange={(e) => setFormData({ ...formData, user_id: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              required
            >
              <option value="">Sélectionner un utilisateur</option>
              {users.map(user => (
                <option key={user.id} value={user.id}>
                  {user.phone} - {[user.first_name, user.last_name].filter(Boolean).join(' ') || user.user_type}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Type *</label>
            <select
              value={formData.payout_type}
              onChange={(e) => setFormData({ ...formData, payout_type: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              required
            >
              <option value="delivery">Paiement Livreur</option>
              <option value="merchant">Paiement Commerçant</option>
              <option value="refund">Remboursement</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Montant (FCFA) *</label>
            <input
              type="number"
              step="0.01"
              value={formData.amount}
              onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
              placeholder="0.00"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">ID Commande (optionnel)</label>
            <input
              type="number"
              value={formData.order_id}
              onChange={(e) => setFormData({ ...formData, order_id: e.target.value })}
              placeholder="ID de la commande"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Raison (optionnel)</label>
            <textarea
              value={formData.reason}
              onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
              placeholder="Raison du payout"
              rows="3"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          {selectedPayout && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Référence Flutterwave</label>
              <input
                type="text"
                value={formData.flutterwave_payout_id}
                onChange={(e) => setFormData({ ...formData, flutterwave_payout_id: e.target.value })}
                placeholder="Référence Flutterwave"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          )}
          {selectedPayout && (
            <div className="bg-gray-50 p-4 rounded-lg space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Statut actuel:</span>
                <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(selectedPayout.status)}`}>
                  {getStatusLabel(selectedPayout.status)}
                </span>
              </div>
            </div>
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
              {selectedPayout ? 'Enregistrer' : 'Créer'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default AdminPayoutsSection;

