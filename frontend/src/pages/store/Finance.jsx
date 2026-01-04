import { useState, useEffect } from 'react';
import { Tab } from '@headlessui/react';
import { ChartBarIcon, CurrencyDollarIcon } from '@heroicons/react/24/outline';
import FinanceSummary from '../../components/finance/FinanceSummary';
import RevenusTab from '../../components/finance/RevenusTab';
import DepensesTab from '../../components/finance/DepensesTab';
import { getFinanceSummary } from '../../services/financeService';

function classNames(...classes) {
  return classes.filter(Boolean).join(' ');
}

const Finance = () => {
  const [loading, setLoading] = useState(true);
  const [summary, setSummary] = useState(null);
  const [planFeatures, setPlanFeatures] = useState(null);
  const [dateFilters, setDateFilters] = useState({
    date_from: '',
    date_to: '',
  });
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchSummary();
  }, [dateFilters]);

  const fetchSummary = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await getFinanceSummary(dateFilters);
      setSummary(response.data);
      setPlanFeatures(response.plan_features);
    } catch (err) {
      console.error('Erreur lors du chargement du résumé financier:', err);
      setError(err.message || "Erreur lors du chargement des données financières");
    } finally {
      setLoading(false);
    }
  };

  const handleDateFilterChange = (newFilters) => {
    setDateFilters(prev => ({ ...prev, ...newFilters }));
  };

  if (loading && !summary) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600"></div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Finance</h1>
        <p className="text-gray-600 mt-1">
          Gérez vos revenus, dépenses et suivez votre rentabilité
        </p>
        
        {/* Plan Badge */}
        {planFeatures && (
          <div className="mt-4">
            <span className={classNames(
              "inline-flex items-center px-3 py-1 rounded-full text-sm font-medium",
              planFeatures.plan_name === 'Business' ? 'bg-purple-100 text-purple-800' :
              planFeatures.plan_name === 'Pro' ? 'bg-blue-100 text-blue-800' :
              'bg-gray-100 text-gray-800'
            )}>
              {planFeatures.plan_name}
            </span>
            {planFeatures.history_limit_days && (
              <span className="ml-2 text-sm text-gray-500">
                Historique : {planFeatures.history_limit_days} jours
              </span>
            )}
          </div>
        )}
      </div>

      {/* Error Alert */}
      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded relative">
          <strong className="font-bold">Erreur!</strong>
          <span className="block sm:inline"> {error}</span>
        </div>
      )}

      {/* Summary Block */}
      {summary && (
        <FinanceSummary 
          summary={summary} 
          planFeatures={planFeatures}
          onRefresh={fetchSummary}
          loading={loading}
        />
      )}

      {/* Tabs */}
      <div className="mt-8">
        <Tab.Group>
          <Tab.List className="flex space-x-1 rounded-xl bg-gray-100 p-1">
            <Tab
              className={({ selected }) =>
                classNames(
                  'w-full rounded-lg py-2.5 text-sm font-medium leading-5',
                  'ring-white ring-opacity-60 ring-offset-2 ring-offset-green-400 focus:outline-none focus:ring-2',
                  selected
                    ? 'bg-white text-green-700 shadow'
                    : 'text-gray-700 hover:bg-white/[0.12] hover:text-gray-900'
                )
              }
            >
              <div className="flex items-center justify-center">
                <ChartBarIcon className="w-5 h-5 mr-2" />
                Revenus (Ventes)
              </div>
            </Tab>
            <Tab
              className={({ selected }) =>
                classNames(
                  'w-full rounded-lg py-2.5 text-sm font-medium leading-5',
                  'ring-white ring-opacity-60 ring-offset-2 ring-offset-red-400 focus:outline-none focus:ring-2',
                  selected
                    ? 'bg-white text-red-700 shadow'
                    : 'text-gray-700 hover:bg-white/[0.12] hover:text-gray-900'
                )
              }
            >
              <div className="flex items-center justify-center">
                <CurrencyDollarIcon className="w-5 h-5 mr-2" />
                Dépenses (Approvisionnement)
              </div>
            </Tab>
          </Tab.List>
          <Tab.Panels className="mt-6">
            <Tab.Panel>
              <RevenusTab 
                planFeatures={planFeatures}
                dateFilters={dateFilters}
                onDateFilterChange={handleDateFilterChange}
              />
            </Tab.Panel>
            <Tab.Panel>
              <DepensesTab 
                planFeatures={planFeatures}
                dateFilters={dateFilters}
                onDateFilterChange={handleDateFilterChange}
              />
            </Tab.Panel>
          </Tab.Panels>
        </Tab.Group>
      </div>
    </div>
  );
};

export default Finance;

