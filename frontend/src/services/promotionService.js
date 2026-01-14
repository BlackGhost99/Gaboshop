import api from './api';

/**
 * Service pour récupérer les promotions et offres spéciales
 */

export const getPromotions = async () => {
  try {
    const response = await api.get('/products/', {
      params: {
        limit: 20, // Récupérer plus de produits pour filtrer ceux avec remise
      },
    });
    
    // Normalize response
    let data = [];
    if (response.data?.success) {
      // Si response.data.data existe et est un tableau, l'utiliser
      if (Array.isArray(response.data.data)) {
        data = response.data.data;
      } else if (response.data.data?.data && Array.isArray(response.data.data.data)) {
        // Cas où la structure est { success: true, data: { data: [...] } }
        data = response.data.data.data;
      } else if (Array.isArray(response.data.data)) {
        data = response.data.data;
      } else {
        data = [];
      }
    } else if (response.data?.results) {
      data = Array.isArray(response.data.results) ? response.data.results : [];
    } else if (Array.isArray(response.data)) {
      data = response.data;
    } else if (response.data?.data && Array.isArray(response.data.data)) {
      // Cas où la structure est { data: [...] }
      data = response.data.data;
    }
    
    // S'assurer que data est un tableau
    if (!Array.isArray(data)) {
      console.warn('Promotions: data is not an array', response.data);
      return [];
    }
    
    // Filtrer les produits avec remise et trier par pourcentage de remise
    const productsWithDiscount = data
      .filter(product => product.has_discount === true)
      .sort((a, b) => (b.discount_percentage || 0) - (a.discount_percentage || 0))
      .slice(0, 6); // Limiter à 6 produits
    
    // Transform to promotion format
    return productsWithDiscount.map((product) => ({
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
    const response = await api.get('/stores/categories/', {
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
