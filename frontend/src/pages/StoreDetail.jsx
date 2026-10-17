import React, { useState, useEffect } from 'react';
import { useParams, Link, useSearchParams } from 'react-router-dom';
import api from '../services/api';
import { getProducts } from '../services/productService';
import LoadingSpinner from '../components/LoadingSpinner';
import ProductCard from '../components/ProductCard';
import ProductDetailModal from '../components/ProductDetailModal';
import LoginRequiredModal from '../components/LoginRequiredModal';
import { isLoggedIn, savePendingCartItem, applyPendingCartItem, addToCart } from '../utils/session';
import { defaultChoice, needsChoice } from '../utils/productOptions';
import HomeNavbar from '../components/HomeNavbar'; // Reusing HomeNavbar
import Footer from '../components/Footer';

// Page de boutique personnalisée : l'API ne renvoie ces champs au public que si le forfait du commerce les inclut.
const HEX_COLOR = /^#[0-9A-Fa-f]{6}$/;
// Texte blanc ou foncé selon la clarté de la couleur choisie par le commerce.
const readableOn = (hex) => {
    const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
    return (r * 299 + g * 587 + b * 114) / 1000 > 160 ? '#111827' : '#FFFFFF';
};
// Lien publié -> adresse sûre (http/https seulement), sinon rien.
const safeLink = (url) => (/^https?:\/\//i.test(url || '') ? url : '');

const SocialIcon = ({ kind }) => {
    const common = { className: 'h-5 w-5', fill: 'currentColor', viewBox: '0 0 24 24', 'aria-hidden': true };
    if (kind === 'facebook') {
        return <svg {...common}><path d="M13.5 21v-7.5h2.6l.4-3h-3V8.6c0-.9.3-1.5 1.5-1.5h1.6V4.4c-.3 0-1.2-.1-2.3-.1-2.3 0-3.9 1.4-3.9 4v2.2H7.8v3h2.6V21h3.1z" /></svg>;
    }
    if (kind === 'instagram') {
        return <svg {...common}><path d="M7.5 3h9A4.5 4.5 0 0 1 21 7.5v9a4.5 4.5 0 0 1-4.5 4.5h-9A4.5 4.5 0 0 1 3 16.5v-9A4.5 4.5 0 0 1 7.5 3zm0 1.8A2.7 2.7 0 0 0 4.8 7.5v9a2.7 2.7 0 0 0 2.7 2.7h9a2.7 2.7 0 0 0 2.7-2.7v-9a2.7 2.7 0 0 0-2.7-2.7h-9zM12 7.5a4.5 4.5 0 1 1 0 9 4.5 4.5 0 0 1 0-9zm0 1.8a2.7 2.7 0 1 0 0 5.4 2.7 2.7 0 0 0 0-5.4zm5-2.6a1.05 1.05 0 1 1 0 2.1 1.05 1.05 0 0 1 0-2.1z" /></svg>;
    }
    if (kind === 'tiktok') {
        return <svg {...common}><path d="M16.6 3h-2.8v11.6a2.4 2.4 0 1 1-2.4-2.4c.2 0 .5 0 .7.1V9.4a5.2 5.2 0 1 0 4.5 5.1V8.9a6 6 0 0 0 3.4 1.1V7.2A3.4 3.4 0 0 1 16.6 3z" /></svg>;
    }
    return <svg {...common}><path d="M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zm6.9 8h-3a14 14 0 0 0-1.2-5A7.2 7.2 0 0 1 18.9 11zM12 4.9c.8.9 1.6 2.7 1.9 6.1h-3.8c.3-3.4 1.1-5.2 1.9-6.1zM9.3 6a14 14 0 0 0-1.2 5h-3A7.2 7.2 0 0 1 9.3 6zM5.1 13h3c.1 1.8.5 3.5 1.2 5A7.2 7.2 0 0 1 5.1 13zm5 0h3.8c-.3 3.4-1.1 5.2-1.9 6.1-.8-.9-1.6-2.7-1.9-6.1zm5.6 5c.7-1.5 1.1-3.2 1.2-5h3a7.2 7.2 0 0 1-4.2 5z" /></svg>;
};

const SOCIAL_LINKS = [
    ['facebook_url', 'facebook', 'Facebook'],
    ['instagram_url', 'instagram', 'Instagram'],
    ['tiktok_url', 'tiktok', 'TikTok'],
    ['website_url', 'website', 'Site web'],
];

// Temporary service patch if getStoreDetail doesn't exist, we will try to filter from getStores or assume an endpoint exists
// Actually, let's assume we can fetch products by store.

const StoreDetail = () => {
    const { id } = useParams();
    const [store, setStore] = useState(null);
    const [products, setProducts] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedProduct, setSelectedProduct] = useState(null);
    const [toast, setToast] = useState(null);

    const [loginPromptProduct, setLoginPromptProduct] = useState(null);
    const [searchParams, setSearchParams] = useSearchParams();
    const requestedProductId = Number(searchParams.get('product')) || null;

    // Lien depuis l'assistant d'achat : ouvre directement la fiche du produit
    useEffect(() => {
        if (!requestedProductId) return undefined;
        const timer = setTimeout(() => {
            setSelectedProduct({ id: requestedProductId });
            setSearchParams({}, { replace: true });
        }, 0);
        return () => clearTimeout(timer);
    }, [requestedProductId, setSearchParams]);

    // Même panier que la page d'accueil (stocké sur l'appareil)
    const handleAddToCart = (product, options = null) => {
        if (needsChoice(product) && !options) {
            setSelectedProduct(product);  // la fiche demande la pointure / la couleur
            return;
        }
        const chosen = options || defaultChoice(product);
        if (!isLoggedIn()) {
            savePendingCartItem(product, chosen);
            setSelectedProduct(null);
            setLoginPromptProduct(product);
            return;
        }
        addToCart(product, 1, chosen);
        setToast(`${product.name} ajouté au panier`);
        setTimeout(() => setToast(null), 1800);
    };

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

                let storeJson;
                try {
                    ({ data: storeJson } = await api.get(`/stores/${id}/`));
                } catch {
                    throw new Error('Impossible de charger le magasin');
                }
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

    // Produit choisi avant la connexion : ajouté maintenant que le client est connecté
    useEffect(() => {
        const pendingName = applyPendingCartItem();
        if (!pendingName) return undefined;
        const showId = setTimeout(() => setToast(`${pendingName} ajouté au panier`), 0);
        const hideId = setTimeout(() => setToast(null), 2500);
        return () => { clearTimeout(showId); clearTimeout(hideId); };
    }, []);

    if (loading) return <LoadingSpinner />;
    if (error) return <div className="text-center py-10 text-red-600">Erreur: {error}</div>;
    if (!store) return <div className="text-center py-10">Magasin introuvable</div>;

    const accent = HEX_COLOR.test(store.accent_color || '') ? store.accent_color : '';
    const onAccent = accent ? readableOn(accent) : '';
    const socialLinks = SOCIAL_LINKS.filter(([field]) => safeLink(store[field]));
    const hasAbout = Boolean((store.about || '').trim());

    return (
        <div className="min-h-screen bg-gray-50 store-custom-page" style={accent ? { '--store-accent': accent } : undefined}>
            {accent && (
                // Boutons « Ajouter au panier » aux couleurs du commerce (couleur validée #RRGGBB côté serveur et ici).
                <style>{`.store-custom-page .bg-cta-600{background-color:${accent} !important;color:${onAccent} !important}.store-custom-page .bg-cta-600:hover{filter:brightness(.92)}`}</style>
            )}
            <HomeNavbar />

            {/* Store Banner & Info */}
            <div className="bg-white shadow">
                <div className="h-48 md:h-64 bg-gray-800 w-full relative overflow-hidden">
                    {store.banner_image ? (
                        <img src={store.banner_image} alt="" className="w-full h-full object-cover opacity-75" onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                    ) : accent ? (
                        <div className="w-full h-full" style={{ background: `linear-gradient(120deg, ${accent}, #111827)` }} />
                    ) : (
                        <div className="w-full h-full bg-gradient-to-r from-indigo-900 to-purple-900" />
                    )}
                    <div className="absolute inset-0 flex flex-col items-center justify-center px-4 text-center">
                        <h1 className="text-4xl md:text-5xl font-bold text-white shadow-lg">{store.name}</h1>
                        {store.tagline && (
                            <p className="mt-2 max-w-2xl text-base md:text-lg font-medium text-white drop-shadow">{store.tagline}</p>
                        )}
                    </div>
                    {accent && <div className="absolute inset-x-0 bottom-0 h-1.5" style={{ backgroundColor: accent }} />}
                </div>

                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 -mt-12 relative z-10 pb-6">
                    <div
                        className="bg-white rounded-lg shadow-lg p-6 flex flex-col md:flex-row items-center md:items-start gap-6"
                        style={accent ? { borderTop: `4px solid ${accent}` } : undefined}
                    >
                        <div
                            className="h-24 w-24 rounded-full bg-indigo-100 border-4 border-white shadow-md flex items-center justify-center overflow-hidden flex-shrink-0"
                            style={accent ? { backgroundColor: accent } : undefined}
                        >
                            {store.logo ? (
                                <img src={store.logo} alt="" className="w-full h-full object-cover" onError={(e) => { e.currentTarget.style.display = 'none'; }} />
                            ) : (
                                <span className="text-3xl font-bold text-indigo-600" style={accent ? { color: onAccent } : undefined}>{store.name.charAt(0)}</span>
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

                            {socialLinks.length > 0 && (
                                <div className="mt-4 flex flex-wrap gap-2 justify-center md:justify-start">
                                    {socialLinks.map(([field, kind, label]) => (
                                        <a
                                            key={field}
                                            href={safeLink(store[field])}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            aria-label={`${label} de ${store.name}`}
                                            title={label}
                                            className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-gray-100 text-gray-700 hover:bg-gray-200"
                                            style={accent ? { backgroundColor: accent, color: onAccent } : undefined}
                                        >
                                            <SocialIcon kind={kind} />
                                        </a>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>

            {hasAbout && (
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8">
                    <section className="bg-white rounded-lg shadow-sm p-6" aria-labelledby="store-about-title">
                        <h3 id="store-about-title" className="text-xl font-bold text-gray-900" style={accent ? { color: accent } : undefined}>
                            À propos de {store.name}
                        </h3>
                        <p className="mt-3 whitespace-pre-line break-words text-gray-700">{store.about}</p>
                    </section>
                </div>
            )}

            {/* Products Grid */}
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
                <h3 className="text-2xl font-bold text-gray-900 mb-6">Produits disponibles ({products.length})</h3>

                {products.length > 0 ? (
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
                        {products.map(product => (
                            <ProductCard
                                key={product.id}
                                product={product}
                                onAddToCart={handleAddToCart}
                                onViewDetails={setSelectedProduct}
                            />
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-12 bg-white rounded-lg shadow-sm">
                        <p className="text-gray-500 text-lg">Aucun produit dans cette boutique pour le moment.</p>
                    </div>
                )}
            </div>

            <Footer />

            {selectedProduct && (
                <ProductDetailModal
                    key={selectedProduct.id}
                    product={selectedProduct}
                    onClose={() => setSelectedProduct(null)}
                    onAddToCart={handleAddToCart}
                />
            )}

            {loginPromptProduct && (
                <LoginRequiredModal
                    productName={loginPromptProduct.name}
                    onClose={() => setLoginPromptProduct(null)}
                />
            )}

            {toast && (
                <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-[70] bg-white shadow-xl border border-green-100 rounded-lg px-4 py-3 text-sm font-medium text-gray-900">
                    ✓ {toast}
                </div>
            )}
        </div>
    );
};

export default StoreDetail;
