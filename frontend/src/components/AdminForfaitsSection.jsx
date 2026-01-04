import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import ConfirmModal from './ConfirmModal';
import {
  getForfaits,
  createForfait,
  updateForfait,
  getClientForfaits,
  createClientForfait,
  updateClientForfait
} from '../services/adminService';
import { getAdminUsers } from '../services/adminService';

/**
 * Section Admin pour gérer les forfaits et abonnements clients
 */
const AdminForfaitsSection = () => {
  const [activeSubTab, setActiveSubTab] = useState('forfaits');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Forfaits
  const [forfaits, setForfaits] = useState([]);
  const [selectedForfait, setSelectedForfait] = useState(null);
  const [isForfaitModalOpen, setIsForfaitModalOpen] = useState(false);
  const [forfaitFormData, setForfaitFormData] = useState({
    name: '',
    description: '',
    monthly_price: '',
    max_priority_orders: '',
    discount_rate: '',
    can_schedule_delivery: false,
    can_track_realtime: false,
    can_contact_driver: false,
    priority_support: false,
    is_active: true
  });

  // Client Forfaits
  const [clientForfaits, setClientForfaits] = useState([]);
  const [selectedClientForfait, setSelectedClientForfait] = useState(null);
  const [isClientForfaitModalOpen, setIsClientForfaitModalOpen] = useState(false);
  const [clientForfaitFormData, setClientForfaitFormData] = useState({
    user_id: '',
    forfait_id: '',
    expiration_date: '',
    status: 'active',
    auto_renew: true
  });

  const [clients, setClients] = useState([]);

  useEffect(() => {
    loadClients();
  }, []);

  useEffect(() => {
    loadData();
  }, [activeSubTab]);

  const loadClients = async () => {
    try {
      const res = await getAdminUsers('client');
      if (res?.success) {
        setClients(res.data || []);
      }
    } catch (err) {
      console.error('Error loading clients:', err);
    }
  };

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      if (activeSubTab === 'forfaits') {
        const res = await getForfaits();
        if (res?.success) setForfaits(res.data || []);
      } else if (activeSubTab === 'client-forfaits') {
        const res = await getClientForfaits();
        if (res?.success) setClientForfaits(res.data || []);
      }
    } catch (err) {
      setError(err?.message || 'Erreur lors du chargement');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateForfait = () => {
    setForfaitFormData({
      name: '',
      description: '',
      monthly_price: '',
      max_priority_orders: '',
      discount_rate: '',
      can_schedule_delivery: false,
      can_track_realtime: false,
      can_contact_driver: false,
      priority_support: false,
      is_active: true
    });
    setSelectedForfait(null);
    setIsForfaitModalOpen(true);
  };

  const handleEditForfait = (forfait) => {
    setForfaitFormData({
      name: forfait.name,
      description: forfait.description || '',
      monthly_price: forfait.monthly_price,
      max_priority_orders: forfait.max_priority_orders || '',
      discount_rate: forfait.discount_rate || '',
      can_schedule_delivery: forfait.can_schedule_delivery || false,
      can_track_realtime: forfait.can_track_realtime || false,
      can_contact_driver: forfait.can_contact_driver || false,
      priority_support: forfait.priority_support || false,
      is_active: forfait.is_active !== undefined ? forfait.is_active : true
    });
    setSelectedForfait(forfait);
    setIsForfaitModalOpen(true);
  };

  const handleSaveForfait = async () => {
    setError(null);
    setSuccess(null);
    try {
      const payload = {
        name: forfaitFormData.name,
        description: forfaitFormData.description,
        monthly_price: parseFloat(forfaitFormData.monthly_price) || 0,
        max_priority_orders: parseInt(forfaitFormData.max_priority_orders) || 0,
        discount_rate: parseFloat(forfaitFormData.discount_rate) || 0,
        can_schedule_delivery: forfaitFormData.can_schedule_delivery,
        can_track_realtime: forfaitFormData.can_track_realtime,
        can_contact_driver: forfaitFormData.can_contact_driver,
        priority_support: forfaitFormData.priority_support,
        is_active: forfaitFormData.is_active
      };

      let res;
      if (selectedForfait) {
        res = await updateForfait(selectedForfait.id, payload);
      } else {
        res = await createForfait(payload);
      }
      if (res?.success) {
        setSuccess(selectedForfait ? 'Forfait mis à jour' : 'Forfait créé');
        setIsForfaitModalOpen(false);
        loadData();
      } else {
        setError(res?.error || 'Erreur lors de la sauvegarde');
      }
    } catch (err) {
      setError(err?.message || 'Erreur lors de la sauvegarde');
    }
  };

  const handleCreateClientForfait = () => {
    setClientForfaitFormData({
      user_id: '',
      forfait_id: '',
      expiration_date: '',
      status: 'active',
      auto_renew: true
    });
    setSelectedClientForfait(null);
    setIsClientForfaitModalOpen(true);
  };

  const handleEditClientForfait = (clientForfait) => {
    setClientForfaitFormData({
      user_id: clientForfait.user,
      forfait_id: clientForfait.forfait,
      expiration_date: clientForfait.expiration_date ? clientForfait.expiration_date.split('T')[0] : '',
      status: clientForfait.status,
      auto_renew: clientForfait.auto_renew
    });
    setSelectedClientForfait(clientForfait);
    setIsClientForfaitModalOpen(true);
  };

  const handleSaveClientForfait = async () => {
    setError(null);
    setSuccess(null);
    try {
      if (!clientForfaitFormData.user_id || !clientForfaitFormData.forfait_id || !clientForfaitFormData.expiration_date) {
        setError('Veuillez remplir tous les champs obligatoires');
        return;
      }

      const payload = {
        user: clientForfaitFormData.user_id,
        forfait: clientForfaitFormData.forfait_id,
        expiration_date: clientForfaitFormData.expiration_date,
        status: clientForfaitFormData.status,
        auto_renew: clientForfaitFormData.auto_renew
      };

      let res;
      if (selectedClientForfait) {
        res = await updateClientForfait(selectedClientForfait.id, payload);
      } else {
        res = await createClientForfait(payload);
      }
      if (res?.success) {
        setSuccess(selectedClientForfait ? 'Abonnement mis à jour' : 'Abonnement créé');
        setIsClientForfaitModalOpen(false);
        loadData();
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
      'active': 'Actif',
      'expired': 'Expiré',
      'suspended': 'Suspendu',
      'cancelled': 'Annulé'
    };
    return labels[status] || status;
  };

  const getStatusColor = (status) => {
    const colors = {
      'active': 'bg-green-100 text-green-800',
      'expired': 'bg-red-100 text-red-800',
      'suspended': 'bg-yellow-100 text-yellow-800',
      'cancelled': 'bg-gray-100 text-gray-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getDefaultExpirationDate = () => {
    const date = new Date();
    date.setMonth(date.getMonth() + 1);
    return date.toISOString().split('T')[0];
  };

  const subTabs = [
    { id: 'forfaits', label: 'Forfaits' },
    { id: 'client-forfaits', label: 'Abonnements Clients' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Gestion des Forfaits</h2>
        <button
          onClick={activeSubTab === 'forfaits' ? handleCreateForfait : handleCreateClientForfait}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
        >
          + {activeSubTab === 'forfaits' ? 'Créer un forfait' : 'Créer un abonnement'}
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

      {/* Forfaits Table */}
      {!loading && activeSubTab === 'forfaits' && (
        <div className="bg-white shadow-sm rounded-lg border border-gray-100 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Nom</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Prix mensuel</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Commandes prioritaires</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Réduction</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Fonctionnalités</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {forfaits.length === 0 ? (
                <tr>
                  <td colSpan="7" className="px-6 py-8 text-center text-gray-500">
                    Aucun forfait trouvé
                  </td>
                </tr>
              ) : (
                forfaits.map(forfait => (
                  <tr key={forfait.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {forfait.name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatPrice(forfait.monthly_price)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {forfait.max_priority_orders || 0}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {forfait.discount_rate ? `${forfait.discount_rate}%` : '—'}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      <div className="flex flex-wrap gap-1">
                        {forfait.can_schedule_delivery && <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">Planification</span>}
                        {forfait.can_track_realtime && <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">Suivi temps réel</span>}
                        {forfait.can_contact_driver && <span className="px-2 py-1 bg-purple-100 text-purple-800 text-xs rounded">Contact livreur</span>}
                        {forfait.priority_support && <span className="px-2 py-1 bg-orange-100 text-orange-800 text-xs rounded">Support prioritaire</span>}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                        forfait.is_active ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {forfait.is_active ? 'Actif' : 'Inactif'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => handleEditForfait(forfait)}
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
      )}

      {/* Client Forfaits Table */}
      {!loading && activeSubTab === 'client-forfaits' && (
        <div className="bg-white shadow-sm rounded-lg border border-gray-100 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Client</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Forfait</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date début</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date expiration</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Renouvellement auto</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {clientForfaits.length === 0 ? (
                <tr>
                  <td colSpan="7" className="px-6 py-8 text-center text-gray-500">
                    Aucun abonnement trouvé
                  </td>
                </tr>
              ) : (
                clientForfaits.map(clientForfait => (
                  <tr key={clientForfait.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {clientForfait.client_name || `Client #${clientForfait.user}`}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {clientForfait.forfait_name || '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(clientForfait.start_date)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(clientForfait.expiration_date)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(clientForfait.status)}`}>
                        {getStatusLabel(clientForfait.status)}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {clientForfait.auto_renew ? 'Oui' : 'Non'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => handleEditClientForfait(clientForfait)}
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
      )}

      {/* Forfait Modal */}
      <Modal
        isOpen={isForfaitModalOpen}
        onClose={() => setIsForfaitModalOpen(false)}
        title={selectedForfait ? 'Modifier le forfait' : 'Créer un forfait'}
        size="lg"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Nom *</label>
            <input
              type="text"
              value={forfaitFormData.name}
              onChange={(e) => setForfaitFormData({ ...forfaitFormData, name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={forfaitFormData.description}
              onChange={(e) => setForfaitFormData({ ...forfaitFormData, description: e.target.value })}
              rows="3"
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Prix mensuel (FCFA) *</label>
              <input
                type="number"
                step="0.01"
                value={forfaitFormData.monthly_price}
                onChange={(e) => setForfaitFormData({ ...forfaitFormData, monthly_price: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Commandes prioritaires max</label>
              <input
                type="number"
                value={forfaitFormData.max_priority_orders}
                onChange={(e) => setForfaitFormData({ ...forfaitFormData, max_priority_orders: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Réduction sur frais (%)</label>
            <input
              type="number"
              step="0.1"
              value={forfaitFormData.discount_rate}
              onChange={(e) => setForfaitFormData({ ...forfaitFormData, discount_rate: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-700 mb-1">Fonctionnalités</label>
            <div className="space-y-2">
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={forfaitFormData.can_schedule_delivery}
                  onChange={(e) => setForfaitFormData({ ...forfaitFormData, can_schedule_delivery: e.target.checked })}
                  className="mr-2"
                />
                Planification de livraison
              </label>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={forfaitFormData.can_track_realtime}
                  onChange={(e) => setForfaitFormData({ ...forfaitFormData, can_track_realtime: e.target.checked })}
                  className="mr-2"
                />
                Suivi en temps réel
              </label>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={forfaitFormData.can_contact_driver}
                  onChange={(e) => setForfaitFormData({ ...forfaitFormData, can_contact_driver: e.target.checked })}
                  className="mr-2"
                />
                Contact livreur
              </label>
              <label className="flex items-center">
                <input
                  type="checkbox"
                  checked={forfaitFormData.priority_support}
                  onChange={(e) => setForfaitFormData({ ...forfaitFormData, priority_support: e.target.checked })}
                  className="mr-2"
                />
                Support prioritaire
              </label>
            </div>
          </div>
          <div>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={forfaitFormData.is_active}
                onChange={(e) => setForfaitFormData({ ...forfaitFormData, is_active: e.target.checked })}
                className="mr-2"
              />
              Actif
            </label>
          </div>
          <div className="flex justify-end gap-3 pt-4">
            <button
              onClick={() => setIsForfaitModalOpen(false)}
              className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
            >
              Annuler
            </button>
            <button
              onClick={handleSaveForfait}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
            >
              {selectedForfait ? 'Enregistrer' : 'Créer'}
            </button>
          </div>
        </div>
      </Modal>

      {/* Client Forfait Modal */}
      <Modal
        isOpen={isClientForfaitModalOpen}
        onClose={() => setIsClientForfaitModalOpen(false)}
        title={selectedClientForfait ? 'Modifier l\'abonnement' : 'Créer un abonnement client'}
        size="md"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Client *</label>
            <select
              value={clientForfaitFormData.user_id}
              onChange={(e) => setClientForfaitFormData({ ...clientForfaitFormData, user_id: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              required
            >
              <option value="">Sélectionner un client</option>
              {clients.map(client => (
                <option key={client.id} value={client.id}>
                  {client.phone} - {[client.first_name, client.last_name].filter(Boolean).join(' ') || 'Sans nom'}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Forfait *</label>
            <select
              value={clientForfaitFormData.forfait_id}
              onChange={(e) => setClientForfaitFormData({ ...clientForfaitFormData, forfait_id: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              required
            >
              <option value="">Sélectionner un forfait</option>
              {forfaits.filter(f => f.is_active).map(forfait => (
                <option key={forfait.id} value={forfait.id}>{forfait.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Date d'expiration *</label>
            <input
              type="date"
              value={clientForfaitFormData.expiration_date || getDefaultExpirationDate()}
              onChange={(e) => setClientForfaitFormData({ ...clientForfaitFormData, expiration_date: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Statut</label>
            <select
              value={clientForfaitFormData.status}
              onChange={(e) => setClientForfaitFormData({ ...clientForfaitFormData, status: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            >
              <option value="active">Actif</option>
              <option value="expired">Expiré</option>
              <option value="suspended">Suspendu</option>
              <option value="cancelled">Annulé</option>
            </select>
          </div>
          <div>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={clientForfaitFormData.auto_renew}
                onChange={(e) => setClientForfaitFormData({ ...clientForfaitFormData, auto_renew: e.target.checked })}
                className="mr-2"
              />
              Renouvellement automatique
            </label>
          </div>
          <div className="flex justify-end gap-3 pt-4">
            <button
              onClick={() => setIsClientForfaitModalOpen(false)}
              className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
            >
              Annuler
            </button>
            <button
              onClick={handleSaveClientForfait}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
            >
              {selectedClientForfait ? 'Enregistrer' : 'Créer'}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default AdminForfaitsSection;

