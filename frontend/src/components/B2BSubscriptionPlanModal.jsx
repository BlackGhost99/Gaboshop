import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import {
  createB2BSubscriptionPlan,
  updateB2BSubscriptionPlan,
  getB2BSubscriptionPlanDetail
} from '../services/adminService';

/**
 * Modal pour créer/modifier un plan d'abonnement B2B
 */
const B2BSubscriptionPlanModal = ({ isOpen, onClose, planId = null, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeSection, setActiveSection] = useState('general');
  
  // Form state
  const [formData, setFormData] = useState({
    name: '',
    slug: '',
    plan_type: 'free',
    price: 0,
    applies_to: 'b2b_wholesaler',
    description: '',
    tagline: '',
    is_active: true,
    is_popular: false,
    display_order: 0,
    
    // Limites
    max_b2b_products: null,
    max_b2c_buyers: null,
    max_monthly_orders: null,
    
    // Distribution & visibilité
    catalog_priority: 0,
    featured_in_catalog: false,
    
    // Fonctionnalités
    can_offer_bulk_discounts: true,
    can_view_detailed_reports: false,
    has_priority_support: false,
    can_create_promotions: false,
    has_api_access: false,
    
    // Commissions
    commission_reduction_percent: 0,
    
    // Finance
    can_view_finance_basic: true,
    can_view_finance_detailed: false,
    can_export_finance_csv: false,
    can_export_finance_pdf: false,
    finance_history_limit_days: 30,
    
    // Custom features
    custom_features: []
  });

  useEffect(() => {
    if (planId && isOpen) {
      loadPlan();
    } else if (isOpen) {
      // Reset form for new plan
      setFormData({
        name: '',
        slug: '',
        plan_type: 'free',
        price: 0,
        applies_to: 'b2b_wholesaler',
        description: '',
        tagline: '',
        is_active: true,
        is_popular: false,
        display_order: 0,
        max_b2b_products: null,
        max_b2c_buyers: null,
        max_monthly_orders: null,
        catalog_priority: 0,
        featured_in_catalog: false,
        can_offer_bulk_discounts: true,
        can_view_detailed_reports: false,
        has_priority_support: false,
        can_create_promotions: false,
        has_api_access: false,
        commission_reduction_percent: 0,
        can_view_finance_basic: true,
        can_view_finance_detailed: false,
        can_export_finance_csv: false,
        can_export_finance_pdf: false,
        finance_history_limit_days: 30,
        custom_features: []
      });
    }
  }, [planId, isOpen]);

  const loadPlan = async () => {
    try {
      const res = await getB2BSubscriptionPlanDetail(planId);
      if (res?.success && res?.data) {
        setFormData(res.data);
      }
    } catch (err) {
      setError('Erreur lors du chargement du plan');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      let res;
      if (planId) {
        res = await updateB2BSubscriptionPlan(planId, formData);
      } else {
        res = await createB2BSubscriptionPlan(formData);
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

  const sections = [
    { id: 'general', label: 'Informations générales' },
    { id: 'limits', label: 'Limites & Quotas' },
    { id: 'visibility', label: 'Distribution & Visibilité' },
    { id: 'features', label: 'Fonctionnalités' },
    { id: 'commissions', label: 'Commissions' },
    { id: 'finance', label: 'Finance' },
  ];

  if (!isOpen) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={planId ? 'Modifier le plan B2B' : 'Créer un plan B2B'}
      size="xl"
    >
      <form onSubmit={handleSubmit} className="space-y-6">
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm">
            {error}
          </div>
        )}

        {/* Section Navigation */}
        <div className="flex flex-wrap gap-2 border-b border-gray-200 pb-3">
          {sections.map(section => (
            <button
              key={section.id}
              type="button"
              onClick={() => setActiveSection(section.id)}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors ${
                activeSection === section.id
                  ? 'bg-indigo-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {section.label}
            </button>
          ))}
        </div>

        {/* General Section */}
        {activeSection === 'general' && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
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
                <label className="block text-sm font-semibold text-gray-700 mb-1">Slug *</label>
                <input
                  type="text"
                  value={formData.slug}
                  onChange={(e) => updateField('slug', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  required
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Type de plan *</label>
                <select
                  value={formData.plan_type}
                  onChange={(e) => updateField('plan_type', e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  required
                >
                  <option value="free">Free</option>
                  <option value="pro">Pro</option>
                  <option value="business">Business</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Prix mensuel (FCFA) *</label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={formData.price}
                  onChange={(e) => updateField('price', parseFloat(e.target.value) || 0)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  required
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">Tagline</label>
              <input
                type="text"
                value={formData.tagline}
                onChange={(e) => updateField('tagline', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                placeholder="Ex: Idéal pour débuter"
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
            <div className="grid grid-cols-3 gap-4">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={formData.is_active}
                  onChange={(e) => updateField('is_active', e.target.checked)}
                  className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                />
                <label htmlFor="is_active" className="text-sm text-gray-700">Actif</label>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_popular"
                  checked={formData.is_popular}
                  onChange={(e) => updateField('is_popular', e.target.checked)}
                  className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
                />
                <label htmlFor="is_popular" className="text-sm text-gray-700">Populaire</label>
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Ordre d'affichage</label>
                <input
                  type="number"
                  min="0"
                  value={formData.display_order}
                  onChange={(e) => updateField('display_order', parseInt(e.target.value) || 0)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            </div>
          </div>
        )}

        {/* Limits Section */}
        {activeSection === 'limits' && (
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Max produits B2B (null = illimité)</label>
                <input
                  type="number"
                  min="0"
                  value={formData.max_b2b_products || ''}
                  onChange={(e) => updateField('max_b2b_products', e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  placeholder="Illimité"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Max magasins B2C clients (null = illimité)</label>
                <input
                  type="number"
                  min="0"
                  value={formData.max_b2c_buyers || ''}
                  onChange={(e) => updateField('max_b2c_buyers', e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  placeholder="Illimité"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Max commandes/mois (null = illimité)</label>
                <input
                  type="number"
                  min="0"
                  value={formData.max_monthly_orders || ''}
                  onChange={(e) => updateField('max_monthly_orders', e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  placeholder="Illimité"
                />
              </div>
            </div>
          </div>
        )}

        {/* Visibility Section */}
        {activeSection === 'visibility' && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">Priorité catalogue (Distribution prioritaire)</label>
              <input
                type="number"
                min="0"
                value={formData.catalog_priority}
                onChange={(e) => updateField('catalog_priority', parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="featured_in_catalog"
                checked={formData.featured_in_catalog}
                onChange={(e) => updateField('featured_in_catalog', e.target.checked)}
                className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="featured_in_catalog" className="text-sm text-gray-700">Référencé en tête du catalogue (Grossiste recommandé)</label>
            </div>
          </div>
        )}

        {/* Features Section */}
        {activeSection === 'features' && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="can_offer_bulk_discounts"
                checked={formData.can_offer_bulk_discounts}
                onChange={(e) => updateField('can_offer_bulk_discounts', e.target.checked)}
                className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="can_offer_bulk_discounts" className="text-sm text-gray-700">Peut proposer des remises pour achats en gros</label>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="can_view_detailed_reports"
                checked={formData.can_view_detailed_reports}
                onChange={(e) => updateField('can_view_detailed_reports', e.target.checked)}
                className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="can_view_detailed_reports" className="text-sm text-gray-700">Peut voir les détails par commande et catégorie</label>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="has_priority_support"
                checked={formData.has_priority_support}
                onChange={(e) => updateField('has_priority_support', e.target.checked)}
                className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="has_priority_support" className="text-sm text-gray-700">Support prioritaire</label>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="can_create_promotions"
                checked={formData.can_create_promotions}
                onChange={(e) => updateField('can_create_promotions', e.target.checked)}
                className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="can_create_promotions" className="text-sm text-gray-700">Peut créer des promotions B2B</label>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="has_api_access"
                checked={formData.has_api_access}
                onChange={(e) => updateField('has_api_access', e.target.checked)}
                className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="has_api_access" className="text-sm text-gray-700">Accès à l'API pour intégrations</label>
            </div>
          </div>
        )}

        {/* Commissions Section */}
        {activeSection === 'commissions' && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">Réduction commission (%)</label>
              <input
                type="number"
                min="0"
                max="100"
                step="0.01"
                value={formData.commission_reduction_percent}
                onChange={(e) => updateField('commission_reduction_percent', parseFloat(e.target.value) || 0)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              />
              <p className="text-xs text-gray-500 mt-1">Ex: 10 pour -10%</p>
            </div>
          </div>
        )}

        {/* Finance Section */}
        {activeSection === 'finance' && (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="can_view_finance_basic"
                checked={formData.can_view_finance_basic}
                onChange={(e) => updateField('can_view_finance_basic', e.target.checked)}
                className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="can_view_finance_basic" className="text-sm text-gray-700">Peut voir les rapports financiers basiques</label>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="can_view_finance_detailed"
                checked={formData.can_view_finance_detailed}
                onChange={(e) => updateField('can_view_finance_detailed', e.target.checked)}
                className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="can_view_finance_detailed" className="text-sm text-gray-700">Peut voir les détails financiers</label>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="can_export_finance_csv"
                checked={formData.can_export_finance_csv}
                onChange={(e) => updateField('can_export_finance_csv', e.target.checked)}
                className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="can_export_finance_csv" className="text-sm text-gray-700">Peut exporter finance en CSV</label>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="can_export_finance_pdf"
                checked={formData.can_export_finance_pdf}
                onChange={(e) => updateField('can_export_finance_pdf', e.target.checked)}
                className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="can_export_finance_pdf" className="text-sm text-gray-700">Peut exporter finance en PDF</label>
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">Limite historique finance (jours, null = illimité)</label>
              <input
                type="number"
                min="0"
                value={formData.finance_history_limit_days || ''}
                onChange={(e) => updateField('finance_history_limit_days', e.target.value ? parseInt(e.target.value) : null)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                placeholder="Illimité"
              />
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-3 pt-4 border-t border-gray-200">
          <button
            type="submit"
            disabled={loading}
            className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? 'Enregistrement...' : planId ? 'Mettre à jour' : 'Créer'}
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

export default B2BSubscriptionPlanModal;

