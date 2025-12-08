import React, { useState, useEffect } from 'react';
import StoreLayout from '../../components/StoreLayout';
import { api } from '../../services/api';

const SubscriptionPlans = () => {
  const [plans, setPlans] = useState([]);
  const [currentPlan, setCurrentPlan] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPlans = async () => {
      try {
        const response = await api.get('/payments/subscription-plans/');
        setPlans(response.data.plans || []);
        setCurrentPlan(response.data.current_plan);
      } catch (err) {
        console.error('Erreur chargement plans:', err);
      } finally {
        setLoading(false);
      }
    };
    fetchPlans();
  }, []);

  const getPlanIcon = (planType) => {
    const icons = {
      starter: '🚀',
      pro: '💼',
      business: '👑'
    };
    return icons[planType] || '📦';
  };

  const getPlanColor = (planType) => {
    const colors = {
      starter: 'from-gray-700 to-gray-900',
      pro: 'from-blue-700 to-blue-900',
      business: 'from-purple-700 to-purple-900'
    };
    return colors[planType] || 'from-gray-700 to-gray-900';
  };

  if (loading) {
    return (
      <StoreLayout title="Forfaits">
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-slate-900 mx-auto"></div>
        </div>
      </StoreLayout>
    );
  }

  return (
    <StoreLayout title="Choisir votre forfait">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-3xl font-bold text-slate-900 mb-4">
            Choisissez le forfait adapté à votre business
          </h2>
          <p className="text-gray-600 max-w-2xl mx-auto">
            Développez votre activité avec des fonctionnalités premium et une meilleure visibilité sur GABOSHOP
          </p>
        </div>

        {currentPlan && (
          <div className="mb-8 p-4 bg-emerald-50 border border-emerald-200 rounded-lg">
            <p className="text-emerald-800">
              <strong>Votre forfait actuel :</strong> {currentPlan.name}
              {currentPlan.end_date && (
                <span className="ml-2 text-sm">
                  (expire le {new Date(currentPlan.end_date).toLocaleDateString('fr-FR')})
                </span>
              )}
            </p>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {plans.map((plan) => (
            <div
              key={plan.id}
              className={`relative rounded-2xl shadow-xl overflow-hidden ${
                currentPlan?.plan_type === plan.plan_type ? 'ring-4 ring-emerald-500' : ''
              }`}
            >
              {/* Header avec gradient */}
              <div className={`bg-gradient-to-br ${getPlanColor(plan.plan_type)} p-8 text-white`}>
                <div className="text-5xl mb-4">{getPlanIcon(plan.plan_type)}</div>
                <h3 className="text-2xl font-bold mb-2">{plan.name}</h3>
                <div className="flex items-baseline">
                  {plan.price === 0 ? (
                    <span className="text-4xl font-bold">GRATUIT</span>
                  ) : (
                    <>
                      <span className="text-4xl font-bold">{plan.price.toLocaleString('fr-FR')}</span>
                      <span className="ml-2 text-xl">FCFA/mois</span>
                    </>
                  )}
                </div>
                {plan.commission_rate && (
                  <p className="mt-2 text-sm opacity-90">
                    Commission réduite à {plan.commission_rate}%
                  </p>
                )}
              </div>

              {/* Features */}
              <div className="p-8 bg-white">
                <ul className="space-y-4 mb-8">
                  {plan.max_products !== null ? (
                    <li className="flex items-start">
                      <svg className="w-5 h-5 text-emerald-500 mr-3 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      <span className="text-gray-700">Jusqu'à {plan.max_products} produits</span>
                    </li>
                  ) : (
                    <li className="flex items-start">
                      <svg className="w-5 h-5 text-emerald-500 mr-3 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      <span className="text-gray-700 font-semibold">Produits illimités</span>
                    </li>
                  )}

                  {plan.has_statistics && (
                    <li className="flex items-start">
                      <svg className="w-5 h-5 text-emerald-500 mr-3 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      <span className="text-gray-700">Statistiques et rapports</span>
                    </li>
                  )}

                  {plan.has_custom_page && (
                    <li className="flex items-start">
                      <svg className="w-5 h-5 text-emerald-500 mr-3 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      <span className="text-gray-700">Page personnalisée</span>
                    </li>
                  )}

                  {plan.has_priority_support && (
                    <li className="flex items-start">
                      <svg className="w-5 h-5 text-emerald-500 mr-3 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      <span className="text-gray-700">Support VIP prioritaire</span>
                    </li>
                  )}

                  {plan.priority_listing > 0 && (
                    <li className="flex items-start">
                      <svg className="w-5 h-5 text-emerald-500 mr-3 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      <span className="text-gray-700">Meilleure visibilité</span>
                    </li>
                  )}

                  {plan.can_sponsor_products && (
                    <li className="flex items-start">
                      <svg className="w-5 h-5 text-emerald-500 mr-3 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      <span className="text-gray-700">Produits sponsorisés</span>
                    </li>
                  )}

                  {plan.features_json?.map((feature, idx) => (
                    <li key={idx} className="flex items-start">
                      <svg className="w-5 h-5 text-emerald-500 mr-3 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      <span className="text-gray-700">{feature}</span>
                    </li>
                  ))}
                </ul>

                <button
                  disabled={currentPlan?.plan_type === plan.plan_type}
                  className={`w-full py-3 px-6 rounded-lg font-semibold transition-colors ${
                    currentPlan?.plan_type === plan.plan_type
                      ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                      : 'bg-slate-900 text-white hover:bg-slate-800'
                  }`}
                >
                  {currentPlan?.plan_type === plan.plan_type ? 'Forfait actuel' : 'Choisir ce forfait'}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </StoreLayout>
  );
};

export default SubscriptionPlans;
