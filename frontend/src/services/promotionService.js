import api from './api';

/**
 * Service pour récupérer les promotions et offres spéciales
 */

export const getPromotions = async () => {
  try {
    const response = await api.get('/products/', {
      params: {
        has_discount: true,
        limit: 6,
        ordering: '-discount_percentage',
      },
    });
    
    // Normalize response
    let data = [];
    if (response.data?.success) {
      data = response.data.data || [];
    } else if (response.data?.results) {
      data = response.data.results;
    } else if (Array.isArray(response.data)) {
      data = response.data;
    }
    
    // Transform to promotion format
    return data.map((product) => ({
      id: product.id,
      title: product.name,
      subtitle: `${product.store_name || 'Magasin'} - Jusqu'à -${product.discount_percentage || 0}%`,
      cta: 'Voir l\'offre',
      icon: '🎉',
      image: product.image,
      product_id: product.id,
      discount: product.discount_percentage || 0,
      price: product.price,
      original_price: product.compare_price || product.price,
      bg: 'bg-gradient-to-r from-cta-500 to-orange-400',
    }));
  } catch (error) {
    console.error('Erreur récupération promotions:', error);
    return [];
  }
};

export const getCategories = async () => {
  try {
    // Essayer de récupérer depuis les catégories de magasin
    const response = await api.get('/store-categories/', {
      params: {
        limit: 10,
      },
    });
    
    // Normalize response
    let data = [];
    if (response.data?.success) {
      data = response.data.data || [];
    } else if (response.data?.results) {
      data = response.data.results;
    } else if (Array.isArray(response.data)) {
      data = response.data;
    }
    
    // Si pas de catégories API, retourner les catégories par défaut
    if (data.length === 0) {
      return null; // Signale au composant d'utiliser les defaults
    }
    
    return data.map((cat) => ({
      id: cat.id,
      name: cat.name,
      icon: cat.icon || '📦',
      color: cat.color || 'bg-gray-100',
      textColor: cat.text_color || 'text-gray-700',
      slug: cat.slug || `category-${cat.id}`,
    }));
  } catch (error) {
    console.error('Erreur récupération catégories:', error);
    return null; // Retour null = utiliser les defaults
  }
};

export const getFeaturedProducts = async () => {
  try {
    const response = await api.get('/products/', {
      params: {
        featured: true,
        limit: 12,
      },
    });
    
    // Normalize response
    let data = [];
    if (response.data?.success) {
      data = response.data.data || [];
    } else if (response.data?.results) {
      data = response.data.results;
    } else if (Array.isArray(response.data)) {
      data = response.data;
    }
    
    return data;
  } catch (error) {
    console.error('Erreur récupération featured products:', error);
    return [];
  }
};

export const searchProducts = async (query) => {
  try {
    const response = await api.get('/products/', {
      params: {
        search: query,
        limit: 20,
      },
    });
    
    // Normalize response
    let data = [];
    if (response.data?.success) {
      data = response.data.data || [];
    } else if (response.data?.results) {
      data = response.data.results;
    } else if (Array.isArray(response.data)) {
      data = response.data;
    }
    
    return data;
  } catch (error) {
    console.error('Erreur recherche produits:', error);
    return [];
  }
};
