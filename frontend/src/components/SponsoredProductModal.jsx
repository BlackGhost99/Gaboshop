import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import {
  createSponsoredProduct,
  updateSponsoredProduct
} from '../services/adminService';
import { getStoresListAdmin, getProductsListAdmin } from '../services/adminService';

/**
 * Modal pour créer/modifier un produit sponsorisé
 */
const SponsoredProductModal = ({ isOpen, onClose, sponsoredProduct = null, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [stores, setStores] = useState([]);
  const [products, setProducts] = useState([]);
  const [filteredProducts, setFilteredProducts] = useState([]);
  
  const [formData, setFormData] = useState({
    store_id: '',
    product_id: '',
    sponsor_type: 'featured',
    price_paid: '',
    status: 'active',
    end_date: ''
  });

  useEffect(() => {
    if (isOpen) {
      loadStores();
      if (formData.store_id) {
        loadProducts(formData.store_id);
      }
      if (sponsoredProduct) {
        setFormData({
          store_id: sponsoredProduct.store || '',
          product_id: sponsoredProduct.product || '',
          sponsor_type: sponsoredProduct.sponsor_type || 'featured',
          price_paid: sponsoredProduct.price_paid || '',
          status: sponsoredProduct.status || 'active',
          end_date: sponsoredProduct.end_date ? sponsoredProduct.end_date.split('T')[0] : ''
        });
      } else {
        // Calculate default end_date (30 days from now)
        const defaultEndDate = new Date();
        defaultEndDate.setDate(defaultEndDate.getDate() + 30);
        setFormData({
          store_id: '',
          product_id: '',
          sponsor_type: 'featured',
          price_paid: '',
          status: 'active',
          end_date: defaultEndDate.toISOString().split('T')[0]
        });
      }
    }
  }, [isOpen, sponsoredProduct]);

  useEffect(() => {
    if (formData.store_id) {
      loadProducts(formData.store_id);
    } else {
      setFilteredProducts([]);
    }
  }, [formData.store_id]);

  const loadStores = async () => {
    try {
      const res = await getStoresListAdmin();
      if (res?.success) {
        setStores(res.data || []);
      }
    } catch (err) {
      console.error('Error loading stores:', err);
    }
  };

  const loadProducts = async (storeId) => {
    try {
      const res = await getProductsListAdmin({ store_id: storeId });
      if (res?.success) {
        setProducts(res.data || []);
        setFilteredProducts(res.data || []);
      }
    } catch (err) {
      console.error('Error loading products:', err);
      setProducts([]);
      setFilteredProducts([]);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const payload = {
        store: formData.store_id,
        product: formData.product_id,
        sponsor_type: formData.sponsor_type,
        price_paid: parseFloat(formData.price_paid),
        status: formData.status,
        end_date: formData.end_date
      };

      let res;
      if (sponsoredProduct) {
        res = await updateSponsoredProduct(sponsoredProduct.id, payload);
      } else {
        res = await createSponsoredProduct(payload);
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

  const formatPrice = (price) => {
    return new Intl.NumberFormat('fr-FR').format(price) + ' FCFA';
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={sponsoredProduct ? 'Modifier le produit sponsorisé' : 'Créer un produit sponsorisé'}
      size="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
            {error}
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Magasin *</label>
          <select
            value={formData.store_id}
            onChange={(e) => setFormData({ ...formData, store_id: e.target.value, product_id: '' })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            required
            disabled={!!sponsoredProduct}
          >
            <option value="">Sélectionner un magasin</option>
            {stores.map(store => (
              <option key={store.id} value={store.id}>{store.name}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Produit *</label>
          <select
            value={formData.product_id}
            onChange={(e) => setFormData({ ...formData, product_id: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            required
            disabled={!formData.store_id || !!sponsoredProduct}
          >
            <option value="">Sélectionner un produit</option>
            {filteredProducts.map(product => (
              <option key={product.id} value={product.id}>
                {product.name} - {formatPrice(product.price)}
              </option>
            ))}
          </select>
          {!formData.store_id && (
            <p className="mt-1 text-xs text-gray-500">Veuillez d'abord sélectionner un magasin</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Type de sponsoring *</label>
          <select
            value={formData.sponsor_type}
            onChange={(e) => setFormData({ ...formData, sponsor_type: e.target.value })}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            required
          >
            <option value="featured">Mise en avant</option>
            <option value="banner">Bannière</option>
            <option value="top_search">Top recherche</option>
            <option value="homepage">Page d'accueil</option>
            <option value="other">Autre</option>
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Prix payé (FCFA) *</label>
          <input
            type="number"
            step="0.01"
            value={formData.price_paid}
            onChange={(e) => setFormData({ ...formData, price_paid: e.target.value })}
            placeholder="0.00"
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Date de fin *</label>
          <input
            type="date"
            value={formData.end_date}
            onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
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
            <option value="paused">Suspendu</option>
          </select>
        </div>

        {sponsoredProduct && (
          <div className="bg-gray-50 p-4 rounded-lg space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Impressions:</span>
              <span className="font-semibold">{sponsoredProduct.impressions || 0}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Clics:</span>
              <span className="font-semibold">{sponsoredProduct.clicks || 0}</span>
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
            {loading ? 'Enregistrement...' : (sponsoredProduct ? 'Enregistrer' : 'Créer')}
          </button>
        </div>
      </form>
    </Modal>
  );
};

export default SponsoredProductModal;

