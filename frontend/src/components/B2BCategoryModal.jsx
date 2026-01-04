import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import {
  createB2BCategory,
  updateB2BCategory
} from '../services/adminService';

/**
 * Modal pour créer/modifier une catégorie B2B
 */
const B2BCategoryModal = ({ isOpen, onClose, category = null, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    is_active: true
  });

  useEffect(() => {
    if (isOpen) {
      if (category) {
        setFormData({
          name: category.name || '',
          description: category.description || '',
          is_active: category.is_active !== undefined ? category.is_active : true
        });
      } else {
        setFormData({
          name: '',
          description: '',
          is_active: true
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
      if (category?.id) {
        res = await updateB2BCategory(category.id, formData);
      } else {
        res = await createB2BCategory(formData);
      }

      if (res?.success) {
        if (onSuccess) onSuccess();
        onClose();
      } else {
        setError(res?.error || res?.errors || 'Erreur lors de l\'enregistrement');
      }
    } catch (err) {
      setError(err?.message || 'Erreur lors de l\'enregistrement');
    } finally {
      setLoading(false);
    }
  };

  const updateField = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  if (!isOpen) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={category ? 'Modifier la catégorie B2B' : 'Créer une catégorie B2B'}
      size="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
            {error}
          </div>
        )}

        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-1">Nom *</label>
          <input
            type="text"
            value={formData.name}
            onChange={(e) => updateField('name', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-1">Description</label>
          <textarea
            value={formData.description}
            onChange={(e) => updateField('description', e.target.value)}
            rows="3"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="is_active"
            checked={formData.is_active}
            onChange={(e) => updateField('is_active', e.target.checked)}
            className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
          />
          <label htmlFor="is_active" className="text-sm text-gray-700">Catégorie active</label>
        </div>

        <div className="flex gap-3 pt-4 border-t border-gray-200">
          <button
            type="submit"
            disabled={loading}
            className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Enregistrement...' : category ? 'Mettre à jour' : 'Créer'}
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

export default B2BCategoryModal;

