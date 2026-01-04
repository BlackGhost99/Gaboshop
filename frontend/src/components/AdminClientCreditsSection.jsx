import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import ConfirmModal from './ConfirmModal';
import {
  getClientCredits,
  createClientCredit,
  updateClientCredit
} from '../services/adminService';

/**
 * Section Admin pour gérer les crédits clients
 */
const AdminClientCreditsSection = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const [credits, setCredits] = useState([]);
  const [selectedCredit, setSelectedCredit] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [creditToDelete, setCreditToDelete] = useState(null);

  const [filters, setFilters] = useState({
    client_id: '',
    status: '',
    credit_type: '',
    date_from: '',
    date_to: ''
  });

  const [formData, setFormData] = useState({
    client_id: '',
    amount: '',
    credit_type: 'promotion',
    reason: '',
    expiration_date: ''
  });

  const [clients, setClients] = useState([]);
  const [clientSearch, setClientSearch] = useState('');
  const [clientSearchResults, setClientSearchResults] = useState([]);

  useEffect(() => {
    loadCredits();
  }, [filters]);

  const loadCredits = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getClientCredits(filters);
      if (res?.success) {
        setCredits(res.data || []);
      } else {
        setError(res?.error || 'Erreur lors du chargement');
      }
    } catch (err) {
      setError(err?.message || 'Erreur lors du chargement');
    } finally {
      setLoading(false);
    }
  };

  const searchClients = async (query) => {
    if (!query || query.length < 2) {
      setClientSearchResults([]);
      return;
    }
    try {
      // TODO: Implement client search API endpoint
      // For now, we'll use a placeholder
      // const res = await searchClientsAPI(query);
      // setClientSearchResults(res.data || []);
    } catch (err) {
      console.error('Error searching clients:', err);
    }
  };

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (clientSearch) {
        searchClients(clientSearch);
      }
    }, 300);
    return () => clearTimeout(timeoutId);
  }, [clientSearch]);

  const handleCreate = () => {
    setFormData({
      client_id: '',
      amount: '',
      credit_type: 'promotion',
      reason: '',
      expiration_date: ''
    });
    setSelectedCredit(null);
    setIsModalOpen(true);
  };

  const handleEdit = (credit) => {
    setFormData({
      client_id: credit.client,
      amount: credit.amount,
      credit_type: credit.credit_type,
      reason: credit.reason || '',
      expiration_date: credit.expiration_date ? credit.expiration_date.split('T')[0] : ''
    });
    setSelectedCredit(credit);
    setIsModalOpen(true);
  };

  const handleSave = async () => {
    setError(null);
    setSuccess(null);
    try {
      if (!formData.client_id || !formData.amount || !formData.expiration_date) {
        setError('Veuillez remplir tous les champs obligatoires');
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
      if (selectedCredit) {
        res = await updateClientCredit(selectedCredit.id, payload);
      } else {
        res = await createClientCredit(payload);
      }
      if (res?.success) {
        setSuccess(selectedCredit ? 'Crédit mis à jour' : 'Crédit créé');
        setIsModalOpen(false);
        loadCredits();
      } else {
        setError(res?.error || 'Erreur lors de la sauvegarde');
      }
    } catch (err) {
      setError(err?.message || 'Erreur lors de la sauvegarde');
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

  const getCreditTypeLabel = (type) => {
    const labels = {
      'promotion': 'Promotion',
      'referral': 'Parrainage',
      'loyalty': 'Fidélité',
      'compensation': 'Compensation',
      'other': 'Autre'
    };
    return labels[type] || type;
  };

  // Calculate expiration date (default: 90 days from now)
  const getDefaultExpirationDate = () => {
    const date = new Date();
    date.setDate(date.getDate() + 90);
    return date.toISOString().split('T')[0];
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Gestion des Crédits Clients</h2>
        <button
          onClick={handleCreate}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
        >
          + Créer un crédit
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
            type="text"
            placeholder="ID Client"
            value={filters.client_id}
            onChange={(e) => setFilters({ ...filters, client_id: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
          />
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Tous les statuts</option>
            <option value="available">Disponible</option>
            <option value="used">Utilisé</option>
            <option value="expired">Expiré</option>
          </select>
          <select
            value={filters.credit_type}
            onChange={(e) => setFilters({ ...filters, credit_type: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Tous les types</option>
            <option value="promotion">Promotion</option>
            <option value="referral">Parrainage</option>
            <option value="loyalty">Fidélité</option>
            <option value="compensation">Compensation</option>
            <option value="other">Autre</option>
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
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Client</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Montant</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Raison</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date création</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Expiration</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {credits.length === 0 ? (
                <tr>
                  <td colSpan="8" className="px-6 py-8 text-center text-gray-500">
                    Aucun crédit trouvé
                  </td>
                </tr>
              ) : (
                credits.map(credit => (
                  <tr key={credit.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {credit.client_name || `Client #${credit.client}`}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-indigo-600">
                      {formatPrice(credit.amount)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {getCreditTypeLabel(credit.credit_type)}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500 max-w-xs truncate">
                      {credit.reason || '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(credit.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(credit.expiration_date)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(credit.status)}`}>
                        {getStatusLabel(credit.status)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => handleEdit(credit)}
                        className="text-indigo-600 hover:text-indigo-900"
                        disabled={credit.status === 'used'}
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
      )}

      {/* Create/Edit Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={selectedCredit ? 'Modifier le crédit' : 'Créer un crédit client'}
        size="md"
      >
        <div className="space-y-4">
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
              value={formData.expiration_date || getDefaultExpirationDate()}
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
          {selectedCredit && (
            <div className="bg-gray-50 p-4 rounded-lg space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Statut actuel:</span>
                <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(selectedCredit.status)}`}>
                  {getStatusLabel(selectedCredit.status)}
                </span>
              </div>
              {selectedCredit.status === 'used' && (
                <p className="text-xs text-red-600">Note: Le montant ne peut pas être modifié pour un crédit déjà utilisé.</p>
              )}
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
              {selectedCredit ? 'Enregistrer' : 'Créer'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default AdminClientCreditsSection;

