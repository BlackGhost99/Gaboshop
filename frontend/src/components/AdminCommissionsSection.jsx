import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import ConfirmModal from './ConfirmModal';
import {
  getCommissions,
  settleCommission,
  getCategoryCommissionLogs
} from '../services/adminService';
import { getStoresListAdmin } from '../services/adminService';

/**
 * Section Admin pour gérer les commissions
 */
const AdminCommissionsSection = () => {
  const [activeSubTab, setActiveSubTab] = useState('commissions');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Commissions
  const [commissions, setCommissions] = useState([]);
  const [selectedCommission, setSelectedCommission] = useState(null);
  const [commissionFilters, setCommissionFilters] = useState({
    store_id: '',
    is_settled: '',
    date_from: '',
    date_to: ''
  });
  const [confirmSettleCommission, setConfirmSettleCommission] = useState(null);

  // Category Commission Logs
  const [commissionLogs, setCommissionLogs] = useState([]);
  const [logFilters, setLogFilters] = useState({
    category_id: '',
    date_from: '',
    date_to: ''
  });

  const [stores, setStores] = useState([]);

  useEffect(() => {
    loadStores();
  }, []);

  useEffect(() => {
    loadData();
  }, [activeSubTab, commissionFilters, logFilters]);

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

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      if (activeSubTab === 'commissions') {
        const res = await getCommissions(commissionFilters);
        if (res?.success) setCommissions(res.data || []);
      } else if (activeSubTab === 'logs') {
        const res = await getCategoryCommissionLogs(logFilters);
        if (res?.success) setCommissionLogs(res.data || []);
      }
    } catch (err) {
      setError(err?.message || 'Erreur lors du chargement');
    } finally {
      setLoading(false);
    }
  };

  const handleSettleCommission = async () => {
    if (!confirmSettleCommission) return;
    try {
      const res = await settleCommission(confirmSettleCommission);
      if (res?.success) {
        setSuccess('Commission marquée comme réglée');
        loadData();
      } else {
        setError(res?.error || 'Erreur lors du règlement');
      }
    } catch (err) {
      setError(err?.message || 'Erreur lors du règlement');
    }
    setConfirmSettleCommission(null);
  };

  const formatPrice = (price) => {
    return new Intl.NumberFormat('fr-FR').format(price) + ' FCFA';
  };

  const formatDate = (dateString) => {
    if (!dateString) return '—';
    return new Date(dateString).toLocaleDateString('fr-FR');
  };

  const subTabs = [
    { id: 'commissions', label: 'Commissions' },
    { id: 'logs', label: 'Historique Changements' },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Gestion des Commissions</h2>
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

      {/* Commissions */}
      {!loading && activeSubTab === 'commissions' && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-4">
            <select
              value={commissionFilters.store_id}
              onChange={(e) => setCommissionFilters({ ...commissionFilters, store_id: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">Tous les magasins</option>
              {stores.map(store => (
                <option key={store.id} value={store.id}>{store.name}</option>
              ))}
            </select>
            <select
              value={commissionFilters.is_settled}
              onChange={(e) => setCommissionFilters({ ...commissionFilters, is_settled: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">Tous les statuts</option>
              <option value="true">Réglées</option>
              <option value="false">En attente</option>
            </select>
            <input
              type="date"
              placeholder="Date début"
              value={commissionFilters.date_from}
              onChange={(e) => setCommissionFilters({ ...commissionFilters, date_from: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            />
            <input
              type="date"
              placeholder="Date fin"
              value={commissionFilters.date_to}
              onChange={(e) => setCommissionFilters({ ...commissionFilters, date_to: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div className="bg-white shadow-sm rounded-lg border border-gray-100 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">N° Commande</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Magasin</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Montant commande</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Taux (%)</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Commission</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {commissions.length === 0 ? (
                  <tr>
                    <td colSpan="8" className="px-6 py-8 text-center text-gray-500">
                      Aucune commission trouvée
                    </td>
                  </tr>
                ) : (
                  commissions.map(commission => (
                    <tr key={commission.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {commission.order_number || '—'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {commission.store_name || '—'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {formatPrice(commission.order_amount)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {commission.commission_rate}%
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">
                        {formatPrice(commission.commission_amount)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(commission.created_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                          commission.is_settled ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                        }`}>
                          {commission.is_settled ? 'Réglée' : 'En attente'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        {!commission.is_settled && (
                          <button
                            onClick={() => setConfirmSettleCommission(commission.id)}
                            className="text-green-600 hover:text-green-900"
                          >
                            Marquer comme réglée
                          </button>
                        )}
                        <button
                          onClick={() => setSelectedCommission(commission)}
                          className="text-indigo-600 hover:text-indigo-900 ml-4"
                        >
                          Détail
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Category Commission Logs */}
      {!loading && activeSubTab === 'logs' && (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-4">
            <input
              type="date"
              placeholder="Date début"
              value={logFilters.date_from}
              onChange={(e) => setLogFilters({ ...logFilters, date_from: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            />
            <input
              type="date"
              placeholder="Date fin"
              value={logFilters.date_to}
              onChange={(e) => setLogFilters({ ...logFilters, date_to: e.target.value })}
              className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div className="bg-white shadow-sm rounded-lg border border-gray-100 overflow-hidden">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Catégorie</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ancien taux</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Nouveau taux</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Modifié par</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Note</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {commissionLogs.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="px-6 py-8 text-center text-gray-500">
                      Aucun changement trouvé
                    </td>
                  </tr>
                ) : (
                  commissionLogs.map(log => (
                    <tr key={log.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {log.category_name || '—'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {log.old_rate !== null && log.old_rate !== undefined ? `${log.old_rate}%` : '—'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">
                        {log.new_rate}%
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {log.changed_by_name || 'Système'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(log.created_at)}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {log.note || '—'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modals */}
      <ConfirmModal
        isOpen={!!confirmSettleCommission}
        onClose={() => setConfirmSettleCommission(null)}
        title="Marquer comme réglée"
        message="Êtes-vous sûr de vouloir marquer cette commission comme réglée ?"
        onConfirm={handleSettleCommission}
        variant="info"
      />

      {/* Commission Detail Modal */}
      {selectedCommission && (
        <Modal
          isOpen={!!selectedCommission}
          onClose={() => setSelectedCommission(null)}
          title={`Commission ${selectedCommission.order_number || selectedCommission.id}`}
          size="md"
        >
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500">Magasin</p>
                <p className="font-semibold">{selectedCommission.store_name || '—'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">N° Commande</p>
                <p className="font-semibold">{selectedCommission.order_number || '—'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Montant commande</p>
                <p className="font-semibold">{formatPrice(selectedCommission.order_amount)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Taux commission</p>
                <p className="font-semibold">{selectedCommission.commission_rate}%</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Montant commission</p>
                <p className="font-semibold text-indigo-600">{formatPrice(selectedCommission.commission_amount)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Statut</p>
                <p className="font-semibold">
                  <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                    selectedCommission.is_settled ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                  }`}>
                    {selectedCommission.is_settled ? 'Réglée' : 'En attente'}
                  </span>
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Date</p>
                <p className="font-semibold">{formatDate(selectedCommission.created_at)}</p>
              </div>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};

export default AdminCommissionsSection;

