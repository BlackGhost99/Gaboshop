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

export const updateStoreB2BSettings = async (storeId, payload) => {
  const res = await api.patch(`/admin/stores/${storeId}/b2b-settings/`, payload);
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

// ============================================================================
// SUBSCRIPTION PLANS API
// ============================================================================

// Subscription Plans (B2C)
export const getSubscriptionPlans = async () => {
  const res = await api.get('/admin/subscription-plans/');
  return res.data;
};

export const createSubscriptionPlan = async (payload) => {
  const res = await api.post('/admin/subscription-plans/create/', payload);
  return res.data;
};

export const getSubscriptionPlanDetail = async (planId) => {
  const res = await api.get(`/admin/subscription-plans/${planId}/`);
  return res.data;
};

export const updateSubscriptionPlan = async (planId, payload) => {
  const res = await api.patch(`/admin/subscription-plans/${planId}/update/`, payload);
  return res.data;
};

export const deleteSubscriptionPlan = async (planId) => {
  const res = await api.delete(`/admin/subscription-plans/${planId}/delete/`);
  return res.data;
};

// B2B Subscription Plans
export const getB2BSubscriptionPlans = async () => {
  const res = await api.get('/admin/b2b-subscription-plans/');
  return res.data;
};

export const createB2BSubscriptionPlan = async (payload) => {
  const res = await api.post('/admin/b2b-subscription-plans/create/', payload);
  return res.data;
};

export const getB2BSubscriptionPlanDetail = async (planId) => {
  const res = await api.get(`/admin/b2b-subscription-plans/${planId}/`);
  return res.data;
};

export const updateB2BSubscriptionPlan = async (planId, payload) => {
  const res = await api.patch(`/admin/b2b-subscription-plans/${planId}/update/`, payload);
  return res.data;
};

export const deleteB2BSubscriptionPlan = async (planId) => {
  const res = await api.delete(`/admin/b2b-subscription-plans/${planId}/delete/`);
  return res.data;
};

// Store Subscriptions (B2C)
export const getStoreSubscriptions = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.store_id) params.append('store_id', filters.store_id);
  if (filters.plan_id) params.append('plan_id', filters.plan_id);
  if (filters.status) params.append('status', filters.status);
  if (filters.search) params.append('search', filters.search);
  
  const res = await api.get('/admin/store-subscriptions/', { params });
  return res.data;
};

export const createStoreSubscription = async (payload) => {
  const res = await api.post('/admin/store-subscriptions/create/', payload);
  return res.data;
};

export const updateStoreSubscription = async (subscriptionId, payload) => {
  const res = await api.patch(`/admin/store-subscriptions/${subscriptionId}/`, payload);
  return res.data;
};

// B2B Store Subscriptions
export const getB2BStoreSubscriptions = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.store_id) params.append('store_id', filters.store_id);
  if (filters.plan_id) params.append('plan_id', filters.plan_id);
  if (filters.status) params.append('status', filters.status);
  if (filters.search) params.append('search', filters.search);
  
  const res = await api.get('/admin/b2b-store-subscriptions/', { params });
  return res.data;
};

export const createB2BStoreSubscription = async (payload) => {
  const res = await api.post('/admin/b2b-store-subscriptions/create/', payload);
  return res.data;
};

export const updateB2BStoreSubscription = async (subscriptionId, payload) => {
  const res = await api.patch(`/admin/b2b-store-subscriptions/${subscriptionId}/`, payload);
  return res.data;
};

// ============================================================================
// B2B ADMIN API
// ============================================================================

// B2B Categories
export const getB2BCategories = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.is_active !== undefined) params.append('is_active', filters.is_active);
  if (filters.search) params.append('search', filters.search);
  
  const res = await api.get('/admin/b2b/categories/', { params });
  return res.data;
};

export const createB2BCategory = async (payload) => {
  const res = await api.post('/admin/b2b/categories/create/', payload);
  return res.data;
};

export const updateB2BCategory = async (categoryId, payload) => {
  const res = await api.patch(`/admin/b2b/categories/${categoryId}/`, payload);
  return res.data;
};

export const deleteB2BCategory = async (categoryId) => {
  const res = await api.delete(`/admin/b2b/categories/${categoryId}/delete/`);
  return res.data;
};

// B2B Orders
export const getB2BOrders = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.store_id) params.append('store_id', filters.store_id);
  if (filters.source_store_id) params.append('source_store_id', filters.source_store_id);
  if (filters.status) params.append('status', filters.status);
  if (filters.date_from) params.append('date_from', filters.date_from);
  if (filters.date_to) params.append('date_to', filters.date_to);
  if (filters.search) params.append('search', filters.search);
  
  const res = await api.get('/admin/b2b/orders/', { params });
  return res.data;
};

export const getB2BOrderDetail = async (orderId) => {
  const res = await api.get(`/admin/b2b/orders/${orderId}/`);
  return res.data;
};

export const updateB2BOrderStatus = async (orderId, status) => {
  const res = await api.patch(`/admin/b2b/orders/${orderId}/status/`, { status });
  return res.data;
};

// ============================================================================
// FINANCE ADMIN API
// ============================================================================

// Reversements
export const getReversements = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.store_id) params.append('store_id', filters.store_id);
  if (filters.status) params.append('status', filters.status);
  if (filters.date_from) params.append('date_from', filters.date_from);
  if (filters.date_to) params.append('date_to', filters.date_to);
  
  const res = await api.get('/admin/finance/reversements/', { params });
  return res.data;
};

export const createReversement = async (payload) => {
  const res = await api.post('/admin/finance/reversements/create/', payload);
  return res.data;
};

export const updateReversement = async (reversementId, payload) => {
  const res = await api.patch(`/admin/finance/reversements/${reversementId}/`, payload);
  return res.data;
};

// Commissions
export const getCommissions = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.store_id) params.append('store_id', filters.store_id);
  if (filters.is_settled !== undefined) params.append('is_settled', filters.is_settled);
  if (filters.date_from) params.append('date_from', filters.date_from);
  if (filters.date_to) params.append('date_to', filters.date_to);
  
  const res = await api.get('/admin/finance/commissions/', { params });
  return res.data;
};

export const settleCommission = async (commissionId) => {
  const res = await api.patch(`/admin/finance/commissions/${commissionId}/settle/`);
  return res.data;
};

// Category Commission Change Logs
export const getCategoryCommissionLogs = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.category_id) params.append('category_id', filters.category_id);
  if (filters.date_from) params.append('date_from', filters.date_from);
  if (filters.date_to) params.append('date_to', filters.date_to);
  
  const res = await api.get('/admin/finance/category-commission-logs/', { params });
  return res.data;
};

// Delivery Payouts
export const updateDeliveryPayout = async (payoutId, payload) => {
  const res = await api.patch(`/admin/finance/delivery-payouts/${payoutId}/`, payload);
  return res.data;
};

// Sponsored Products
export const createSponsoredProduct = async (payload) => {
  const res = await api.post('/admin/finance/sponsored-products/create/', payload);
  return res.data;
};

export const updateSponsoredProduct = async (sponsoredId, payload) => {
  const res = await api.patch(`/admin/finance/sponsored-products/${sponsoredId}/`, payload);
  return res.data;
};

// Client Credits
export const getClientCredits = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.client_id) params.append('client_id', filters.client_id);
  if (filters.status) params.append('status', filters.status);
  if (filters.credit_type) params.append('credit_type', filters.credit_type);
  if (filters.date_from) params.append('date_from', filters.date_from);
  if (filters.date_to) params.append('date_to', filters.date_to);
  
  const res = await api.get('/admin/finance/client-credits/', { params });
  return res.data;
};

export const createClientCredit = async (payload) => {
  const res = await api.post('/admin/finance/client-credits/create/', payload);
  return res.data;
};

export const updateClientCredit = async (creditId, payload) => {
  const res = await api.patch(`/admin/finance/client-credits/${creditId}/`, payload);
  return res.data;
};

// Forfaits
export const getForfaits = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.is_active !== undefined) params.append('is_active', filters.is_active);
  
  const res = await api.get('/admin/finance/forfaits/', { params });
  return res.data;
};

export const createForfait = async (payload) => {
  const res = await api.post('/admin/finance/forfaits/create/', payload);
  return res.data;
};

export const updateForfait = async (forfaitId, payload) => {
  const res = await api.patch(`/admin/finance/forfaits/${forfaitId}/`, payload);
  return res.data;
};

// Client Forfaits
export const getClientForfaits = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.user_id) params.append('user_id', filters.user_id);
  if (filters.forfait_id) params.append('forfait_id', filters.forfait_id);
  if (filters.status) params.append('status', filters.status);
  
  const res = await api.get('/admin/finance/client-forfaits/', { params });
  return res.data;
};

export const createClientForfait = async (payload) => {
  const res = await api.post('/admin/finance/client-forfaits/create/', payload);
  return res.data;
};

export const updateClientForfait = async (clientForfaitId, payload) => {
  const res = await api.patch(`/admin/finance/client-forfaits/${clientForfaitId}/`, payload);
  return res.data;
};

// ============================================================================
// PAYMENTS ADMIN API
// ============================================================================

// Payment Callback Logs
export const getPaymentCallbacks = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.order_id) params.append('order_id', filters.order_id);
  if (filters.processed !== undefined) params.append('processed', filters.processed);
  if (filters.signature_valid !== undefined) params.append('signature_valid', filters.signature_valid);
  if (filters.date_from) params.append('date_from', filters.date_from);
  if (filters.date_to) params.append('date_to', filters.date_to);
  if (filters.transaction_id) params.append('transaction_id', filters.transaction_id);
  
  const res = await api.get('/admin/payment-callbacks/', { params });
  return res.data;
};

export const getPaymentCallbackDetail = async (logId) => {
  const res = await api.get(`/admin/payment-callbacks/${logId}/`);
  return res.data;
};

// Payouts
export const getPayouts = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.user_id) params.append('user_id', filters.user_id);
  if (filters.payout_type) params.append('payout_type', filters.payout_type);
  if (filters.status) params.append('status', filters.status);
  if (filters.date_from) params.append('date_from', filters.date_from);
  if (filters.date_to) params.append('date_to', filters.date_to);
  
  const res = await api.get('/admin/payouts/', { params });
  return res.data;
};

export const createPayout = async (payload) => {
  const res = await api.post('/admin/payouts/create/', payload);
  return res.data;
};

export const updatePayout = async (payoutId, payload) => {
  const res = await api.patch(`/admin/payouts/${payoutId}/`, payload);
  return res.data;
};

// ============================================================================
// B2B PROFILE API (from b2b/api/views.py)
// ============================================================================

export const getB2BProfile = async (storeId) => {
  const res = await api.get(`/b2b/profiles/${storeId}/`);
  return res.data;
};

export const createB2BProfile = async (payload) => {
  const res = await api.post('/b2b/profiles/', payload);
  return res.data;
};

export const updateB2BProfile = async (storeId, payload) => {
  const res = await api.put(`/b2b/profiles/${storeId}/update/`, payload);
  return res.data;
};

export const activateB2BProfile = async (storeId) => {
  const res = await api.post(`/b2b/profiles/${storeId}/activate/`);
  return res.data;
};

export const deactivateB2BProfile = async (storeId) => {
  const res = await api.post(`/b2b/profiles/${storeId}/deactivate/`);
  return res.data;
};

// ============================================================================
// B2B PRODUCT PRICING API (from b2b/api/views.py)
// ============================================================================

export const getB2BProductPricings = async (storeId) => {
  const res = await api.get(`/b2b/pricing/${storeId}/`);
  return res.data;
};

export const createB2BProductPricing = async (payload) => {
  const res = await api.post('/b2b/pricing/', payload);
  return res.data;
};

export const updateB2BProductPricing = async (pricingId, payload) => {
  const res = await api.put(`/b2b/pricing/${pricingId}/`, payload);
  return res.data;
};

export const deleteB2BProductPricing = async (pricingId) => {
  const res = await api.delete(`/b2b/pricing/${pricingId}/delete/`);
  return res.data;
};

export const bulkCreateB2BProductPricing = async (payload) => {
  const res = await api.post('/b2b/pricing/bulk/', payload);
  return res.data;
};

