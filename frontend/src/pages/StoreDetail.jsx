import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getProducts } from '../services/productService';
import { getStores } from '../services/storeService'; // Need a getStoreDetail really, but getStores filter might work or I'll use list for now
import LoadingSpinner from '../components/LoadingSpinner';
import ProductCard from '../components/ProductCard';
import HomeNavbar from '../components/HomeNavbar'; // Reusing HomeNavbar
import Footer from '../components/Footer';

// Temporary service patch if getStoreDetail doesn't exist, we will try to filter from getStores or assume an endpoint exists
// Actually, let's assume we can fetch products by store.

const StoreDetail = () => {
    const { id } = useParams();
    const [store, setStore] = useState(null);
    const [products, setProducts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                setLoading(true);
                // 1. Fetch Store Details (We might need a dedicated endpoint or search)
                // For now, let's fetch all stores and find the one. Ideally backend has /api/v1/stores/:id
                // We know api/v1/stores/:id exists from backend code analysis (StoreDetailView).
                // Let's assume there is a service method getStore(id) or we make one.
                // Since I can't easily see services/storeService.js, I'll try to use a direct fetch or existing service if I can guess it.
                // Actually, let's rely on standard fetch if service is unknown, or better, check service first.
                // But for speed, I'll stick to what I know: api/v1/stores/${id}/

                const token = sessionStorage.getItem('token');
                const headers = token ? { Authorization: `Bearer ${token}` } : {};

                const storeRes = await fetch(`http://localhost:8000/api/v1/stores/${id}/`, { headers });
                if (!storeRes.ok) throw new Error('Impossible de charger le magasin');
                const storeJson = await storeRes.json();
                setStore(storeJson.data);

                // 2. Fetch Products for this store
                const productsRes = await getProducts({ store: id });

                let productsData = [];
                if (productsRes.success) {
                    productsData = productsRes.data;
                } else if (productsRes.results) {
                    productsData = productsRes.results.data || productsRes.results;
                } else if (Array.isArray(productsRes)) {
                    productsData = productsRes;
                }
                setProducts(productsData);

            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        if (id) fetchData();
    }, [id]);

    if (loading) return <LoadingSpinner />;
    if (error) return <div className="text-center py-10 text-red-600">Erreur: {error}</div>;
    if (!store) return <div className="text-center py-10">Magasin introuvable</div>;

    return (
        <div className="min-h-screen bg-gray-50">
            <HomeNavbar />

            {/* Store Banner & Info */}
            <div className="bg-white shadow">
                <div className="h-48 md:h-64 bg-gray-800 w-full relative overflow-hidden">
                    {store.banner_image ? (
                        <img src={store.banner_image} alt="Banner" className="w-full h-full object-cover opacity-75" />
                    ) : (
                        <div className="w-full h-full bg-gradient-to-r from-indigo-900 to-purple-900" />
                    )}
                    <div className="absolute inset-0 flex items-center justify-center">
                        <h1 className="text-4xl md:text-5xl font-bold text-white shadow-lg">{store.name}</h1>
                    </div>
                </div>

                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 -mt-12 relative z-10 pb-6">
                    <div className="bg-white rounded-lg shadow-lg p-6 flex flex-col md:flex-row items-center md:items-start gap-6">
                        <div className="h-24 w-24 rounded-full bg-indigo-100 border-4 border-white shadow-md flex items-center justify-center overflow-hidden flex-shrink-0">
                            {store.logo ? (
                                <img src={store.logo} alt="Logo" className="w-full h-full object-cover" />
                            ) : (
                                <span className="text-3xl font-bold text-indigo-600">{store.name.charAt(0)}</span>
                            )}
                        </div>
                        <div className="text-center md:text-left flex-1">
                            <h2 className="text-2xl font-bold text-gray-900">{store.name}</h2>
                            <p className="text-gray-500">{store.category_name || 'Magasin'} • {store.city}</p>
                            <p className="text-gray-600 mt-2 max-w-2xl">{store.description}</p>

                            <div className="mt-4 flex flex-wrap gap-2 justify-center md:justify-start">
                                <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm font-medium">Ouvert</span>
                                {store.address && <span className="px-3 py-1 bg-gray-100 text-gray-800 rounded-full text-sm">📍 {store.address}</span>}
                                {store.phone && <span className="px-3 py-1 bg-gray-100 text-gray-800 rounded-full text-sm">📞 {store.phone}</span>}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Products Grid */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                <h3 className="text-2xl font-bold text-gray-900 mb-6">Produits disponibles ({products.length})</h3>

                {products.length > 0 ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                        {products.map(product => (
                            <ProductCard key={product.id} product={product} />
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-12 bg-white rounded-lg shadow-sm">
                        <p className="text-gray-500 text-lg">Aucun produit dans cette boutique pour le moment.</p>
                    </div>
                )}
            </div>

            <Footer />
        </div>
    );
};

export default StoreDetail;
