import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import {
  createPayout,
  updatePayout
} from '../services/adminService';
import { getAdminUsers } from '../services/adminService';

/**
 * Modal pour créer/modifier un payout
 */
const PayoutModal = ({ isOpen, onClose, payout = null, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [users, setUsers] = useState([]);
  
  const [formData, setFormData] = useState({
    user_id: '',
    order_id: '',
    payout_type: 'delivery',
    amount: '',
    reason: '',
    flutterwave_payout_id: ''
  });

  useEffect(() => {
    if (isOpen) {
      loadUsers();
      if (payout) {
        setFormData({
          user_id: payout.user || '',
          order_id: payout.order || '',
          payout_type: payout.payout_type || 'delivery',
          amount: payout.amount || '',
          reason: payout.reason || '',
          flutterwave_payout_id: payout.flutterwave_payout_id || ''
        });
      } else {
        setFormData({
          user_id: '',
          order_id: '',
          payout_type: 'delivery',
          amount: '',
          reason: '',
          flutterwave_payout_id: ''
        });
      }
    }
  }, [isOpen, payout]);

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

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (!formData.user_id || !formData.amount) {
        setError('Veuillez remplir tous les champs obligatoires');
        setLoading(false);
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
      if (payout) {
        res = await updatePayout(payout.id, payload);
      } else {
        res = await createPayout(payload);
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

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={payout ? 'Modifier le payout' : 'Créer un payout'}
      size="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
            {error}
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Utilisateur *</label>
          <select
            value={formData.user_id}
            onChange={(e) => setFormData({ ...formData, user_id: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            required
            disabled={!!payout}
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

        {payout && (
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

        {payout && (
          <div className="bg-gray-50 p-4 rounded-lg space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Statut actuel:</span>
              <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(payout.status)}`}>
                {getStatusLabel(payout.status)}
              </span>
            </div>
          </div>
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
            {loading ? 'Enregistrement...' : (payout ? 'Enregistrer' : 'Créer')}
          </button>
        </div>
      </form>
    </Modal>
  );
};

export default PayoutModal;

