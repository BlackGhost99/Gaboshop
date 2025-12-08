import { useState } from 'react';

const AdminProductsSection = ({
  productsListAdmin,
  productsFilter,
  setProductsFilter,
  loadProductsData,
  productStats,
  setShowAddProduct,
  setEditingProduct,
  viewProductDetail,
  handleActivateProduct,
  handleDeactivateProduct,
  handleDeleteProduct,
  handleBulkActions,
  productCategories,
  stores,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedProducts, setSelectedProducts] = useState([]);
  const [bulkAction, setBulkAction] = useState('');
  const [showBulkStock, setShowBulkStock] = useState(false);
  const [bulkStockValue, setBulkStockValue] = useState(0);

  const handleSearch = (value) => {
    setSearchTerm(value);
    setProductsFilter({ ...productsFilter, search: value });
  };

  const getStockBadge = (stockStatus) => {
    if (stockStatus === 'in_stock') return 'bg-green-50 text-green-700';
    if (stockStatus === 'low_stock') return 'bg-yellow-50 text-yellow-700';
    return 'bg-red-50 text-red-700';
  };

  const getStockLabel = (stockStatus) => {
    if (stockStatus === 'in_stock') return 'En stock';
    if (stockStatus === 'low_stock') return 'Stock faible';
    return 'Rupture';
  };

  const toggleProductSelection = (productId) => {
    setSelectedProducts((prev) =>
      prev.includes(productId)
        ? prev.filter((id) => id !== productId)
        : [...prev, productId]
    );
  };

  const toggleSelectAll = () => {
    if (selectedProducts.length === productsListAdmin.length) {
      setSelectedProducts([]);
    } else {
      setSelectedProducts(productsListAdmin.map((p) => p.id));
    }
  };

  const handleBulkActionSubmit = () => {
    if (bulkAction && selectedProducts.length > 0) {
      if (bulkAction === 'update_stock') {
        handleBulkActions(bulkAction, selectedProducts, bulkStockValue);
      } else {
        handleBulkActions(bulkAction, selectedProducts);
      }
      setSelectedProducts([]);
      setBulkAction('');
      setShowBulkStock(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* KPI Stats Cards */}
      {productStats && (
        <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
          <div className="bg-white p-4 rounded-lg shadow-sm border border-gray-100">
            <p className="text-xs text-gray-500 mb-1">Total Produits</p>
            <p className="text-2xl font-bold text-gray-900">{productStats.total_products}</p>
          </div>
          <div className="bg-green-50 p-4 rounded-lg border border-green-200">
            <p className="text-xs text-green-700 mb-1">Actifs</p>
            <p className="text-2xl font-bold text-green-800">{productStats.active_products}</p>
          </div>
          <div className="bg-red-50 p-4 rounded-lg border border-red-200">
            <p className="text-xs text-red-700 mb-1">Inactifs</p>
            <p className="text-2xl font-bold text-red-800">{productStats.inactive_products}</p>
          </div>
          <div className="bg-orange-50 p-4 rounded-lg border border-orange-200">
            <p className="text-xs text-orange-700 mb-1">Rupture</p>
            <p className="text-2xl font-bold text-orange-800">{productStats.out_of_stock}</p>
          </div>
          <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
            <p className="text-xs text-yellow-700 mb-1">Stock Faible</p>
            <p className="text-2xl font-bold text-yellow-800">{productStats.low_stock}</p>
          </div>
          <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
            <p className="text-xs text-purple-700 mb-1">En Promo</p>
            <p className="text-2xl font-bold text-purple-800">{productStats.on_promo}</p>
          </div>
        </div>
      )}

      {/* Filtres */}
      <div className="bg-white shadow-sm rounded-lg p-4 border border-gray-100">
        <h3 className="font-semibold mb-3 text-sm">🔍 Recherche et Filtres</h3>
        <div className="grid grid-cols-1 md:grid-cols-8 gap-3">
          <input
            type="text"
            placeholder="Chercher un produit..."
            value={searchTerm}
            onChange={(e) => handleSearch(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded text-sm md:col-span-2"
          />

          <select
            value={productsFilter.category}
            onChange={(e) => setProductsFilter({ ...productsFilter, category: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded text-sm"
          >
            <option value="">Toutes catégories</option>
            {productCategories.map((c) => (
              <option key={c.id} value={c.id}>{c.name}</option>
            ))}
          </select>

          <select
            value={productsFilter.store_id}
            onChange={(e) => setProductsFilter({ ...productsFilter, store_id: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded text-sm"
          >
            <option value="">Tous les magasins</option>
            {stores.map((s) => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>

          <select
            value={productsFilter.status}
            onChange={(e) => setProductsFilter({ ...productsFilter, status: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded text-sm"
          >
            <option value="all">Tous statuts</option>
            <option value="active">Actifs</option>
            <option value="inactive">Inactifs</option>
          </select>

          <select
            value={productsFilter.stock}
            onChange={(e) => setProductsFilter({ ...productsFilter, stock: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded text-sm"
          >
            <option value="all">Tous stocks</option>
            <option value="in_stock">En stock</option>
            <option value="low_stock">Stock faible</option>
            <option value="out_of_stock">Rupture</option>
          </select>

          <select
            value={productsFilter.promo}
            onChange={(e) => setProductsFilter({ ...productsFilter, promo: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded text-sm"
          >
            <option value="all">Promo</option>
            <option value="promo">En promo</option>
            <option value="no_promo">Sans promo</option>
          </select>

          <button
            onClick={loadProductsData}
            className="px-3 py-2 bg-indigo-600 text-white rounded text-sm font-semibold hover:bg-indigo-700"
          >
            Appliquer
          </button>
        </div>
      </div>

      {/* Actions en masse */}
      {selectedProducts.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center gap-4">
            <span className="text-sm font-medium text-blue-900">
              {selectedProducts.length} produit(s) sélectionné(s)
            </span>
            <select
              value={bulkAction}
              onChange={(e) => {
                setBulkAction(e.target.value);
                setShowBulkStock(e.target.value === 'update_stock');
              }}
              className="px-3 py-2 border border-blue-300 rounded text-sm"
            >
              <option value="">Choisir une action...</option>
              <option value="activate">Activer</option>
              <option value="deactivate">Désactiver</option>
              <option value="delete">Supprimer</option>
              <option value="update_stock">Modifier le stock</option>
            </select>
            {showBulkStock && (
              <input
                type="number"
                min="0"
                value={bulkStockValue}
                onChange={(e) => setBulkStockValue(parseInt(e.target.value))}
                className="px-3 py-2 border border-blue-300 rounded text-sm w-24"
                placeholder="Stock"
              />
            )}
            <button
              onClick={handleBulkActionSubmit}
              disabled={!bulkAction}
              className="px-4 py-2 bg-blue-600 text-white rounded text-sm font-semibold hover:bg-blue-700 disabled:opacity-50"
            >
              Exécuter
            </button>
          </div>
        </div>
      )}

      {/* Bouton Ajouter */}
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">Liste des Produits ({productsListAdmin.length})</h2>
        <button
          onClick={() => setShowAddProduct(true)}
          className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-semibold hover:bg-indigo-700"
        >
          ➕ Ajouter un produit
        </button>
      </div>

      {/* Tableau des produits */}
      <div className="bg-white shadow-sm rounded-lg border border-gray-100 overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left">
                <input
                  type="checkbox"
                  checked={selectedProducts.length === productsListAdmin.length && productsListAdmin.length > 0}
                  onChange={toggleSelectAll}
                  className="rounded"
                />
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Image</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Nom</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Catégorie</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Magasin</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Prix</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Promo</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Stock</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Statut</th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Mis à jour</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {productsListAdmin.map((product) => (
              <tr key={product.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <input
                    type="checkbox"
                    checked={selectedProducts.includes(product.id)}
                    onChange={() => toggleProductSelection(product.id)}
                    className="rounded"
                  />
                </td>
                <td className="px-4 py-3">
                  {product.image ? (
                    <img src={product.image} alt={product.name} className="h-12 w-12 object-cover rounded" />
                  ) : (
                    <div className="h-12 w-12 bg-gray-200 rounded flex items-center justify-center text-gray-400 text-xs">
                      📦
                    </div>
                  )}
                </td>
                <td className="px-4 py-3 text-sm font-medium text-gray-900">{product.name}</td>
                <td className="px-4 py-3 text-sm text-gray-500">{product.category_name || '-'}</td>
                <td className="px-4 py-3 text-sm text-gray-500">{product.store_name}</td>
                <td className="px-4 py-3 text-sm font-semibold text-gray-900">{product.price} F</td>
                <td className="px-4 py-3 text-sm">
                  {product.on_promo ? (
                    <span className="text-red-600 font-semibold">{product.promo_price} F</span>
                  ) : (
                    '-'
                  )}
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 text-xs rounded-full ${getStockBadge(product.stock_status)}`}>
                    {product.stock} • {getStockLabel(product.stock_status)}
                  </span>
                </td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 text-xs rounded-full ${product.is_available ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
                    {product.is_available ? 'Actif' : 'Inactif'}
                  </span>
                </td>
                <td className="px-4 py-3 text-sm text-gray-500">
                  {product.updated_at ? new Date(product.updated_at).toLocaleDateString() : '-'}
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => viewProductDetail(product.id)}
                      className="p-1.5 text-blue-600 hover:text-blue-900 hover:bg-blue-50 rounded"
                      title="Voir détails"
                    >
                      🔍
                    </button>
                    <button
                      onClick={() => setEditingProduct(product)}
                      className="p-1.5 text-indigo-600 hover:text-indigo-900 hover:bg-indigo-50 rounded"
                      title="Modifier"
                    >
                      ✏️
                    </button>
                    {product.is_available ? (
                      <button
                        onClick={() => handleDeactivateProduct(product.id)}
                        className="p-1.5 text-orange-600 hover:text-orange-900 hover:bg-orange-50 rounded"
                        title="Désactiver"
                      >
                        🚫
                      </button>
                    ) : (
                      <button
                        onClick={() => handleActivateProduct(product.id)}
                        className="p-1.5 text-green-600 hover:text-green-900 hover:bg-green-50 rounded"
                        title="Activer"
                      >
                        ✅
                      </button>
                    )}
                    <button
                      onClick={() => handleDeleteProduct(product.id)}
                      className="p-1.5 text-red-600 hover:text-red-900 hover:bg-red-50 rounded"
                      title="Supprimer"
                    >
                      🗑️
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {productsListAdmin.length === 0 && (
              <tr>
                <td colSpan="11" className="px-6 py-8 text-center text-gray-500">
                  Aucun produit trouvé
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default AdminProductsSection;
