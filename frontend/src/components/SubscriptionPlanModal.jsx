import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import {
  createSubscriptionPlan,
  updateSubscriptionPlan,
  getSubscriptionPlanDetail
} from '../services/adminService';

/**
 * Modal pour créer/modifier un plan d'abonnement B2C
 */
const SubscriptionPlanModal = ({ isOpen, onClose, planId = null, onSuccess }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [activeSection, setActiveSection] = useState('general');
  
  // Form state
  const [formData, setFormData] = useState({
    name: '',
    slug: '',
    plan_type: 'free',
    price: 0,
    applies_to: 'b2c',
    description: '',
    is_active: true,
    
    // Limites
    max_products: null,
    max_orders_per_month: null,
    can_sell_non_food_products: true,
    max_products_non_food: 5,
    
    // Quotas B2B
    max_b2b_suppliers: null,
    max_b2b_monthly_orders: null,
    
    // Frais de service
    service_fee_client_amount: 500,
    service_fee_to_wholesaler_amount: 1000,
    
    // Commissions
    commission_reduction_percent: 0,
    commission_rate: null,
    commission_multiplier: 1.0,
    
    // Fonctionnalités B2B
    can_access_b2b: false,
    has_b2b_visibility: false,
    
    // Visibilité B2B
    b2b_catalog_priority: 0,
    b2b_featured_access: false,
    
    // Livraison
    can_offer_express_delivery: false,
    has_advanced_delivery_tracking: false,
    
    // Rapports et Exports
    can_view_basic_reports: true,
    can_view_detailed_reports: false,
    can_export_excel: false,
    can_export_pdf: false,
    history_limit_days: 30,
    
    // Finance B2B
    can_view_finance_basic: true,
    can_view_finance_detailed: false,
    can_export_finance_csv: false,
    can_export_finance_pdf: false,
    finance_history_limit_days: 30,
    
    // Support
    support_level: 'standard',
    
    // Autres
    can_sponsor_products: false,
    has_statistics: false,
    has_custom_page: false,
    has_priority_support: false,
    priority_listing: 0,
    features_json: []
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
        applies_to: 'b2c',
        description: '',
        is_active: true,
        max_products: null,
        max_orders_per_month: null,
        can_sell_non_food_products: true,
        max_products_non_food: 5,
        max_b2b_suppliers: null,
        max_b2b_monthly_orders: null,
        service_fee_client_amount: 500,
        service_fee_to_wholesaler_amount: 1000,
        commission_reduction_percent: 0,
        commission_rate: null,
        commission_multiplier: 1.0,
        can_access_b2b: false,
        has_b2b_visibility: false,
        b2b_catalog_priority: 0,
        b2b_featured_access: false,
        can_offer_express_delivery: false,
        has_advanced_delivery_tracking: false,
        can_view_basic_reports: true,
        can_view_detailed_reports: false,
        can_export_excel: false,
        can_export_pdf: false,
        history_limit_days: 30,
        can_view_finance_basic: true,
        can_view_finance_detailed: false,
        can_export_finance_csv: false,
        can_export_finance_pdf: false,
        finance_history_limit_days: 30,
        support_level: 'standard',
        can_sponsor_products: false,
        has_statistics: false,
        has_custom_page: false,
        has_priority_support: false,
        priority_listing: 0,
        features_json: []
      });
    }
  }, [planId, isOpen]);

  const loadPlan = async () => {
    try {
      const res = await getSubscriptionPlanDetail(planId);
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
        res = await updateSubscriptionPlan(planId, formData);
      } else {
        res = await createSubscriptionPlan(formData);
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
    { id: 'limits', label: 'Limites Produits & Commandes' },
    { id: 'b2b_quotas', label: 'Quotas B2B' },
    { id: 'fees', label: 'Frais de Service' },
    { id: 'commissions', label: 'Commissions' },
    { id: 'b2b_features', label: 'Fonctionnalités B2B' },
    { id: 'b2b_visibility', label: 'Visibilité B2B' },
    { id: 'delivery', label: 'Livraison' },
    { id: 'reports', label: 'Rapports et Exports' },
    { id: 'finance', label: 'Finance B2B' },
    { id: 'support', label: 'Support' },
  ];

  if (!isOpen) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={planId ? 'Modifier le plan d\'abonnement' : 'Créer un plan d\'abonnement'}
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
              <label className="block text-sm font-semibold text-gray-700 mb-1">S'applique à *</label>
              <select
                value={formData.applies_to}
                onChange={(e) => updateField('applies_to', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              >
                <option value="b2c">B2C Store uniquement</option>
                <option value="b2b_buyer">B2B Buyer (boutique cliente)</option>
                <option value="b2b_wholesaler">B2B Grossiste</option>
                <option value="both">B2C et B2B</option>
              </select>
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
              <label htmlFor="is_active" className="text-sm text-gray-700">Plan actif</label>
            </div>
          </div>
        )}

        {/* Limits Section */}
        {activeSection === 'limits' && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Max produits (null = illimité)</label>
                <input
                  type="number"
                  min="0"
                  value={formData.max_products || ''}
                  onChange={(e) => updateField('max_products', e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  placeholder="Illimité"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Max commandes/mois (null = illimité)</label>
                <input
                  type="number"
                  min="0"
                  value={formData.max_orders_per_month || ''}
                  onChange={(e) => updateField('max_orders_per_month', e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  placeholder="Illimité"
                />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="can_sell_non_food"
                checked={formData.can_sell_non_food_products}
                onChange={(e) => updateField('can_sell_non_food_products', e.target.checked)}
                className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="can_sell_non_food" className="text-sm text-gray-700">Peut vendre des produits non alimentaires</label>
            </div>
            {formData.can_sell_non_food_products && (
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Max produits non alimentaires</label>
                <input
                  type="number"
                  min="0"
                  value={formData.max_products_non_food || ''}
                  onChange={(e) => updateField('max_products_non_food', e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                />
              </div>
            )}
          </div>
        )}

        {/* B2B Quotas Section */}
        {activeSection === 'b2b_quotas' && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Max grossistes (null = illimité)</label>
                <input
                  type="number"
                  min="0"
                  value={formData.max_b2b_suppliers || ''}
                  onChange={(e) => updateField('max_b2b_suppliers', e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  placeholder="Illimité"
                />
              </div>
              <div>
                <label className="block text-sm font-semibold text-gray-700 mb-1">Max commandes B2B/mois (null = illimité)</label>
                <input
                  type="number"
                  min="0"
                  value={formData.max_b2b_monthly_orders || ''}
                  onChange={(e) => updateField('max_b2b_monthly_orders', e.target.value ? parseInt(e.target.value) : null)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                  placeholder="Illimité"
                />
              </div>
            </div>
          </div>
        )}

        {/* Fees Section */}
        {activeSection === 'fees' && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">Frais de service client (FCFA)</label>
              <input
                type="number"
                min="0"
                value={formData.service_fee_client_amount}
                onChange={(e) => updateField('service_fee_client_amount', parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">Frais vers grossiste (FCFA)</label>
              <input
                type="number"
                min="0"
                value={formData.service_fee_to_wholesaler_amount}
                onChange={(e) => updateField('service_fee_to_wholesaler_amount', parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              />
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
                value={formData.commission_reduction_percent}
                onChange={(e) => updateField('commission_reduction_percent', parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              />
              <p className="text-xs text-gray-500 mt-1">Ex: 40 = -40%, 75 = -75%</p>
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">Taux commission spécifique (%)</label>
              <input
                type="number"
                min="0"
                max="100"
                step="0.01"
                value={formData.commission_rate || ''}
                onChange={(e) => updateField('commission_rate', e.target.value ? parseFloat(e.target.value) : null)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                placeholder="Null = taux par défaut"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">Multiplicateur commission</label>
              <input
                type="number"
                min="0"
                max="1"
                step="0.01"
                value={formData.commission_multiplier}
                onChange={(e) => updateField('commission_multiplier', parseFloat(e.target.value) || 1.0)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              />
              <p className="text-xs text-gray-500 mt-1">Ex: 0.60 = -40%, 0.25 = -75%</p>
            </div>
          </div>
        )}

        {/* B2B Features Section */}
        {activeSection === 'b2b_features' && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="can_access_b2b"
                checked={formData.can_access_b2b}
                onChange={(e) => updateField('can_access_b2b', e.target.checked)}
                className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="can_access_b2b" className="text-sm text-gray-700">Accès approvisionnement B2B</label>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="has_b2b_visibility"
                checked={formData.has_b2b_visibility}
                onChange={(e) => updateField('has_b2b_visibility', e.target.checked)}
                className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="has_b2b_visibility" className="text-sm text-gray-700">Visibilité maximale catalogue B2B</label>
            </div>
          </div>
        )}

        {/* B2B Visibility Section */}
        {activeSection === 'b2b_visibility' && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">Priorité catalogue B2B</label>
              <input
                type="number"
                min="0"
                value={formData.b2b_catalog_priority}
                onChange={(e) => updateField('b2b_catalog_priority', parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              />
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="b2b_featured_access"
                checked={formData.b2b_featured_access}
                onChange={(e) => updateField('b2b_featured_access', e.target.checked)}
                className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="b2b_featured_access" className="text-sm text-gray-700">Accès prioritaire aux grossistes mis en avant</label>
            </div>
          </div>
        )}

        {/* Delivery Section */}
        {activeSection === 'delivery' && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="can_offer_express"
                checked={formData.can_offer_express_delivery}
                onChange={(e) => updateField('can_offer_express_delivery', e.target.checked)}
                className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="can_offer_express" className="text-sm text-gray-700">Peut proposer la livraison express</label>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="has_advanced_tracking"
                checked={formData.has_advanced_delivery_tracking}
                onChange={(e) => updateField('has_advanced_delivery_tracking', e.target.checked)}
                className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="has_advanced_tracking" className="text-sm text-gray-700">Suivi détaillé des livraisons (GPS, temps réel)</label>
            </div>
          </div>
        )}

        {/* Reports Section */}
        {activeSection === 'reports' && (
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="can_view_basic_reports"
                checked={formData.can_view_basic_reports}
                onChange={(e) => updateField('can_view_basic_reports', e.target.checked)}
                className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="can_view_basic_reports" className="text-sm text-gray-700">Peut voir les rapports basiques</label>
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
                id="can_export_excel"
                checked={formData.can_export_excel}
                onChange={(e) => updateField('can_export_excel', e.target.checked)}
                className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="can_export_excel" className="text-sm text-gray-700">Peut exporter en Excel/CSV</label>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="can_export_pdf"
                checked={formData.can_export_pdf}
                onChange={(e) => updateField('can_export_pdf', e.target.checked)}
                className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="can_export_pdf" className="text-sm text-gray-700">Peut exporter en PDF</label>
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">Limite historique (jours, null = illimité)</label>
              <input
                type="number"
                min="0"
                value={formData.history_limit_days || ''}
                onChange={(e) => updateField('history_limit_days', e.target.value ? parseInt(e.target.value) : null)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
                placeholder="Illimité"
              />
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

        {/* Support Section */}
        {activeSection === 'support' && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">Niveau de support</label>
              <select
                value={formData.support_level}
                onChange={(e) => updateField('support_level', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
              >
                <option value="standard">Standard</option>
                <option value="prioritaire">Prioritaire</option>
                <option value="dedie">Dédié VIP</option>
              </select>
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
                id="can_sponsor_products"
                checked={formData.can_sponsor_products}
                onChange={(e) => updateField('can_sponsor_products', e.target.checked)}
                className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="can_sponsor_products" className="text-sm text-gray-700">Peut sponsoriser des produits</label>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="has_statistics"
                checked={formData.has_statistics}
                onChange={(e) => updateField('has_statistics', e.target.checked)}
                className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="has_statistics" className="text-sm text-gray-700">Accès aux statistiques avancées</label>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="has_custom_page"
                checked={formData.has_custom_page}
                onChange={(e) => updateField('has_custom_page', e.target.checked)}
                className="w-4 h-4 text-indigo-600 border-gray-300 rounded focus:ring-indigo-500"
              />
              <label htmlFor="has_custom_page" className="text-sm text-gray-700">Page personnalisée</label>
            </div>
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-1">Priorité dans les listings</label>
              <input
                type="number"
                min="0"
                value={formData.priority_listing}
                onChange={(e) => updateField('priority_listing', parseInt(e.target.value) || 0)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
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

export default SubscriptionPlanModal;

