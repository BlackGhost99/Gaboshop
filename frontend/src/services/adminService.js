import api from './api';

export const getAdminSummary = async () => {
  const res = await api.get('/admin/summary/');
  return res.data;
};

export const getAdminUsers = async (type) => {
  const res = await api.get('/admin/users/', { params: { type } });
  return res.data;
};

export const getAdminOrders = async (status) => {
  const res = await api.get('/admin/orders/', { params: { status } });
  return res.data;
};

export const getAdminFinancials = async () => {
  const res = await api.get('/admin/financials/');
  return res.data;
};

export const getStoreCategories = async () => {
  const res = await api.get('/admin/store-categories/');
  return res.data;
};

export const createStoreCategory = async (payload) => {
  const res = await api.post('/admin/store-categories/', payload);
  return res.data;
};

export const updateStoreCategory = async (id, payload) => {
  const res = await api.patch('/admin/store-categories/', { id, ...payload });
  return res.data;
};

export const deleteStoreCategory = async (id) => {
  const res = await api.delete('/admin/store-categories/', { params: { id } });
  return res.data;
};

export const getAllProductCategories = async () => {
  const res = await api.get('/admin/product-categories/');
  return res.data;
};

export const getStoreProductCategories = async (storeId) => {
  if (!storeId) return { data: [] };
  const res = await api.get(`/stores/${storeId}/categories/`);
  return res.data;
};

export const getAdminPayments = async () => {
  const res = await api.get('/admin/payments/');
  return res.data;
};

export const getAdminDeliveries = async () => {
  const res = await api.get('/admin/deliveries/');
  return res.data;
};

export const createAdminUser = async (payload) => {
  const res = await api.post('/admin/users/', payload);
  return res.data;
};

export const updateAdminUser = async (id, payload) => {
  const res = await api.patch('/admin/users/', { id, ...payload });
  return res.data;
};

export const deleteAdminUser = async (id) => {
  const res = await api.delete('/admin/users/', { data: { id } });
  return res.data;
};

export const getAdminStores = async () => {
  const res = await api.get('/admin/stores/list/');
  return res.data;
};

export const createAdminStore = async (payload) => {
  const res = await api.post('/admin/stores/', payload);
  return res.data;
};

export const updateAdminStore = async (id, payload) => {
  const res = await api.patch('/admin/stores/', { id, ...payload });
  return res.data;
};

export const deleteAdminStore = async (id) => {
  const res = await api.delete('/admin/stores/', { params: { id } });
  return res.data;
};

export const getAdminProducts = async () => {
  const res = await api.get('/admin/products/');
  return res.data;
};

export const createAdminProduct = async (payload) => {
  const res = await api.post('/admin/products/', payload);
  return res.data;
};

export const updateAdminProduct = async (id, payload) => {
  const res = await api.patch('/admin/products/', { id, ...payload });
  return res.data;
};

export const deleteAdminProduct = async (id) => {
  const res = await api.delete('/admin/products/', { params: { id } });
  return res.data;
};

export const getSystemSettings = async () => {
  const res = await api.get('/settings/');
  return res.data;
};

export const updateSystemSettings = async (payload) => {
  const res = await api.patch('/settings/', payload);
  return res.data;
};

// Finance API
export const getFinanceDashboard = async () => {
  const res = await api.get('/finance/dashboard/');
  return res.data;
};

export const getTransactions = async () => {
  const res = await api.get('/finance/transactions/');
  return res.data;
};

export const getCommissionsByStore = async () => {
  const res = await api.get('/finance/commissions/');
  return res.data;
};

export const getDeliveryPayouts = async () => {
  const res = await api.get('/finance/delivery-payouts/');
  return res.data;
};

export const getSubscriptions = async () => {
  const res = await api.get('/finance/subscriptions/');
  return res.data;
};

export const getSponsoredProducts = async () => {
  const res = await api.get('/finance/sponsored-products/');
  return res.data;
};

export const getRevenueBreakdown = async () => {
  const res = await api.get('/finance/revenue-breakdown/');
  return res.data;
};

// Orders Admin Management API
export const getOrderStats = async () => {
  const res = await api.get('/admin/orders/stats/');
  return res.data;
};

export const getOrdersList = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.status) params.append('status', filters.status);
  if (filters.city) params.append('city', filters.city);
  if (filters.store_id) params.append('store_id', filters.store_id);
  if (filters.date_range) params.append('date_range', filters.date_range);
  if (filters.payment_method) params.append('payment_method', filters.payment_method);
  
  const res = await api.get('/admin/orders/list/', { params });
  return res.data;
};

export const getOrderDetail = async (orderId) => {
  const res = await api.get(`/admin/orders/${orderId}/`);
  return res.data;
};

export const assignDelivery = async (orderId, payload) => {
  const res = await api.post(`/admin/orders/${orderId}/assign-delivery/`, payload);
  return res.data;
};

export const updateOrderStatus = async (orderId, status) => {
  const res = await api.patch(`/admin/orders/${orderId}/status/`, { status });
  return res.data;
};

export const cancelOrder = async (orderId, reason = '') => {
  const res = await api.post(`/admin/orders/${orderId}/cancel/`, { reason });
  return res.data;
};

export const getOrdersByStore = async () => {
  const res = await api.get('/admin/orders/by-store/');
  return res.data;
};

export const getDeliveryAgentStats = async () => {
  const res = await api.get('/admin/delivery-agents/stats/');
  return res.data;
};

// Stores Admin Management API
export const getStoresListAdmin = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.search) params.append('search', filters.search);
  if (filters.category) params.append('category', filters.category);
  if (filters.city) params.append('city', filters.city);
  if (filters.status) params.append('status', filters.status);
  if (filters.sort) params.append('sort', filters.sort);
  
  const res = await api.get('/admin/stores/list/', { params });
  return res.data;
};

export const getStoreDetailAdmin = async (storeId) => {
  const res = await api.get(`/admin/stores/${storeId}/detail/`);
  return res.data;
};

export const createStoreAdmin = async (payload) => {
  const res = await api.post('/admin/stores/create/', payload);
  return res.data;
};

export const updateStoreAdmin = async (storeId, payload) => {
  const res = await api.patch(`/admin/stores/${storeId}/update/`, payload);
  return res.data;
};

export const deactivateStoreAdmin = async (storeId) => {
  const res = await api.post(`/admin/stores/${storeId}/deactivate/`);
  return res.data;
};

export const activateStoreAdmin = async (storeId) => {
  const res = await api.post(`/admin/stores/${storeId}/activate/`);
  return res.data;
};

export const deleteStoreAdmin = async (storeId, hardDelete = false) => {
  const res = await api.delete(`/admin/stores/${storeId}/`, { params: { hard_delete: hardDelete } });
  return res.data;
};

export const getStoreProductsAdmin = async (storeId, filters = {}) => {
  const params = new URLSearchParams();
  if (filters.search) params.append('search', filters.search);
  if (filters.category) params.append('category', filters.category);
  
  const res = await api.get(`/admin/stores/${storeId}/products/`, { params });
  return res.data;
};

export const getStoreOrdersAdmin = async (storeId, filters = {}) => {
  const params = new URLSearchParams();
  if (filters.status) params.append('status', filters.status);
  if (filters.date_range) params.append('date_range', filters.date_range);
  
  const res = await api.get(`/admin/stores/${storeId}/orders/`, { params });
  return res.data;
};

export const getStoreDeliveryAgentsAdmin = async (storeId) => {
  const res = await api.get(`/admin/stores/${storeId}/delivery-agents/`);
  return res.data;
};

// Products Admin Management API
export const getProductStats = async () => {
  const res = await api.get('/admin/products/stats/');
  return res.data;
};

export const getProductsListAdmin = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.search) params.append('search', filters.search);
  if (filters.category) params.append('category', filters.category);
  if (filters.store_id) params.append('store_id', filters.store_id);
  if (filters.status) params.append('status', filters.status);
  if (filters.stock) params.append('stock', filters.stock);
  if (filters.promo) params.append('promo', filters.promo);
  if (filters.price_min) params.append('price_min', filters.price_min);
  if (filters.price_max) params.append('price_max', filters.price_max);
  if (filters.sort) params.append('sort', filters.sort);
  
  const res = await api.get('/admin/products/list/', { params });
  return res.data;
};

export const getProductDetailAdmin = async (productId) => {
  const res = await api.get(`/admin/products/${productId}/detail/`);
  return res.data;
};

export const createProductAdmin = async (payload) => {
  const res = await api.post('/admin/products/create/', payload);
  return res.data;
};

export const updateProductAdmin = async (productId, payload) => {
  const res = await api.patch(`/admin/products/${productId}/update/`, payload);
  return res.data;
};

export const activateProductAdmin = async (productId) => {
  const res = await api.post(`/admin/products/${productId}/activate/`);
  return res.data;
};

export const deactivateProductAdmin = async (productId) => {
  const res = await api.post(`/admin/products/${productId}/deactivate/`);
  return res.data;
};

export const deleteProductAdmin = async (productId, hardDelete = false) => {
  const res = await api.delete(`/admin/products/${productId}/`, { params: { hard_delete: hardDelete } });
  return res.data;
};

export const bulkActionsProductsAdmin = async (action, productIds, stockValue = null) => {
  const payload = { action, product_ids: productIds };
  if (stockValue !== null) {
    payload.stock_value = stockValue;
  }
  const res = await api.post('/admin/products/bulk-actions/', payload);
  return res.data;
};

export const getDeliveryAgents = async () => {
  // Prefer the admin users endpoint (already working in dashboard) to fetch delivery agents
  const res = await api.get('/admin/users/', { params: { type: 'delivery_agent' } });
  // Support wrapped {data: [...]} or raw arrays
  return res.data?.data || res.data;
};

export const createDeliveryAgent = async (payload) => {
  const res = await api.post('/delivery/agents/', payload);
  return res.data;
};

export const updateDeliveryAgent = async (id, payload) => {
  const res = await api.patch(`/delivery/agents/${id}/`, payload);
  return res.data;
};

export const toggleDeliveryAgentStatus = async (id, isActive) => {
  const res = await api.patch(`/admin/users/${id}/`, { is_active: !isActive });
  return res.data;
};

export const getDeliveryStats = async () => {
  const res = await api.get('/delivery/stats/');
  return res.data;
};

