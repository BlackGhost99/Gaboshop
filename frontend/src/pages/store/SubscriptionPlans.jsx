import React, { useState, useEffect } from 'react';
import StoreLayout from '../../components/StoreLayout';
import api from '../../services/api';
import useVisibleInterval from '../../hooks/useVisibleInterval';
import { notifyError, notifySuccess } from '../../utils/feedback';

const SubscriptionPlans = () => {
  const [plans, setPlans] = useState([]);
  const [currentPlan, setCurrentPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [subscribing, setSubscribing] = useState(null);
  const [storeType, setStoreType] = useState(null);
  // Seul le Mobile Money fonctionne : Airtel Money ou Moov Money (pas de carte bancaire).
  const [paymentProvider, setPaymentProvider] = useState('airtel');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [lastIntent, setLastIntent] = useState(null);

  useEffect(() => {
    fetchPlans();
  }, []);

  // quiet : pendant le suivi d'un paiement (toutes les 10 s), ne pas répéter le message d'erreur.
  const fetchPlans = async ({ quiet = false } = {}) => {
    try {
      const response = await api.get('/payments/subscription-plans/');
      setPlans(response.data.plans || []);
      setCurrentPlan(response.data.current_plan);
      setStoreType(response.data.store_type);
    } catch (err) {
      console.error('Erreur chargement plans:', err);
      if (!quiet) {
        notifyError(err, {
          action: 'Charger les forfaits',
          fallback: "Les forfaits n'ont pas pu être chargés.",
        });
      }
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
      // Toujours Airtel ou Moov : le paiement par carte (CinetPay) ne fonctionne pas.
      const provider = paymentProvider === 'moov' ? 'moov' : 'airtel';
      if (!phoneNumber.trim()) {
        notifyError({ error: { message: 'Le numéro Mobile Money est requis.', reason: 'Le paiement du plan part sur votre téléphone.', next_step: 'Saisissez votre numéro Airtel ou Moov dans « Mode de paiement », puis recommencez.' } }, { action: 'Activer le plan' });
        setSubscribing(null);
        return;
      }

      const response = await api.post('/payments/subscriptions/intent/', {
        plan_id: planId,
        provider,
        phone_number: phoneNumber.trim()
      });

      if (response.data.success) {
        const intent = response.data.payment_intent;
        setLastIntent(intent);
        if (intent?.payment_url) {
          window.open(intent.payment_url, '_blank', 'noopener,noreferrer');
        }
        notifySuccess(
          'Demande de paiement envoyée',
          intent?.payment_url
            ? 'Finalisez le paiement dans la page qui vient de s\'ouvrir : votre plan s\'active dès qu\'il est confirmé.'
            : 'Validez le paiement sur votre téléphone avec votre code secret : votre plan s\'active dès qu\'il est confirmé.',
        );
        setTimeout(() => fetchPlans(), 2500);
      } else {
        notifyError(response.data, { action: 'Activer le plan' });
      }
    } catch (err) {
      console.error('Erreur souscription:', err);
      notifyError(err, { action: 'Activer le plan' });
    } finally {
      setSubscribing(null);
    }
  };

  // Paiement en attente : suivre l'activation du plan (et au retour dans l'app)
  useVisibleInterval(() => fetchPlans({ quiet: true }), 10000, Boolean(lastIntent));

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

  // Ce que le Pro débloque vraiment, lu sur sa carte (le serveur n'y met que les outils branchés).
  const proPlan = plans.find((plan) => plan.plan_type === 'pro' && plan.is_available !== false);
  const featureTitles = (plan) => (plan?.features || [])
    .map((feature) => (typeof feature === 'string' ? feature : feature?.title))
    .filter(Boolean);
  // Seulement ce que le Gratuit n'a pas déjà.
  const freeTitles = new Set(featureTitles(plans.find((plan) => plan.plan_type === 'free')));
  const proHighlights = featureTitles(proPlan)
    .filter((feature) => !freeTitles.has(feature))
    .filter((feature) => !/^commandes illimit/i.test(feature))
    .map((feature) => feature.split(' : ')[0].split(', et ')[0])
    .slice(0, 6);

  return (
    <StoreLayout title="Plans de Souscription">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <h2 className="text-4xl font-bold text-gray-900 mb-4">
            Choisissez le plan adapté à votre business
          </h2>
          <p className="text-lg text-gray-600 max-w-3xl mx-auto break-words">
            Commencez gratuitement, puis passez au forfait Pro quand vous voulez vendre plus. Chaque carte liste exactement ce que le forfait vous donne.
          </p>
        </div>

        {/* Payment Method */}
        <div className="mb-10 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <h3 className="text-lg font-semibold text-slate-900">Mode de paiement</h3>
              <p className="text-sm text-slate-600">
                Airtel Money ou Moov Money. Vous validez le paiement sur votre téléphone.
              </p>
            </div>
            <div className="flex flex-col sm:flex-row gap-3 min-w-0">
              <select
                value={paymentProvider}
                onChange={(event) => setPaymentProvider(event.target.value)}
                className="w-full sm:w-auto rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700"
              >
                <option value="airtel">Airtel Money</option>
                <option value="moov">Moov Money</option>
              </select>
              <input
                type="tel"
                value={phoneNumber}
                onChange={(event) => setPhoneNumber(event.target.value)}
                placeholder="Téléphone Mobile Money"
                className="w-full sm:w-auto min-w-0 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-700"
              />
            </div>
          </div>
          {lastIntent && (
            <div className="mt-4 rounded-lg bg-slate-50 px-4 py-3 text-sm text-slate-600 break-words">
              Paiement en attente. Référence : <span className="font-semibold text-slate-900">{lastIntent.reference}</span>
            </div>
          )}
        </div>

        {/* Current Plan Banner */}
        {currentPlan && (
          <div className="mb-10 p-6 bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-200 rounded-xl shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="min-w-0">
                <p className="text-lg font-semibold text-green-900 break-words">
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
              {currentPlan.plan_type === 'free' && proHighlights.length > 0 && (
                <div className="min-w-0 text-left sm:text-right">
                  <p className="text-sm text-gray-600">Passez à Pro pour débloquer :</p>
                  <p className="text-xs text-indigo-600 font-semibold mt-1 break-words">{proHighlights.map((item) => `✓ ${item}`).join('  ')}</p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Plans Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-12">
          {plans.map((plan) => {
            const isCurrent = currentPlan?.plan_type === plan.plan_type;
            const unavailable = plan.is_available === false;
            const isHighlighted = plan.plan_type === 'pro' && !unavailable;

            return (
              <div
                key={plan.id}
                className={`relative rounded-2xl shadow-2xl overflow-hidden transform transition-all duration-300 ${unavailable ? 'opacity-60 grayscale' : 'hover:scale-105'} ${
                  isCurrent ? 'ring-4 ring-green-500' : ''
                } ${isHighlighted ? 'border-4 border-indigo-400' : 'border border-gray-200'}`}
              >
                {/* Badge "Recommandé" ou "Actuel" */}
                {unavailable && (
                  <div className="absolute top-4 right-4 bg-gray-700 text-white px-4 py-1 rounded-full text-sm font-bold shadow-lg z-10">
                    Bientôt disponible
                  </div>
                )}
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
                    {unavailable ? (
                      <span className="text-3xl font-bold">Bientôt disponible</span>
                    ) : Number(plan.actual_price ?? plan.price) === 0 ? (
                      <span className="text-4xl font-bold">GRATUIT</span>
                    ) : (
                      <>
                        <span className="text-5xl font-bold">{Math.floor(plan.actual_price || plan.price).toLocaleString('fr-FR')}</span>
                        <span className="ml-2 text-xl">F/mois</span>
                      </>
                    )}
                  </div>
                  {unavailable && plan.description && (
                    <p className="text-sm text-white/90">{plan.description}</p>
                  )}
                  {!unavailable && plan.price_label && plan.plan_type === 'business' && (
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
                  {unavailable ? (
                    <button
                      disabled
                      className="w-full py-4 px-6 bg-gray-300 text-gray-500 rounded-lg font-bold cursor-not-allowed"
                    >
                      Indisponible
                    </button>
                  ) : plan.plan_type === 'free' ? (
                    <button
                      disabled
                      className="w-full py-4 px-6 bg-gray-300 text-gray-500 rounded-lg font-bold cursor-not-allowed"
                    >
                      {isCurrent ? '✓ Plan actif (gratuit)' : 'Plan par défaut'}
                    </button>
                  ) : isCurrent ? (
                    // Renouveler en avance : les jours qui restent s'ajoutent au nouveau mois (serveur : carried_days).
                    <div className="space-y-2">
                      <p className="text-center text-sm font-semibold text-green-700">✓ Plan actif</p>
                      <button
                        onClick={() => handleSubscribe(plan.id)}
                        disabled={!!subscribing}
                        className={`w-full py-4 px-6 rounded-lg font-bold text-green-800 bg-green-100 border-2 border-green-300 hover:bg-green-200 transition-colors ${subscribing ? 'opacity-50 cursor-wait' : ''}`}
                      >
                        {subscribing === plan.id ? 'Traitement...' : 'Renouveler maintenant'}
                      </button>
                      <p className="text-center text-xs text-gray-500">Les jours qui vous restent sont gardés et s'ajoutent au nouveau mois.</p>
                    </div>
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
                Après paiement par Airtel Money ou Moov Money, votre plan est activé automatiquement.
                Si vous ne voyez pas le changement immédiatement, rafraîchissez la page.
              </p>
            </div>
          </div>
        </div>
      </div>
    </StoreLayout>
  );
};

export default SubscriptionPlans;
