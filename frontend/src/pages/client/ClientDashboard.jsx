import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import ClientLayout from '../../components/ClientLayout';
import StatCard from '../../components/StatCard';
import LoadingSpinner from '../../components/LoadingSpinner';
import { getClientDashboard } from '../../services/dashboardService';
import { formatCurrency, formatDateTime, getOrderStatusBadge } from '../../utils/helpers';
import { createOrder } from '../../services/orderService';
import { getPaymentOptions, initPayment } from '../../services/paymentService';
import { getProductDetails } from '../../services/productService';
import { METHOD_LABELS } from '../../components/payments/paymentLabels';

const CART_KEY = 'gaboshop_cart';
const envBase = import.meta.env.VITE_API_URL;
const API_BASE = envBase ? `${envBase.replace(/\/$/, '')}/api/v1` : '/api/v1';
const DEFAULT_WEIGHT_KG = 0.5;
const DEFAULT_LENGTH_M = 0.5;

const flattenApiErrors = (value, parentPath = '') => {
  if (Array.isArray(value)) {
    return value.flatMap((entry, index) => {
      if (typeof entry === 'string') {
        return parentPath ? [`${parentPath}: ${entry}`] : [entry];
      }
      const nextPath = parentPath || `[${index}]`;
      return flattenApiErrors(entry, nextPath);
    });
  }

  if (value && typeof value === 'object') {
    return Object.entries(value).flatMap(([key, nested]) => {
      const nextPath = parentPath ? `${parentPath}.${key}` : key;
      return flattenApiErrors(nested, nextPath);
    });
  }

  if (value === null || value === undefined) return [];
  return parentPath ? [`${parentPath}: ${String(value)}`] : [String(value)];
};

const getReadableApiErrorMessage = (details, fallbackMessage = '') => {
  const lines = flattenApiErrors(details).filter(Boolean);
  if (lines.length) return lines.join(' | ');
  return fallbackMessage || '';
};

const isStoreClosedMessage = (message) => {
  if (typeof message !== 'string') return false;
  const normalized = message.toLowerCase();
  return normalized.includes('magasin') && normalized.includes('ferm');
};

// Explication sous le choix du paiement : elle suit l'option choisie.
const paymentHint = (flow, method) => {
  if (flow === 'platform_online') {
    return 'Paiement en ligne : après la commande, vous recevez une demande sur votre téléphone. Validez-la avec votre code secret Airtel Money ou Moov Money.';
  }
  if (method === 'cash') {
    if (flow === 'courier_cash') return 'Vous payez en espèces au livreur à la livraison.';
    if (flow === 'store_collects_all') return 'Vous payez tout en espèces au commerce.';
    return 'Vous payez les articles en espèces au commerce, et la livraison au livreur.';
  }
  return "Mobile Money direct : vous payez le commerce à son code marchand, puis vous déclarez l'ID de transaction reçu par SMS. Le commerce confirme avant de préparer.";
};

const ClientDashboard = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState(null);
  const [error, setError] = useState(null);
  const [cartItems, setCartItems] = useState([]);
  const [cartByStore, setCartByStore] = useState({});
  const [storeForms, setStoreForms] = useState({});
  const [submitting, setSubmitting] = useState({});
  const [toast, setToast] = useState(null);
  const [storeAlerts, setStoreAlerts] = useState({});
  const [paymentOptions, setPaymentOptions] = useState({});
  const [zones, setZones] = useState([]);
  const [zonesLoading, setZonesLoading] = useState(true);

  // Helper: Calculate total amount
  const calculateTotal = (subtotal, deliveryCost) => {
    return subtotal + deliveryCost;
  };

  const selectVehicleType = (totalWeight, totalLength) => {
    if (totalWeight <= 30 && totalLength <= 0.5) return 'MOTO';
    if (totalWeight <= 80 && totalLength <= 1) return 'CAR';
    if (totalWeight <= 150 && totalLength <= 2) return 'VAN';
    return 'TRUCK';
  };

  const getTotals = (items) => {
    const totals = items.reduce((acc, item) => {
      const qty = item.quantity || 0;
      const weight = parseFloat(item.weight_kg);
      const length = parseFloat(item.length_m);
      acc.totalWeight += (Number.isFinite(weight) ? weight : DEFAULT_WEIGHT_KG) * qty;
      acc.totalLength += (Number.isFinite(length) ? length : DEFAULT_LENGTH_M) * qty;
      return acc;
    }, { totalWeight: 0, totalLength: 0 });
    return totals;
  };

  // Helper: Calculate delivery cost based on zone and items
  const calculateDeliveryCost = (zoneName, city, items) => {
    try {
      if (!items || !items.length) return 0;
      
      const normalizedZone = zoneName?.trim().toLowerCase();
      let zoneForDelivery = normalizedZone
        ? zones.find(z => z.name?.toLowerCase() === normalizedZone)
        : null;

      if (!zoneForDelivery && city) {
        zoneForDelivery = zones.find(z => z.city?.toLowerCase() === city?.toLowerCase());
      }

      if (!zoneForDelivery || !zoneForDelivery.rates || !zoneForDelivery.rates.length) {
        // Fallback: use a default estimate
        return 3000; // Placeholder if zone not configured
      }
      
      const { totalWeight, totalLength } = getTotals(items);
      
      // Select vehicle based on weight + length (same logic as backend)
      const vehicleType = selectVehicleType(totalWeight, totalLength);
      const selectedRate = zoneForDelivery.rates.find(r => r.vehicle_type === vehicleType);
      
      if (!selectedRate) {
        return 3000; // Fallback
      }
      
      const baseCost = parseFloat(selectedRate.base_price) || 0;
      return Math.round(baseCost);
    } catch (err) {
      console.warn('Erreur calcul frais livraison', err);
      return 3000;
    }
  };

  const groupByStore = (items) => {
    return items.reduce((acc, item) => {
      const key = item.store_name || 'Magasin';
      if (!acc[key]) acc[key] = { total: 0, items: [] };
      const lineTotal = (Number(item.price) || 0) * (item.quantity || 0);
      acc[key].items.push({ ...item, lineTotal });
      acc[key].total += lineTotal;
      return acc;
    }, {});
  };

  const persistCart = useCallback((items) => {
    setCartItems(items);
    setCartByStore(groupByStore(items));
    try {
      localStorage.setItem(CART_KEY, JSON.stringify(items));
    } catch (e) {
      console.error('Erreur sauvegarde panier', e);
    }
  }, []);

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        setLoading(true);
        const response = await getClientDashboard();
        if (response.success) {
          setDashboardData(response.data);
        } else {
          setError('Impossible de charger les données');
        }
      } catch (err) {
        setError('Erreur lors du chargement des données');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboard();
  }, []);

  // Fetch delivery zones with rates
  useEffect(() => {
    const fetchZones = async () => {
      try {
        setZonesLoading(true);
        const response = await fetch(`${API_BASE}/delivery/zones/?active=true`);
        if (response.ok) {
          const data = await response.json();
          setZones(Array.isArray(data) ? data : data.results || []);
        } else {
          console.warn('Erreur au chargement des zones');
        }
      } catch (err) {
        console.warn('Impossible de charger les zones de livraison', err);
      } finally {
        setZonesLoading(false);
      }
    };

    fetchZones();
  }, []);

  // Durée de vie des toasts pour qu'elles restent visibles
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(null), 4500);
    return () => clearTimeout(timer);
  }, [toast]);

  // L'assistant peut ajouter au panier pendant que la page est ouverte
  useEffect(() => {
    const reload = () => {
      try {
        const parsed = JSON.parse(localStorage.getItem(CART_KEY) || '[]');
        setCartItems(parsed);
        setCartByStore(groupByStore(parsed));
        setStoreForms((prev) => {
          const nextForms = { ...prev };
          parsed.forEach((it) => {
            const key = it.store_name || 'Magasin';
            if (!nextForms[key]) nextForms[key] = { city: 'Libreville', address: '', phone: '', payment_phone: '', zone: '', notes: '', payment_flow: '', payment_method: '' };
          });
          return nextForms;
        });
      } catch {
        // panier illisible : on garde l'affichage actuel
      }
    };
    window.addEventListener('gaboshop:cart-updated', reload);
    return () => window.removeEventListener('gaboshop:cart-updated', reload);
  }, []);

  useEffect(() => {
    // Charge le panier local et regroupe par magasin pour affichage "porte-feuille"
    try {
      const saved = localStorage.getItem(CART_KEY);
      const parsed = saved ? JSON.parse(saved) : [];
      setCartItems(parsed);
      setCartByStore(groupByStore(parsed));
      // Init form defaults
      const defaults = {};
      parsed.forEach((it) => {
        const key = it.store_name || 'Magasin';
        if (!defaults[key]) defaults[key] = { city: 'Libreville', address: '', phone: '', payment_phone: '', zone: '', notes: '', payment_flow: '', payment_method: '' };
      });
      setStoreForms(defaults);
    } catch (e) {
      console.error('Erreur chargement panier', e);
      setCartItems([]);
      setCartByStore({});
      setStoreForms({});
    }
  }, []);

  useEffect(() => {
    // Met à jour les formulaires si de nouveaux magasins apparaissent
    setStoreForms((prev) => {
      const updated = { ...prev };
      Object.keys(cartByStore).forEach((name) => {
        if (!updated[name]) {
          updated[name] = { city: 'Libreville', address: '', phone: '', payment_phone: '', zone: '', notes: '', payment_flow: '', payment_method: '' };
        }
      });
      return updated;
    });
  }, [cartByStore]);

  useEffect(() => {
    let active = true;
    Object.entries(cartByStore).forEach(async ([storeName, group]) => {
      const storeId = group.items?.[0]?.store_id;
      if (!storeId) return;
      try {
        const response = await getPaymentOptions(storeId, storeForms[storeName]?.delivery_requested !== false);
        const options = response?.data?.options || [];
        if (!active) return;
        setPaymentOptions((prev) => ({...prev, [storeName]: options}));
        if (options.length && !storeForms[storeName]?.payment_flow) {
          setStoreForms((prev) => ({...prev, [storeName]: {...prev[storeName], payment_flow: options[0].flow, payment_method: options[0].method}}));
        }
      } catch (error) {
        if (active) setPaymentOptions((prev) => ({...prev, [storeName]: []}));
      }
    });
    return () => { active = false; };
  }, [cartByStore]);

  useEffect(() => {
    // Backfill store_id/weight/length for legacy cart items
    const missing = cartItems.filter((it) => !it.store_id || !it.weight_kg || !it.length_m);
    if (!missing.length) return;
    let active = true;
    const run = async () => {
      const updated = [...cartItems];
      for (const miss of missing) {
        try {
          const res = await getProductDetails(miss.id);
          const data = res?.data || res;
          if (data?.store) {
            const idx = updated.findIndex((i) => i.id === miss.id && !i.store_id);
            if (idx !== -1) {
              updated[idx] = { ...updated[idx], store_id: data.store, store_name: data.store_name || updated[idx].store_name };
            }
          }
          const idx = updated.findIndex((i) => i.id === miss.id);
          if (idx !== -1) {
            const next = { ...updated[idx] };
            if (!next.weight_kg && data?.weight_kg) next.weight_kg = data.weight_kg;
            if (!next.length_m && data?.length_m) next.length_m = data.length_m;
            updated[idx] = next;
          }
        } catch (e) {
          console.warn('Impossible de récupérer le store du produit', miss.id, e);
        }
      }
      if (active) {
        persistCart(updated);
      }
    };
    run();
    return () => { active = false; };
  }, [cartItems, persistCart]);

  const handleUpdateQuantity = (storeName, itemId, delta) => {
    persistCart(
      cartItems
        .map((it) =>
          it.id === itemId && (it.store_name || 'Magasin') === storeName
            ? { ...it, quantity: Math.max(0, (it.quantity || 0) + delta) }
            : it
        )
        .filter((it) => it.quantity > 0)
    );
  };

  const handleRemoveItem = (storeName, itemId) => {
    persistCart(
      cartItems.filter(
        (it) => !(it.id === itemId && (it.store_name || 'Magasin') === storeName)
      )
    );
  };

  const handleClearStoreCart = (storeName) => {
    persistCart(cartItems.filter((it) => (it.store_name || 'Magasin') !== storeName));
  };

  const handleChangeForm = (storeName, field, value) => {
    setStoreForms((prev) => ({
      ...prev,
      [storeName]: {
        city: prev[storeName]?.city ?? 'Libreville',
        address: prev[storeName]?.address ?? '',
        phone: prev[storeName]?.phone ?? '',
        payment_phone: prev[storeName]?.payment_phone ?? '',
        zone: prev[storeName]?.zone ?? '',
        notes: prev[storeName]?.notes ?? '',
        payment_flow: prev[storeName]?.payment_flow ?? '',
        payment_method: prev[storeName]?.payment_method ?? '',
        delivery_requested: prev[storeName]?.delivery_requested ?? true,
        [field]: value,
      },
    }));
  };

  const handleSubmitOrder = async (storeName) => {
    const items = cartByStore[storeName]?.items || [];
    if (!items.length) {
      setToast({ type: 'error', message: 'Ajoutez au moins un produit.' });
      return;
    }
    const storeId = items[0].store_id;
    if (!storeId) {
      setToast({ type: 'error', message: 'Magasin introuvable pour ce panier.' });
      return;
    }

    const form = storeForms[storeName] || {};
    const city = form.city?.trim() || 'Libreville';
    const delivery_address = form.address?.trim();
    const delivery_phone = form.phone?.trim();
    const payment_phone = form.payment_phone?.trim() || delivery_phone;
    const delivery_zone = form.zone?.trim();
    const payment_flow = form.payment_flow;
    const payment_method = form.payment_method;

    // Front validations avant envoi au backend
    if (!delivery_address) {
      setToast({ type: 'error', message: 'Renseignez une adresse de livraison.' });
      return;
    }
    if (!delivery_phone || delivery_phone.length < 6) {
      setToast({ type: 'error', message: 'Renseignez un numéro de téléphone valide.' });
      return;
    }
    if (payment_flow === 'platform_online' && (!payment_phone || payment_phone.length < 6)) {
      setToast({ type: 'error', message: 'Renseignez un numéro Mobile Money valide.' });
      return;
    }
    if (payment_flow === 'platform_online') {
      // Airtel ne peut pas envoyer sa demande de code à un numéro Moov (06…), et inversement.
      const digits = payment_phone.replace(/\D/g, '').replace(/^241(?=\d{8}$)/, '');
      const local = digits.length === 8 ? `0${digits}` : digits;
      if (payment_method === 'airtel_money' && local.startsWith('06')) {
        setToast({ type: 'error', message: `Le ${local} est un numéro Moov : choisissez Moov Money, ou un numéro Airtel (074, 076, 077).` });
        return;
      }
      if (payment_method === 'moov_money' && local.startsWith('07')) {
        setToast({ type: 'error', message: `Le ${local} est un numéro Airtel : choisissez Airtel Money, ou un numéro Moov (062, 065, 066).` });
        return;
      }
    }
    if (!delivery_zone) {
      setToast({ type: 'error', message: 'Renseignez une zone/quartier.' });
      return;
    }

    const payload = {
      store: storeId,
      city,
      delivery_address,
      delivery_phone,
      delivery_zone,
      delivery_requested: form.delivery_requested !== false,
      notes: form.notes || '',
      payment_flow,
      payment_method,
      items: items.map((it) => ({ product_id: it.id, quantity: it.quantity || 1 })),
    };

    setSubmitting((prev) => ({ ...prev, [storeName]: true }));
    try {
      const res = await createOrder(payload);
      if (res.success) {
        const orderId = res.data?.id;
        let paymentInfo = null;
        let paymentSteps = null;
        let payerPhoneUsed = payment_phone;
        let paymentInitFailed = false;
        let paymentInitError = '';

        // Init paiement reel selon le moyen choisi
        if (orderId && payment_flow === 'platform_online') {
          try {
            const payRes = await initPayment(orderId, {
              payment_method,
              phone_number: payment_phone,
            });
            paymentInfo = payRes?.data?.payment || payRes?.payment || null;
            paymentSteps = payRes?.data?.next_steps || null;
            payerPhoneUsed = payRes?.data?.payer_phone || payment_phone;
          } catch (payErr) {
            console.warn('Initialisation paiement echouee', payErr);
            paymentInitFailed = true;
            paymentInitError = getReadableApiErrorMessage(
              payErr?.error?.details,
              payErr?.error?.message || String(payErr)
            );
          }
        }

        // Retire ce panier magasin
        handleClearStoreCart(storeName);
        setStoreAlerts((prev) => {
          const next = { ...prev };
          delete next[storeName];
          return next;
        });
        let toastType = 'success';
        let toastMessage = 'Commande creee.';

        if (paymentInitFailed) {
          toastType = 'warning';
          toastMessage = paymentInitError
            ? `Commande creee, mais le paiement a echoue: ${paymentInitError}`
            : 'Commande creee, mais le paiement n a pas pu etre initialise. Reessayez depuis Mes commandes.';
        } else if (paymentInfo) {
          const providerLabel = payment_method === 'moov_money' ? 'Moov Money' : 'Airtel Money';
          const providerHint = paymentSteps?.message || `Paiement ${providerLabel} initialise.`;
          toastMessage = `${providerHint} Numero payeur: ${payerPhoneUsed}. Verifiez votre telephone et confirmez avec votre PIN.`;
        }

        setToast({ type: toastType, message: toastMessage });
        // Mobile Money : on ouvre tout de suite le suivi du paiement (en ligne : validation et
        // vérification automatique ; direct : code marchand et déclaration de l'ID de transaction).
        if (orderId && payment_method !== 'cash') {
          navigate(`/client/orders?pay=${orderId}`);
        }
      } else {
        const details = res.error?.details;
        const detailMsg = getReadableApiErrorMessage(details, res.error?.message);

        const closed = isStoreClosedMessage(detailMsg);
        // Champs manquants côté backend
        const missingFields = details && typeof details === 'object'
          ? Object.entries(details)
              .filter(([, errs]) => Array.isArray(errs) && errs.some((e) => String(e).toLowerCase().includes('requis') || String(e).toLowerCase().includes('required')))
              .map(([field]) => field)
          : [];

        if (closed) {
          setStoreAlerts((prev) => ({ ...prev, [storeName]: 'Ce magasin est actuellement fermé. Repassez plus tard.' }));
        } else if (missingFields.length) {
          setStoreAlerts((prev) => ({ ...prev, [storeName]: `Champs manquants : ${missingFields.join(', ')}` }));
        }

        const isWarning = closed || missingFields.length > 0;
        setToast({ type: isWarning ? 'warning' : 'error', message: detailMsg || 'Impossible de créer la commande' });
      }
    } catch (err) {
      const details = err?.error?.details;
      const msg = getReadableApiErrorMessage(details, err?.error?.message || String(err));
      const closed = isStoreClosedMessage(msg);
      const missingFields = details && typeof details === 'object'
        ? Object.entries(details)
            .filter(([, errs]) => Array.isArray(errs) && errs.some((e) => String(e).toLowerCase().includes('requis') || String(e).toLowerCase().includes('required')))
            .map(([field]) => field)
        : [];

      if (closed) {
        setStoreAlerts((prev) => ({ ...prev, [storeName]: 'Ce magasin est actuellement fermé. Repassez plus tard.' }));
      } else if (missingFields.length) {
        setStoreAlerts((prev) => ({ ...prev, [storeName]: `Champs manquants : ${missingFields.join(', ')}` }));
      }

      const isWarning = closed || missingFields.length > 0;
      setToast({ type: isWarning ? 'warning' : 'error', message: 'Erreur commande: ' + msg });
    } finally {
      setSubmitting((prev) => ({ ...prev, [storeName]: false }));
    }
  };

  if (loading) return <ClientLayout title="Dashboard"><LoadingSpinner /></ClientLayout>;

  if (error) {
    return (
      <ClientLayout title="Dashboard">
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      </ClientLayout>
    );
  }

  return (
    <ClientLayout title="Dashboard" userName={dashboardData?.profile?.name || 'Client'}>
      <style>{`
        @keyframes popIn { 0% { transform: translateY(12px) scale(0.98); opacity: 0; } 100% { transform: translateY(0) scale(1); opacity: 1; } }
      `}</style>

      {/* En-tête */}
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-gray-900">
          Bienvenue, {dashboardData?.profile?.name || 'Client'} !
        </h2>
        <p className="text-gray-600 mt-2">Voici un aperçu de vos commandes</p>
      </div>

        {/* Statistiques */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            title="Commandes totales"
            value={dashboardData?.stats?.total_orders || 0}
            icon={
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
              </svg>
            }
            bgColor="bg-slate-600"
          />
          <StatCard
            title="En cours"
            value={dashboardData?.stats?.active_orders || 0}
            icon={
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            }
            bgColor="bg-amber-500"
          />
          <StatCard
            title="Livrées"
            value={(dashboardData?.stats?.total_orders || 0) - (dashboardData?.stats?.active_orders || 0)}
            icon={
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            }
            bgColor="bg-emerald-500"
          />
          <StatCard
            title="Cashback disponible"
            value={formatCurrency(0)}
            icon={
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            }
            bgColor="bg-teal-500"
          />
        </div>

        {/* Commandes récentes */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-xl font-bold text-gray-900 mb-6">Commandes récentes</h3>
          
          {dashboardData?.recent_orders?.length > 0 ? (
            <>
            <div className="md:hidden space-y-3">
              {dashboardData.recent_orders.map((order) => {
                const statusBadge = getOrderStatusBadge(order.status);
                return (
                  <div key={order.id} className="border border-gray-200 rounded-lg p-4">
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <p className="text-base font-semibold text-gray-900">#{order.id}</p>
                        <p className="text-sm text-gray-700">{order.store_name}</p>
                        <p className="text-xs text-gray-500">{formatDateTime(order.created_at)}</p>
                      </div>
                      <p className="text-base font-semibold text-gray-900">{formatCurrency(order.total_amount)}</p>
                    </div>
                    <div className="mt-2">
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${statusBadge.className}`}>
                        {statusBadge.label}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="hidden md:block overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      N° Commande
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Magasin
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Date
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Montant
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Statut
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {dashboardData.recent_orders.map((order) => {
                    const statusBadge = getOrderStatusBadge(order.status);
                    return (
                      <tr key={order.id}>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          #{order.id}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {order.store_name}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatDateTime(order.created_at)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">
                          {formatCurrency(order.total_amount)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`px-3 py-1 rounded-full text-xs font-medium ${statusBadge.className}`}>
                            {statusBadge.label}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          <button className="text-indigo-600 hover:text-indigo-900 font-medium">
                            Voir détails
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            </>
          ) : (
            <div className="text-center py-12">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
              </svg>
              <p className="mt-4 text-gray-500">Aucune commande trouvée</p>
            </div>
          )}
        </div>

        {/* Paniers en cours (par magasin) */}
        <div className="bg-white rounded-lg shadow-md p-6 mt-8">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-xl font-bold text-gray-900">Mes paniers</h3>
              <p className="text-sm text-gray-500">Regroupés par magasin (porte-feuille)</p>
            </div>
          </div>

          {Object.keys(cartByStore).length === 0 ? (
            <div className="text-center py-10 text-gray-500">Aucun article dans le panier.</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {Object.entries(cartByStore).map(([storeName, data]) => (
                <div key={storeName} className="border border-gray-100 rounded-lg p-4 shadow-sm">
                  <div className="flex items-center justify-between mb-3">
                    <div>
                      <p className="text-sm text-indigo-600 font-semibold">{storeName}</p>
                      <p className="text-xs text-gray-500">{data.items.length} article(s)</p>
                    </div>
                    <span className="text-lg font-bold text-gray-900">{formatCurrency(data.total)}</span>
                  </div>

                  {storeAlerts[storeName] && (
                    <div className="mb-3 bg-amber-50 border border-amber-300 text-amber-900 text-sm px-3 py-2 rounded flex items-start gap-2 shadow-sm">
                      <span className="text-amber-600 font-bold">!</span>
                      <span className="font-semibold">{storeAlerts[storeName]}</span>
                    </div>
                  )}

                  <div className="divide-y divide-gray-100 max-h-60 overflow-y-auto">
                    {data.items.map((item) => (
                      <div key={`${storeName}-${item.id}`} className="py-3 flex justify-between items-start gap-3">
                        <div className="flex gap-3">
                          <div className="h-14 w-14 rounded-md bg-gray-100 overflow-hidden flex-shrink-0">
                            {item.image ? (
                              <img src={item.image} alt={item.name} className="h-full w-full object-cover" />
                            ) : (
                              <div className="h-full w-full flex items-center justify-center text-gray-400 text-xs">Img</div>
                            )}
                          </div>
                          <div className="space-y-1">
                            <p className="text-sm font-medium text-gray-900">{item.name}</p>
                            <p className="text-xs text-gray-500">{formatCurrency(item.price)}</p>
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => handleUpdateQuantity(storeName, item.id, -1)}
                                className="h-7 w-7 rounded border border-gray-200 text-gray-600 hover:bg-gray-50"
                                aria-label="Diminuer"
                              >
                                -
                              </button>
                              <span className="text-sm font-semibold text-gray-800 min-w-[24px] text-center">{item.quantity}</span>
                              <button
                                onClick={() => handleUpdateQuantity(storeName, item.id, 1)}
                                className="h-7 w-7 rounded border border-gray-200 text-gray-600 hover:bg-gray-50"
                                aria-label="Augmenter"
                              >
                                +
                              </button>
                              <button
                                onClick={() => handleRemoveItem(storeName, item.id)}
                                className="ml-2 text-xs text-red-500 hover:text-red-600"
                              >
                                Supprimer
                              </button>
                            </div>
                          </div>
                        </div>
                        <p className="text-sm font-semibold text-gray-900">{formatCurrency(item.lineTotal)}</p>
                      </div>
                    ))}
                  </div>

                  {/* Livraison souhaitée toggle */}
                  <div className="mt-4 mb-4 flex items-center gap-3 bg-blue-50 border border-blue-200 rounded-md px-4 py-3">
                    <input
                      type="checkbox"
                      id={`delivery-${storeName}`}
                      checked={storeForms[storeName]?.delivery_requested !== false}
                      onChange={(e) => handleChangeForm(storeName, 'delivery_requested', e.target.checked)}
                      className="h-5 w-5 text-blue-600 border-gray-300 rounded cursor-pointer"
                    />
                    <label htmlFor={`delivery-${storeName}`} className="flex-1 cursor-pointer">
                      <p className="font-semibold text-gray-900">&#x1F69A; Livraison souhaitée</p>
                      <p className="text-xs text-gray-600">Activée par défaut. Désactiver pour retrait au magasin.</p>
                    </label>
                  </div>

                  <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                    <input
                      className="w-full border border-gray-200 rounded-md px-3 py-2"
                      placeholder="Téléphone"
                      value={storeForms[storeName]?.phone || ''}
                      onChange={(e) => handleChangeForm(storeName, 'phone', e.target.value)}
                    />
                    <input
                      className="w-full border border-gray-200 rounded-md px-3 py-2"
                      placeholder="Téléphone payeur (Mobile Money)"
                      value={storeForms[storeName]?.payment_phone || ''}
                      onChange={(e) => handleChangeForm(storeName, 'payment_phone', e.target.value)}
                    />
                    <input
                      className="w-full border border-gray-200 rounded-md px-3 py-2"
                      placeholder="Ville"
                      value={storeForms[storeName]?.city || ''}
                      onChange={(e) => handleChangeForm(storeName, 'city', e.target.value)}
                    />
                    <input
                      className="w-full border border-gray-200 rounded-md px-3 py-2"
                      placeholder="Zone"
                      value={storeForms[storeName]?.zone || ''}
                      onChange={(e) => handleChangeForm(storeName, 'zone', e.target.value)}
                    />
                    <input
                      className="w-full border border-gray-200 rounded-md px-3 py-2"
                      placeholder="Adresse de livraison"
                      value={storeForms[storeName]?.address || ''}
                      onChange={(e) => handleChangeForm(storeName, 'address', e.target.value)}
                    />
                    <select
                      className="w-full border border-gray-200 rounded-md px-3 py-2"
                      value={`${storeForms[storeName]?.payment_flow || ''}|${storeForms[storeName]?.payment_method || ''}`}
                      onChange={(e) => {
                        const [flow, method] = e.target.value.split('|');
                        handleChangeForm(storeName, 'payment_flow', flow);
                        handleChangeForm(storeName, 'payment_method', method);
                      }}
                    >
                      {!paymentOptions[storeName]?.length && <option value="|">Aucune option disponible</option>}
                      {(paymentOptions[storeName] || []).map((option) => (
                        <option key={`${option.flow}-${option.method}`} value={`${option.flow}|${option.method}`}>
                          {option.label} — {METHOD_LABELS[option.method] || option.method}
                        </option>
                      ))}
                    </select>
                    <div className="md:col-span-2 text-xs text-gray-500 -mt-1">
                      {paymentHint(storeForms[storeName]?.payment_flow, storeForms[storeName]?.payment_method)}
                    </div>
                    <textarea
                      className="md:col-span-2 w-full border border-gray-200 rounded-md px-3 py-2"
                      placeholder="Notes"
                      rows={2}
                      value={storeForms[storeName]?.notes || ''}
                      onChange={(e) => handleChangeForm(storeName, 'notes', e.target.value)}
                    />
                  </div>

                  {storeAlerts[storeName] && (
                    <div className="mt-4 bg-amber-50 border border-amber-300 text-amber-900 text-sm px-3 py-2 rounded flex items-start gap-2 shadow-sm">
                      <span className="text-amber-600 font-bold">!</span>
                      <div>
                        <p className="font-semibold">Action bloquée</p>
                        <p>{storeAlerts[storeName]}</p>
                      </div>
                    </div>
                  )}

                  {/* Détail des frais */}
                  <div className="mt-4 bg-gray-50 border border-gray-200 rounded-md p-3 space-y-2">
                    <p className="text-xs font-semibold text-gray-700 uppercase">Détail du devis</p>
                    <div className="space-y-1 text-xs text-gray-700">
                      <div className="flex justify-between">
                        <span>Sous-total (articles)</span>
                        <span className="font-semibold">{formatCurrency(data.total)}</span>
                      </div>
                      
                      {/* Delivery fee */}
                      {storeForms[storeName]?.delivery_requested !== false && (
                        <div className="flex justify-between text-amber-700">
                          <span>&#x1F69A; Frais de livraison</span>
                          <span className="font-semibold">
                            {!zonesLoading ? formatCurrency(calculateDeliveryCost(storeForms[storeName]?.zone, storeForms[storeName]?.city || 'Libreville', data.items)) : 'Calcul...'}
                          </span>
                        </div>
                      )}
                      
                      {/* TOTAL */}
                      <div className="pt-2 border-t border-gray-300 flex justify-between font-bold text-gray-900 text-sm">
                        <span>TOTAL A PAYER</span>
                        <span className="text-base text-indigo-600">
                          {!zonesLoading ? formatCurrency(
                            calculateTotal(
                              data.total,
                              storeForms[storeName]?.delivery_requested !== false ? calculateDeliveryCost(storeForms[storeName]?.zone, storeForms[storeName]?.city || 'Libreville', data.items) : 0
                            )
                          ) : 'Calcul...'}
                        </span>
                      </div>
                    </div>
                    <p className="text-xs text-gray-500 italic pt-2">Tous les frais sont calculés et affichés ici. Aucune surcharge à la confirmation.</p>
                  </div>

                  <div className="mt-4 flex gap-2">
                    <button
                      onClick={() => handleSubmitOrder(storeName)}
                      disabled={!!submitting[storeName]}
                      className={`flex-1 text-sm font-medium px-4 py-2 rounded-md text-white ${submitting[storeName] ? 'bg-indigo-300' : 'bg-indigo-600 hover:bg-indigo-700'}`}
                    >
                       {submitting[storeName] ? 'Envoi...' : 'Passer la commande'}
                     </button>
                    <button
                      onClick={() => handleClearStoreCart(storeName)}
                      className="px-3 py-2 text-sm text-gray-600 hover:text-gray-800 border border-gray-200 rounded-md"
                    >
                      Vider ce panier
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

      {toast && (
        <div className="fixed bottom-5 right-5 z-50">
          <div
            className={`px-4 py-3 rounded-lg shadow-xl border text-sm font-medium text-white animate-[popIn_0.25s_ease-out]
              ${toast.type === 'success' ? 'bg-green-600 border-green-500'
                : toast.type === 'warning' ? 'bg-amber-500 border-amber-400'
                : 'bg-red-600 border-red-500'}`}
          >
            {toast.message}
          </div>
        </div>
      )}
    </ClientLayout>
  );
};

export default ClientDashboard;


