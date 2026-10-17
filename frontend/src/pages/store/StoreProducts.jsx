import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { notifyError, notifySuccess, notifyWarning } from '../../utils/feedback';
import StoreLayout from '../../components/StoreLayout';
import ProductSpecsFields, { isFashionCategory } from '../../components/ProductSpecsFields';
import ConfirmModal from '../../components/ConfirmModal';
import ProductPhotosField from '../../components/ProductPhotosField';
import { allPhotos } from '../../utils/productPhotos';
import { getStoreDashboard } from '../../services/dashboardService';
import { 
    getStoreProducts, 
    getManagerStoreProducts,
    getStoreCategories, 
    getAllCategories,
    createProduct, 
    updateProduct,
    deleteProduct,
    downloadProductImportTemplate,
    importProducts
    // createStoreCategory - DÉSACTIVÉ: Seul l'admin peut créer des catégories
} from '../../services/productService';

const emptyProduct = () => ({
    name: '', description: '', price: '', compare_price: '', stock: '', category: '', weight_kg: '', length_m: '', attributes: {}, image: null
});

const IMPORT_MAX_BYTES = 2 * 1024 * 1024;

const IMPORT_STATUS = {
    ok: { label: 'Prêt', className: 'bg-indigo-100 text-indigo-700' },
    created: { label: 'Créé', className: 'bg-green-100 text-green-700' },
    skipped: { label: 'Déjà présent', className: 'bg-gray-100 text-gray-700' },
    error: { label: 'Erreur', className: 'bg-red-100 text-red-700' },
};

const formatPrice = (value) => `${Number(value || 0).toLocaleString('fr-FR')} FCFA`;

// Pourcentage de réduction quand un prix avant promo (barré) est plus grand que le prix de vente.
const promoPercent = (product) => {
    const price = Number(product?.price);
    const before = Number(product?.compare_price);
    if (!before || !(before > price)) return 0;
    return product.discount_percentage || Math.max(1, Math.floor(((before - price) / before) * 100));
};

const PriceWithPromo = ({ product, className = '' }) => {
    const percent = promoPercent(product);
    return (
        <div className={`flex flex-wrap items-baseline gap-x-2 gap-y-1 ${className}`}>
            <span className="font-bold text-indigo-600">{formatPrice(product.price)}</span>
            {percent > 0 && (
                <>
                    <span className="text-sm text-gray-400 line-through">{formatPrice(product.compare_price)}</span>
                    <span className="rounded bg-red-100 px-1.5 py-0.5 text-xs font-semibold text-red-700">-{percent} %</span>
                </>
            )}
        </div>
    );
};

const StoreProducts = () => {
    const [store, setStore] = useState(null);
    const [products, setProducts] = useState([]);
    const [categories, setCategories] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showProductModal, setShowProductModal] = useState(false);
    const [showCategoryModal, setShowCategoryModal] = useState(false);
    const [confirmDeleteProduct, setConfirmDeleteProduct] = useState(null);
    const [deletingProductId, setDeletingProductId] = useState(null);
    
    // Form states
    const [newProduct, setNewProduct] = useState(emptyProduct);
    const [newCategory, setNewCategory] = useState({
        name: '', description: '', commission_rate: '8.00', order: 0
    });
    const [galleryFiles, setGalleryFiles] = useState([]);
    const [removedPhotos, setRemovedPhotos] = useState([]);
    const [viewingProduct, setViewingProduct] = useState(null);
    const [viewingPhoto, setViewingPhoto] = useState(0);
    const [editingProduct, setEditingProduct] = useState(null);
    const [toast, setToast] = useState(null);
    const [subscriptionInfo, setSubscriptionInfo] = useState(null);
    // Import Excel/CSV : fichier choisi, aperçu renvoyé par le serveur, action en cours.
    const [showImportModal, setShowImportModal] = useState(false);
    const [importFile, setImportFile] = useState(null);
    const [importInputKey, setImportInputKey] = useState(0);
    const [importPreview, setImportPreview] = useState(null);
    const [importBusy, setImportBusy] = useState('');

    // Outils du forfait (même règle que le serveur) : true = inclus.
    const tools = subscriptionInfo?.subscription?.tools || {};
    const canImport = tools.product_import === true;
    const canPromote = tools.promotions === true;

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const dashboardData = await getStoreDashboard();
            if (dashboardData.success) {
                // Store info from API
                const storeInfo = dashboardData.data.store || dashboardData.data.store_info;
                setStore(storeInfo);
                const storeId = storeInfo.id;
                
                // Utiliser les informations de subscription du dashboard (qui incluent maintenant les limites)
                if (dashboardData.data.subscription) {
                    setSubscriptionInfo({
                        subscription: dashboardData.data.subscription,
                        features: dashboardData.data.subscription.features,
                        limits: dashboardData.data.subscription.limits,
                    });
                }
                
                const [productsRes, storeCategoriesRes, allCategoriesRes] = await Promise.all([
                    getManagerStoreProducts(storeId),
                    getStoreCategories(storeId),
                    getAllCategories()
                ]);

                if (productsRes.success) {
                    // Filtrer les produits désactivés (is_available=false) après suppression
                    const allProducts = productsRes.data.products || [];
                    const activeProducts = allProducts.filter(p => p.is_available !== false);
                    setProducts(activeProducts);
                }
                // Catégories créées par l'admin pour le type de ce magasin ; à défaut, toutes
                // les catégories existantes. Les suggestions sans id ne sont pas attribuables.
                const withId = (res) => (res && res.success ? (res.data || []).filter(c => c.id) : []);
                const storeCats = withId(storeCategoriesRes);
                setCategories(storeCats.length ? storeCats : withId(allCategoriesRes));
            }
        } catch (error) {
            console.error("Error fetching data", error);
        } finally {
            setLoading(false);
        }
    };

    // Fonction désactivée - Seul l'admin peut créer des catégories
    // const handleCreateCategory = async (e) => {
    //     e.preventDefault();
    //     if (!store) return;
    //     
    //     try {
    //         const categoryData = {
    //             name: newCategory.name,
    //             description: newCategory.description || '',
    //             commission_rate: parseFloat(newCategory.commission_rate),
    //             order: parseInt(newCategory.order) || 0
    //         };
    //         
    //         const res = await createStoreCategory(store.id, categoryData);
    //         if (res.success) {
    //             setCategories([...categories, res.data]);
    //             setShowCategoryModal(false);
    //             setNewCategory({ name: '', description: '', commission_rate: '8.00', order: 0 });
    //             alert('Catégorie créée avec succès!');
    //         }
    //     } catch (error) {
    //         console.error("Error creating category", error);
    //         const message = error.error?.details 
    //             ? Object.values(error.error.details).flat().join('\n')
    //             : (error.error?.message || "Erreur lors de la création de la catégorie");
    //         alert(message);
    //     }
    // };

    const showToast = (message, type = 'success') => {
        setToast({ message, type });
        setTimeout(() => setToast(null), 5000);
    };

    const handleViewProduct = (product) => {
        setViewingProduct(product);
        setViewingPhoto(0);
    };

    const handleEditProduct = (product) => {
        setEditingProduct(product);
        setNewProduct({
            name: product.name,
            description: product.description || '',
            price: product.price,
            compare_price: product.compare_price || '',
            stock: product.stock,
            category: product.category,
            weight_kg: product.weight_kg || '',
            length_m: product.length_m || '',
            attributes: product.attributes || {},
            image: null
        });
        setGalleryFiles([]);
        setRemovedPhotos([]);
        setShowProductModal(true);
    };

    const handleSaveProduct = async (e) => {
        e.preventDefault();
        const comparePrice = String(newProduct.compare_price ?? '').trim();
        if (comparePrice !== '' && Number(comparePrice) <= Number(newProduct.price)) {
            notifyWarning('Prix avant promo trop bas', 'Il doit être plus grand que le prix de vente.');
            return;
        }
        const formData = new FormData();
        Object.keys(newProduct).forEach(key => {
            if (key === 'attributes') {
                formData.append(key, JSON.stringify(newProduct.attributes || {}));
            } else if (newProduct[key] !== null && newProduct[key] !== '') {
                formData.append(key, newProduct[key]);
            }
        });
        // Promo retirée : envoyer un champ vide pour que le serveur efface le prix barré.
        if (editingProduct?.compare_price && comparePrice === '') {
            formData.append('compare_price', '');
        }
        galleryFiles.forEach((file) => formData.append('gallery', file));
        if (editingProduct && removedPhotos.length) {
            formData.append('remove_images', removedPhotos.join(','));
        }

        try {
            let res;
            if (editingProduct) {
                res = await updateProduct(editingProduct.id, formData);
            } else {
                res = await createProduct(store.id, formData);
            }

            if (res.success) {
                if (editingProduct) {
                    setProducts(products.map(p => p.id === editingProduct.id ? res.data : p));
                } else {
                    setProducts([...products, res.data]);
                }
                setShowProductModal(false);
                setEditingProduct(null);
                setNewProduct(emptyProduct()); setGalleryFiles([]); setRemovedPhotos([]);
            }
        } catch (error) {
            console.error("Error saving product", error);
            const message = error.error?.details 
                ? Object.values(error.error.details).flat().join('\n')
                : (error.error?.message || "Erreur lors de l'enregistrement du produit");
            notifyError(error, { action: 'Enregistrer le produit', fallback: message });
        }
    };
    
    const closeImportModal = () => {
        if (importBusy) return;
        setShowImportModal(false);
        setImportFile(null);
        setImportPreview(null);
        setImportInputKey(k => k + 1);
    };

    const handleDownloadTemplate = async () => {
        setImportBusy('template');
        try {
            const where = await downloadProductImportTemplate();
            notifySuccess(
                where === 'browser' ? 'Modèle ouvert dans votre navigateur' : 'Modèle téléchargé',
                'Ouvrez-le dans Excel, remplissez une ligne par produit, puis enregistrez-le.',
            );
        } catch (error) {
            notifyError(error, { action: 'Télécharger le modèle' });
        } finally {
            setImportBusy('');
        }
    };

    const handleImportFile = (file) => {
        setImportPreview(null);
        if (!file) {
            setImportFile(null);
            return;
        }
        const name = (file.name || '').toLowerCase();
        let problem = null;
        if (!name.endsWith('.xlsx') && !name.endsWith('.csv')) {
            problem = ['Format non pris en charge', 'Choisissez un fichier Excel (.xlsx) ou CSV (.csv).'];
        } else if (file.size > IMPORT_MAX_BYTES) {
            problem = ['Fichier trop lourd (2 Mo au plus)', 'Coupez-le en plusieurs fichiers, puis importez-les un par un.'];
        }
        if (problem) {
            notifyWarning(...problem);
            setImportFile(null);
            setImportInputKey(k => k + 1);
            return;
        }
        setImportFile(file);
    };

    const runImport = async (confirm) => {
        if (!importFile) {
            notifyWarning('Aucun fichier choisi', 'Choisissez votre fichier Excel ou CSV, puis touchez « Vérifier le fichier ».');
            return;
        }
        setImportBusy(confirm ? 'confirm' : 'preview');
        try {
            const res = await importProducts(importFile, confirm);
            if (!res?.success) {
                notifyError(res, { action: confirm ? 'Créer les produits' : 'Vérifier le fichier' });
                return;
            }
            const data = res.data || {};
            if (!confirm) {
                setImportPreview(data);
                return;
            }
            if (data.counts?.created > 0) {
                notifySuccess('Import terminé', data.message);
            } else {
                notifyWarning('Aucun produit créé', data.message);
            }
            setShowImportModal(false);
            setImportFile(null);
            setImportPreview(null);
            setImportInputKey(k => k + 1);
            await fetchData();
        } catch (error) {
            notifyError(error, { action: confirm ? 'Créer les produits' : 'Vérifier le fichier' });
        } finally {
            setImportBusy('');
        }
    };

    const handleDeleteProduct = (productId) => {
        // Ouvrir le modal de confirmation
        setConfirmDeleteProduct(productId);
    }

    const confirmDelete = async () => {
        if (!confirmDeleteProduct || deletingProductId) return;
        
        
        setDeletingProductId(confirmDeleteProduct);
        try {
            
            const response = await deleteProduct(confirmDeleteProduct);
            
            
            if (response?.success) {
                // Retirer immédiatement le produit de la liste (même s'il est désactivé au lieu d'être supprimé)
                setProducts(prevProducts => prevProducts.filter(p => p.id !== confirmDeleteProduct));
                // Rafraîchir la liste depuis le backend pour avoir les données à jour
                await fetchData();
                setConfirmDeleteProduct(null);
            } else {
                const errorMsg = response?.error?.message || response?.error || 'Erreur lors de la suppression du produit';
                notifyError(response?.error || errorMsg, { action: 'Supprimer le produit' });
                setConfirmDeleteProduct(null);
            }
        } catch (error) {
            console.error("Error deleting product", error);
            const errorMessage = error?.response?.data?.error?.message 
                || error?.response?.data?.error
                || error?.response?.data?.message 
                || error?.message 
                || 'Erreur lors de la suppression du produit';
            notifyError(error, { action: 'Supprimer le produit', fallback: errorMessage });
            setConfirmDeleteProduct(null);
        } finally {
            setDeletingProductId(null);
        }
    }

    // Group products by category
    const productsByCategory = {};
    categories.forEach(cat => {
        productsByCategory[cat.id] = { ...cat, items: [] };
    });
    // Add a "Uncategorized" or handle products with null category if any
    products.forEach(p => {
        if (p.category && productsByCategory[p.category]) {
            productsByCategory[p.category].items.push(p);
        } else {
            // Handle uncategorized or deleted categories
             if (!productsByCategory['uncategorized']) {
                 productsByCategory['uncategorized'] = { name: 'Sans catégorie', items: [] };
             }
             productsByCategory['uncategorized'].items.push(p);
        }
    });

    if (loading) return <StoreLayout title="Chargement..."><div>Chargement...</div></StoreLayout>;

    const hasCategories = Array.isArray(categories) && categories.length > 0;

    return (
        <>
        <StoreLayout title="Gestion des Produits">
            <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-2xl font-bold">Mes Produits</h2>
                <div className="flex flex-wrap gap-2">
                    {/* Bouton désactivé - Seul l'admin peut créer des catégories */}
                    {/* <button 
                        onClick={() => setShowCategoryModal(true)}
                        className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                    >
                        + Nouvelle Catégorie
                    </button> */}
                    <button 
                        onClick={async () => {
                            
                            // Vérifier si le magasin peut ajouter des produits
                            const canAdd = subscriptionInfo?.features?.can_add_more_products ?? subscriptionInfo?.limits?.products?.can_add_more ?? true;
                            
                            if (!canAdd) {
                                
                                // Le serveur rédige le conseil : il ne propose qu'un forfait réellement en vente.
                                const maxProducts = subscriptionInfo?.limits?.products?.max ?? subscriptionInfo?.features?.max_products ?? null;
                                const message = subscriptionInfo?.limits?.products?.limit_message
                                    || (maxProducts !== null
                                        ? `Vous avez atteint la limite de ${maxProducts} produits de votre forfait.`
                                        : 'Vous avez atteint la limite de produits de votre forfait.');
                                
                                showToast(message, 'error');
                                return;
                            }
                            
                            setShowProductModal(true);
                            showToast('Formulaire de création de produit ouvert', 'success');
                        }}
                        className="bg-indigo-600 text-white px-4 py-2 rounded hover:bg-indigo-700"
                    >
                        + Nouveau Produit
                    </button>
                    <button
                        type="button"
                        onClick={() => setShowImportModal(true)}
                        className="inline-flex items-center gap-2 border border-indigo-600 text-indigo-700 px-4 py-2 rounded hover:bg-indigo-50"
                    >
                        Importer (Excel/CSV)
                        {!canImport && (
                            <span className="rounded bg-amber-100 px-1.5 py-0.5 text-xs font-semibold text-amber-800">Pro</span>
                        )}
                    </button>
                </div>
            </div>

            <div className="space-y-8">
                {Object.values(productsByCategory).map((category, idx) => (
                    <div key={category.id || idx} className="bg-white p-6 rounded-lg shadow">
                        <h3 className="text-xl font-semibold mb-4 border-b pb-2">{category.name}</h3>
                        {category.items.length === 0 ? (
                            <p className="text-gray-500">Aucun produit dans cette catégorie.</p>
                        ) : (
                            <div className="flex overflow-x-auto space-x-4 pb-4">
                                {category.items.map(product => (
                                    <div key={product.id} className="border rounded p-4 flex flex-col min-w-[280px] w-[280px] flex-shrink-0 bg-white hover:shadow-md transition-shadow">
                                        {product.image && (
                                            <div className="relative mb-3">
                                                <img src={product.image} alt={product.name} className="w-full h-40 object-cover rounded" />
                                                {allPhotos(product).length > 1 && (
                                                    <span className="absolute bottom-2 right-2 rounded bg-black/60 px-2 py-0.5 text-xs text-white">📷 {allPhotos(product).length}</span>
                                                )}
                                            </div>
                                        )}
                                        <h4 className="font-bold text-lg mb-1 truncate" title={product.name}>{product.name}</h4>
                                        <PriceWithPromo product={product} className="mb-2" />
                                        <p className="text-sm text-gray-600 mb-3 line-clamp-2 h-10 overflow-hidden">{product.description}</p>
                                        <div className="mt-auto flex justify-between items-center pt-2 border-t">
                                            <div className="flex space-x-6 w-full justify-center">
                                                <button 
                                                    onClick={() => handleViewProduct(product)}
                                                    className="text-blue-600 hover:text-blue-800"
                                                    title="Voir"
                                                >
                                                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                                    </svg>
                                                </button>
                                                <button 
                                                    onClick={() => handleEditProduct(product)}
                                                    className="text-yellow-600 hover:text-yellow-800"
                                                    title="Modifier"
                                                >
                                                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                                                    </svg>
                                                </button>
                                                <button 
                                                    onClick={() => handleDeleteProduct(product.id)}
                                                    className="text-red-600 hover:text-red-800"
                                                    title="Supprimer"
                                                >
                                                    <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                                    </svg>
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                ))}
            </div>

            {/* View Product Modal */}
            {viewingProduct && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
                    <div className="bg-white rounded-lg p-6 w-full max-w-lg relative">
                        <button 
                            onClick={() => setViewingProduct(null)}
                            className="absolute top-4 right-4 text-gray-500 hover:text-gray-700"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                        <h3 className="text-2xl font-bold mb-4 pr-8">{viewingProduct.name}</h3>
                        {allPhotos(viewingProduct).length > 0 && (
                            <div className="mb-4">
                                <img src={allPhotos(viewingProduct)[viewingPhoto] || allPhotos(viewingProduct)[0]} alt={viewingProduct.name} className="w-full h-64 object-cover rounded" />
                                {allPhotos(viewingProduct).length > 1 && (
                                    <div className="mt-2 flex gap-2 overflow-x-auto">
                                        {allPhotos(viewingProduct).map((src, i) => (
                                            <button key={src} type="button" onClick={() => setViewingPhoto(i)} className={`h-14 w-14 flex-shrink-0 overflow-hidden rounded border-2 ${i === viewingPhoto ? 'border-indigo-600' : 'border-transparent'}`}>
                                                <img src={src} alt="" className="h-full w-full object-cover" />
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}
                        <div className="space-y-3">
                            <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                                <span className="font-semibold text-gray-700">Prix:</span>
                                <PriceWithPromo product={viewingProduct} className="text-xl" />
                            </div>
                            <div>
                                <span className="font-semibold text-gray-700">Stock:</span>
                                <span className="ml-2">{viewingProduct.stock} unités</span>
                            </div>
                            <div>
                                <span className="font-semibold text-gray-700">Poids:</span>
                                <span className="ml-2">{viewingProduct.weight_kg ? `${viewingProduct.weight_kg} kg` : '?'}</span>
                            </div>
                            <div>
                                <span className="font-semibold text-gray-700">Longueur:</span>
                                <span className="ml-2">{viewingProduct.length_m ? `${viewingProduct.length_m} m` : '?'}</span>
                            </div>
                            {[['brand', 'Marque'], ['model', 'Modèle'], ['sizes', 'Tailles / pointures'], ['color', 'Couleur']]
                                .filter(([k]) => viewingProduct.attributes?.[k])
                                .map(([k, label]) => (
                                    <div key={k}>
                                        <span className="font-semibold text-gray-700">{label}:</span>
                                        <span className="ml-2">{viewingProduct.attributes[k]}</span>
                                    </div>
                                ))}
                            <div>
                                <span className="font-semibold text-gray-700">Catégorie:</span>
                                <span className="ml-2 bg-gray-100 px-2 py-1 rounded text-sm">
                                    {categories.find(c => c.id === viewingProduct.category)?.name || 'Non catégorisé'}
                                </span>
                            </div>
                            <div>
                                <h4 className="font-semibold text-gray-700 mb-1">Description:</h4>
                                <p className="text-gray-600 whitespace-pre-wrap">{viewingProduct.description || "Aucune description."}</p>
                            </div>
                        </div>
                        <div className="mt-6 flex justify-end">
                            <button 
                                onClick={() => setViewingProduct(null)}
                                className="px-4 py-2 bg-gray-200 text-gray-800 rounded hover:bg-gray-300"
                            >
                                Fermer
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Category Modal - DÉSACTIVÉ - Seul l'admin peut créer des catégories */}
            {/* {showCategoryModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
                    <div className="bg-white rounded-lg p-6 w-full max-w-lg">
                        <h3 className="text-lg font-bold mb-4">Nouvelle Catégorie</h3>
                        <form onSubmit={handleCreateCategory}>
                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-1">Nom *</label>
                                <input 
                                    type="text" 
                                    className="w-full border rounded p-2"
                                    value={newCategory.name}
                                    onChange={e => setNewCategory({...newCategory, name: e.target.value})}
                                    required
                                />
                            </div>
                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-1">Description</label>
                                <textarea 
                                    className="w-full border rounded p-2"
                                    value={newCategory.description}
                                    onChange={e => setNewCategory({...newCategory, description: e.target.value})}
                                    rows="3"
                                />
                            </div>
                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-1">Taux de commission (%) *</label>
                                <input 
                                    type="number" 
                                    step="0.01"
                                    min="0"
                                    max="100"
                                    className="w-full border rounded p-2"
                                    value={newCategory.commission_rate}
                                    onChange={e => setNewCategory({...newCategory, commission_rate: e.target.value})}
                                    required
                                />
                                <p className="text-xs text-gray-500 mt-1">Valeur entre 0 et 100</p>
                            </div>
                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-1">Ordre d'affichage</label>
                                <input 
                                    type="number" 
                                    className="w-full border rounded p-2"
                                    value={newCategory.order}
                                    onChange={e => setNewCategory({...newCategory, order: e.target.value})}
                                />
                            </div>
                            <div className="flex justify-end space-x-2">
                                <button 
                                    type="button"
                                    onClick={() => {
                                        setShowCategoryModal(false);
                                        setNewCategory({ name: '', description: '', commission_rate: '8.00', order: 0 });
                                    }}
                                    className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded"
                                >
                                    Annuler
                                </button>
                                <button 
                                    type="submit"
                                    className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                                >
                                    Créer
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )} */}

            {/* Product Modal */}
            {showProductModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-3 z-[60]">
                    <div className="bg-white rounded-lg px-5 pt-5 w-full max-w-lg max-h-[85dvh] overflow-y-auto">
                        <h3 className="text-lg font-bold mb-4">{editingProduct ? 'Modifier le Produit' : 'Nouveau Produit'}</h3>
                        <form onSubmit={handleSaveProduct}>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
                                <div>
                                    <label className="block text-sm font-medium mb-1">Nom</label>
                                    <input 
                                        type="text" 
                                        className="w-full border rounded p-2"
                                        value={newProduct.name}
                                        onChange={e => setNewProduct({...newProduct, name: e.target.value})}
                                        required
                                    />
                                </div>
                                <div>
                                    <label className="block text-sm font-medium mb-1">Prix</label>
                                    <input 
                                        type="number" 
                                        className="w-full border rounded p-2"
                                        value={newProduct.price}
                                        onChange={e => setNewProduct({...newProduct, price: e.target.value})}
                                        required
                                    />
                                </div>
                            </div>

                            <div className="mb-4">
                                <label htmlFor="compare-price" className="block text-sm font-medium mb-1">Prix avant promo (barré)</label>
                                {canPromote ? (
                                    <>
                                        <input
                                            id="compare-price"
                                            type="number"
                                            min="0"
                                            className="w-full border rounded p-2"
                                            value={newProduct.compare_price}
                                            onChange={e => setNewProduct({ ...newProduct, compare_price: e.target.value })}
                                        />
                                        <p className="text-xs text-gray-500 mt-1">Laissez vide s'il n'y a pas de promotion.</p>
                                    </>
                                ) : editingProduct?.compare_price && newProduct.compare_price !== '' ? (
                                    <>
                                        <div className="flex flex-wrap items-center gap-2">
                                            <input
                                                id="compare-price"
                                                type="number"
                                                className="min-w-0 flex-1 border rounded p-2 bg-gray-100 text-gray-600"
                                                value={newProduct.compare_price}
                                                readOnly
                                            />
                                            <button
                                                type="button"
                                                onClick={() => setNewProduct({ ...newProduct, compare_price: '' })}
                                                className="px-3 py-2 text-sm text-red-700 border border-red-200 rounded hover:bg-red-50"
                                            >
                                                Retirer la promo
                                            </button>
                                        </div>
                                        <p className="text-xs text-gray-500 mt-1 break-words">
                                            {store?.is_b2b ? (
                                                "Cette promo reste en place. Les grossistes ne peuvent pas encore en créer d'autres."
                                            ) : (
                                                <>
                                                    Cette promo reste en place. Pour la modifier ou en créer d'autres :{' '}
                                                    <Link to="/store/subscription" className="text-indigo-600 underline">passer au forfait Pro</Link>.
                                                </>
                                            )}
                                        </p>
                                    </>
                                ) : (
                                    <>
                                        <input
                                            id="compare-price"
                                            type="number"
                                            className="w-full border rounded p-2 bg-gray-100"
                                            value=""
                                            disabled
                                            readOnly
                                        />
                                        <p className="text-xs text-gray-600 mt-1 break-words">
                                            {store?.is_b2b ? (
                                                "Les promotions (prix barré) ne sont pas encore proposées aux grossistes."
                                            ) : (
                                                <>
                                                    Promotions (prix barré) : forfait Pro.{' '}
                                                    <Link to="/store/subscription" className="text-indigo-600 underline">Passer au forfait Pro</Link>
                                                </>
                                            )}
                                        </p>
                                    </>
                                )}
                            </div>

                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-1">Catégorie</label>
                                <select 
                                    className="w-full border rounded p-2"
                                    value={newProduct.category}
                                    onChange={e => setNewProduct({...newProduct, category: e.target.value})}
                                    required
                                    disabled={!hasCategories}
                                >
                                    <option value="">{hasCategories ? 'Sélectionner une catégorie' : 'Aucune catégorie disponible'}</option>
                                    {categories.map(c => (
                                        <option key={c.id} value={c.id}>{c.name}</option>
                                    ))}
                                </select>
                                {!hasCategories && (
                                    <p className="text-sm text-gray-500 mt-2">Aucune catégorie disponible pour votre magasin. Contactez l'administrateur.</p>
                                )}
                            </div>
                            <div className="space-y-4 mb-4">
                                <ProductSpecsFields
                                    key={editingProduct?.id || 'new'}
                                    weightKg={newProduct.weight_kg}
                                    lengthM={newProduct.length_m}
                                    attributes={newProduct.attributes || {}}
                                    fashion={isFashionCategory(categories.find(c => String(c.id) === String(newProduct.category))?.name)}
                                    onChange={(patch) => setNewProduct(prev => ({ ...prev, ...patch }))}
                                    inputClass="w-full border rounded p-2"
                                    labelClass="block text-sm font-medium"
                                />
                            </div>
                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-1">Description</label>
                                <textarea 
                                    className="w-full border rounded p-2"
                                    value={newProduct.description}
                                    onChange={e => setNewProduct({...newProduct, description: e.target.value})}
                                />
                            </div>
                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-1">Stock</label>
                                <input 
                                    type="number" 
                                    className="w-full border rounded p-2"
                                    value={newProduct.stock}
                                    onChange={e => setNewProduct({...newProduct, stock: e.target.value})}
                                    required
                                />
                            </div>
                            <ProductPhotosField
                                product={editingProduct}
                                mainFile={newProduct.image}
                                onMainFile={(file) => setNewProduct({ ...newProduct, image: file })}
                                galleryFiles={galleryFiles}
                                onGalleryFiles={setGalleryFiles}
                                removed={removedPhotos}
                                onRemoved={setRemovedPhotos}
                            />
                            <div className="sticky bottom-0 -mx-5 px-5 py-3 bg-white border-t border-gray-100 flex justify-end space-x-2">
                                <button 
                                    type="button"
                                    onClick={() => {
                                        setShowProductModal(false);
                                        setEditingProduct(null);
                                        setNewProduct(emptyProduct()); setGalleryFiles([]); setRemovedPhotos([]);
                                    }}
                                    className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded"
                                >
                                    Annuler
                                </button>
                                <button 
                                    type="submit"
                                    className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
                                    disabled={!hasCategories}
                                >
                                    {editingProduct ? 'Enregistrer' : 'Créer'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            {/* Import Excel/CSV : présentation de l'outil Pro, ou modèle -> fichier -> aperçu -> création */}
            {showImportModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-3 z-[60]">
                    <div className={`bg-white rounded-lg px-5 pt-5 w-full ${canImport ? 'max-w-2xl' : 'max-w-md pb-5'} max-h-[85dvh] overflow-y-auto relative`}>
                        <button
                            type="button"
                            onClick={closeImportModal}
                            disabled={!!importBusy}
                            className="absolute top-4 right-4 text-gray-500 hover:text-gray-700 disabled:opacity-40"
                            aria-label="Fermer"
                        >
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                            </svg>
                        </button>
                        <h3 className="text-lg font-bold mb-3 pr-8">Importer des produits (Excel/CSV)</h3>

                        {!canImport ? (
                            <div className="space-y-4">
                                <span className="inline-block rounded bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-800">Forfait Pro</span>
                                <p className="text-sm text-gray-700">
                                    Ajoutez des centaines de produits en une fois depuis un fichier Excel ou CSV (dans la limite de produits de votre forfait), au lieu de les saisir un par un.
                                </p>
                                <p className="text-sm text-gray-700">Cet outil fait partie du forfait Pro.</p>
                                <div className="flex flex-wrap justify-end gap-2">
                                    <button
                                        type="button"
                                        onClick={closeImportModal}
                                        className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded"
                                    >
                                        Fermer
                                    </button>
                                    <Link
                                        to="/store/subscription"
                                        className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
                                    >
                                        Passer au forfait Pro
                                    </Link>
                                </div>
                            </div>
                        ) : (
                            <>
                                <ol className="space-y-5">
                                    <li>
                                        <p className="font-semibold mb-2">1. Téléchargez le modèle</p>
                                        <ul className="list-disc pl-5 text-sm text-gray-600 space-y-1 mb-3">
                                            <li>Colonnes obligatoires : Nom, Prix, Poids (kg), Longueur (m).</li>
                                            <li>500 lignes et 2 Mo maximum par fichier, .xlsx ou .csv, dans la limite de produits de votre forfait.</li>
                                            <li>Prix en francs CFA, sans centimes : « 4500 », « 4 500 » ou « 4.500 ».</li>
                                            <li>Une ligne par produit. Les photos s'ajoutent ensuite, produit par produit.</li>
                                            <li>Les lignes qui commencent par « Exemple » sont ignorées : remplacez-les par vos produits.</li>
                                        </ul>
                                        <button
                                            type="button"
                                            onClick={handleDownloadTemplate}
                                            disabled={!!importBusy}
                                            className="px-4 py-2 border border-indigo-600 text-indigo-700 rounded hover:bg-indigo-50 disabled:opacity-50"
                                        >
                                            {importBusy === 'template' ? 'Téléchargement...' : 'Télécharger le modèle'}
                                        </button>
                                    </li>
                                    <li>
                                        <p className="font-semibold mb-2">2. Choisissez votre fichier rempli</p>
                                        {/* Sélection vidée à l'ouverture : choisir à nouveau le même fichier corrigé relance bien la lecture. */}
                                        <input
                                            key={importInputKey}
                                            type="file"
                                            accept=".xlsx,.csv"
                                            onClick={e => { e.target.value = ''; }}
                                            onChange={e => handleImportFile(e.target.files?.[0] || null)}
                                            disabled={!!importBusy}
                                            className="block w-full min-w-0 text-sm file:mr-3 file:rounded file:border-0 file:bg-gray-100 file:px-3 file:py-2"
                                        />
                                        {importFile && (
                                            <p className="text-xs text-gray-500 mt-1 break-words">
                                                {importFile.name} ({Math.max(1, Math.round(importFile.size / 1024))} Ko)
                                            </p>
                                        )}
                                        <button
                                            type="button"
                                            onClick={() => runImport(false)}
                                            disabled={!!importBusy}
                                            className="mt-3 px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
                                        >
                                            {importBusy === 'preview' ? 'Vérification...' : 'Vérifier le fichier'}
                                        </button>
                                    </li>
                                    <li>
                                        <p className="font-semibold mb-2">3. Vérifiez, puis créez les produits</p>
                                        {!importPreview ? (
                                            <p className="text-sm text-gray-500">L'aperçu s'affiche ici. Rien n'est créé avant votre confirmation.</p>
                                        ) : (
                                            <div className="space-y-3">
                                                {importPreview.message && (
                                                    <p className="text-sm text-gray-800 bg-indigo-50 border border-indigo-100 rounded p-3 break-words">{importPreview.message}</p>
                                                )}
                                                {importPreview.unknown_columns?.length > 0 && (
                                                    <p className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded p-3 break-words">
                                                        Colonnes ignorées : {importPreview.unknown_columns.join(', ')}
                                                    </p>
                                                )}
                                                {importPreview.rows?.length > 0 ? (
                                                    <div className="overflow-x-auto border rounded">
                                                        <table className="w-full min-w-[520px] text-sm">
                                                            <thead className="bg-gray-50 text-left text-gray-600">
                                                                <tr>
                                                                    <th className="px-3 py-2 font-medium">Ligne</th>
                                                                    <th className="px-3 py-2 font-medium">Produit</th>
                                                                    <th className="px-3 py-2 font-medium">Prix</th>
                                                                    <th className="px-3 py-2 font-medium">État</th>
                                                                    <th className="px-3 py-2 font-medium">Détail</th>
                                                                </tr>
                                                            </thead>
                                                            <tbody className="divide-y">
                                                                {importPreview.rows.map(row => {
                                                                    const status = IMPORT_STATUS[row.status] || IMPORT_STATUS.error;
                                                                    return (
                                                                        <tr key={row.row} className="align-top">
                                                                            <td className="px-3 py-2 text-gray-500">{row.row}</td>
                                                                            <td className="px-3 py-2 font-medium break-words max-w-[180px]">{row.name || '—'}</td>
                                                                            <td className="px-3 py-2 whitespace-nowrap">
                                                                                {row.price ? `${Number(row.price).toLocaleString('fr-FR')} F` : '—'}
                                                                                {row.compare_price ? (
                                                                                    <span className="block text-xs text-gray-400 line-through">{Number(row.compare_price).toLocaleString('fr-FR')} F</span>
                                                                                ) : null}
                                                                            </td>
                                                                            <td className="px-3 py-2">
                                                                                <span className={`whitespace-nowrap rounded px-2 py-0.5 text-xs font-semibold ${status.className}`}>{status.label}</span>
                                                                            </td>
                                                                            <td className="px-3 py-2 text-gray-600 break-words">
                                                                                {row.message && <p>{row.message}</p>}
                                                                                {row.notes?.length > 0 && (
                                                                                    <p className="text-xs text-amber-700">{row.notes.join(' · ')}</p>
                                                                                )}
                                                                            </td>
                                                                        </tr>
                                                                    );
                                                                })}
                                                            </tbody>
                                                        </table>
                                                    </div>
                                                ) : (
                                                    <p className="text-sm text-gray-500">Le fichier ne contient aucune ligne de produit.</p>
                                                )}
                                                {importPreview.categories?.length > 0 && (
                                                    <details className="text-xs text-gray-500">
                                                        <summary className="cursor-pointer">Catégories reconnues ({importPreview.categories.length})</summary>
                                                        <p className="mt-1 break-words">{importPreview.categories.join(', ')}</p>
                                                    </details>
                                                )}
                                                {!(importPreview.counts?.ok > 0) && (
                                                    <p className="text-sm text-red-700">
                                                        Aucune ligne prête à créer : corrigez le fichier, choisissez-le à nouveau, puis vérifiez-le.
                                                    </p>
                                                )}
                                            </div>
                                        )}
                                    </li>
                                </ol>
                                <div className="sticky bottom-0 -mx-5 px-5 py-3 mt-5 bg-white border-t border-gray-100 flex flex-wrap justify-end gap-2">
                                    <button
                                        type="button"
                                        onClick={closeImportModal}
                                        disabled={!!importBusy}
                                        className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded disabled:opacity-50"
                                    >
                                        Fermer
                                    </button>
                                    {importPreview && (
                                        <button
                                            type="button"
                                            onClick={() => runImport(true)}
                                            disabled={!!importBusy || !(importPreview.counts?.ok > 0)}
                                            className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            {importBusy === 'confirm'
                                                ? 'Création en cours...'
                                                : `Créer ${importPreview.counts?.ok || 0} produit${(importPreview.counts?.ok || 0) > 1 ? 's' : ''}`}
                                        </button>
                                    )}
                                </div>
                            </>
                        )}
                    </div>
                </div>
            )}

            {/* Modal de confirmation de suppression */}
            <ConfirmModal
                isOpen={!!confirmDeleteProduct}
                onClose={() => {
                    if (!deletingProductId) {
                        setConfirmDeleteProduct(null);
                    }
                }}
                title="Supprimer le produit"
                message="Êtes-vous sûr de vouloir supprimer ce produit ? Cette action est irréversible."
                confirmText={deletingProductId ? "Suppression en cours..." : "Supprimer"}
                cancelText="Annuler"
                onConfirm={confirmDelete}
                variant="danger"
                autoClose={false}
                loading={!!deletingProductId}
            />

        </StoreLayout>
        {/* Toast Notification - Rendered outside StoreLayout to avoid overflow issues */}
        {toast && (
            <div className="fixed bottom-5 right-5 z-[100] animate-slide-in-right max-w-md">
                <div
                    className={`px-6 py-4 rounded-lg shadow-2xl border-2 text-white font-semibold ${
                        toast.type === 'success' 
                            ? 'bg-green-600 border-green-500' 
                            : 'bg-red-600 border-red-500'
                    }`}
                >
                    <div className="flex items-start gap-3">
                        {toast.type === 'success' ? (
                            <svg className="w-6 h-6 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        ) : (
                            <svg className="w-6 h-6 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                        )}
                        <div className="flex-1">
                            <p className="font-bold text-lg mb-1">
                                {toast.type === 'success' ? 'Succès' : 'Limite atteinte'}
                            </p>
                            <p className="text-sm leading-relaxed">{toast.message}</p>
                        </div>
                    </div>
                </div>
            </div>
        )}
        </>
    );
};

export default StoreProducts;
