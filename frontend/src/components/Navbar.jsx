import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { fetchNotifications, markAllNotificationsRead, markNotificationRead, deleteNotification } from '../services/notificationService';
import { formatDateTime } from '../utils/helpers';

const POLL_INTERVAL_MS = 20000;

const Navbar = ({ userRole, userName }) => {
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Notification Detail Modal
  const [selectedNotification, setSelectedNotification] = useState(null);
  const [showNotificationModal, setShowNotificationModal] = useState(false);

  const unreadCount = useMemo(
    () => notifications.filter((n) => !n.is_read).length,
    [notifications]
  );

  const loadNotifications = useCallback(async (isBackground = false) => {
    if (!isBackground) {
      setLoading(true);
      setError(null);
    }
    try {
      const res = await fetchNotifications();
      const items = res?.data || res?.results || [];
      setNotifications(Array.isArray(items) ? items : []);
    } catch (e) {
      // En cas d'erreur réseau/401, on garde l'UI silencieuse pour éviter le bruit
      setError(null);
    } finally {
      if (!isBackground) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    let mounted = true;
    loadNotifications();

    const intervalId = setInterval(() => {
      if (mounted) {
        loadNotifications(true);
      }
    }, POLL_INTERVAL_MS);

    return () => {
      mounted = false;
      clearInterval(intervalId);
    };
  }, [loadNotifications]);

  const handleToggle = () => setOpen((prev) => !prev);

  const handleMarkAll = async () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
    try {
      await markAllNotificationsRead();
    } catch (e) {
      // Silent fail; UI already optimistic
    }
  };

  const handleMarkOne = async (id) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
    try {
      await markNotificationRead(id);
    } catch (e) {
      // Silent fail; next poll will reconcile
    }
  };

  const handleOpenNotification = async (notif) => {
    setSelectedNotification(notif);
    setShowNotificationModal(true);
    setOpen(false); // Fermer le dropdown
    if (!notif.is_read) {
      await handleMarkOne(notif.id);
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

  const getBadgeColor = (type) => {
    const map = {
      order: 'bg-slate-100 text-slate-800',
      delivery: 'bg-emerald-100 text-emerald-800',
      payment: 'bg-amber-100 text-amber-800',
      warning: 'bg-red-100 text-red-700',
      info: 'bg-gray-100 text-gray-700',
    };
    return map[type] || map.info;
  };
  const getRoleName = (role) => {
    const roleMap = {
      CLIENT: 'Client',
      GERANT: 'Gérant',
      LIVREUR: 'Livreur',
      ADMIN: 'Admin',
    };
    return roleMap[role] || 'Utilisateur';
  };

  return (
    <nav className="bg-white shadow-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center space-x-8">
            <h1 className="text-2xl font-bold text-slate-900">GABOSHOP</h1>
            <a href="/" className="text-slate-900 hover:text-slate-700 font-medium">
              Accueil
            </a>
          </div>
          <div className="flex items-center space-x-4 relative">
            <div className="relative">
              <button
                onClick={handleToggle}
                className="relative p-2 rounded-full hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-300"
                aria-label="Notifications"
              >
                <svg className="h-6 w-6 text-slate-900" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="1.5"
                    d="M15 17h5l-1.4-1.4A2 2 0 0118 14.2V11a6 6 0 10-12 0v3.2a2 2 0 01-.6 1.4L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                  />
                </svg>
                {unreadCount > 0 && (
                  <span className="absolute -top-1 -right-1 inline-flex items-center justify-center px-1.5 py-0.5 text-xs font-bold leading-none text-white bg-red-600 rounded-full">
                    {unreadCount}
                  </span>
                )}
              </button>

              {open && (
                <div className="absolute right-0 mt-3 w-96 bg-white shadow-xl border border-gray-100 rounded-lg z-50">
                  <div className="flex items-center justify-between px-4 py-3 border-b">
                    <div>
                      <p className="text-sm font-semibold text-gray-900">Notifications</p>
                      <p className="text-xs text-gray-500">{unreadCount} non lues</p>
                    </div>
                    <button
                      onClick={handleMarkAll}
                      className="text-xs font-medium text-slate-900 hover:text-slate-700"
                    >
                      Tout marquer lu
                    </button>
                  </div>

                  <div className="max-h-96 overflow-y-auto divide-y">
                    {loading && (
                      <div className="p-4 text-sm text-gray-500">Chargement...</div>
                    )}
                    {!loading && !notifications.length && !error && (
                      <div className="p-4 text-sm text-gray-500">Aucune notification pour le moment.</div>
                    )}
                    {notifications.map((notif) => (
                      <button
                        key={notif.id}
                        onClick={() => handleOpenNotification(notif)}
                        className={`w-full text-left px-4 py-3 hover:bg-gray-50 transition ${notif.is_read ? 'bg-white' : 'bg-slate-50/60'}`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <div className="flex items-center gap-2">
                              {!notif.is_read && <span className="w-2 h-2 bg-slate-900 rounded-full flex-shrink-0" />}
                              <p className="text-sm font-semibold text-gray-900">{notif.title}</p>
                            </div>
                            <p className="text-sm text-gray-600 mt-1 line-clamp-2">{notif.body}</p>
                            <p className="text-xs text-gray-500 mt-1">{formatDateTime(notif.created_at)}</p>
                          </div>
                          <div className="flex flex-col items-end gap-2">
                            <span className={`text-[10px] px-2 py-1 rounded-full ${getBadgeColor(notif.notif_type)}`}>
                              {notif.notif_type}
                            </span>
                            <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <span className="text-sm text-slate-900">
              {getRoleName(userRole)} - {userName}
            </span>
            <button
              className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-md text-sm font-medium"
              onClick={() => {
                sessionStorage.removeItem('token');
                sessionStorage.removeItem('refresh_token');
                window.location.href = '/login';
              }}
            >
              Déconnexion
            </button>
          </div>
        </div>
      </div>

      {/* Notification Detail Modal */}
      {showNotificationModal && selectedNotification && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
              <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
                  {/* Header */}
                  <div className={`px-6 py-4 border-b ${
                      selectedNotification.is_read ? 'bg-gray-50' : 'bg-slate-50'
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
                              <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${
                                  selectedNotification.notif_type === 'delivery' ? 'bg-slate-100 text-slate-700' :
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
    </nav>
  );
};

export default Navbar;
