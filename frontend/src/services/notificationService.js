import api from './api';

// Liste par pages : { data, has_more, unread_count }. `before` = id de la plus ancienne déjà affichée.
export const fetchNotifications = async ({ limit, before, unread, type } = {}) => {
  const params = {};
  if (limit) params.limit = limit;
  if (before) params.before = before;
  if (unread) params.unread = 1;
  if (type) params.type = type;
  const response = await api.get('/notifications/', { params });
  return response.data;
};

// Appel léger pour le badge : { unread_count, latest_id }.
export const fetchUnreadCount = async () => {
  const response = await api.get('/notifications/unread-count/');
  return response.data?.data || { unread_count: 0, latest_id: 0 };
};

export const markAllNotificationsRead = async () => {
  const response = await api.post('/notifications/mark-all-read/');
  return response.data;
};

export const markNotificationRead = async (id) => {
  const response = await api.post(`/notifications/${id}/read/`);
  return response.data;
};

export const deleteNotification = async (id) => {
  const response = await api.delete(`/notifications/${id}/`);
  return response.data;
};

// --- Alertes sur l'appareil (téléphone, ordinateur) ---

export const getPushConfig = async () => (await api.get('/notifications/push/config/')).data?.data || {};

export const subscribePush = async (subscription) => (await api.post('/notifications/push/subscribe/', {
  endpoint: subscription.endpoint,
  keys: subscription.keys,
  user_agent: typeof navigator !== 'undefined' ? navigator.userAgent : '',
})).data;

export const unsubscribePush = async (endpoint) => (await api.post('/notifications/push/unsubscribe/', { endpoint })).data;

export const sendTestPush = async () => (await api.post('/notifications/push/test/')).data?.data || {};

// --- Réglages ---

export const getNotificationPreferences = async () => (await api.get('/notifications/preferences/')).data?.data || {};

export const setAnnouncementsPreference = async (announcements) => (
  await api.patch('/notifications/preferences/', { announcements })
).data?.data || {};

// --- Annonces de l'administration ---

export const getAdminAnnouncements = async () => (await api.get('/admin/announcements/')).data?.data || {};

export const sendAdminAnnouncement = async (payload) => (await api.post('/admin/announcements/', payload)).data?.data || {};
