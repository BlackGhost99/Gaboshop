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
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/3034891a-d8c4-4be8-b0a8-8720a23ed625',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'productService.js:49',message:'deleteProduct API call',data:{productId,url:`/products/${productId}/delete/`},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
    // #endregion
    try {
        const response = await api.delete(`/products/${productId}/delete/`);
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/3034891a-d8c4-4be8-b0a8-8720a23ed625',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'productService.js:52',message:'deleteProduct API success',data:{productId,status:response.status,data:response.data},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
        // #endregion
        return response.data;
    } catch (error) {
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/3034891a-d8c4-4be8-b0a8-8720a23ed625',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'productService.js:56',message:'deleteProduct API error',data:{productId,errorStatus:error?.response?.status,errorData:error?.response?.data,errorMessage:error?.message},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B,C,D'})}).catch(()=>{});
        // #endregion
        throw error;
    }
};

export const getStoreCategories = async (storeId) => {
  const response = await api.get(`/stores/${storeId}/categories/`);
  return response.data;
};

export const getAllCategories = async () => {
  const response = await api.get(`/products/categories/`);
  return response.data;
};

export const createStoreCategory = async (storeId, categoryData) => {
  const response = await api.post(`/stores/${storeId}/categories/create/`, categoryData);
  return response.data;
};

