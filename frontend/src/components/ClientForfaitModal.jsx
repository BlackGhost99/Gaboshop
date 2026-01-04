import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import {
  createClientForfait,
  updateClientForfait,
  getForfaits
} from '../services/adminService';
import { getAdminUsers } from '../services/adminService';

/**
 * Modal pour créer/modifier un abonnement client (ClientForfait)
 */
const ClientForfaitModal = ({ isOpen, onClose, clientForfait = null, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [clients, setClients] = useState([]);
  const [forfaits, setForfaits] = useState([]);
  
  const [formData, setFormData] = useState({
    user_id: '',
    forfait_id: '',
    expiration_date: '',
    status: 'active',
    auto_renew: true
  });

  useEffect(() => {
    if (isOpen) {
      loadClients();
      loadForfaits();
      if (clientForfait) {
        setFormData({
          user_id: clientForfait.user || '',
          forfait_id: clientForfait.forfait || '',
          expiration_date: clientForfait.expiration_date ? clientForfait.expiration_date.split('T')[0] : '',
          status: clientForfait.status || 'active',
          auto_renew: clientForfait.auto_renew !== undefined ? clientForfait.auto_renew : true
        });
      } else {
        // Calculate default expiration date (30 days from now)
        const defaultExpirationDate = new Date();
        defaultExpirationDate.setMonth(defaultExpirationDate.getMonth() + 1);
        setFormData({
          user_id: '',
          forfait_id: '',
          expiration_date: defaultExpirationDate.toISOString().split('T')[0],
          status: 'active',
          auto_renew: true
        });
      }
    }
  }, [isOpen, clientForfait]);

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

  const loadForfaits = async () => {
    try {
      const res = await getForfaits();
      if (res?.success) {
        setForfaits(res.data || []);
      }
    } catch (err) {
      console.error('Error loading forfaits:', err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      if (!formData.user_id || !formData.forfait_id || !formData.expiration_date) {
        setError('Veuillez remplir tous les champs obligatoires');
        setLoading(false);
        return;
      }

      const payload = {
        user: formData.user_id,
        forfait: formData.forfait_id,
        expiration_date: formData.expiration_date,
        status: formData.status,
        auto_renew: formData.auto_renew
      };

      let res;
      if (clientForfait) {
        res = await updateClientForfait(clientForfait.id, payload);
      } else {
        res = await createClientForfait(payload);
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

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={clientForfait ? 'Modifier l\'abonnement' : 'Créer un abonnement client'}
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
          <select
            value={formData.user_id}
            onChange={(e) => setFormData({ ...formData, user_id: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            required
            disabled={!!clientForfait}
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
            value={formData.forfait_id}
            onChange={(e) => setFormData({ ...formData, forfait_id: e.target.value })}
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
            value={formData.expiration_date}
            onChange={(e) => setFormData({ ...formData, expiration_date: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Statut</label>
          <select
            value={formData.status}
            onChange={(e) => setFormData({ ...formData, status: e.target.value })}
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
              checked={formData.auto_renew}
              onChange={(e) => setFormData({ ...formData, auto_renew: e.target.checked })}
              className="mr-2"
            />
            Renouvellement automatique
          </label>
        </div>

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
            {loading ? 'Enregistrement...' : (clientForfait ? 'Enregistrer' : 'Créer')}
          </button>
        </div>
      </form>
    </Modal>
  );
};

export default ClientForfaitModal;

