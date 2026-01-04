import { useState, useEffect } from 'react';
import { 
  getExpenses, 
  createExpense, 
  updateExpense, 
  deleteExpense,
  exportExpensesCSV,
  exportExpensesPDF,
  getSuppliers
} from '../../services/financeService';
import ExportButton from './ExportButton';
import { PlusIcon, PencilIcon, TrashIcon, XMarkIcon } from '@heroicons/react/24/outline';

const DepensesTab = ({ planFeatures, dateFilters, onDateFilterChange }) => {
  const [expenses, setExpenses] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [showModal, setShowModal] = useState(false);
  const [editingExpense, setEditingExpense] = useState(null);
  const [filters, setFilters] = useState({
    expense_type: '',
    payment_method: '',
    supplier_search: '',
    min_amount: '',
    max_amount: '',
  });

  const [formData, setFormData] = useState({
    expense_type: 'APPROVISIONNEMENT',
    supplier: '',
    supplier_name: '',
    reference: '',
    amount: '',
    expense_date: new Date().toISOString().split('T')[0],
    payment_method: 'CASH',
    payment_status: 'PAID',
    notes: '',
  });

  useEffect(() => {
    fetchExpenses();
    fetchSuppliers();
  }, [page, dateFilters, filters]);

  const fetchExpenses = async () => {
    try {
      setLoading(true);
      setError(null);
      const allFilters = { ...dateFilters, ...filters };
      const response = await getExpenses(allFilters, page);
      setExpenses(response.results || []);
      setTotalPages(Math.ceil((response.count || 0) / 50));
    } catch (err) {
      console.error('Erreur lors du chargement des dépenses:', err);
      setError(err.message || "Erreur lors du chargement des dépenses");
    } finally {
      setLoading(false);
    }
  };

  const fetchSuppliers = async () => {
    try {
      const response = await getSuppliers({ is_active: 'true' });
      setSuppliers(response.results || response || []);
    } catch (err) {
      console.error('Erreur lors du chargement des fournisseurs:', err);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setPage(1);
  };

  const handleDateChange = (key, value) => {
    onDateFilterChange({ [key]: value });
    setPage(1);
  };

  const resetFilters = () => {
    setFilters({
      expense_type: '',
      payment_method: '',
      supplier_search: '',
      min_amount: '',
      max_amount: '',
    });
    onDateFilterChange({ date_from: '', date_to: '' });
    setPage(1);
  };

  const openCreateModal = () => {
    setEditingExpense(null);
    setFormData({
      expense_type: 'APPROVISIONNEMENT',
      supplier: '',
      supplier_name: '',
      reference: '',
      amount: '',
      expense_date: new Date().toISOString().split('T')[0],
      payment_method: 'CASH',
      payment_status: 'PAID',
      notes: '',
    });
    setShowModal(true);
  };

  const openEditModal = (expense) => {
    setEditingExpense(expense);
    setFormData({
      expense_type: expense.expense_type,
      supplier: expense.supplier || '',
      supplier_name: expense.supplier_name || '',
      reference: expense.reference || '',
      amount: expense.amount,
      expense_date: expense.expense_date,
      payment_method: expense.payment_method,
      payment_status: expense.payment_status,
      notes: expense.notes || '',
    });
    setShowModal(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingExpense) {
        await updateExpense(editingExpense.id, formData);
      } else {
        await createExpense(formData);
      }
      setShowModal(false);
      fetchExpenses();
    } catch (err) {
      console.error('Erreur lors de l\'enregistrement:', err);
      alert(err.message || "Erreur lors de l'enregistrement");
    }
  };

  const handleDelete = async (expenseId) => {
    if (!confirm('Êtes-vous sûr de vouloir supprimer cette dépense ?')) return;
    
    try {
      await deleteExpense(expenseId);
      fetchExpenses();
    } catch (err) {
      console.error('Erreur lors de la suppression:', err);
      alert(err.message || "Erreur lors de la suppression");
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'decimal',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount) + ' F';
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('fr-FR');
  };

  const expenseTypes = [
    { value: 'APPROVISIONNEMENT', label: 'Approvisionnement' },
    { value: 'LOGISTIQUE', label: 'Logistique & Transport' },
    { value: 'PERSONNEL', label: 'Personnel' },
    { value: 'LOYER', label: 'Loyer & Charges' },
    { value: 'MARKETING', label: 'Marketing & Publicité' },
    { value: 'AUTRE', label: 'Autre' },
  ];

  const paymentMethods = [
    { value: 'CASH', label: 'Espèces' },
    { value: 'MOMO', label: 'Mobile Money' },
    { value: 'BANK_TRANSFER', label: 'Virement' },
    { value: 'CHECK', label: 'Chèque' },
    { value: 'CARD', label: 'Carte' },
    { value: 'AUTRE', label: 'Autre' },
  ];

  return (
    <div className="space-y-6">
      {/* Filters & Actions */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Dépenses</h3>
          <button
            onClick={openCreateModal}
            className="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
          >
            <PlusIcon className="-ml-1 mr-2 h-5 w-5" />
            Nouvelle dépense
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Date Filters */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Date début</label>
            <input
              type="date"
              value={dateFilters.date_from}
              onChange={(e) => handleDateChange('date_from', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Date fin</label>
            <input
              type="date"
              value={dateFilters.date_to}
              onChange={(e) => handleDateChange('date_to', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>

          {/* Expense Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
            <select
              value={filters.expense_type}
              onChange={(e) => handleFilterChange('expense_type', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              <option value="">Tous</option>
              {expenseTypes.map(type => (
                <option key={type.value} value={type.value}>{type.label}</option>
              ))}
            </select>
          </div>

          {/* Payment Method */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Paiement</label>
            <select
              value={filters.payment_method}
              onChange={(e) => handleFilterChange('payment_method', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
            >
              <option value="">Tous</option>
              {paymentMethods.map(method => (
                <option key={method.value} value={method.value}>{method.label}</option>
              ))}
            </select>
          </div>

          {/* Supplier Search */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Fournisseur</label>
            <input
              type="text"
              value={filters.supplier_search}
              onChange={(e) => handleFilterChange('supplier_search', e.target.value)}
              placeholder="Nom du fournisseur..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>

          {/* Amount Range */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Montant min</label>
            <input
              type="number"
              value={filters.min_amount}
              onChange={(e) => handleFilterChange('min_amount', e.target.value)}
              placeholder="0"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Montant max</label>
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
          <button onClick={resetFilters} className="text-sm text-gray-600 hover:text-gray-900 underline">
            Réinitialiser les filtres
          </button>

          <div className="flex gap-2">
            <ExportButton
              type="csv"
              onExport={exportExpensesCSV}
              filename={`depenses_${new Date().toISOString().split('T')[0]}`}
              planFeatures={planFeatures}
              filters={{ ...dateFilters, ...filters }}
            />
            <ExportButton
              type="pdf"
              onExport={exportExpensesPDF}
              filename={`depenses_${new Date().toISOString().split('T')[0]}`}
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

      {/* Expenses Table */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fournisseur</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Référence</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Montant</th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Paiement</th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Auto</th>
                <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase">Actions</th>
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
              ) : expenses.length === 0 ? (
                <tr>
                  <td colSpan="8" className="px-6 py-4 text-center text-gray-500">
                    Aucune dépense trouvée
                  </td>
                </tr>
              ) : (
                expenses.map((expense) => (
                  <tr key={expense.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {formatDate(expense.expense_date)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {expenseTypes.find(t => t.value === expense.expense_type)?.label || expense.expense_type}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {expense.supplier_display || '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {expense.reference || '—'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium text-red-600">
                      {formatCurrency(expense.amount)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-900">
                      {paymentMethods.find(m => m.value === expense.payment_method)?.label || expense.payment_method}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center">
                      {expense.b2b_order ? (
                        <span className="px-2 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">
                          Auto
                        </span>
                      ) : (
                        <span className="px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-800">
                          Manuel
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-center text-sm">
                      <button
                        onClick={() => openEditModal(expense)}
                        disabled={!!expense.b2b_order}
                        className="text-blue-600 hover:text-blue-900 mr-3 disabled:opacity-50 disabled:cursor-not-allowed"
                        title={expense.b2b_order ? "Dépense auto-trackée (non modifiable)" : "Modifier"}
                      >
                        <PencilIcon className="h-5 w-5" />
                      </button>
                      <button
                        onClick={() => handleDelete(expense.id)}
                        disabled={!!expense.b2b_order}
                        className="text-red-600 hover:text-red-900 disabled:opacity-50 disabled:cursor-not-allowed"
                        title={expense.b2b_order ? "Dépense auto-trackée (non supprimable)" : "Supprimer"}
                      >
                        <TrashIcon className="h-5 w-5" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="bg-white px-4 py-3 flex items-center justify-between border-t border-gray-200">
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
              <p className="text-sm text-gray-700">
                Page <span className="font-medium">{page}</span> sur <span className="font-medium">{totalPages}</span>
              </p>
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
        )}
      </div>

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-full max-w-2xl shadow-lg rounded-md bg-white">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-900">
                {editingExpense ? 'Modifier la dépense' : 'Nouvelle dépense'}
              </h3>
              <button onClick={() => setShowModal(false)} className="text-gray-400 hover:text-gray-600">
                <XMarkIcon className="h-6 w-6" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Expense Type */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Type de dépense *</label>
                  <select
                    value={formData.expense_type}
                    onChange={(e) => setFormData({ ...formData, expense_type: e.target.value })}
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  >
                    {expenseTypes.map(type => (
                      <option key={type.value} value={type.value}>{type.label}</option>
                    ))}
                  </select>
                </div>

                {/* Supplier */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Fournisseur</label>
                  <select
                    value={formData.supplier}
                    onChange={(e) => setFormData({ ...formData, supplier: e.target.value, supplier_name: '' })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  >
                    <option value="">-- Sélectionner --</option>
                    {suppliers.map(supplier => (
                      <option key={supplier.id} value={supplier.id}>{supplier.name}</option>
                    ))}
                  </select>
                </div>

                {/* Supplier Name (if no supplier selected) */}
                {!formData.supplier && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Nom du fournisseur</label>
                    <input
                      type="text"
                      value={formData.supplier_name}
                      onChange={(e) => setFormData({ ...formData, supplier_name: e.target.value })}
                      placeholder="Nom du fournisseur..."
                      className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                    />
                  </div>
                )}

                {/* Reference */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Référence</label>
                  <input
                    type="text"
                    value={formData.reference}
                    onChange={(e) => setFormData({ ...formData, reference: e.target.value })}
                    placeholder="Facture, bon de commande..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  />
                </div>

                {/* Amount */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Montant (FCFA) *</label>
                  <input
                    type="number"
                    value={formData.amount}
                    onChange={(e) => setFormData({ ...formData, amount: e.target.value })}
                    required
                    min="0"
                    step="1"
                    placeholder="0"
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  />
                </div>

                {/* Date */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Date *</label>
                  <input
                    type="date"
                    value={formData.expense_date}
                    onChange={(e) => setFormData({ ...formData, expense_date: e.target.value })}
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  />
                </div>

                {/* Payment Method */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Méthode de paiement *</label>
                  <select
                    value={formData.payment_method}
                    onChange={(e) => setFormData({ ...formData, payment_method: e.target.value })}
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  >
                    {paymentMethods.map(method => (
                      <option key={method.value} value={method.value}>{method.label}</option>
                    ))}
                  </select>
                </div>

                {/* Payment Status */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Statut paiement *</label>
                  <select
                    value={formData.payment_status}
                    onChange={(e) => setFormData({ ...formData, payment_status: e.target.value })}
                    required
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                  >
                    <option value="PAID">Payé</option>
                    <option value="PENDING">En attente</option>
                    <option value="PARTIAL">Partiel</option>
                  </select>
                </div>
              </div>

              {/* Notes */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  rows="3"
                  placeholder="Notes additionnelles..."
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-green-500"
                />
              </div>

              {/* Actions */}
              <div className="flex justify-end gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                >
                  {editingExpense ? 'Mettre à jour' : 'Créer'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default DepensesTab;

