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
    try {
        const response = await api.delete(`/products/${productId}/delete/`);
        return response.data;
    } catch (error) {
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


// Import de produits par fichier Excel/CSV (outil des forfaits Pro et Business).
// Le modèle demande la connexion : on le télécharge avec le jeton puis on lance l'enregistrement du fichier.
// Dans l'application Android, la page ne peut pas enregistrer un fichier : le modèle (public, sans donnée
// personnelle) s'ouvre dans le navigateur du téléphone, qui le télécharge. Renvoie 'browser' dans ce cas.
export const downloadProductImportTemplate = async () => {
  if (window.Capacitor?.isNativePlatform?.() && /^https?:/i.test(api.defaults.baseURL || '')) {
    window.location.href = `${api.defaults.baseURL}/store/products/import/template/`;
    return 'browser';
  }
  let response;
  try {
    response = await api.get('/store/products/import/template/', { responseType: 'blob' });
  } catch (error) {
    // En mode « fichier », l'erreur du serveur arrive aussi en fichier : on la relit pour afficher son message.
    const body = error.response?.data;
    if (typeof Blob !== 'undefined' && body instanceof Blob) {
      try {
        error.response.data = JSON.parse(await body.text());
      } catch {
        // Réponse illisible : l'erreur d'origine suffit.
      }
    }
    throw error;
  }
  const url = URL.createObjectURL(response.data);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'modele-import-produits-gaboshop.csv';
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  return 'file';
};

// confirm = false : aperçu, rien n'est créé. confirm = true : création des lignes valides.
export const importProducts = async (file, confirm = false) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('confirm', confirm ? '1' : '0');
  const response = await api.post('/store/products/import/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};
