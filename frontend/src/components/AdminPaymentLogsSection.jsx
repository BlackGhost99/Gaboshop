import React, { useState, useEffect } from 'react';
import Modal from './Modal';
import {
  getPaymentCallbacks,
  getPaymentCallbackDetail
} from '../services/adminService';

/**
 * Section Admin pour visualiser les logs de paiement (PaymentCallbackLog)
 */
const AdminPaymentLogsSection = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [logs, setLogs] = useState([]);
  const [selectedLog, setSelectedLog] = useState(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);

  const [filters, setFilters] = useState({
    order_id: '',
    processed: '',
    signature_valid: '',
    transaction_id: '',
    date_from: '',
    date_to: ''
  });

  useEffect(() => {
    loadLogs();
  }, [filters]);

  const loadLogs = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getPaymentCallbacks(filters);
      if (res?.success) {
        setLogs(res.data || []);
      } else {
        setError(res?.error || 'Erreur lors du chargement');
      }
    } catch (err) {
      setError(err?.message || 'Erreur lors du chargement');
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetail = async (logId) => {
    try {
      const res = await getPaymentCallbackDetail(logId);
      if (res?.success) {
        setSelectedLog(res.data);
        setIsDetailModalOpen(true);
      } else {
        setError(res?.error || 'Erreur lors du chargement du détail');
      }
    } catch (err) {
      setError(err?.message || 'Erreur lors du chargement du détail');
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return '—';
    return new Date(dateString).toLocaleString('fr-FR');
  };

  const getStatusColor = (status) => {
    if (status >= 200 && status < 300) return 'bg-green-100 text-green-800';
    if (status >= 400 && status < 500) return 'bg-yellow-100 text-yellow-800';
    if (status >= 500) return 'bg-red-100 text-red-800';
    return 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Logs de Paiement (Callbacks)</h2>
      </div>

      {/* Messages */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded text-sm flex justify-between items-center">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-red-600 hover:text-red-800">✕</button>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white p-4 rounded-lg border border-gray-200">
        <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
          <input
            type="number"
            placeholder="ID Commande"
            value={filters.order_id}
            onChange={(e) => setFilters({ ...filters, order_id: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
          />
          <input
            type="text"
            placeholder="Transaction ID"
            value={filters.transaction_id}
            onChange={(e) => setFilters({ ...filters, transaction_id: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
          />
          <select
            value={filters.processed}
            onChange={(e) => setFilters({ ...filters, processed: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Tous (traités)</option>
            <option value="true">Traité</option>
            <option value="false">Non traité</option>
          </select>
          <select
            value={filters.signature_valid}
            onChange={(e) => setFilters({ ...filters, signature_valid: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">Tous (signature)</option>
            <option value="true">Valide</option>
            <option value="false">Invalide</option>
          </select>
          <input
            type="date"
            placeholder="Date début"
            value={filters.date_from}
            onChange={(e) => setFilters({ ...filters, date_from: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
          />
          <input
            type="date"
            placeholder="Date fin"
            value={filters.date_to}
            onChange={(e) => setFilters({ ...filters, date_to: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500"
          />
        </div>
      </div>

      {/* Table */}
      {loading && (
        <div className="text-center py-12">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
          <p className="mt-2 text-gray-600">Chargement...</p>
        </div>
      )}

      {!loading && (
        <div className="bg-white shadow-sm rounded-lg border border-gray-100 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">N° Commande</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date réception</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Code HTTP</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Signature</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Traité</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan="7" className="px-6 py-8 text-center text-gray-500">
                    Aucun log trouvé
                  </td>
                </tr>
              ) : (
                logs.map(log => (
                  <tr key={log.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      #{log.id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {log.order_number || '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(log.received_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(log.status_code)}`}>
                        {log.status_code}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                        log.signature_valid ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {log.signature_valid ? 'Valide' : 'Invalide'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                        log.processed ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {log.processed ? 'Traité' : 'Non traité'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <button
                        onClick={() => handleViewDetail(log.id)}
                        className="text-indigo-600 hover:text-indigo-900"
                      >
                        Voir détail
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Detail Modal */}
      <Modal
        isOpen={isDetailModalOpen}
        onClose={() => setIsDetailModalOpen(false)}
        title={`Détail du log #${selectedLog?.id || ''}`}
        size="lg"
      >
        {selectedLog && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-500">N° Commande</p>
                <p className="font-semibold">{selectedLog.order_number || '—'}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Date réception</p>
                <p className="font-semibold">{formatDate(selectedLog.received_at)}</p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Code HTTP</p>
                <p className="font-semibold">
                  <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(selectedLog.status_code)}`}>
                    {selectedLog.status_code}
                  </span>
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Signature</p>
                <p className="font-semibold">
                  <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                    selectedLog.signature_valid ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                  }`}>
                    {selectedLog.signature_valid ? 'Valide' : 'Invalide'}
                  </span>
                </p>
              </div>
              <div>
                <p className="text-sm text-gray-500">Traité</p>
                <p className="font-semibold">
                  <span className={`px-2 py-1 text-xs font-semibold rounded-full ${
                    selectedLog.processed ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                  }`}>
                    {selectedLog.processed ? 'Traité' : 'Non traité'}
                  </span>
                </p>
              </div>
            </div>
            <div>
              <p className="text-sm text-gray-500 mb-2">Données brutes (JSON)</p>
              <pre className="bg-gray-50 p-4 rounded-lg text-xs overflow-auto max-h-96 border border-gray-200">
                {JSON.stringify(selectedLog.raw_data, null, 2)}
              </pre>
            </div>
            <div className="flex justify-end pt-4">
              <button
                onClick={() => setIsDetailModalOpen(false)}
                className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
              >
                Fermer
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default AdminPaymentLogsSection;

