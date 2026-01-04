import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import {
  createForfait,
  updateForfait
} from '../services/adminService';

/**
 * Modal pour créer/modifier un forfait
 */
const ForfaitModal = ({ isOpen, onClose, forfait = null, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const [formData, setFormData] = useState({
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

  useEffect(() => {
    if (isOpen) {
      if (forfait) {
        setFormData({
          name: forfait.name || '',
          description: forfait.description || '',
          monthly_price: forfait.monthly_price || '',
          max_priority_orders: forfait.max_priority_orders || '',
          discount_rate: forfait.discount_rate || '',
          can_schedule_delivery: forfait.can_schedule_delivery || false,
          can_track_realtime: forfait.can_track_realtime || false,
          can_contact_driver: forfait.can_contact_driver || false,
          priority_support: forfait.priority_support || false,
          is_active: forfait.is_active !== undefined ? forfait.is_active : true
        });
      } else {
        setFormData({
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
      }
    }
  }, [isOpen, forfait]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const payload = {
        name: formData.name,
        description: formData.description,
        monthly_price: parseFloat(formData.monthly_price) || 0,
        max_priority_orders: parseInt(formData.max_priority_orders) || 0,
        discount_rate: parseFloat(formData.discount_rate) || 0,
        can_schedule_delivery: formData.can_schedule_delivery,
        can_track_realtime: formData.can_track_realtime,
        can_contact_driver: formData.can_contact_driver,
        priority_support: formData.priority_support,
        is_active: formData.is_active
      };

      let res;
      if (forfait) {
        res = await updateForfait(forfait.id, payload);
      } else {
        res = await createForfait(payload);
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
      title={forfait ? 'Modifier le forfait' : 'Créer un forfait'}
      size="lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
            {error}
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Nom *</label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
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
              value={formData.monthly_price}
              onChange={(e) => setFormData({ ...formData, monthly_price: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Commandes prioritaires max</label>
            <input
              type="number"
              value={formData.max_priority_orders}
              onChange={(e) => setFormData({ ...formData, max_priority_orders: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Réduction sur frais (%)</label>
          <input
            type="number"
            step="0.1"
            value={formData.discount_rate}
            onChange={(e) => setFormData({ ...formData, discount_rate: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">Fonctionnalités</label>
          <div className="space-y-2">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.can_schedule_delivery}
                onChange={(e) => setFormData({ ...formData, can_schedule_delivery: e.target.checked })}
                className="mr-2"
              />
              Planification de livraison
            </label>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.can_track_realtime}
                onChange={(e) => setFormData({ ...formData, can_track_realtime: e.target.checked })}
                className="mr-2"
              />
              Suivi en temps réel
            </label>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.can_contact_driver}
                onChange={(e) => setFormData({ ...formData, can_contact_driver: e.target.checked })}
                className="mr-2"
              />
              Contact livreur
            </label>
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={formData.priority_support}
                onChange={(e) => setFormData({ ...formData, priority_support: e.target.checked })}
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
              checked={formData.is_active}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              className="mr-2"
            />
            Actif
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
            {loading ? 'Enregistrement...' : (forfait ? 'Enregistrer' : 'Créer')}
          </button>
        </div>
      </form>
    </Modal>
  );
};

export default ForfaitModal;

