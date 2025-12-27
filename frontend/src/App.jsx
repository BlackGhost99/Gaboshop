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
import DeliveryDashboard from './pages/delivery/DeliveryDashboard';
import AdminDashboard from './pages/admin/AdminDashboard';
import ErrorBoundary from './components/ErrorBoundary';
import SubscriptionPlans from './pages/SubscriptionPlans';

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
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/dashboard" element={<DashboardRedirect />} />

        <Route path="/stores/:id" element={<StoreDetail />} />

        <Route path="/client/dashboard" element={<ClientDashboard />} />
        <Route path="/client/orders" element={<ClientOrders />} />

        {/* Store Routes */}
        <Route path="/store/dashboard" element={<StoreDashboard />} />
        <Route path="/store/products" element={<StoreProducts />} />
        <Route path="/store/orders" element={<StoreOrders />} />
        <Route path="/store/settings" element={<StoreSettings />} />
        <Route path="/store/settings/profile" element={<StoreProfile />} />

        <Route path="/delivery/dashboard" element={<DeliveryDashboard />} />

        <Route path="/admin/dashboard" element={
          <ErrorBoundary>
            <AdminDashboard />
          </ErrorBoundary>
        } />
        <Route path="/plans" element={<SubscriptionPlans />} />
      </Routes>
      <GaboshopAI />
    </Router>
  );
}

export default App;
