import React, { useState, useEffect } from 'react';
import StoreLayout from '../../components/StoreLayout';
import ConfirmModal from '../../components/ConfirmModal';
import { getStoreDashboard } from '../../services/dashboardService';
import { 
    getStoreProducts, 
    getManagerStoreProducts,
    getStoreCategories, 
    getAllCategories,
    createProduct, 
    updateProduct,
    deleteProduct
    // createStoreCategory - DÉSACTIVÉ: Seul l'admin peut créer des catégories
} from '../../services/productService';

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
    const [newProduct, setNewProduct] = useState({
        name: '', description: '', price: '', stock: '', category: '', image: null
    });
    const [newCategory, setNewCategory] = useState({
        name: '', description: '', commission_rate: '8.00', order: 0
    });
    const [viewingProduct, setViewingProduct] = useState(null);
    const [editingProduct, setEditingProduct] = useState(null);
    const [toast, setToast] = useState(null);
    const [subscriptionInfo, setSubscriptionInfo] = useState(null);

    useEffect(() => {
        fetchData();
    }, []);

    useEffect(() => {
        // #region agent log
        if (toast) {
            fetch('http://127.0.0.1:7242/ingest/3034891a-d8c4-4be8-b0a8-8720a23ed625',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'StoreProducts.jsx:38',message:'Toast state changed',data:{toastExists:!!toast,toastMessage:toast?.message,toastType:toast?.type},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B,D'})}).catch(()=>{});
        }
        // #endregion
    }, [toast]);

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
                // Prefer global list when available, otherwise use store-specific
                if (allCategoriesRes && allCategoriesRes.success) {
                    setCategories(allCategoriesRes.data || []);
                } else if (storeCategoriesRes && storeCategoriesRes.success) {
                    setCategories(storeCategoriesRes.data || []);
                }
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
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/3034891a-d8c4-4be8-b0a8-8720a23ed625',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'StoreProducts.jsx:105',message:'showToast entry',data:{message,type},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A,B'})}).catch(()=>{});
        // #endregion
        setToast({ message, type });
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/3034891a-d8c4-4be8-b0a8-8720a23ed625',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'StoreProducts.jsx:108',message:'showToast after setToast',data:{message,type},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'B'})}).catch(()=>{});
        // #endregion
        setTimeout(() => setToast(null), 5000);
    };

    const handleViewProduct = (product) => {
        setViewingProduct(product);
    };

    const handleEditProduct = (product) => {
        setEditingProduct(product);
        setNewProduct({
            name: product.name,
            description: product.description || '',
            price: product.price,
            stock: product.stock,
            category: product.category,
            image: null
        });
        setShowProductModal(true);
    };

    const handleSaveProduct = async (e) => {
        e.preventDefault();
        const formData = new FormData();
        Object.keys(newProduct).forEach(key => {
            if (newProduct[key] !== null && newProduct[key] !== '') {
                formData.append(key, newProduct[key]);
            }
        });

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
                setNewProduct({ name: '', description: '', price: '', stock: '', category: '', image: null });
            }
        } catch (error) {
            console.error("Error saving product", error);
            const message = error.error?.details 
                ? Object.values(error.error.details).flat().join('\n')
                : (error.error?.message || "Erreur lors de l'enregistrement du produit");
            alert(message);
        }
    };
    
    const handleDeleteProduct = (productId) => {
        // Ouvrir le modal de confirmation
        setConfirmDeleteProduct(productId);
    }

    const confirmDelete = async () => {
        if (!confirmDeleteProduct || deletingProductId) return;
        
        // #region agent log
        fetch('http://127.0.0.1:7242/ingest/3034891a-d8c4-4be8-b0a8-8720a23ed625',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'StoreProducts.jsx:157',message:'confirmDelete entry',data:{productId:confirmDeleteProduct},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A,B,C,D'})}).catch(()=>{});
        // #endregion
        
        setDeletingProductId(confirmDeleteProduct);
        try {
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/3034891a-d8c4-4be8-b0a8-8720a23ed625',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'StoreProducts.jsx:162',message:'Before deleteProduct API call',data:{productId:confirmDeleteProduct},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
            // #endregion
            
            const response = await deleteProduct(confirmDeleteProduct);
            
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/3034891a-d8c4-4be8-b0a8-8720a23ed625',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'StoreProducts.jsx:165',message:'deleteProduct API response',data:{responseSuccess:response?.success,responseMessage:response?.message,responseError:response?.error,responseFull:response},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A,B'})}).catch(()=>{});
            // #endregion
            
            if (response?.success) {
                // Retirer immédiatement le produit de la liste (même s'il est désactivé au lieu d'être supprimé)
                setProducts(prevProducts => prevProducts.filter(p => p.id !== confirmDeleteProduct));
                // Rafraîchir la liste depuis le backend pour avoir les données à jour
                await fetchData();
                setConfirmDeleteProduct(null);
            } else {
                const errorMsg = response?.error?.message || response?.error || 'Erreur lors de la suppression du produit';
                alert(errorMsg);
                setConfirmDeleteProduct(null);
            }
        } catch (error) {
            // #region agent log
            fetch('http://127.0.0.1:7242/ingest/3034891a-d8c4-4be8-b0a8-8720a23ed625',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'StoreProducts.jsx:173',message:'Error in confirmDelete',data:{errorMessage:error?.message,errorResponse:error?.response?.data,errorStatus:error?.response?.status,errorFull:JSON.stringify(error)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C,D'})}).catch(()=>{});
            // #endregion
            console.error("Error deleting product", error);
            const errorMessage = error?.response?.data?.error?.message 
                || error?.response?.data?.error
                || error?.response?.data?.message 
                || error?.message 
                || 'Erreur lors de la suppression du produit';
            alert(errorMessage);
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
            <div className="mb-6 flex justify-between">
                <h2 className="text-2xl font-bold">Mes Produits</h2>
                <div className="space-x-2">
                    {/* Bouton désactivé - Seul l'admin peut créer des catégories */}
                    {/* <button 
                        onClick={() => setShowCategoryModal(true)}
                        className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                    >
                        + Nouvelle Catégorie
                    </button> */}
                    <button 
                        onClick={async () => {
                            // #region agent log
                            fetch('http://127.0.0.1:7242/ingest/3034891a-d8c4-4be8-b0a8-8720a23ed625',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'StoreProducts.jsx:264',message:'Button onClick triggered',data:{},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'A'})}).catch(()=>{});
                            // #endregion
                            
                            // Vérifier si le magasin peut ajouter des produits
                            const canAdd = subscriptionInfo?.features?.can_add_more_products ?? subscriptionInfo?.limits?.products?.can_add_more ?? true;
                            
                            if (!canAdd) {
                                // #region agent log
                                fetch('http://127.0.0.1:7242/ingest/3034891a-d8c4-4be8-b0a8-8720a23ed625',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'StoreProducts.jsx:270',message:'Product limit reached',data:{canAdd,subscriptionInfo},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'C'})}).catch(()=>{});
                                // #endregion
                                
                                const currentProducts = subscriptionInfo?.limits?.products?.current ?? subscriptionInfo?.features?.current_products ?? 0;
                                const maxProducts = subscriptionInfo?.limits?.products?.max ?? subscriptionInfo?.features?.max_products ?? null;
                                const planName = subscriptionInfo?.subscription?.plan_name ?? subscriptionInfo?.plan?.name ?? 'votre forfait';
                                
                                let message = `Vous avez atteint la limite de produits de ${planName}. `;
                                if (maxProducts !== null) {
                                    message += `Vous avez ${currentProducts}/${maxProducts} produits. `;
                                }
                                message += `Passez à un forfait supérieur pour ajouter plus de produits.`;
                                
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
                                            <img src={product.image} alt={product.name} className="w-full h-40 object-cover mb-3 rounded" />
                                        )}
                                        <h4 className="font-bold text-lg mb-1 truncate" title={product.name}>{product.name}</h4>
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
                        {viewingProduct.image && (
                            <img src={viewingProduct.image} alt={viewingProduct.name} className="w-full h-64 object-cover mb-4 rounded" />
                        )}
                        <div className="space-y-3">
                            <div>
                                <span className="font-semibold text-gray-700">Prix:</span>
                                <span className="ml-2 text-xl font-bold text-indigo-600">{viewingProduct.price} FCFA</span>
                            </div>
                            <div>
                                <span className="font-semibold text-gray-700">Stock:</span>
                                <span className="ml-2">{viewingProduct.stock} unités</span>
                            </div>
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
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 overflow-y-auto z-50">
                    <div className="bg-white rounded-lg p-6 w-full max-w-lg my-8">
                        <h3 className="text-lg font-bold mb-4">{editingProduct ? 'Modifier le Produit' : 'Nouveau Produit'}</h3>
                        <form onSubmit={handleSaveProduct}>
                            <div className="grid grid-cols-2 gap-4 mb-4">
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
                            <div className="mb-4">
                                <label className="block text-sm font-medium mb-1">Image</label>
                                <input 
                                    type="file" 
                                    className="w-full border rounded p-2"
                                    onChange={e => setNewProduct({...newProduct, image: e.target.files[0]})}
                                />
                                {editingProduct && editingProduct.image && (
                                    <p className="text-xs text-gray-500 mt-1">Laissez vide pour conserver l'image actuelle.</p>
                                )}
                            </div>
                            <div className="flex justify-end space-x-2">
                                <button 
                                    type="button"
                                    onClick={() => {
                                        setShowProductModal(false);
                                        setEditingProduct(null);
                                        setNewProduct({ name: '', description: '', price: '', stock: '', category: '', image: null });
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
