import React, { Suspense, lazy, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link } from 'react-router-dom';
import AndroidBackButton from './components/AndroidBackButton';
import ScrollToTop from './components/ScrollToTop';
import Login from './pages/Login';
import ForgotPassword from './pages/ForgotPassword';
import Register from './pages/Register';
import Home from './pages/Home';
import StoreCategories from './pages/StoreCategories';
import Stores from './pages/Stores';
import StoreDetail from './pages/StoreDetail';
import ProductsRedirect from './pages/ProductsRedirect';
import DashboardRedirect from './components/DashboardRedirect';
import GaboshopAI from './components/GaboshopAI';
import FeedbackCenter from './components/FeedbackCenter';
import AIAlertBanner from './components/AIAlertBanner';
import MobileTabBar from './components/MobileTabBar';
import { AIContextProvider } from './context/AIContext';
import { NotificationProvider } from './context/NotificationContext';
import { registerServiceWorker } from './utils/push';
const ClientDashboard = lazy(() => import('./pages/client/ClientDashboard'));
const ClientOrders = lazy(() => import('./pages/client/ClientOrders'));
const StoreDashboard = lazy(() => import('./pages/store/StoreDashboard'));
const StoreProducts = lazy(() => import('./pages/store/StoreProducts'));
const StoreOrders = lazy(() => import('./pages/store/StoreOrders'));
const StoreSettings = lazy(() => import('./pages/store/StoreSettings'));
const StoreProfile = lazy(() => import('./pages/store/StoreProfile'));
const B2BProcurement = lazy(() => import('./pages/store/B2BProcurement'));
const Finance = lazy(() => import('./pages/store/Finance'));
const StoreSubscriptionPlans = lazy(() => import('./pages/store/SubscriptionPlans'));
const DeliveryDashboard = lazy(() => import('./pages/delivery/DeliveryDashboard'));
const AdminDashboard = lazy(() => import('./pages/admin/AdminDashboard'));
import ErrorBoundary from './components/ErrorBoundary';
import PrivateRoute from './components/guards/PrivateRoute';
import PublicRoute from './components/guards/PublicRoute';
import authStorage from './utils/authStorage';
const CGU = lazy(() => import('./pages/legal/CGU'));
const Confidentialite = lazy(() => import('./pages/legal/Confidentialite'));
const MentionsLegales = lazy(() => import('./pages/legal/MentionsLegales'));
const SuppressionCompte = lazy(() => import('./pages/legal/SuppressionCompte'));
const DeleteAccount = lazy(() => import('./pages/DeleteAccount'));
const Notifications = lazy(() => import('./pages/Notifications'));

// Les espaces client, commerce, livreur et admin se chargent à la demande :
// le premier écran du site reste léger.
const PageLoader = () => (
  <div className="flex min-h-[50vh] items-center justify-center">
    <div className="h-8 w-8 animate-spin rounded-full border-4 border-green-600 border-t-transparent" />
  </div>
);

// Adresse inconnue (lien ancien, faute de frappe) : un message et deux sorties, au lieu d'une page blanche.
const NotFound = () => (
  <div className="flex min-h-[70vh] flex-col items-center justify-center gap-3 px-6 text-center">
    <p className="text-5xl" aria-hidden="true">🧭</p>
    <h1 className="text-xl font-bold text-gray-900">Cette page n’existe pas</h1>
    <p className="max-w-sm text-sm text-gray-600">Le lien est peut-être ancien ou mal écrit. Revenez à l’accueil ou à votre espace.</p>
    <div className="flex gap-2">
      <Link to="/" className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white">Accueil</Link>
      <Link to="/dashboard" className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-semibold text-gray-800">Mon espace</Link>
    </div>
  </div>
);

const CLIENT_ONLY = ['client'];
const INACTIVITY_LIMIT = 30 * 60 * 1000; // 30 minutes

function App() {
  // Le service qui reçoit les alertes (téléphone et ordinateur) est prêt dès l'ouverture.
  useEffect(() => { registerServiceWorker(); }, []);

  useEffect(() => {
    let timeoutId;

    const handleLogout = () => {
      if (authStorage.getItem('token')) {
        authStorage.removeItem('token');
        authStorage.removeItem('refresh_token');
        window.location.href = '/login';
      }
    };

    const resetTimer = () => {
      if (timeoutId) clearTimeout(timeoutId);
      timeoutId = setTimeout(handleLogout, INACTIVITY_LIMIT);
    };

    // Events to listen for activity
    const events = ['mousedown', 'keypress', 'scroll', 'touchstart', 'click'];

    // Add listeners
    events.forEach(event => {
      document.addEventListener(event, resetTimer);
    });

    // Initial start
    resetTimer();

    // Cleanup
    return () => {
      if (timeoutId) clearTimeout(timeoutId);
      events.forEach(event => {
        document.removeEventListener(event, resetTimer);
      });
    };
  }, []);

  return (
    <Router>
      <ScrollToTop />
      <AndroidBackButton />
      <AIContextProvider>
        <NotificationProvider>
        <Suspense fallback={<PageLoader />}>
        <Routes>
        {/* Routes publiques (BLOQUEES pour store_managers) */}
        <Route path="/" element={<PublicRoute><Home /></PublicRoute>} />
        <Route path="/products" element={<PublicRoute><ProductsRedirect /></PublicRoute>} />
        <Route path="/categories" element={<PublicRoute allowStoreManager><StoreCategories /></PublicRoute>} />
        <Route path="/boutiques" element={<PublicRoute allowStoreManager><Stores /></PublicRoute>} />
        <Route path="/stores/:id" element={<PublicRoute allowStoreManager><StoreDetail /></PublicRoute>} />
        
        {/* Auth (accessible à tous) */}
        <Route path="/login" element={<Login />} />
        <Route path="/mot-de-passe-oublie" element={<ForgotPassword />} />
        <Route path="/register" element={<Register />} />
        <Route path="/dashboard" element={<DashboardRedirect />} />

        {/* Pages légales (publiques, accessibles à tous) */}
        <Route path="/cgu" element={<CGU />} />
        <Route path="/confidentialite" element={<Confidentialite />} />
        <Route path="/mentions-legales" element={<MentionsLegales />} />
        <Route path="/suppression-compte" element={<SuppressionCompte />} />
        <Route path="/supprimer-mon-compte" element={<DeleteAccount />} />

        {/* Notifications : tous les comptes connectés */}
        <Route path="/notifications" element={
          <PrivateRoute>
            <Notifications />
          </PrivateRoute>
        } />

        {/* Panier : il vit dans l'espace client (lien de la barre du bas, de l'en-tête et de l'assistant) */}
        <Route path="/cart" element={
          <PrivateRoute allowedRoles={CLIENT_ONLY}>
            <Navigate to="/client/dashboard#paniers" replace />
          </PrivateRoute>
        } />

        {/* Client routes (PROTEGEES) */}
        <Route path="/client/dashboard" element={
          <PrivateRoute allowedRoles={['client']}>
            <ClientDashboard />
          </PrivateRoute>
        } />
        <Route path="/client/orders" element={
          <PrivateRoute allowedRoles={['client']}>
            <ClientOrders />
          </PrivateRoute>
        } />

        {/* Store routes (PROTEGEES) */}
        <Route path="/store/dashboard" element={
          <PrivateRoute allowedRoles={['store_manager']}>
            <StoreDashboard />
          </PrivateRoute>
        } />
        <Route path="/store/products" element={
          <PrivateRoute allowedRoles={['store_manager']}>
            <StoreProducts />
          </PrivateRoute>
        } />
        <Route path="/store/orders" element={
          <PrivateRoute allowedRoles={['store_manager']}>
            <StoreOrders />
          </PrivateRoute>
        } />
        <Route path="/store/b2b" element={
          <PrivateRoute allowedRoles={['store_manager']}>
            <B2BProcurement />
          </PrivateRoute>
        } />
        <Route path="/store/finance" element={
          <PrivateRoute allowedRoles={['store_manager']}>
            <Finance />
          </PrivateRoute>
        } />
        <Route path="/store/settings" element={
          <PrivateRoute allowedRoles={['store_manager']}>
            <StoreSettings />
          </PrivateRoute>
        } />
        <Route path="/store/settings/profile" element={
          <PrivateRoute allowedRoles={['store_manager']}>
            <StoreProfile />
          </PrivateRoute>
        } />
        <Route path="/store/subscription" element={
          <PrivateRoute allowedRoles={['store_manager']}>
            <StoreSubscriptionPlans />
          </PrivateRoute>
        } />

        {/* Delivery routes (PROTEGEES) */}
        <Route path="/delivery/dashboard" element={
          <PrivateRoute allowedRoles={['delivery_agent']}>
            <DeliveryDashboard />
          </PrivateRoute>
        } />

        {/* Admin routes (PROTEGEES) */}
        <Route path="/admin/dashboard" element={
          <PrivateRoute allowedRoles={['admin']}>
            <ErrorBoundary>
              <AdminDashboard />
            </ErrorBoundary>
          </PrivateRoute>
        } />
        
        {/* Plans (store managers only) */}
        <Route path="/plans" element={
          <PrivateRoute allowedRoles={['store_manager']}>
            <StoreSubscriptionPlans />
          </PrivateRoute>
        } />
        <Route path="*" element={<NotFound />} />
        </Routes>
        </Suspense>
        <MobileTabBar />
        <AIAlertBanner />
        <GaboshopAI />
        <FeedbackCenter />
        </NotificationProvider>
      </AIContextProvider>
    </Router>
  );
}

export default App;
