import api from './api';

export const fetchNotifications = async () => {
  const response = await api.get('/notifications/');
  return response.data;
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
