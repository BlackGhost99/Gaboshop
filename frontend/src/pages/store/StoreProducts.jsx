import React, { useState, useEffect } from 'react';
import StoreLayout from '../../components/StoreLayout';
import { getStoreDashboard } from '../../services/dashboardService';
import { 
    getStoreProducts, 
    getManagerStoreProducts,
    getStoreCategories, 
    getAllCategories,
    createProduct, 
    updateProduct,
    deleteProduct
} from '../../services/productService';

const StoreProducts = () => {
    const [store, setStore] = useState(null);
    const [products, setProducts] = useState([]);
    const [categories, setCategories] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showProductModal, setShowProductModal] = useState(false);
    
    // Form states
    const [newProduct, setNewProduct] = useState({
        name: '', description: '', price: '', stock: '', category: '', image: null
    });
    const [viewingProduct, setViewingProduct] = useState(null);
    const [editingProduct, setEditingProduct] = useState(null);

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
                
                const [productsRes, storeCategoriesRes, allCategoriesRes] = await Promise.all([
                    getManagerStoreProducts(storeId),
                    getStoreCategories(storeId),
                    getAllCategories()
                ]);

                if (productsRes.success) setProducts(productsRes.data.products || []);
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

    // Note: merchants cannot create categories from the frontend.

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
    
    const handleDeleteProduct = async (productId) => {
        if(!window.confirm("Êtes-vous sûr de vouloir supprimer ce produit ?")) return;
        try {
            await deleteProduct(productId);
            setProducts(products.filter(p => p.id !== productId));
        } catch (error) {
            console.error("Error deleting product", error);
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
        <StoreLayout title="Gestion des Produits">
            <div className="mb-6 flex justify-between">
                <h2 className="text-2xl font-bold">Mes Produits</h2>
                <div className="space-x-2">
                    <button 
                        onClick={() => setShowProductModal(true)}
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

            {/* Category Modal */}
            {/* Category creation removed: merchants cannot add categories from frontend */}

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
        </StoreLayout>
    );
};

export default StoreProducts;
