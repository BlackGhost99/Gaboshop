import api from './api';

export const getProducts = async (params = {}) => {
  try {
    const response = await api.get('/products/', { params });
    return response.data;
  } catch (error) {
    throw error.response?.data || error.message;
  }
};

export const getProductDetails = async (id) => {
  try {
    const response = await api.get(`/products/${id}/`);
    return response.data;
  } catch (error) {
    throw error.response?.data || error.message;
  }
};

export const getStoreProducts = async (storeId) => {
  const response = await api.get(`/stores/${storeId}/products/`);
  return response.data;
};

export const getManagerStoreProducts = async (storeId) => {
  const response = await api.get(`/stores/${storeId}/products/manager/`);
  return response.data;
};

export const createProduct = async (storeId, productData) => {
  const response = await api.post(`/stores/${storeId}/products/create/`, productData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const updateProduct = async (productId, productData) => {
    const response = await api.patch(`/products/${productId}/update/`, productData, {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
    });
    return response.data;
};

export const deleteProduct = async (productId) => {
    const response = await api.delete(`/products/${productId}/delete/`);
    return response.data;
};

export const getStoreCategories = async (storeId) => {
  const response = await api.get(`/stores/${storeId}/categories/`);
  return response.data;
};

export const createStoreCategory = async (storeId, categoryData) => {
  const response = await api.post(`/stores/${storeId}/categories/create/`, categoryData);
  return response.data;
};

