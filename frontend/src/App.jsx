import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import Register from './pages/Register';
import Home from './pages/Home';
import StoreDetail from './pages/StoreDetail';
import DashboardRedirect from './components/DashboardRedirect';
import GaboshopAI from './components/GaboshopAI';
import ClientDashboard from './pages/client/ClientDashboard';
import ClientOrders from './pages/client/ClientOrders';
import StoreDashboard from './pages/store/StoreDashboard';
import StoreProducts from './pages/store/StoreProducts';
import StoreOrders from './pages/store/StoreOrders';
import StoreSettings from './pages/store/StoreSettings';
import StoreProfile from './pages/store/StoreProfile';
import B2BProcurement from './pages/store/B2BProcurement';
import Finance from './pages/store/Finance';
import DeliveryDashboard from './pages/delivery/DeliveryDashboard';
import AdminDashboard from './pages/admin/AdminDashboard';
import ErrorBoundary from './components/ErrorBoundary';
import SubscriptionPlans from './pages/SubscriptionPlans';
import PrivateRoute from './components/guards/PrivateRoute';
import PublicRoute from './components/guards/PublicRoute';

const INACTIVITY_LIMIT = 30 * 60 * 1000; // 30 minutes

function App() {
  useEffect(() => {
    let timeoutId;

    const handleLogout = () => {
      if (sessionStorage.getItem('token')) {
        sessionStorage.removeItem('token');
        sessionStorage.removeItem('refresh_token');
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
      <Routes>
        {/* Routes publiques (BLOQUEES pour store_managers) */}
        <Route path="/" element={<PublicRoute><Home /></PublicRoute>} />
        <Route path="/stores/:id" element={<PublicRoute><StoreDetail /></PublicRoute>} />
        
        {/* Auth (accessible à tous) */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/dashboard" element={<DashboardRedirect />} />

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
        
        {/* Plans (accessible à tous) */}
        <Route path="/plans" element={<SubscriptionPlans />} />
      </Routes>
      <GaboshopAI />
    </Router>
  );
}

export default App;
