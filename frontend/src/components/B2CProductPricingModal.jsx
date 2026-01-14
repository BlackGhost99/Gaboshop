import React, { useState } from 'react';
import Modal from './Modal';
import { updateB2CProductPrice } from '../services/adminService';

/**
 * Modal pour modifier le prix B2C d'un produit
 */
const B2CProductPricingModal = ({ isOpen, onClose, product = null, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const [formData, setFormData] = useState({
    price: 0,
    compare_price: null
  });

  React.useEffect(() => {
    if (isOpen && product) {
      setFormData({
        price: product.price || 0,
        compare_price: product.compare_price || null
      });
    }
  }, [isOpen, product]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!product) return;
    
    setLoading(true);
    setError(null);

    try {
      const payload = {
        price: parseFloat(formData.price),
      };
      
      if (formData.compare_price) {
        payload.compare_price = parseFloat(formData.compare_price);
      }
      
      const res = await updateB2CProductPrice(product.id, payload);

      if (res?.success) {
        if (onSuccess) {
          onSuccess();
        }
        onClose();
      } else {
        setError(res?.error || 'Erreur lors de la mise à jour');
      }
    } catch (err) {
      setError(err?.message || 'Erreur lors de la mise à jour');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen || !product) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Modifier le prix - ${product.name}`}
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
            Prix B2C (FCFA) *
          </label>
          <input
            type="number"
            min="0"
            step="1"
            value={formData.price}
            onChange={(e) => setFormData({ ...formData, price: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            required
            placeholder="0"
          />
          <p className="text-xs text-gray-500 mt-1">
            Prix de vente au détail pour ce produit
          </p>
        </div>

        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Prix de comparaison (FCFA) - Optionnel
          </label>
          <input
            type="number"
            min="0"
            step="1"
            value={formData.compare_price || ''}
            onChange={(e) => setFormData({ ...formData, compare_price: e.target.value || null })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            placeholder="Ancien prix (pour afficher une promotion)"
          />
          <p className="text-xs text-gray-500 mt-1">
            Si renseigné, ce prix sera affiché barré pour indiquer une promotion
          </p>
        </div>

        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
          <p className="text-xs text-blue-800">
            <strong>Note:</strong> Ce prix s'applique uniquement aux ventes B2C (détail). 
            Les produits avec <code>market_type='b2c'</code> ou <code>'both'</code> seront visibles dans le catalogue client.
          </p>
        </div>

        <div className="flex gap-3 pt-4 border-t border-gray-200">
          <button
            type="submit"
            disabled={loading}
            className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Enregistrement...' : 'Enregistrer'}
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

export default B2CProductPricingModal;
