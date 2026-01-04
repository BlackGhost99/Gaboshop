import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import {
  createClientCredit,
  updateClientCredit
} from '../services/adminService';

/**
 * Modal pour créer/modifier un crédit client
 */
const ClientCreditModal = ({ isOpen, onClose, credit = null, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const [formData, setFormData] = useState({
    client_id: '',
    amount: '',
    credit_type: 'promotion',
    reason: '',
    expiration_date: ''
  });

  useEffect(() => {
    if (isOpen) {
      if (credit) {
        setFormData({
          client_id: credit.client || '',
          amount: credit.amount || '',
          credit_type: credit.credit_type || 'promotion',
          reason: credit.reason || '',
          expiration_date: credit.expiration_date ? credit.expiration_date.split('T')[0] : ''
        });
      } else {
        // Calculate default expiration date (90 days from now)
        const defaultExpirationDate = new Date();
        defaultExpirationDate.setDate(defaultExpirationDate.getDate() + 90);
        setFormData({
          client_id: '',
          amount: '',
          credit_type: 'promotion',
          reason: '',
          expiration_date: defaultExpirationDate.toISOString().split('T')[0]
        });
      }
    }
  }, [isOpen, credit]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (!formData.client_id || !formData.amount || !formData.expiration_date) {
        setError('Veuillez remplir tous les champs obligatoires');
        setLoading(false);
        return;
      }

      const payload = {
        client: formData.client_id,
        amount: parseFloat(formData.amount),
        credit_type: formData.credit_type,
        reason: formData.reason,
        expiration_date: formData.expiration_date
      };

      let res;
      if (credit) {
        res = await updateClientCredit(credit.id, payload);
      } else {
        res = await createClientCredit(payload);
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
      'available': 'Disponible',
      'used': 'Utilisé',
      'expired': 'Expiré'
    };
    return labels[status] || status;
  };

  const getStatusColor = (status) => {
    const colors = {
      'available': 'bg-green-100 text-green-800',
      'used': 'bg-gray-100 text-gray-800',
      'expired': 'bg-red-100 text-red-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={credit ? 'Modifier le crédit' : 'Créer un crédit client'}
      size="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
            {error}
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Client *</label>
          <input
            type="number"
            value={formData.client_id}
            onChange={(e) => setFormData({ ...formData, client_id: e.target.value })}
            placeholder="ID du client"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            required
          />
          <p className="mt-1 text-xs text-gray-500">Entrez l'ID du client</p>
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
          <label className="block text-sm font-medium text-gray-700 mb-1">Type *</label>
          <select
            value={formData.credit_type}
            onChange={(e) => setFormData({ ...formData, credit_type: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            required
          >
            <option value="promotion">Promotion</option>
            <option value="referral">Parrainage</option>
            <option value="loyalty">Fidélité</option>
            <option value="compensation">Compensation</option>
            <option value="other">Autre</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Date d'expiration *</label>
          <input
            type="date"
            value={formData.expiration_date}
            onChange={(e) => setFormData({ ...formData, expiration_date: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Raison (optionnel)</label>
          <textarea
            value={formData.reason}
            onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
            placeholder="Raison de l'attribution du crédit"
            rows="3"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        {credit && (
          <div className="bg-gray-50 p-4 rounded-lg space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Statut actuel:</span>
              <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(credit.status)}`}>
                {getStatusLabel(credit.status)}
              </span>
            </div>
            {credit.status === 'used' && (
              <p className="text-xs text-red-600">Note: Le montant ne peut pas être modifié pour un crédit déjà utilisé.</p>
            )}
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
            {loading ? 'Enregistrement...' : (credit ? 'Enregistrer' : 'Créer')}
          </button>
        </div>
      </form>
    </Modal>
  );
};

export default ClientCreditModal;

