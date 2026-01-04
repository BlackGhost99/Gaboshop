import { useState } from 'react';
import { ArrowDownTrayIcon } from '@heroicons/react/24/outline';
import { downloadFile } from '../../services/financeService';

const ExportButton = ({ 
  type, // 'csv' or 'pdf'
  onExport, // function that returns a promise with blob
  filename,
  planFeatures,
  filters = {},
  disabled = false
}) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Check permissions
  const canExportCSV = planFeatures?.can_export_excel;
  const canExportPDF = planFeatures?.can_export_pdf;
  const planName = planFeatures?.plan_name || 'Free';

  const handleExport = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const blob = await onExport(filters);
      const extension = type === 'pdf' ? 'pdf' : 'csv';
      const fullFilename = `${filename}.${extension}`;
      
      downloadFile(blob, fullFilename);
    } catch (err) {
      console.error('Erreur lors de l\'export:', err);
      setError(err.message || "Erreur lors de l'export");
      
      // Show permission error if 403
      if (err.response?.status === 403) {
        alert(err.response?.data?.detail || "Cette fonctionnalité nécessite un plan supérieur.");
      }
    } finally {
      setLoading(false);
    }
  };

  // Check if export is allowed
  const isAllowed = type === 'csv' ? canExportCSV : canExportPDF;
  const isDisabled = disabled || loading || !isAllowed;

  // Upgrade message
  const getUpgradeMessage = () => {
    if (type === 'csv' && !canExportCSV) {
      return 'Export CSV disponible avec le plan Pro ou Business';
    }
    if (type === 'pdf' && !canExportPDF) {
      return 'Export PDF disponible uniquement avec le plan Business';
    }
    return null;
  };

  const upgradeMessage = getUpgradeMessage();

  return (
    <div className="relative group">
      <button
        onClick={handleExport}
        disabled={isDisabled}
        className={`inline-flex items-center px-4 py-2 border rounded-md shadow-sm text-sm font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 ${
          isDisabled
            ? 'border-gray-300 text-gray-400 bg-gray-100 cursor-not-allowed'
            : type === 'pdf'
            ? 'border-red-300 text-red-700 bg-red-50 hover:bg-red-100 focus:ring-red-500'
            : 'border-green-300 text-green-700 bg-green-50 hover:bg-green-100 focus:ring-green-500'
        }`}
      >
        {loading ? (
          <>
            <svg className="animate-spin -ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Export...
          </>
        ) : (
          <>
            <ArrowDownTrayIcon className="-ml-1 mr-2 h-4 w-4" />
            Export {type.toUpperCase()}
          </>
        )}
      </button>

      {/* Upgrade Tooltip */}
      {upgradeMessage && (
        <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-gray-900 text-white text-xs rounded-md whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
          {upgradeMessage}
          <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-gray-900"></div>
        </div>
      )}

      {/* Locked Badge */}
      {!isAllowed && (
        <div className="absolute -top-1 -right-1 bg-yellow-400 text-yellow-900 text-xs font-bold px-2 py-0.5 rounded-full">
          🔒 {planName === 'Free' ? 'Pro+' : 'Business'}
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="absolute top-full left-0 mt-1 text-xs text-red-600 whitespace-nowrap">
          {error}
        </div>
      )}
    </div>
  );
};

export default ExportButton;

