import api from './api';

// Mes demandes (l'admin reçoit toutes les demandes, priorité d'abord). Filtres : status, priority, mine.
export const fetchTickets = async (params = {}) => (await api.get('/support/tickets/', { params })).data?.data || [];

export const fetchTicket = async (id) => (await api.get(`/support/tickets/${id}/`)).data?.data;

export const createTicket = async ({ subject, message, category }) => (
  await api.post('/support/tickets/', { subject, message, category })
).data;

export const replyToTicket = async (id, message) => (
  await api.post(`/support/tickets/${id}/replies/`, { message })
).data?.data;

export const setTicketStatus = async (id, status) => (
  await api.patch(`/support/tickets/${id}/`, { status })
).data?.data;

// Contact direct de Gaboshop : le numéro n'est donné qu'aux forfaits avec support prioritaire.
export const fetchSupportContact = async () => (await api.get('/support/contact/')).data?.data || null;
