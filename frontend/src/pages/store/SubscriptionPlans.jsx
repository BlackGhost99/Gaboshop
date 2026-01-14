import React, { useState, useEffect } from 'react';
import StoreLayout from '../../components/StoreLayout';
import api from '../../services/api';

const SubscriptionPlans = () => {
  const [plans, setPlans] = useState([]);
  const [currentPlan, setCurrentPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [subscribing, setSubscribing] = useState(null);
  const [toast, setToast] = useState(null);
  const [storeType, setStoreType] = useState(null);

  useEffect(() => {
    fetchPlans();
  }, []);

  const fetchPlans = async () => {
    try {
      const response = await api.get('/payments/subscription-plans/');
      setPlans(response.data.plans || []);
      setCurrentPlan(response.data.current_plan);
      setStoreType(response.data.store_type);
    } catch (err) {
      console.error('Erreur chargement plans:', err);
      showToast('Erreur lors du chargement des plans', 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleSubscribe = async (planId) => {
    if (!window.confirm('Voulez-vous vraiment souscrire à ce plan ?')) {
      return;
    }

    setSubscribing(planId);
    try {
      const response = await api.post('/payments/subscriptions/subscribe/', {
        plan_id: planId,
        payment_method: 'admin_validation'
      });

      if (response.data.success) {
        showToast(response.data.message, 'success');
        // Refresh plans after subscription
        setTimeout(() => fetchPlans(), 2000);
      } else {
        showToast(response.data.error || 'Erreur lors de la souscription', 'error');
      }
    } catch (err) {
      console.error('Erreur souscription:', err);
      showToast(err.response?.data?.error || 'Erreur lors de la souscription', 'error');
    } finally {
      setSubscribing(null);
    }
  };

  const showToast = (message, type) => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 5000);
  };

  const getPlanIcon = (planType) => {
    const icons = {
      free: '🆓',
      pro: '💼',
      business: '👑'
    };
    return icons[planType] || '📦';
  };

  const getPlanColor = (planType) => {
    const colors = {
      free: 'from-gray-500 to-gray-700',
      pro: 'from-blue-600 to-blue-800',
      business: 'from-indigo-600 to-purple-800'
    };
    return colors[planType] || 'from-gray-500 to-gray-700';
  };

  const getPlanBadgeColor = (planType) => {
    const colors = {
      free: 'bg-gray-100 text-gray-800 border-gray-300',
      pro: 'bg-blue-100 text-blue-800 border-blue-300',
      business: 'bg-purple-100 text-purple-800 border-purple-300'
    };
    return colors[planType] || 'bg-gray-100 text-gray-800 border-gray-300';
  };

  if (loading) {
    return (
      <StoreLayout title="Plans de Souscription">
        <div className="text-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Chargement des plans...</p>
        </div>
      </StoreLayout>
    );
  }

  return (
    <StoreLayout title="Plans de Souscription">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h2 className="text-4xl font-bold text-gray-900 mb-4">
            Choisissez le plan adapté à votre business
          </h2>
          <p className="text-lg text-gray-600 max-w-3xl mx-auto">
            Développez votre activité avec des fonctionnalités premium, commissions réduites et visibilité maximale sur GABOSHOP
          </p>
        </div>

        {/* Current Plan Banner */}
        {currentPlan && (
          <div className="mb-10 p-6 bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-200 rounded-xl shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-lg font-semibold text-green-900">
                  {getPlanIcon(currentPlan.plan_type)} Votre plan actuel : <span className="text-green-700">{currentPlan.name}</span>
                </p>
                {currentPlan.end_date && currentPlan.days_until_expiry !== undefined && (
                  <p className="mt-2 text-sm text-green-700">
                    {currentPlan.days_until_expiry > 7 ? (
                      <>Expire le {new Date(currentPlan.end_date).toLocaleDateString('fr-FR')}</>
                    ) : currentPlan.days_until_expiry > 0 ? (
                      <span className="text-orange-700 font-semibold">⚠️ Expire dans {currentPlan.days_until_expiry} jour{currentPlan.days_until_expiry > 1 ? 's' : ''}</span>
                    ) : (
                      <span className="text-red-700 font-semibold">❌ Plan expiré</span>
                    )}
                  </p>
                )}
              </div>
              {currentPlan.plan_type === 'free' && (
                <div className="text-right">
                  <p className="text-sm text-gray-600">Passez au plan Business pour débloquer :</p>
                  <p className="text-xs text-indigo-600 font-semibold mt-1">✓ Accès B2B ✓ Commission 0-2% ✓ Analytics avancés</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Plans Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
          {plans.map((plan) => {
            const isCurrent = currentPlan?.plan_type === plan.plan_type;
            const isHighlighted = plan.plan_type === 'business';

            return (
              <div
                key={plan.id}
                className={`relative rounded-2xl shadow-2xl overflow-hidden transform transition-all duration-300 hover:scale-105 ${
                  isCurrent ? 'ring-4 ring-green-500' : ''
                } ${isHighlighted ? 'border-4 border-indigo-400' : 'border border-gray-200'}`}
              >
                {/* Badge "Recommandé" ou "Actuel" */}
                {isHighlighted && !isCurrent && (
                  <div className="absolute top-4 right-4 bg-indigo-600 text-white px-4 py-1 rounded-full text-sm font-bold shadow-lg z-10">
                    ⭐ RECOMMANDÉ
                  </div>
                )}
                {isCurrent && (
                  <div className="absolute top-4 right-4 bg-green-600 text-white px-4 py-1 rounded-full text-sm font-bold shadow-lg z-10">
                    ✓ ACTUEL
                  </div>
                )}

                {/* Header avec gradient */}
                <div className={`bg-gradient-to-br ${getPlanColor(plan.plan_type)} p-8 text-white`}>
                  <div className="text-6xl mb-4">{getPlanIcon(plan.plan_type)}</div>
                  <h3 className="text-3xl font-bold mb-2">{plan.name}</h3>
                  <div className="flex items-baseline mb-2">
                    {plan.actual_price === 0 || plan.price === 0 ? (
                      <span className="text-4xl font-bold">GRATUIT</span>
                    ) : (
                      <>
                        <span className="text-5xl font-bold">{Math.floor(plan.actual_price || plan.price).toLocaleString('fr-FR')}</span>
                        <span className="ml-2 text-xl">F/mois</span>
                      </>
                    )}
                  </div>
                  {plan.price_label && plan.plan_type === 'business' && (
                    <p className="text-sm text-white/80">{plan.price_label}</p>
                  )}
                </div>

                {/* Features List */}
                <div className="p-8 bg-white">
                  <ul className="space-y-4 mb-8">
                    {plan.features && plan.features.length > 0 ? (
                      plan.features.map((feature, index) => (
                        <li key={index} className="flex items-start">
                          <svg className="w-6 h-6 text-green-500 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                          <span className="text-gray-700 text-sm">{feature}</span>
                        </li>
                      ))
                    ) : (
                      <li className="text-gray-500 text-sm">Aucune fonctionnalité listée</li>
                    )}
                  </ul>

                  {/* CTA Button */}
                  {plan.plan_type === 'free' ? (
                    <button
                      disabled
                      className="w-full py-4 px-6 bg-gray-300 text-gray-500 rounded-lg font-bold cursor-not-allowed"
                    >
                      Plan par défaut
                    </button>
                  ) : isCurrent ? (
                    <button
                      disabled
                      className="w-full py-4 px-6 bg-green-100 text-green-700 rounded-lg font-bold cursor-default border-2 border-green-300"
                    >
                      ✓ Plan actif
                    </button>
                  ) : (
                    <button
                      onClick={() => handleSubscribe(plan.id)}
                      disabled={!!subscribing}
                      className={`w-full py-4 px-6 rounded-lg font-bold text-white transition-all duration-200 shadow-lg hover:shadow-xl transform hover:scale-105 ${
                        plan.plan_type === 'business'
                          ? 'bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700'
                          : 'bg-blue-600 hover:bg-blue-700'
                      } ${subscribing ? 'opacity-50 cursor-wait' : ''}`}
                    >
                      {subscribing === plan.id ? (
                        <span className="flex items-center justify-center gap-2">
                          <svg className="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                          Traitement...
                        </span>
                      ) : (
                        `Souscrire au plan ${plan.name}`
                      )}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Info Section */}
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-6 mb-8">
          <div className="flex items-start gap-4">
            <svg className="w-6 h-6 text-blue-600 flex-shrink-0 mt-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <h4 className="font-bold text-blue-900 mb-2">À propos des paiements</h4>
              <p className="text-sm text-blue-800">
                Les souscriptions sont actuellement validées manuellement par notre équipe. 
                Après avoir cliqué sur "Souscrire", votre demande sera traitée dans les 24h. 
                Vous recevrez une notification une fois votre plan activé.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Toast Notification */}
      {toast && (
        <div className="fixed bottom-5 right-5 z-50 animate-slide-in-right">
          <div
            className={`px-6 py-4 rounded-lg shadow-2xl border-2 text-white font-semibold ${
              toast.type === 'success' ? 'bg-green-600 border-green-500' : 'bg-red-600 border-red-500'
            }`}
          >
            <div className="flex items-center gap-3">
              {toast.type === 'success' ? (
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              ) : (
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              )}
              <span>{toast.message}</span>
            </div>
          </div>
        </div>
      )}
    </StoreLayout>
  );
};

export default SubscriptionPlans;
