import { useState, useEffect } from 'react';
import { getSales, exportSalesCSV, exportSalesPDF } from '../../services/financeService';
import ExportButton from './ExportButton';
import { MagnifyingGlassIcon } from '@heroicons/react/24/outline';

const RevenusTab = ({ planFeatures, dateFilters, onDateFilterChange }) => {
  const [sales, setSales] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filters, setFilters] = useState({
    status: '',
    payment_method: '',
    is_b2b: '',
    search: '',
    min_amount: '',
    max_amount: '',
  });

  useEffect(() => {
    fetchSales();
  }, [page, dateFilters, filters]);

  const fetchSales = async () => {
    try {
      setLoading(true);
      setError(null);
      const allFilters = { ...dateFilters, ...filters };
      const response = await getSales(allFilters, page);
      setSales(response.results || []);
      setTotalPages(Math.ceil((response.count || 0) / 50));
    } catch (err) {
      console.error('Erreur lors du chargement des ventes:', err);
      setError(err.message || "Erreur lors du chargement des ventes");
    } finally {
      setLoading(false);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPage(1); // Reset to first page
  };

  const handleDateChange = (key, value) => {
    onDateFilterChange({ [key]: value });
    setPage(1);
  };

  const resetFilters = () => {
    setFilters({
      status: '',
      payment_method: '',
      is_b2b: '',
      search: '',
      min_amount: '',
      max_amount: '',
    });
    onDateFilterChange({ date_from: '', date_to: '' });
    setPage(1);
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'decimal',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount) + ' F';
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusBadge = (status) => {
    const badges = {
      delivered: 'bg-green-100 text-green-800',
      confirmed: 'bg-blue-100 text-blue-800',
      in_preparation: 'bg-yellow-100 text-yellow-800',
      pending: 'bg-gray-100 text-gray-800',
      cancelled: 'bg-red-100 text-red-800',
    };
    return badges[status] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Filtres</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Date From */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Date début
            </label>
            <input
              type="date"
              value={dateFilters.date_from}
              onChange={(e) => handleDateChange('date_from', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>

          {/* Date To */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Date fin
            </label>
            <input
              type="date"
              value={dateFilters.date_to}
              onChange={(e) => handleDateChange('date_to', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>

          {/* Status */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Statut
            </label>
            <select
              value={filters.status}
              onChange={(e) => handleFilterChange('status', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              <option value="">Tous</option>
              <option value="delivered">Livré</option>
              <option value="confirmed">Confirmé</option>
              <option value="in_preparation">En préparation</option>
              <option value="pending">En attente</option>
              <option value="cancelled">Annulé</option>
            </select>
          </div>

          {/* Payment Method */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Paiement
            </label>
            <select
              value={filters.payment_method}
              onChange={(e) => handleFilterChange('payment_method', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              <option value="">Tous</option>
              <option value="momo">Mobile Money</option>
              <option value="cash">Espèces</option>
              <option value="card">Carte</option>
            </select>
          </div>

          {/* Channel (B2C/B2B) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Type
            </label>
            <select
              value={filters.is_b2b}
              onChange={(e) => handleFilterChange('is_b2b', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              <option value="">Tous</option>
              <option value="false">B2C</option>
              <option value="true">B2B</option>
            </select>
          </div>

          {/* Search */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Recherche
            </label>
            <div className="relative">
              <input
                type="text"
                value={filters.search}
                onChange={(e) => handleFilterChange('search', e.target.value)}
                placeholder="N° commande, client..."
                className="w-full px-3 py-2 pl-10 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
              />
              <MagnifyingGlassIcon className="absolute left-3 top-2.5 h-5 w-5 text-gray-400" />
            </div>
          </div>

          {/* Min Amount */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Montant min
            </label>
            <input
              type="number"
              value={filters.min_amount}
              onChange={(e) => handleFilterChange('min_amount', e.target.value)}
              placeholder="0"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>

          {/* Max Amount */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Montant max
            </label>
            <input
              type="number"
              value={filters.max_amount}
              onChange={(e) => handleFilterChange('max_amount', e.target.value)}
              placeholder="∞"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>
        </div>

        {/* Actions */}
        <div className="mt-4 flex justify-between items-center">
          <button
            onClick={resetFilters}
            className="text-sm text-gray-600 hover:text-gray-900 underline"
          >
            Réinitialiser les filtres
          </button>

          <div className="flex gap-2">
            <ExportButton
              type="csv"
              onExport={exportSalesCSV}
              filename={`ventes_${new Date().toISOString().split('T')[0]}`}
              planFeatures={planFeatures}
              filters={{ ...dateFilters, ...filters }}
            />
            <ExportButton
              type="pdf"
              onExport={exportSalesPDF}
              filename={`ventes_${new Date().toISOString().split('T')[0]}`}
              planFeatures={planFeatures}
              filters={{ ...dateFilters, ...filters }}
            />
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Sales Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Date
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  N° Commande
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Client
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Montant HT
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Commission
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Net
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Statut
                </th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {loading ? (
                <tr>
                  <td colSpan="8" className="px-6 py-4 text-center">
                    <div className="flex justify-center">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-green-600"></div>
                    </div>
                  </td>
                </tr>
              ) : sales.length === 0 ? (
                <tr>
                  <td colSpan="8" className="px-6 py-4 text-center text-gray-500">
                    Aucune vente trouvée
                  </td>
                </tr>
              ) : (
                sales.map((sale) => (
                  <tr key={sale.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatDate(sale.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {sale.order_number}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {sale.client_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-gray-900">
                      {formatCurrency(sale.items_total)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right text-red-600">
                      {formatCurrency(sale.commission_amount)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium text-green-600">
                      {formatCurrency(sale.net_amount)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusBadge(sale.status)}`}>
                        {sale.status_display}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      <span className={`px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full ${
                        sale.is_b2b ? 'bg-yellow-100 text-yellow-800' : 'bg-blue-100 text-blue-800'
                      }`}>
                        {sale.is_b2b ? 'B2B' : 'B2C'}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200 sm:px-6">
            <div className="flex-1 flex justify-between sm:hidden">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
              >
                Précédent
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
              >
                Suivant
              </button>
            </div>
            <div className="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
              <div>
                <p className="text-sm text-gray-700">
                  Page <span className="font-medium">{page}</span> sur{' '}
                  <span className="font-medium">{totalPages}</span>
                </p>
              </div>
              <div>
                <nav className="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                  >
                    ←
                  </button>
                  <button
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                  >
                    →
                  </button>
                </nav>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default RevenusTab;

