import { ArrowTrendingUpIcon, ArrowTrendingDownIcon, ChartBarIcon, BanknotesIcon } from '@heroicons/react/24/outline';

const FinanceSummary = ({ summary, planFeatures, onRefresh, loading }) => {
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('fr-FR', {
      style: 'decimal',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount) + ' FCFA';
  };

  const { sales, expenses, profit_estimate, top_categories } = summary;

  return (
    <div className="space-y-6">
      {/* Main Financial Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Gross Sales */}
        <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg shadow-sm p-6 border border-green-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-green-800">CA Brut</p>
              <p className="text-2xl font-bold text-green-900 mt-2">
                {formatCurrency(sales.gross_sales)}
              </p>
            </div>
            <ArrowTrendingUpIcon className="w-10 h-10 text-green-600" />
          </div>
          <p className="text-xs text-green-700 mt-2">
            {sales.orders_count} commandes
          </p>
        </div>

        {/* Total Expenses */}
        <div className="bg-gradient-to-br from-red-50 to-red-100 rounded-lg shadow-sm p-6 border border-red-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-red-800">Dépenses</p>
              <p className="text-2xl font-bold text-red-900 mt-2">
                {formatCurrency(expenses.expenses_total)}
              </p>
            </div>
            <ArrowTrendingDownIcon className="w-10 h-10 text-red-600" />
          </div>
          <p className="text-xs text-red-700 mt-2">
            {expenses.expenses_count} dépenses
          </p>
        </div>

        {/* Net Received */}
        <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg shadow-sm p-6 border border-blue-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-blue-800">Net Reçu</p>
              <p className="text-2xl font-bold text-blue-900 mt-2">
                {formatCurrency(sales.net_received)}
              </p>
            </div>
            <BanknotesIcon className="w-10 h-10 text-blue-600" />
          </div>
          <p className="text-xs text-blue-700 mt-2">
            Après commissions & frais
          </p>
        </div>

        {/* Profit Estimate */}
        <div className={`bg-gradient-to-br rounded-lg shadow-sm p-6 border ${
          profit_estimate >= 0 
            ? 'from-purple-50 to-purple-100 border-purple-200'
            : 'from-orange-50 to-orange-100 border-orange-200'
        }`}>
          <div className="flex items-center justify-between">
            <div>
              <p className={`text-sm font-medium ${profit_estimate >= 0 ? 'text-purple-800' : 'text-orange-800'}`}>
                Résultat Estimé
              </p>
              <p className={`text-2xl font-bold mt-2 ${profit_estimate >= 0 ? 'text-purple-900' : 'text-orange-900'}`}>
                {formatCurrency(profit_estimate)}
              </p>
            </div>
            <ChartBarIcon className={`w-10 h-10 ${profit_estimate >= 0 ? 'text-purple-600' : 'text-orange-600'}`} />
          </div>
          <p className={`text-xs mt-2 ${profit_estimate >= 0 ? 'text-purple-700' : 'text-orange-700'}`}>
            Net reçu - Dépenses
          </p>
        </div>
      </div>

      {/* Detailed Breakdown */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Détails</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Sales Breakdown */}
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-3">Ventes</h4>
            <dl className="space-y-2">
              <div className="flex justify-between text-sm">
                <dt className="text-gray-600">Montant articles</dt>
                <dd className="font-medium text-gray-900">{formatCurrency(sales.gross_sales)}</dd>
              </div>
              <div className="flex justify-between text-sm">
                <dt className="text-gray-600">Frais de livraison</dt>
                <dd className="font-medium text-gray-900">{formatCurrency(sales.total_delivery_fees || 0)}</dd>
              </div>
              <div className="flex justify-between text-sm text-red-600">
                <dt>Commission Gaboshop</dt>
                <dd className="font-medium">-{formatCurrency(sales.total_commission)}</dd>
              </div>
              <div className="flex justify-between text-sm text-red-600">
                <dt>Frais de service</dt>
                <dd className="font-medium">-{formatCurrency(sales.total_service_fees)}</dd>
              </div>
              <div className="flex justify-between text-sm border-t border-gray-200 pt-2 font-semibold">
                <dt className="text-gray-900">Net reçu</dt>
                <dd className="text-green-600">{formatCurrency(sales.net_received)}</dd>
              </div>
            </dl>
          </div>

          {/* Top Categories (if available) */}
          {planFeatures?.can_view_detailed_reports && top_categories && top_categories.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 mb-3">Top Catégories</h4>
              <dl className="space-y-2">
                {top_categories.map((cat, idx) => (
                  <div key={idx} className="flex justify-between text-sm">
                    <dt className="text-gray-600 truncate">{cat.product__category__name || 'Sans catégorie'}</dt>
                    <dd className="font-medium text-gray-900">{formatCurrency(cat.total_sales)}</dd>
                  </div>
                ))}
              </dl>
            </div>
          )}
        </div>

        {/* Refresh Button */}
        <div className="mt-6 flex justify-end">
          <button
            onClick={onRefresh}
            disabled={loading}
            className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
          >
            {loading ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-gray-700" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Actualisation...
              </>
            ) : (
              <>
                <svg className="-ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Actualiser
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default FinanceSummary;

