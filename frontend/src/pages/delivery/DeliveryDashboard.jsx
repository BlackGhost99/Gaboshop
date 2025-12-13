import React, { useState, useEffect, useCallback } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

import StatCard from '../../components/StatCard';
import LoadingSpinner from '../../components/LoadingSpinner';
import AssignedOrdersList from '../../components/AssignedOrdersList';
import ProofUploadModal from '../../components/ProofUploadModal';
import { getDeliveryDashboard, updateDeliveryProfile } from '../../services/dashboardService';
import { startDelivery, acceptDelivery } from '../../services/deliveryService';
import { formatCurrency, getDeliveryStatusBadge } from '../../utils/helpers';
import { fetchNotifications, markNotificationRead, markAllNotificationsRead, deleteNotification } from '../../services/notificationService';

// Fix for default marker icon
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

const NOTIF_POLL_MS = 20000;

const DeliveryDashboard = () => {
  const [loading, setLoading] = useState(true);
  const [dashboardData, setDashboardData] = useState(null);
  const [error, setError] = useState(null);
  const [isAvailable, setIsAvailable] = useState(true);
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' ou 'assigned'

  // Notification Detail Modal State
  const [selectedNotification, setSelectedNotification] = useState(null);
  const [showNotificationModal, setShowNotificationModal] = useState(false);

  // Profile Modal State
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [profileForm, setProfileForm] = useState({
    first_name: '',
    last_name: '',
    email: '',
    profile_picture: null
  });
  const [previewImage, setPreviewImage] = useState(null);

  // Proof Upload Modal State
  const [showProofModal, setShowProofModal] = useState(false);
  const [selectedDelivery, setSelectedDelivery] = useState(null);

  const [notifications, setNotifications] = useState([]);
  const [notifLoading, setNotifLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState({});

  useEffect(() => {
    fetchDashboard();
  }, []);

  const loadNotifications = useCallback(async (isBackground = false) => {
    if (!isBackground) setNotifLoading(true);
    try {
      const res = await fetchNotifications();
      const items = res?.data || res?.results || [];
      setNotifications(Array.isArray(items) ? items : []);
    } catch {
      /* silent */
    } finally {
      if (!isBackground) setNotifLoading(false);
    }
  }, []);

  useEffect(() => {
    let mounted = true;
    loadNotifications();
    const id = setInterval(() => mounted && loadNotifications(true), NOTIF_POLL_MS);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, [loadNotifications]);

  const fetchDashboard = async () => {
    try {
      setLoading(true);
      const response = await getDeliveryDashboard();
      if (response.success) {
        setDashboardData(response.data);
        setIsAvailable(response.data?.status?.is_available || false);

        // Init profile form
        if (response.data.profile) {
          setProfileForm({
            first_name: response.data.profile.first_name || '',
            last_name: response.data.profile.last_name || '',
            email: response.data.profile.email || '',
            profile_picture: null // File input is separate
          });
          setPreviewImage(response.data.profile.profile_picture);
        }
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

  const toggleAvailability = async () => {
    // TODO: Appeler l'API pour changer la disponibilité
    setIsAvailable(!isAvailable);
  };

  const handleStartDelivery = async (deliveryId) => {
    try {
      setActionLoading(prev => ({ ...prev, [deliveryId]: true }));
      const response = await startDelivery(deliveryId);
      if (response.success) {
        // Rafraîchir le dashboard
        fetchDashboard();
      } else {
        alert(response.error || 'Erreur lors du démarrage');
      }
    } catch (err) {
      alert('Erreur: ' + err.message);
    } finally {
      setActionLoading(prev => ({ ...prev, [deliveryId]: false }));
    }
  };

  const handleAcceptDelivery = async (deliveryId) => {
    try {
      setActionLoading(prev => ({ ...prev, [deliveryId]: true }));
      const res = await acceptDelivery(deliveryId);
      if (res.success) {
        alert('✓ Livraison acceptée avec succès !');
        fetchDashboard();
      } else {
        alert(`❌ ${res.error?.message || res.error || 'Erreur lors de l\'acceptation'}`);
      }
    } catch (err) {
      alert('Erreur: ' + err.message);
    } finally {
      setActionLoading(prev => ({ ...prev, [deliveryId]: false }));
    }
  };

  const handleRejectDelivery = async (deliveryId) => {
    if (!window.confirm('Confirmer le refus de cette livraison ?')) return;
    try {
      setActionLoading(prev => ({ ...prev, [deliveryId]: true }));
      // TODO: Appeler endpoint de refus
      console.log('Refuser livraison', deliveryId);
      fetchDashboard();
    } catch (err) {
      alert('Erreur: ' + err.message);
    } finally {
      setActionLoading(prev => ({ ...prev, [deliveryId]: false }));
    }
  };

  const handleCompleteDelivery = async (deliveryId) => {
    // Trouver la livraison pour passer au modal
    const delivery = dashboardData?.active_delivery?.id === deliveryId
      ? dashboardData.active_delivery
      : null;

    if (delivery) {
      setSelectedDelivery(delivery);
      setShowProofModal(true);
    } else {
      alert('Livraison non trouvée');
    }
  };

  const handleProofSuccess = () => {
    setShowProofModal(false);
    setSelectedDelivery(null);
    fetchDashboard(); // Rafraîchir les données
  };

  const deliveryNotifs = notifications.filter((n) => n.notif_type === 'delivery');
  const unreadCount = deliveryNotifs.filter((n) => !n.is_read).length;

  const unreadBadge = (
    <span className={`ml-3 inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${unreadCount > 0 ? 'bg-slate-100 text-slate-700' : 'bg-gray-100 text-gray-500'}`}>
      Missions: {unreadCount}
    </span>
  );

  const handleMarkRead = async (id) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
    try { await markNotificationRead(id); } catch {
      // Silently ignore errors
    }
  };

  const handleMarkAll = async () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    try { await markAllNotificationsRead(); } catch {
      /* silent */
    }
  };

  const handleOpenNotification = async (notif) => {
    setSelectedNotification(notif);
    setShowNotificationModal(true);
    if (!notif.is_read) {
      await handleMarkRead(notif.id);
    }
  };

  const handleDeleteNotification = async (id) => {
    if (!window.confirm('Supprimer cette notification ?')) return;
    try {
      await deleteNotification(id);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
      setShowNotificationModal(false);
      setSelectedNotification(null);
    } catch (error) {
      console.error('Erreur lors de la suppression:', error);
      alert('Erreur lors de la suppression de la notification');
    }
  };

  const handleProfileChange = (e) => {
    const { name, value } = e.target;
    setProfileForm(prev => ({ ...prev, [name]: value }));
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setProfileForm(prev => ({ ...prev, profile_picture: file }));
      setPreviewImage(URL.createObjectURL(file));
    }
  };

  const handleProfileSubmit = async (e) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append('first_name', profileForm.first_name);
    formData.append('last_name', profileForm.last_name);
    formData.append('email', profileForm.email);
    if (profileForm.profile_picture) {
      formData.append('profile_picture', profileForm.profile_picture);
    }

    try {
      const res = await updateDeliveryProfile(formData);
      if (res.success) {
        setDashboardData(prev => ({
          ...prev,
          profile: {
            ...prev.profile,
            ...res.data
          }
        }));
        setShowProfileModal(false);
        alert("Profil mis à jour !");
      }
    } catch (error) {
      console.error("Error updating profile", error);
      alert("Erreur lors de la mise à jour du profil");
    }
  };

  const handleLogout = () => {
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('refresh_token');
    window.location.href = '/login';
  };

  if (loading) return <LoadingSpinner />;

  if (error) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded">
          {error}
        </div>
      </div>
    );
  }

  const profile = dashboardData?.profile || {};

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Custom Header */}
      <div className="bg-white shadow-sm px-4 py-3 flex justify-between items-center">
        <div className="flex items-center space-x-3 cursor-pointer hover:bg-gray-50 p-2 rounded-lg transition-colors" onClick={() => setShowProfileModal(true)}>
          <div className="h-10 w-10 rounded-full overflow-hidden bg-gray-200 border border-gray-300">
            {profile.profile_picture ? (
              <img src={profile.profile_picture} alt="Profile" className="h-full w-full object-cover" />
            ) : (
              <svg className="h-full w-full text-gray-400" fill="currentColor" viewBox="0 0 24 24">
                <path d="M24 20.993V24H0v-2.996A14.977 14.977 0 0112.004 15c4.904 0 9.26 2.354 11.996 5.993zM16.002 8.999a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            )}
          </div>
          <span className="font-semibold text-gray-800 text-lg">{profile.first_name || 'Livreur'}</span>
        </div>

        <button
          onClick={handleLogout}
          className="text-gray-500 hover:text-red-600 font-medium text-sm"
        >
          Déconnexion
        </button>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* En-tête avec disponibilité */}
        <div className="mb-8 flex justify-between items-center">
          <div>
            <h2 className="text-3xl font-bold text-gray-900">
              Dashboard
            </h2>
            <p className="text-gray-600 mt-2">Gérez vos livraisons en temps réel</p>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-sm font-medium text-gray-700">Disponibilité:</span>
            <button
              onClick={toggleAvailability}
              aria-label={isAvailable ? 'Rendre indisponible' : 'Se rendre disponible'}
              aria-pressed={isAvailable}
              title={isAvailable ? 'Rendre indisponible' : 'Se rendre disponible'}
              className={`relative inline-flex h-10 w-20 items-center rounded-full transition-colors ${isAvailable ? 'bg-green-500' : 'bg-gray-300'
                }`}
            >
              <span className="sr-only">Basculer la disponibilité</span>
              <span
                className={`inline-block h-8 w-8 transform rounded-full bg-white transition-transform ${isAvailable ? 'translate-x-11' : 'translate-x-1'
                  }`}
              />
            </button>
            <span className={`text-sm font-semibold ${isAvailable ? 'text-green-600' : 'text-gray-600'}`}>
              {isAvailable ? 'Disponible' : 'Indisponible'}
            </span>
            {unreadBadge}
          </div>
        </div>

        {/* Statistiques */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            title="Livraisons du jour"
            value={dashboardData?.stats?.completed_today || 0}
            icon={
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
              </svg>
            }
            bgColor="bg-slate-600"
          />
          <StatCard
            title="Revenus du jour"
            value={formatCurrency(dashboardData?.stats?.earnings_today || 0)}
            icon={
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            }
            bgColor="bg-emerald-500"
          />
          <StatCard
            title="En cours"
            value={dashboardData?.active_delivery ? 1 : 0}
            icon={
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0" />
              </svg>
            }
            bgColor="bg-amber-500"
          />
          <StatCard
            title="Total livraisons"
            value={dashboardData?.stats?.total_deliveries || 0}
            icon={
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            }
            bgColor="bg-teal-500"
          />
        </div>

        {/* Tabs */}
        <div className="mb-6 border-b border-gray-200">
          <div className="flex gap-4">
            <button
              onClick={() => setActiveTab('overview')}
              className={`px-4 py-3 font-medium transition-colors border-b-2 ${activeTab === 'overview'
                  ? 'border-slate-900 text-slate-900'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
            >
              Vue d'ensemble
            </button>
            <button
              onClick={() => setActiveTab('assigned')}
              className={`px-4 py-3 font-medium transition-colors border-b-2 ${activeTab === 'assigned'
                  ? 'border-slate-900 text-slate-900'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
            >
              Mes missions
            </button>
          </div>
        </div>

        {/* Content - Overview */}
        {activeTab === 'overview' && (
          <>
            {/* Missions / notifications */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-8">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-xl font-bold text-gray-900">Missions & notifications</h3>
                  <p className="text-sm text-gray-500">Tâches qui te sont confiées</p>
                </div>
                <button
                  onClick={handleMarkAll}
                  className="text-xs font-semibold text-slate-900 hover:text-slate-700"
                >
                  Tout marquer lu
                </button>
              </div>

              {notifLoading && <p className="text-sm text-gray-500">Chargement...</p>}
              {!notifLoading && deliveryNotifs.length === 0 && (
                <p className="text-sm text-gray-500">Aucune mission pour le moment.</p>
              )}

              <div className="space-y-3">
                {deliveryNotifs.map((n) => (
                  <div
                    key={n.id}
                    onClick={() => handleOpenNotification(n)}
                    className={`border rounded-lg p-3 cursor-pointer hover:shadow-md transition-shadow ${n.is_read ? 'bg-white' : 'bg-slate-50/60 border-slate-100'
                      }`}
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          {!n.is_read && (
                            <span className="w-2 h-2 bg-slate-900 rounded-full"></span>
                          )}
                          <p className="text-sm font-semibold text-gray-900">{n.title}</p>
                        </div>
                        <p className="text-sm text-gray-700 mt-1 line-clamp-2">{n.body}</p>
                        <div className="flex items-center gap-3 mt-2">
                          {n.metadata?.from && n.metadata?.to && (
                            <p className="text-xs text-gray-500">{n.metadata.from} → {n.metadata.to}</p>
                          )}
                          {n.order && (
                            <p className="text-xs text-gray-500">Commande #{n.order}</p>
                          )}
                          <p className="text-xs text-gray-400">
                            {new Date(n.created_at).toLocaleDateString('fr-FR', {
                              day: '2-digit',
                              month: 'short',
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </p>
                        </div>
                      </div>
                      <svg
                        className="w-5 h-5 text-gray-400 flex-shrink-0"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </div>
                ))}
              </div>
              {unreadCount > 0 && (
                <p className="text-xs text-slate-900 mt-3">{unreadCount} mission(s) non lue(s)</p>
              )}
            </div>

            {/* Livraison active */}
            <div className="bg-white rounded-lg shadow-md p-6 mb-8">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-bold text-gray-900">Livraison en cours</h3>
                <button className="bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded-md text-sm font-medium">
                  Rafraîchir
                </button>
              </div>

              {dashboardData?.active_delivery ? (
                <div className="space-y-4">
                  {/* MAP ADDITION */}
                  <div className="h-64 w-full rounded-xl overflow-hidden shadow-inner mb-4 z-0 relative">
                    <MapContainer
                      center={[0.4162, 9.4673]}
                      zoom={13}
                      style={{ height: '100%', width: '100%' }}
                      scrollWheelZoom={false}
                    >
                      <TileLayer
                        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                      />
                      <Marker position={[0.4162, 9.4673]}>
                        <Popup>
                          Vous êtes ici (Simulé)
                        </Popup>
                      </Marker>
                      <Marker position={[0.42, 9.48]}>
                        <Popup>
                          Destination Client
                        </Popup>
                      </Marker>
                    </MapContainer>
                  </div>

                  {(() => {
                    const delivery = dashboardData.active_delivery;
                    const statusBadge = getDeliveryStatusBadge(delivery.status);
                    return (
                      <div key={delivery.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                        <div className="flex justify-between items-start mb-4">
                          <div>
                            <h4 className="text-lg font-semibold text-gray-900">
                              Commande #{delivery.order_number}
                            </h4>
                            <p className="text-sm text-gray-600 mt-1">
                              {delivery.store_name}
                            </p>
                          </div>
                          <span className={`px-3 py-1 rounded-full text-xs font-medium ${statusBadge.className}`}>
                            {statusBadge.label}
                          </span>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                          <div>
                            <p className="text-sm text-gray-600">Adresse de livraison:</p>
                            <p className="text-sm font-medium text-gray-900">{delivery.delivery_address}</p>
                          </div>
                          <div>
                            <p className="text-sm text-gray-600">Client:</p>
                            <p className="text-sm font-medium text-gray-900">{delivery.client_name}</p>
                            <p className="text-sm text-gray-600">{delivery.client_phone}</p>
                          </div>
                        </div>

                        <div className="flex justify-between items-center pt-4 border-t border-gray-200">
                          <div>
                            <span className="text-sm text-gray-600">Rémunération: </span>
                            <span className="text-lg font-bold text-green-600">
                              {formatCurrency(delivery.fee || 1200)}
                            </span>
                          </div>
                          <div className="space-x-2">
                            {delivery.status === 'assigned' && (
                              <>
                                <button
                                  onClick={() => handleAcceptDelivery(delivery.id)}
                                  disabled={actionLoading[delivery.id]}
                                  className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-md text-sm font-medium disabled:opacity-50 transition"
                                >
                                  {actionLoading[delivery.id] ? 'Traitement...' : 'Accepter'}
                                </button>
                                <button
                                  onClick={() => handleRejectDelivery(delivery.id)}
                                  disabled={actionLoading[delivery.id]}
                                  className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-md text-sm font-medium disabled:opacity-50 transition"
                                >
                                  {actionLoading[delivery.id] ? 'Traitement...' : 'Refuser'}
                                </button>
                              </>
                            )}
                            {delivery.status === 'accepted' && (
                              <button
                                onClick={() => handleStartDelivery(delivery.id)}
                                disabled={actionLoading[delivery.id]}
                                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium disabled:opacity-50 transition"
                              >
                                {actionLoading[delivery.id] ? 'Traitement...' : '📦 Récupérer le colis'}
                              </button>
                            )}
                            {delivery.status === 'picked_up' && (
                              <button
                                onClick={() => handleStartDelivery(delivery.id)}
                                disabled={actionLoading[delivery.id]}
                                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium disabled:opacity-50 transition"
                              >
                                {actionLoading[delivery.id] ? 'Traitement...' : '🚗 Démarrer la livraison'}
                              </button>
                            )}
                            {delivery.status === 'in_transit' && (
                              <button
                                onClick={() => handleCompleteDelivery(delivery.id)}
                                disabled={actionLoading[delivery.id]}
                                className="bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded-md text-sm font-medium disabled:opacity-50 transition"
                              >
                                {actionLoading[delivery.id] ? 'Traitement...' : '✓ Confirmer livraison'}
                              </button>
                            )}
                            {delivery.can_complete_delivery && delivery.status !== 'in_transit' && (
                              <button
                                onClick={() => handleCompleteDelivery(delivery.id)}
                                disabled={actionLoading[delivery.id]}
                                className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-md text-sm font-medium disabled:opacity-50 transition"
                                title={`Statut: ${delivery.status}`}
                              >
                                {actionLoading[delivery.id] ? 'Traitement...' : '✓ Confirmer livraison (preuve prête)'}
                              </button>
                            )}
                          </div>
                        </div>
                      </div>
                    );
                  })()}
                </div>
              ) : (
                <div className="text-center py-12">
                  <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path d="M9 17a2 2 0 11-4 0 2 2 0 014 0zM19 17a2 2 0 11-4 0 2 2 0 014 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16V6a1 1 0 00-1-1H4a1 1 0 00-1 1v10a1 1 0 001 1h1m8-1a1 1 0 01-1 1H9m4-1V8a1 1 0 011-1h2.586a1 1 0 01.707.293l3.414 3.414a1 1 0 01.293.707V16a1 1 0 01-1 1h-1m-6-1a1 1 0 001 1h1M5 17a2 2 0 104 0m-4 0a2 2 0 114 0m6 0a2 2 0 104 0m-4 0a2 2 0 114 0" />
                  </svg>
                  <p className="mt-4 text-gray-500">Aucune livraison en cours</p>
                  <p className="text-sm text-gray-400 mt-2">
                    {isAvailable ? 'Activez votre disponibilité pour recevoir des livraisons' : 'Vous êtes disponible, les livraisons arrivent bientôt'}
                  </p>
                </div>
              )}
            </div>
          </>
        )}

        {/* Content - Assigned Orders */}
        {activeTab === 'assigned' && (
          <div className="mb-8">
            <AssignedOrdersList />
          </div>
        )}
      </div>

      {/* Profile Modal */}
      {showProfileModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-md">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-bold">Mon Profil</h3>
              <button onClick={() => setShowProfileModal(false)} className="text-gray-500 hover:text-gray-700">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleProfileSubmit} className="space-y-4">
              <div className="flex justify-center mb-4">
                <div className="relative">
                  <div className="h-24 w-24 rounded-full overflow-hidden bg-gray-100 border border-gray-300">
                    {previewImage ? (
                      <img src={previewImage} alt="Preview" className="h-full w-full object-cover" />
                    ) : (
                      <svg className="h-full w-full text-gray-400" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M24 20.993V24H0v-2.996A14.977 14.977 0 0112.004 15c4.904 0 9.26 2.354 11.996 5.993zM16.002 8.999a4 4 0 11-8 0 4 4 0 018 0z" />
                      </svg>
                    )}
                  </div>
                  <label className="absolute bottom-0 right-0 bg-slate-900 text-white p-1 rounded-full cursor-pointer hover:bg-slate-800">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 13a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                    <input type="file" className="hidden" onChange={handleFileChange} accept="image/*" />
                  </label>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">Prénom</label>
                <input
                  type="text"
                  name="first_name"
                  value={profileForm.first_name}
                  onChange={handleProfileChange}
                  className="mt-1 block w-full border rounded-md shadow-sm p-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Nom</label>
                <input
                  type="text"
                  name="last_name"
                  value={profileForm.last_name}
                  onChange={handleProfileChange}
                  className="mt-1 block w-full border rounded-md shadow-sm p-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Email</label>
                <input
                  type="email"
                  name="email"
                  value={profileForm.email}
                  onChange={handleProfileChange}
                  className="mt-1 block w-full border rounded-md shadow-sm p-2"
                />
              </div>

              <div className="pt-4">
                <button
                  type="submit"
                  className="w-full bg-slate-900 text-white py-2 px-4 rounded-md hover:bg-slate-800 font-medium"
                >
                  Enregistrer
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Notification Detail Modal */}
      {showNotificationModal && selectedNotification && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
            {/* Header */}
            <div className={`px-6 py-4 border-b ${selectedNotification.is_read ? 'bg-gray-50' : 'bg-slate-50'
              }`}>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    {!selectedNotification.is_read && (
                      <span className="w-2 h-2 bg-slate-900 rounded-full"></span>
                    )}
                    <h3 className="text-lg font-bold text-gray-900">
                      {selectedNotification.title}
                    </h3>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {new Date(selectedNotification.created_at).toLocaleString('fr-FR', {
                      day: '2-digit',
                      month: 'long',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </p>
                </div>
                <button
                  onClick={() => setShowNotificationModal(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Body */}
            <div className="px-6 py-4 overflow-y-auto" style={{ maxHeight: 'calc(90vh - 180px)' }}>
              <div className="space-y-4">
                {/* Type Badge */}
                <div className="flex items-center gap-2">
                  <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${selectedNotification.notif_type === 'delivery' ? 'bg-indigo-100 text-indigo-700' :
                      selectedNotification.notif_type === 'order' ? 'bg-blue-100 text-blue-700' :
                        selectedNotification.notif_type === 'payment' ? 'bg-green-100 text-green-700' :
                          selectedNotification.notif_type === 'warning' ? 'bg-yellow-100 text-yellow-700' :
                            'bg-gray-100 text-gray-700'
                    }`}>
                    {selectedNotification.notif_type === 'delivery' && '🚚 Livraison'}
                    {selectedNotification.notif_type === 'order' && '📦 Commande'}
                    {selectedNotification.notif_type === 'payment' && '💰 Paiement'}
                    {selectedNotification.notif_type === 'warning' && '⚠️ Alerte'}
                    {selectedNotification.notif_type === 'info' && 'ℹ️ Info'}
                  </span>
                  {selectedNotification.is_read && (
                    <span className="text-xs text-gray-500">✓ Lu</span>
                  )}
                </div>

                {/* Message Content */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">
                    {selectedNotification.body}
                  </p>
                </div>

                {/* Metadata */}
                {(selectedNotification.order || selectedNotification.metadata) && (
                  <div className="border-t pt-4 space-y-2">
                    <h4 className="text-sm font-semibold text-gray-700">Détails</h4>

                    {selectedNotification.order && (
                      <div className="flex items-center gap-2 text-sm">
                        <span className="font-medium text-gray-600">Commande:</span>
                        <span className="text-gray-900 font-mono">#{selectedNotification.order}</span>
                      </div>
                    )}

                    {selectedNotification.metadata?.from && (
                      <div className="flex items-center gap-2 text-sm">
                        <span className="font-medium text-gray-600">Départ:</span>
                        <span className="text-gray-900">{selectedNotification.metadata.from}</span>
                      </div>
                    )}

                    {selectedNotification.metadata?.to && (
                      <div className="flex items-center gap-2 text-sm">
                        <span className="font-medium text-gray-600">Arrivée:</span>
                        <span className="text-gray-900">{selectedNotification.metadata.to}</span>
                      </div>
                    )}

                    {selectedNotification.metadata?.distance && (
                      <div className="flex items-center gap-2 text-sm">
                        <span className="font-medium text-gray-600">Distance:</span>
                        <span className="text-gray-900">{selectedNotification.metadata.distance}</span>
                      </div>
                    )}

                    {selectedNotification.metadata?.amount && (
                      <div className="flex items-center gap-2 text-sm">
                        <span className="font-medium text-gray-600">Montant:</span>
                        <span className="text-gray-900 font-semibold">{selectedNotification.metadata.amount}</span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Footer Actions */}
            <div className="px-6 py-4 bg-gray-50 border-t flex items-center justify-between">
              <button
                onClick={() => handleDeleteNotification(selectedNotification.id)}
                className="flex items-center gap-2 text-sm font-medium text-red-600 hover:text-red-700 hover:bg-red-50 px-3 py-2 rounded-md transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Supprimer
              </button>
              <button
                onClick={() => setShowNotificationModal(false)}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 font-medium text-sm"
              >
                Fermer
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Proof Upload Modal */}
      {showProofModal && selectedDelivery && (
        <ProofUploadModal
          delivery={selectedDelivery}
          onClose={() => {
            setShowProofModal(false);
            setSelectedDelivery(null);
          }}
          onSuccess={handleProofSuccess}
        />
      )}
    </div>
  );
};

export default DeliveryDashboard;
