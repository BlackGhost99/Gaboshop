import api from './api';

export const getStores = async (params = {}) => {
  try {
    const response = await api.get('/stores/', { params });
    return response.data;
  } catch (error) {
    throw error.response?.data || error.message;
  }
};

export const getStoreDetails = async (id) => {
  try {
    const response = await api.get(`/stores/${id}/`);
    return response.data;
  } catch (error) {
    throw error.response?.data || error.message;
  }
};

export const updateStore = async (storeId, storeData) => {
  const response = await api.patch(`/stores/${storeId}/update/`, storeData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

