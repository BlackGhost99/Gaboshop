import api from './api';

/**
 * Finance Service - API calls for Store Finance module
 */

// ============ SUMMARY ============
export const getFinanceSummary = async (filters = {}) => {
  try {
    const params = new URLSearchParams(filters).toString();
    const res = await api.get(`/store/finance/summary/?${params}`);
    return res.data;
  } catch (error) {
    throw error.response?.data || error.message;
  }
};

// ============ SALES (REVENUES) ============
export const getSales = async (filters = {}, page = 1) => {
  try {
    const params = new URLSearchParams({ ...filters, page }).toString();
    const res = await api.get(`/store/finance/sales/?${params}`);
    return res.data;
  } catch (error) {
    throw error.response?.data || error.message;
  }
};

export const exportSalesCSV = async (filters = {}) => {
  try {
    const params = new URLSearchParams(filters).toString();
    const res = await api.get(`/store/finance/sales/export/csv/?${params}`, {
      responseType: 'blob',
    });
    return res.data;
  } catch (error) {
    throw error.response?.data || error.message;
  }
};

export const exportSalesPDF = async (filters = {}) => {
  try {
    const params = new URLSearchParams(filters).toString();
    const res = await api.get(`/store/finance/sales/export/pdf/?${params}`, {
      responseType: 'blob',
    });
    return res.data;
  } catch (error) {
    throw error.response?.data || error.message;
  }
};

// ============ EXPENSES ============
export const getExpenses = async (filters = {}, page = 1) => {
  try {
    const params = new URLSearchParams({ ...filters, page }).toString();
    const res = await api.get(`/store/finance/expenses/?${params}`);
    return res.data;
  } catch (error) {
    throw error.response?.data || error.message;
  }
};

export const createExpense = async (payload) => {
  try {
    const res = await api.post('/store/finance/expenses/', payload);
    return res.data;
  } catch (error) {
    throw error.response?.data || error.message;
  }
};

export const updateExpense = async (expenseId, payload) => {
  try {
    const res = await api.patch(`/store/finance/expenses/${expenseId}/`, payload);
    return res.data;
  } catch (error) {
    throw error.response?.data || error.message;
  }
};

export const deleteExpense = async (expenseId) => {
  try {
    const res = await api.delete(`/store/finance/expenses/${expenseId}/`);
    return res.data;
  } catch (error) {
    throw error.response?.data || error.message;
  }
};

export const exportExpensesCSV = async (filters = {}) => {
  try {
    const params = new URLSearchParams(filters).toString();
    const res = await api.get(`/store/finance/expenses/export/csv/?${params}`, {
      responseType: 'blob',
    });
    return res.data;
  } catch (error) {
    throw error.response?.data || error.message;
  }
};

export const exportExpensesPDF = async (filters = {}) => {
  try {
    const params = new URLSearchParams(filters).toString();
    const res = await api.get(`/store/finance/expenses/export/pdf/?${params}`, {
      responseType: 'blob',
    });
    return res.data;
  } catch (error) {
    throw error.response?.data || error.message;
  }
};

// ============ SUPPLIERS ============
export const getSuppliers = async (filters = {}) => {
  try {
    const params = new URLSearchParams(filters).toString();
    const res = await api.get(`/store/finance/suppliers/?${params}`);
    return res.data;
  } catch (error) {
    throw error.response?.data || error.message;
  }
};

export const createSupplier = async (payload) => {
  try {
    const res = await api.post('/store/finance/suppliers/', payload);
    return res.data;
  } catch (error) {
    throw error.response?.data || error.message;
  }
};

export const updateSupplier = async (supplierId, payload) => {
  try {
    const res = await api.patch(`/store/finance/suppliers/${supplierId}/`, payload);
    return res.data;
  } catch (error) {
    throw error.response?.data || error.message;
  }
};

export const deleteSupplier = async (supplierId) => {
  try {
    const res = await api.delete(`/store/finance/suppliers/${supplierId}/`);
    return res.data;
  } catch (error) {
    throw error.response?.data || error.message;
  }
};

// ============ HELPERS ============
export const downloadFile = (blob, filename) => {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

