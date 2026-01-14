import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import {
  createB2CCategory,
  updateB2CCategory
} from '../services/adminService';
import { getStoresListAdmin } from '../services/adminService';

/**
 * Modal pour créer/modifier une catégorie B2C (ProductCategory)
 */
const B2CCategoryModal = ({ isOpen, onClose, category = null, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [stores, setStores] = useState([]);
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    store_id: '',
    order: 0
  });

  useEffect(() => {
    if (isOpen) {
      // Load stores for dropdown
      getStoresListAdmin({ status: 'all' }).then(res => {
        if (res?.success) {
          setStores(res.data || []);
        }
      });
      
      if (category) {
        setFormData({
          name: category.name || '',
          description: category.description || '',
          store_id: category.store_id || '',
          order: category.order || 0
        });
      } else {
        setFormData({
          name: '',
          description: '',
          store_id: '',
          order: 0
        });
      }
    }
  }, [isOpen, category]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      let res;
      const payload = {
        ...formData,
        store_id: formData.store_id || null
      };
      
      if (category?.id) {
        res = await updateB2CCategory(category.id, payload);
      } else {
        res = await createB2CCategory(payload);
      }

      if (res?.success) {
        if (onSuccess) {
          onSuccess();
        }
        onClose();
      } else {
        setError(res?.error || 'Erreur lors de l\'enregistrement');
      }
    } catch (err) {
      setError(err?.message || 'Erreur lors de l\'enregistrement');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={category ? 'Modifier la catégorie B2C' : 'Créer une catégorie B2C'}
      size="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
            {error}
          </div>
        )}

        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Nom de la catégorie *
          </label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            required
            placeholder="Ex: Électronique, Alimentaire..."
          />
        </div>

        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Description
          </label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            rows="3"
            placeholder="Description de la catégorie..."
          />
        </div>

        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Magasin (optionnel)
          </label>
          <select
            value={formData.store_id}
            onChange={(e) => setFormData({ ...formData, store_id: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
          >
            <option value="">Tous les magasins (catégorie globale)</option>
            {stores.map(store => (
              <option key={store.id} value={store.id}>{store.name}</option>
            ))}
          </select>
          <p className="text-xs text-gray-500 mt-1">
            Si aucun magasin n'est sélectionné, la catégorie sera globale
          </p>
        </div>

        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Ordre d'affichage
          </label>
          <input
            type="number"
            min="0"
            value={formData.order}
            onChange={(e) => setFormData({ ...formData, order: parseInt(e.target.value) || 0 })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="0"
          />
          <p className="text-xs text-gray-500 mt-1">
            Ordre d'affichage dans les listes (plus petit = affiché en premier)
          </p>
        </div>

        <div className="flex gap-3 pt-4 border-t border-gray-200">
          <button
            type="submit"
            disabled={loading}
            className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Enregistrement...' : category ? 'Modifier' : 'Créer'}
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

export default B2CCategoryModal;
