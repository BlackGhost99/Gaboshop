import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { getProducts } from '../services/productService';
import { getStores } from '../services/storeService';
import { getPromotions, getCategories } from '../services/promotionService';
import LoadingSpinner from '../components/LoadingSpinner';
import HomeNavbar from '../components/HomeNavbar';
import HeroBanner from '../components/HeroBanner';
import CategoriesGrid from '../components/CategoriesGrid';
import ProductCard from '../components/ProductCard';
import Footer from '../components/Footer';
import { formatCurrency } from '../utils/helpers';

const CART_KEY = 'gaboshop_cart';

const Home = () => {
  const [products, setProducts] = useState([]);
  const [stores, setStores] = useState([]);
  const [promotions, setPromotions] = useState([]);
  const [categories, setCategories] = useState(null);
  const [selectedStore, setSelectedStore] = useState(null);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [cart, setCart] = useState([]);
  const [toast, setToast] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [error, setError] = useState(null);

  const loadCartFromStorage = () => {
    try {
      const saved = localStorage.getItem(CART_KEY);
      return saved ? JSON.parse(saved) : [];
    } catch (e) {
      console.error('Erreur chargement panier', e);
      return [];
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [productsRes, storesRes] = await Promise.all([
          getProducts(),
          getStores()
        ]);

        // Handle Products Response
        let productsData = [];
        if (productsRes.success) {
          productsData = productsRes.data;
        } else if (productsRes.results) {
          // Handle weird nested structure or standard pagination
          if (productsRes.results.success) {
             productsData = productsRes.results.data;
          } else {
             productsData = productsRes.results;
          }
        }
        setProducts(productsData);

        // Handle Stores Response
        let storesData = [];
        if (storesRes.success) {
          storesData = storesRes.data;
        } else if (storesRes.results) {
          storesData = storesRes.results;
        } else if (Array.isArray(storesRes)) {
          storesData = storesRes;
        }
        setStores(storesData);

        
      } catch (err) {
        setError('Erreur lors du chargement des données');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  useEffect(() => {
    // Charge un panier local pour les tests panier/achat
    setCart(loadCartFromStorage());
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(CART_KEY, JSON.stringify(cart));
    } catch (e) {
      console.error('Erreur sauvegarde panier', e);
    }
  }, [cart]);

  // Fetch dynamic promotions and categories
  useEffect(() => {
    const fetchDynamicContent = async () => {
      try {
        const promos = await getPromotions();
        setPromotions(promos || []);
        
        const cats = await getCategories();
        setCategories(cats);
      } catch (err) {
        console.error('Erreur chargement contenu dynamique:', err);
        // Silently fail - components will use defaults
      }
    };

    fetchDynamicContent();
  }, []);

  const fetchProducts = async (search = '', storeId = null) => {
    try {
      setLoading(true);
      const params = {};
      if (search) params.search = search;
      if (storeId) params.store = storeId;
      
      const response = await getProducts(params);
      
      let productsData = [];
      if (response.success) {
        productsData = response.data;
      } else if (response.results) {
        if (response.results.success) {
           productsData = response.results.data;
        } else {
           productsData = response.results;
        }
      }
      setProducts(productsData);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    fetchProducts(searchTerm, selectedStore);
  };

  const handleViewDetails = (product) => {
    setSelectedProduct(product);
  };

  const handleAddToCart = (product) => {
    setCart((prev) => {
      const existingIndex = prev.findIndex((item) => item.id === product.id);
      if (existingIndex !== -1) {
        const next = [...prev];
        next[existingIndex] = {
          ...next[existingIndex],
          quantity: next[existingIndex].quantity + 1
        };
        return next;
      }
      return [
        ...prev,
        {
          id: product.id,
          name: product.name,
          price: product.price,
          image: product.image,
          store_name: product.store_name,
          store_id: product.store,
          quantity: 1
        }
      ];
    });
    setToast({ message: `${product.name} ajouté au panier`, type: 'success', at: Date.now() });
    setTimeout(() => setToast(null), 1800);
  };

  const handleStoreClick = (storeId) => {
    if (selectedStore === storeId) {
      setSelectedStore(null);
      fetchProducts(searchTerm, null);
    } else {
      setSelectedStore(storeId);
      fetchProducts(searchTerm, storeId);
    }
  };

  return (
    <>
    <div className="min-h-screen bg-white">
      {/* New Navbar */}
      <HomeNavbar cartCount={cart.length} />

      {/* Hero Banner with Carousel */}
      <HeroBanner promotions={promotions} />

      {/* Categories Grid */}
      <CategoriesGrid categories={categories} />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex flex-col lg:flex-row gap-8">
          
          {/* Sidebar - Magasins Partenaires (1/3) */}
          <div className="w-full lg:w-1/3">
            <div className="bg-white rounded-lg shadow-md p-6 sticky top-24">
              <h2 className="text-xl font-bold text-gray-900 mb-4 border-b pb-2">
                Magasins Partenaires
              </h2>
              {loading ? (
                <div className="flex justify-center py-4"><LoadingSpinner /></div>
              ) : (
                <div className="space-y-4">
                  {stores.map((store) => (
                    <div 
                      key={store.id} 
                      onClick={() => handleStoreClick(store.id)}
                      className={`flex items-center space-x-4 p-3 rounded-lg transition-colors cursor-pointer border ${
                        selectedStore === store.id 
                          ? 'bg-indigo-50 border-indigo-500 ring-1 ring-indigo-500' 
                          : 'hover:bg-gray-50 border-gray-100'
                      }`}
                    >
                      <div className={`flex-shrink-0 h-12 w-12 rounded-full flex items-center justify-center font-bold text-lg ${
                        selectedStore === store.id ? 'bg-indigo-600 text-white' : 'bg-indigo-100 text-indigo-600'
                      }`}>
                        {store.name.charAt(0)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {store.name}
                        </p>
                        <p className="text-xs text-gray-500 truncate">
                          {store.category_name} • {store.city}
                        </p>
                      </div>
                      <div>
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          Ouvert
                        </span>
                      </div>
                    </div>
                  ))}
                  {stores.length === 0 && (
                    <p className="text-gray-500 text-sm text-center">Aucun magasin trouvé.</p>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Main Content - Promotions & Produits (2/3) */}
          <div className="w-full lg:w-2/3">
            
            {/* Section Promotions */}
            <div className="mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center">
                <span className="bg-red-100 text-red-600 p-2 rounded-full mr-3">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v13m0-13V6a2 2 0 112 2h-2zm0 0V5.5A2.5 2.5 0 109.5 8H12zm-7 4h14M5 12a2 2 0 110-4h14a2 2 0 110 4M5 12v7a2 2 0 002 2h10a2 2 0 002-2v-7" />
                  </svg>
                </span>
                Promotions du moment
              </h2>
              
              {/* Carousel simple pour les promos (produits avec réduction) */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                {products.filter(p => p.has_discount).slice(0, 2).map((product) => (
                  <div key={product.id} className="bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl shadow-lg overflow-hidden text-white relative">
                    <div className="absolute top-0 right-0 bg-yellow-400 text-yellow-900 font-bold px-3 py-1 rounded-bl-lg z-10">
                      -{product.discount_percentage}%
                    </div>
                    <div className="flex h-full">
                      <div className="w-1/2 p-4 flex flex-col justify-center">
                        <span className="text-xs font-semibold uppercase tracking-wider opacity-75 mb-1">{product.store_name}</span>
                        <h3 className="text-lg font-bold mb-2 leading-tight">{product.name}</h3>
                        <div className="mt-auto">
                          <span className="text-2xl font-bold">{formatCurrency(product.price)}</span>
                          <span className="block text-sm opacity-75 line-through">{formatCurrency(product.compare_price)}</span>
                        </div>
                      </div>
                      <div className="w-1/2 relative">
                        <img 
                          src={product.image} 
                          alt={product.name} 
                          className="absolute inset-0 w-full h-full object-cover opacity-90"
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Section Tous les Produits */}
            <div>
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Nos Produits</h2>
              
              {loading ? (
                <LoadingSpinner />
              ) : error ? (
                <div className="text-center text-red-600 py-8">{error}</div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                  {products.map((product) => (
                    <ProductCard
                      key={product.id}
                      product={product}
                      onAddToCart={handleAddToCart}
                      onViewDetails={handleViewDetails}
                    />
                  ))}
                </div>
              )}
              
              {!loading && products.length === 0 && (
                <div className="text-center py-12 bg-gray-50 rounded-lg">
                  <p className="text-gray-500 text-lg">Aucun produit trouvé.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>

    {selectedProduct && (
      <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 px-4">
        <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full overflow-hidden">
          <div className="flex flex-col md:flex-row">
            <div className="md:w-1/2 h-64 md:h-auto bg-gray-100 relative">
              {selectedProduct.image ? (
                <img
                  src={selectedProduct.image}
                  alt={selectedProduct.name}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="flex items-center justify-center h-full text-gray-400">
                  <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
              )}
              {selectedProduct.has_discount && (
                <span className="absolute top-3 left-3 bg-red-500 text-white text-xs font-bold px-3 py-1 rounded-full">
                  -{selectedProduct.discount_percentage}%
                </span>
              )}
            </div>
            <div className="md:w-1/2 p-6 flex flex-col gap-4">
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-xs font-semibold text-indigo-600 uppercase tracking-wide">{selectedProduct.store_name}</p>
                  <h3 className="text-2xl font-bold text-gray-900 leading-tight">{selectedProduct.name}</h3>
                </div>
                <button
                  onClick={() => setSelectedProduct(null)}
                  className="text-gray-400 hover:text-gray-600"
                  aria-label="Fermer"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <p className="text-gray-600 text-sm leading-relaxed">
                {selectedProduct.description || 'Pas de description fournie.'}
              </p>

              <div className="flex items-center gap-3">
                <span className="text-2xl font-bold text-gray-900">{formatCurrency(selectedProduct.price)}</span>
                {selectedProduct.has_discount && (
                  <span className="text-sm text-gray-400 line-through">{formatCurrency(selectedProduct.compare_price)}</span>
                )}
              </div>

              <div className="flex gap-3 mt-auto">
                <button
                  onClick={() => handleAddToCart(selectedProduct)}
                  className="flex-1 inline-flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-3 rounded-lg shadow"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h2l.4 2M7 13h10l4-8H5.4M7 13L5.4 5M7 13l-2.293 2.293c-.63.63-.184 1.707.707 1.707H17m0 0a2 2 0 100 4 2 2 0 000-4zm-8 2a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                  Ajouter au panier
                </button>
                <button
                  onClick={() => setSelectedProduct(null)}
                  className="inline-flex items-center justify-center px-4 py-3 rounded-lg border border-gray-200 text-gray-700 hover:bg-gray-50"
                >
                  Fermer
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    )}

    {toast && (
      <div className="fixed bottom-4 right-4 z-50">
        <div className="bg-white shadow-xl border border-green-100 text-gray-900 rounded-lg px-4 py-3 flex items-center gap-3 animate-slide-up">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-green-100 text-green-700">
            ✓
          </span>
          <span className="text-sm font-medium">{toast.message}</span>
        </div>
      </div>
    )}

    {/* Footer */}
    <Footer />
    </>
  );
};

export default Home;
