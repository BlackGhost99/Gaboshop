import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import Modal from '../../components/Modal';
import { 
	activateStoreB2B, 
	deactivateStoreB2B, 
	getStoreB2BProfile,
	createStoreB2BProfile 
} from '../../services/b2bService';
import {
  getAdminSummary,
  getAdminFinancials,
  getAdminUsers,
  getAdminOrders,
  getAdminPayments,
  getAdminDeliveries,
  getAdminStores,
  getAdminProducts,
  createAdminUser,
  updateAdminUser,
  deleteAdminUser,
  deleteStoreAdmin,
  getStoreCategories,
  createStoreCategory,
  updateStoreCategory,
  deleteStoreCategory,
  getAllProductCategories,
  getStoreDetailAdmin,
  getStoreOrdersAdmin,
  getStoreDeliveryAgentsAdmin,
  getStoresListAdmin,
  createStoreAdmin,
  updateStoreAdmin,
  deactivateStoreAdmin,
  activateStoreAdmin,
  getProductsListAdmin,
  getProductDetailAdmin,
  activateProductAdmin,
  deactivateProductAdmin,
  deleteProductAdmin,
  bulkActionsProductsAdmin,
  createProductAdmin,
  updateProductAdmin,
  getProductStats,
  getOrderStats,
  getOrdersList,
  getOrderDetail,
  assignDelivery,
  updateOrderStatus,
  cancelOrder,
  getOrdersByStore,
  getDeliveryAgentStats,
  getSystemSettings,
  updateSystemSettings,
  getFinanceDashboard,
  getTransactions,
  getCommissionsByStore,
  getDeliveryPayouts,
  getSubscriptions,
  getSponsoredProducts,
  getRevenueBreakdown,
} from '../../services/adminService';
import AdminSidebar from '../../components/AdminSidebar';
import AdminNavbar from '../../components/AdminNavbar';
import AdminStoresSection from '../../components/AdminStoresSection';
import AdminProductsSection from '../../components/AdminProductsSection';
import AdminOverviewSection from '../../components/AdminOverviewSection';
import AdminDeliverySection from '../../components/AdminDeliverySection';

const StatCard = ({ title, value, hint }) => (
  <div className="bg-white shadow-sm rounded-lg p-4 border border-gray-100">
    <p className="text-xs uppercase tracking-wide text-gray-500">{title}</p>
    <p className="text-2xl font-bold text-gray-900">{value}</p>
    {hint ? <p className="text-xs text-gray-400 mt-1">{hint}</p> : null}
  </div>
);

const AdminDashboard = () => {
  const navigate = useNavigate();
  const [summary, setSummary] = useState(null);
  // const [financials, setFinancials] = useState(null);  // Not used in favor of financeDashboard
  const [users, setUsers] = useState([]);
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [userFilter, setUserFilter] = useState('all');
  const [showAddUser, setShowAddUser] = useState(false);
  const [newUser, setNewUser] = useState({ phone: '', user_type: 'client', first_name: '', last_name: '', email: '', city: 'Libreville', password: '' });
  const [selectedUser, setSelectedUser] = useState(null);
  const [editingUser, setEditingUser] = useState(null);
  const [confirmDeleteUser, setConfirmDeleteUser] = useState(null);
  const [actionError, setActionError] = useState('');
  const [actionSuccess, setActionSuccess] = useState('');
  const [selectedStoreDetail, setSelectedStoreDetail] = useState(null);
  const [showStoreDetailModal, setShowStoreDetailModal] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState({ isOpen: false, message: '', onConfirm: null });
  const [b2bLoading, setB2bLoading] = useState({});
  const [storeCategories, setStoreCategories] = useState([]);
  const [allProductCategories, setAllProductCategories] = useState([]);
  const [payments, setPayments] = useState([]);
  const [deliveries, setDeliveries] = useState([]);
  const [stores, setStores] = useState([]);
  // const [products, setProducts] = useState([]);  // Using productsListAdmin instead
  
  // Store Cat CRUD
  const [showAddStoreCat, setShowAddStoreCat] = useState(false);
  const [editingStoreCat, setEditingStoreCat] = useState(null);
  const [newStoreCat, setNewStoreCat] = useState({ name: '', description: '', icon: '', is_active: true });
  const [selectedStoreCategory, setSelectedStoreCategory] = useState(null);

  // Store CRUD
  const [showAddStore, setShowAddStore] = useState(false);
  const [editingStore, setEditingStore] = useState(null);
  const [newStore, setNewStore] = useState({ name: '', description: '', category_id: '', manager_id: '', phone: '', email: '', address: '', city: 'Libreville', zone: '', commission_rate: 0, delivery_fee: 0, subscription_plan: 'starter', is_active: true });
  const [storesListAdmin, setStoresListAdmin] = useState([]);
  const [storesFilter, setStoresFilter] = useState({ search: '', category: '', city: '', status: 'all', sort: 'date' });

  // Product CRUD
  const [showAddProduct, setShowAddProduct] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [newProduct, setNewProduct] = useState({ name: '', description: '', price: 0, promo_price: null, stock: 0, is_available: true, store_id: '', category_id: '', sku: '' });
  const [viewingProduct, setViewingProduct] = useState(null);
  const [productsListAdmin, setProductsListAdmin] = useState([]);
  const [productStats, setProductStats] = useState(null);
  const [productsFilter, setProductsFilter] = useState({ search: '', category: '', store_id: '', status: 'all', stock: 'all', promo: 'all', price_min: '', price_max: '', sort: 'date' });

  // Orders Data
  const [orderStats, setOrderStats] = useState(null);
  const [ordersList, setOrdersList] = useState([]);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [ordersFilter, setOrdersFilter] = useState({ status: 'all', city: '', store_id: '', date_range: 'all' });
  const [ordersByStore, setOrdersByStore] = useState([]);
  const [deliveryAgents, setDeliveryAgents] = useState([]);
  const [showAssignDelivery, setShowAssignDelivery] = useState(false);
  const [assigningOrder, setAssigningOrder] = useState(null);
  const [autoAssign, setAutoAssign] = useState(false);
  const [selectedDeliveryAgent, setSelectedDeliveryAgent] = useState('');

  // System Settings
  const [systemSettings, setSystemSettings] = useState(null);
  const [editingSettings, setEditingSettings] = useState(false);
  const [settingsForm, setSettingsForm] = useState({});

  // Finance Data
  const [financeDashboard, setFinanceDashboard] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [commissions, setCommissions] = useState([]);
  const [payouts, setPayouts] = useState([]);
  const [subscriptions, setSubscriptions] = useState([]);
  // const [sponsored, setSponsored] = useState([]);  // Not used in dashboard
  const [revenueBreakdown, setRevenueBreakdown] = useState(null);


  const loadData = async (initial = false) => {
    try {
      if (initial) {
        setLoading(true);
      } else {
        setRefreshing(true);
      }
      const [s, _f, u, o, sc, pc, pay, del, st, settings, finDash, trans, commis, payoutsList, subs, _spons, revBreak] = await Promise.all([
        getAdminSummary(),
        getAdminFinancials(),  // Not used
        getAdminUsers(),
        getAdminOrders(),
        getStoreCategories(),
        getAllProductCategories(),
        getAdminPayments(),
        getAdminDeliveries(),
        getAdminStores(),
        // getAdminProducts(),  // Using getProductsListAdmin in products tab
        getSystemSettings(),
        getFinanceDashboard(),
        getTransactions(),
        getCommissionsByStore(),
        getDeliveryPayouts(),
        getSubscriptions(),
        getSponsoredProducts(),
        getRevenueBreakdown(),
      ]);
      if (!s?.success) throw new Error('Erreur summary');
      setSummary(s.data);
      // setFinancials(f?.data || null);  // Not used
      setUsers(u?.data || []);
      setOrders(o?.data || []);
      setStoreCategories(sc?.data || []);
      setAllProductCategories(pc?.data || []);
      setOrders(o?.data || []);
      setAllProductCategories(pc?.data || []);
      setPayments(pay?.data || []);
      setDeliveries(del?.data || []);
      setStores(st?.data || []);
      setStoresListAdmin(st?.data || []);  // Populate admin stores list from initial load
      // setProducts(pr?.data || []);  // Using productsListAdmin instead
      if (settings?.success) {
        setSystemSettings(settings.data);
        setSettingsForm(settings.data);
      }
      if (finDash?.success) {
        console.log('Finance Dashboard Data:', finDash.data);
        setFinanceDashboard(finDash.data);
      } else {
        console.error('Finance Dashboard Error:', finDash);
      }
      if (trans?.success) {
        setTransactions(trans.data);
      }
      if (commis?.success) {
        setCommissions(commis.data);
      }
      if (payoutsList?.success) {
        setPayouts(payoutsList.data);
      }
      if (subs?.success) {
        setSubscriptions(subs.data);
      }
      // if (spons?.success) {  // Not used
      //   setSponsored(spons.data);
      // }
      if (revBreak?.success) {
        setRevenueBreakdown(revBreak.data);
      }
      setError(null);
    } catch (err) {
      setError(err?.message || 'Erreur chargement admin');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData(true);
  }, []);

  const handleLogout = () => {
    sessionStorage.removeItem('token');
    sessionStorage.removeItem('refresh_token');
    navigate('/login');
  };

  const handleAddUser = async (e) => {
    e.preventDefault();
    if (!newUser.phone) return;
    try {
      setActionError('');
      const res = await createAdminUser(newUser);
      if (!res?.success) throw new Error(res?.message || 'Création échouée');
      setUsers((prev) => [res.data, ...prev]);
      setNewUser({ phone: '', user_type: 'client', first_name: '', last_name: '', email: '', city: 'Libreville', password: '' });
      setShowAddUser(false);
    } catch (err) {
      setActionError(err?.message || 'Création échouée');
    }
  };

  const handleUpdateUser = async (payload) => {
    if (!payload?.id) return;
    try {
      setActionError('');
      const res = await updateAdminUser(payload.id, payload);
      if (!res?.success) throw new Error(res?.message || 'Mise à jour échouée');
      setUsers((prev) => prev.map((u) => (u.id === payload.id ? res.data : u)));
      setEditingUser(null);
    } catch (err) {
      setActionError(err?.message || 'Mise à jour échouée');
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!userId) return;
    try {
      setActionError('');
      const res = await deleteAdminUser(userId);
      if (!res?.success) throw new Error(res?.message || 'Suppression échouée');
      setUsers((prev) => prev.filter((u) => u.id !== userId));
      if (selectedUser?.id === userId) setSelectedUser(null);
      if (confirmDeleteUser?.id === userId) setConfirmDeleteUser(null);
    } catch (err) {
      setActionError(err?.message || 'Suppression échouée');
    }
  };

  const handleCreateStoreCat = async (e) => {
    e.preventDefault();
    try {
      await createStoreCategory(newStoreCat);
      setShowAddStoreCat(false);
      setNewStoreCat({ name: '', description: '', icon: '', is_active: true });
      loadData(false);
    } catch (err) {
      setActionError(err?.message || 'Erreur création catégorie');
    }
  };

  const handleUpdateStoreCat = async (e) => {
    e.preventDefault();
    if (!editingStoreCat) return;
    try {
      await updateStoreCategory(editingStoreCat.id, editingStoreCat);
      setEditingStoreCat(null);
      loadData(false);
    } catch (err) {
      setActionError(err?.message || 'Erreur mise à jour catégorie');
    }
  };

  const handleDeleteStoreCat = async (id) => {
    if (!window.confirm('Supprimer cette catégorie ?')) return;
    try {
      await deleteStoreCategory(id);
      loadData(false);
    } catch (err) {
      setActionError(err?.message || 'Erreur suppression catégorie');
    }
  };

  const handleCreateStore = async (e) => {
    e.preventDefault();
    try {
      const res = await createStoreAdmin(newStore);
      if (res?.success) {
        setShowAddStore(false);
        setNewStore({ name: '', description: '', category_id: '', manager_id: '', phone: '', email: '', address: '', city: 'Libreville', zone: '', commission_rate: 0, delivery_fee: 0, subscription_plan: 'starter', is_active: true });
        loadStoresData();
        loadData(false);
      }
    } catch (err) {
      setActionError(err?.message || 'Erreur création magasin');
    }
  };

  const handleUpdateStore = async (e) => {
    e.preventDefault();
    if (!editingStore?.id) return;
    try {
      const res = await updateStoreAdmin(editingStore.id, editingStore);
      if (res?.success) {
        setEditingStore(null);
        loadStoresData();
        loadData(false);
      }
    } catch (err) {
      setActionError(err?.message || 'Erreur mise à jour magasin');
    }
  };

  const handleDeleteStore = async (id, hardDelete = false) => {
    const msg = hardDelete 
      ? 'Supprimer définitivement ce magasin ?' 
      : 'Archiver ce magasin ?';
    if (!window.confirm(msg)) return;
    try {
      const res = await deleteStoreAdmin(id, hardDelete);
      if (res?.success) {
        loadStoresData();
        loadData(false);
      }
    } catch (err) {
      setActionError(err?.message || 'Erreur suppression magasin');
    }
  };

  // Orders functions
  const loadOrdersData = useCallback(async () => {
    try {
      const [stats, list, byStore, agents] = await Promise.all([
        getOrderStats(),
        getOrdersList(ordersFilter),
        getOrdersByStore(),
        getDeliveryAgentStats(),
      ]);
      
      if (stats?.success) setOrderStats(stats.data);
      if (list?.success) setOrdersList(list.data);
      if (byStore?.success) setOrdersByStore(byStore.data);
      if (agents?.success) setDeliveryAgents(agents.data);
    } catch (err) {
      setActionError(err?.message || 'Erreur chargement commandes');
    }
  }, [ordersFilter]);

  const viewOrderDetail = async (orderId) => {
    try {
      const res = await getOrderDetail(orderId);
      if (res?.success) {
        setSelectedOrder(res.data);
      }
    } catch (err) {
      setActionError(err?.message || 'Erreur chargement détails');
    }
  };

  const handleAssignDelivery = async () => {
    if (!assigningOrder) return;
    if (!autoAssign && !selectedDeliveryAgent) {
      alert('Sélectionnez un livreur ou activez l\'attribution automatique');
      return;
    }
    try {
      const res = await assignDelivery(assigningOrder, {
        auto_assign: autoAssign,
        delivery_agent_id: autoAssign ? null : parseInt(selectedDeliveryAgent),
      });
      if (res?.success) {
        setShowAssignDelivery(false);
        setAssigningOrder(null);
        setAutoAssign(false);
        setSelectedDeliveryAgent('');
        await loadOrdersData();
        // Rafraîchir aussi les détails si le modal est ouvert
        if (selectedOrder?.id === assigningOrder) {
          const detail = await getOrderDetail(assigningOrder);
          if (detail?.success) setSelectedOrder(detail.data);
        }
      } else {
        alert(res?.error || 'Erreur lors de l\'attribution');
      }
    } catch (err) {
      alert(err?.message || 'Erreur attribution');
    }
  };

  const handleOrderStatusChange = async (orderId, status) => {
    try {
      const res = await updateOrderStatus(orderId, status);
      if (res?.success) {
        await loadOrdersData();
        if (selectedOrder?.id === orderId) {
          const detail = await getOrderDetail(orderId);
          if (detail?.success) setSelectedOrder(detail.data);
        }
      } else {
        alert(res?.error || 'Impossible de mettre à jour le statut');
      }
    } catch (err) {
      alert(err?.message || 'Erreur mise à jour statut');
    }
  };

  const handleCancelOrder = async (orderId) => {
    const reason = window.prompt('Motif d\'annulation (optionnel) :', '');
    if (reason === null) return;
    try {
      const res = await cancelOrder(orderId, reason || '');
      if (res?.success) {
        await loadOrdersData();
        if (selectedOrder?.id === orderId) setSelectedOrder(null);
      } else {
        alert(res?.error || 'Impossible d\'annuler la commande');
      }
    } catch (err) {
      alert(err?.message || 'Erreur annulation');
    }
  };

  const handleUpdateSettings = async (e) => {
    e.preventDefault();
    try {
      const res = await updateSystemSettings(settingsForm);
      if (res?.success) {
        setSystemSettings(res.data);
        setEditingSettings(false);
        alert('Paramètres mis à jour avec succès!');
      }
    } catch (err) {
      setActionError(err?.message || 'Erreur mise à jour paramètres');
    }
  };

  // Stores functions
  const loadStoresData = useCallback(async () => {
    try {
      console.log('Loading stores with filter:', storesFilter);
      const res = await getStoresListAdmin(storesFilter);
      console.log('Stores response:', res);
      if (res?.success) {
        setStoresListAdmin(res.data || []);
      } else {
        setStoresListAdmin([]);
      }
    } catch (err) {
      console.error('Error loading stores:', err);
      setActionError(err?.message || 'Erreur chargement magasins');
      setStoresListAdmin([]);
    }
  }, [storesFilter]);

  const viewStoreDetail = async (storeId) => {
    try {
      setB2bLoading(prev => ({ ...prev, [storeId]: true }));
      const res = await getStoreDetailAdmin(storeId);
      if (res?.success) {
        // Charger aussi le profil B2B si disponible
        let b2bProfile = null;
        try {
          const b2bRes = await getStoreB2BProfile(storeId);
          if (b2bRes?.success) {
            b2bProfile = b2bRes.data;
          }
        } catch (b2bErr) {
          // Pas de profil B2B, c'est normal
          console.log('Pas de profil B2B pour ce magasin');
        }
        
        setSelectedStoreDetail({ ...res.data, b2b_profile: b2bProfile });
        setShowStoreDetailModal(true);
      }
    } catch (err) {
      setActionError(err?.message || 'Erreur chargement magasin');
    } finally {
      setB2bLoading(prev => ({ ...prev, [storeId]: false }));
    }
  };

  const handleDeactivateStore = async (storeId) => {
    setShowConfirmModal({
      isOpen: true,
      message: 'Désactiver ce magasin ? Les produits deviendront invisibles.',
      onConfirm: async () => {
        try {
          const res = await deactivateStoreAdmin(storeId);
          if (res?.success) {
            setActionSuccess('Magasin désactivé avec succès');
            loadStoresData();
          }
        } catch (err) {
          setActionError(err?.message || 'Erreur désactivation magasin');
        } finally {
          setShowConfirmModal({ isOpen: false, message: '', onConfirm: null });
        }
      }
    });
  };

  const handleActivateStore = async (storeId) => {
    try {
      const res = await activateStoreAdmin(storeId);
      if (res?.success) {
        setActionSuccess('Magasin activé avec succès');
        loadStoresData();
      }
    } catch (err) {
      setActionError(err?.message || 'Erreur activation magasin');
    }
  };

  const handleActivateB2B = async (storeId) => {
    try {
      setB2bLoading(prev => ({ ...prev, [`b2b_${storeId}`]: true }));
      const res = await activateStoreB2B(storeId);
      if (res?.success) {
        setActionSuccess('Profil B2B activé avec succès');
        loadStoresData();
        if (selectedStoreDetail?.id === storeId) {
          // Rafraîchir les détails si le modal est ouvert
          viewStoreDetail(storeId);
        }
      }
    } catch (err) {
      setActionError(err?.response?.data?.error?.message || err?.message || 'Erreur activation B2B');
    } finally {
      setB2bLoading(prev => ({ ...prev, [`b2b_${storeId}`]: false }));
    }
  };

  const handleDeactivateB2B = async (storeId) => {
    setShowConfirmModal({
      isOpen: true,
      message: 'Désactiver le profil B2B de ce magasin ? Il ne sera plus visible dans l\'approvisionnement.',
      onConfirm: async () => {
        try {
          setB2bLoading(prev => ({ ...prev, [`b2b_${storeId}`]: true }));
          const res = await deactivateStoreB2B(storeId);
          if (res?.success) {
            setActionSuccess('Profil B2B désactivé avec succès');
            loadStoresData();
            if (selectedStoreDetail?.id === storeId) {
              viewStoreDetail(storeId);
            }
          }
        } catch (err) {
          setActionError(err?.response?.data?.error?.message || err?.message || 'Erreur désactivation B2B');
        } finally {
          setB2bLoading(prev => ({ ...prev, [`b2b_${storeId}`]: false }));
          setShowConfirmModal({ isOpen: false, message: '', onConfirm: null });
        }
      }
    });
  };

  const handleCreateB2BProfile = async (storeId, data = {}) => {
    try {
      setB2bLoading(prev => ({ ...prev, [`b2b_create_${storeId}`]: true }));
      const res = await createStoreB2BProfile(storeId, data);
      if (res?.success) {
        setActionSuccess('Profil B2B créé avec succès');
        loadStoresData();
        if (selectedStoreDetail?.id === storeId) {
          viewStoreDetail(storeId);
        }
      }
    } catch (err) {
      setActionError(err?.response?.data?.error?.message || err?.message || 'Erreur création profil B2B');
    } finally {
      setB2bLoading(prev => ({ ...prev, [`b2b_create_${storeId}`]: false }));
    }
  };

  // Products Data Loading and Handlers
  const loadProductsData = useCallback(async () => {
    try {
      console.log('Loading products with filter:', productsFilter);
      const [statsRes, productsRes] = await Promise.all([
        getProductStats(),
        getProductsListAdmin(productsFilter)
      ]);
      
      console.log('Products response:', productsRes);
      
      if (statsRes?.success) {
        setProductStats(statsRes.data);
      }
      
      if (productsRes?.success) {
        setProductsListAdmin(productsRes.data || []);
      } else {
        setProductsListAdmin([]);
      }
    } catch (err) {
      console.error('Error loading products:', err);
      setActionError(err?.message || 'Erreur chargement produits');
      setProductsListAdmin([]);
    }
  }, [productsFilter]);

  const viewProductDetail = async (productId) => {
    try {
      const res = await getProductDetailAdmin(productId);
      if (res?.success) {
        setViewingProduct(res.data);
      }
    } catch (err) {
      setActionError(err?.message || 'Erreur chargement produit');
    }
  };

  const handleActivateProduct = async (productId) => {
    try {
      const res = await activateProductAdmin(productId);
      if (res?.success) {
        loadProductsData();
      }
    } catch (err) {
      setActionError(err?.message || 'Erreur activation produit');
    }
  };

  const handleDeactivateProduct = async (productId) => {
    if (!window.confirm('Désactiver ce produit ? Il ne sera plus visible sur le site.')) return;
    try {
      const res = await deactivateProductAdmin(productId);
      if (res?.success) {
        loadProductsData();
      }
    } catch (err) {
      setActionError(err?.message || 'Erreur désactivation produit');
    }
  };

  const handleDeleteProduct = async (productId, hardDelete = false) => {
    const msg = hardDelete 
      ? 'Supprimer définitivement ce produit ?' 
      : 'Archiver ce produit (soft delete) ?';
    if (!window.confirm(msg)) return;
    try {
      const res = await deleteProductAdmin(productId, hardDelete);
      if (res?.success) {
        loadProductsData();
      }
    } catch (err) {
      setActionError(err?.message || 'Erreur suppression produit');
    }
  };

  const handleBulkActions = async (action, productIds, stockValue = null) => {
    if (!window.confirm(`Confirmer l'action "${action}" sur ${productIds.length} produits ?`)) return;
    try {
      const res = await bulkActionsProductsAdmin(action, productIds, stockValue);
      if (res?.success) {
        loadProductsData();
        alert(res.message || 'Action exécutée avec succès');
      }
    } catch (err) {
      setActionError(err?.message || 'Erreur action en masse');
    }
  };

  const handleCreateProduct = async (e) => {
    e.preventDefault();
    try {
      const res = await createProductAdmin(newProduct);  // Using adminService.createProductAdmin
      if (res?.success) {
        setShowAddProduct(false);
        setNewProduct({ name: '', description: '', price: 0, promo_price: null, stock: 0, is_available: true, store_id: '', category_id: '', sku: '' });
        loadProductsData();
        loadData(false);
      }
    } catch (err) {
      setActionError(err?.message || 'Erreur création produit');
    }
  };

  const handleUpdateProduct = async (e) => {
    e.preventDefault();
    if (!editingProduct?.id) return;
    try {
      const res = await updateProductAdmin(editingProduct.id, editingProduct);  // Using adminService.updateProductAdmin
      if (res?.success) {
        setEditingProduct(null);
        loadProductsData();
        loadData(false);
      }
    } catch (err) {
      setActionError(err?.message || 'Erreur mise à jour produit');
    }
  };

  // Load stores data when tab changes to stores
  useEffect(() => {
    if (activeTab === 'stores') {
      loadStoresData();
    }
  }, [activeTab, loadStoresData, storesFilter]);

  // Load orders data when tab changes to orders
  useEffect(() => {
    if (activeTab === 'orders') {
      loadOrdersData();
    }
  }, [activeTab, loadOrdersData, ordersFilter]);

  // Load products data when tab changes to products
  useEffect(() => {
    if (activeTab === 'products') {
      loadProductsData();
    }
  }, [activeTab, loadProductsData, productsFilter]);

  const overviewSection = (
    <AdminOverviewSection summary={summary} loading={loading} />
  );

  const usersSection = (
    <div className="space-y-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="Total utilisateurs" value={(summary?.users?.clients || 0) + (summary?.users?.store_managers || 0) + (summary?.users?.delivery_agents || 0)} />
        <StatCard title="Clients" value={summary?.users?.clients || 0} />
        <StatCard title="Gérants" value={summary?.users?.store_managers || 0} />
        <StatCard title="Livreurs" value={summary?.users?.delivery_agents || 0} />
      </div>
      <div className="bg-white shadow-sm rounded-lg p-4 border border-gray-100">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
          <div>
            <h2 className="text-lg font-semibold">Liste utilisateurs</h2>
            <span className="text-xs text-gray-500">{users.length} profils</span>
          </div>
          <div className="flex flex-wrap gap-2 items-center">
            {[
              { id: 'all', label: 'Tous' },
              { id: 'client', label: 'Clients' },
              { id: 'store_manager', label: 'Gérants' },
              { id: 'delivery_agent', label: 'Livreurs' },
            ].map((opt) => (
              <button
                key={opt.id}
                onClick={() => setUserFilter(opt.id)}
                className={`px-3 py-1.5 text-sm rounded-full border ${
                  userFilter === opt.id
                    ? 'bg-gray-900 text-white border-gray-900'
                    : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'
                }`}
              >
                {opt.label}
              </button>
            ))}
            <button
              onClick={() => setShowAddUser(true)}
              className="px-3 py-1.5 text-sm font-semibold rounded-full border border-indigo-200 bg-indigo-50 text-indigo-700 hover:bg-indigo-100"
            >
              + Ajouter
            </button>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {users
            .filter((u) => userFilter === 'all' || u.user_type === userFilter)
            .map((u) => (
              <div key={u.id} className="border border-gray-100 rounded-md p-3 bg-gray-50">
                <p className="font-semibold text-gray-900">{u.phone}</p>
                <p className="text-xs text-gray-500 mb-1">{u.user_type}</p>
                <p className="text-xs text-gray-500">{[u.first_name, u.last_name].filter(Boolean).join(' ')}</p>
                <p className="text-xs text-gray-500">{u.email}</p>
                <p className="text-xs text-gray-500">{u.city}</p>
                <p className="text-xs text-gray-500">Créé le {new Date(u.created_at).toLocaleDateString()}</p>
                <div className="mt-3 flex gap-2">
                  <button
                    type="button"
                    onClick={() => setSelectedUser(u)}
                    className="inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded border border-gray-200 bg-white hover:bg-gray-100"
                    title="Voir"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                    Voir
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditingUser(u)}
                    className="inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded border border-gray-200 bg-white hover:bg-gray-100"
                    title="Modifier"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L7.5 19.5 3 21l1.5-4.5 12.232-12.232z" />
                    </svg>
                    Modifier
                  </button>
                  <button
                    type="button"
                    onClick={() => setConfirmDeleteUser(u)}
                    className="inline-flex items-center gap-1 px-2 py-1 text-xs font-semibold rounded border border-red-200 bg-red-50 text-red-700 hover:bg-red-100"
                    title="Supprimer"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M9 7V4a1 1 0 011-1h4a1 1 0 011 1v3m-9 0h10" />
                    </svg>
                    Supprimer
                  </button>
                </div>
              </div>
            ))}
        </div>
      </div>
    </div>
  );

  const ordersSection = (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
        <StatCard 
          title="📦 Total" 
          value={orderStats?.today?.total_orders || 0}
          hint="Aujourd'hui"
        />
        <StatCard 
          title="💳 En Attente" 
          value={orderStats?.today?.pending_payment || 0}
          hint="Paiement"
        />
        <StatCard 
          title="✅ Confirmées" 
          value={orderStats?.today?.confirmed || 0}
          hint="Prêtes"
        />
        <StatCard 
          title="👨‍🍳 En Préparation" 
          value={orderStats?.today?.in_preparation || 0}
          hint="Cuisine"
        />
        <StatCard 
          title="🚚 En Livraison" 
          value={orderStats?.today?.in_delivery || 0}
          hint="Route"
        />
        <StatCard 
          title="✔️ Livrées" 
          value={orderStats?.today?.delivered || 0}
          hint="Complétées"
        />
        <StatCard 
          title="❌ Annulées" 
          value={orderStats?.today?.cancelled || 0}
          hint="Échouées"
        />
        <StatCard 
          title="💰 Revenus" 
          value={`${(orderStats?.today?.total_revenue || 0).toLocaleString('fr-FR')} FCFA`}
          hint="Dont frais livraison"
        />
      </div>

      {/* Filtres & Actions */}
      <div className="bg-white shadow-sm rounded-lg p-4 border border-gray-100">
        <h3 className="font-semibold mb-3 text-sm">Filtres & Recherche</h3>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
          <select 
            value={ordersFilter.status}
            onChange={(e) => setOrdersFilter({ ...ordersFilter, status: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded text-sm"
          >
            <option value="all">Tous les statuts</option>
            <option value="pending">En attente</option>
            <option value="confirmed">Confirmée</option>
            <option value="preparing">Préparation</option>
            <option value="assigned">Assignée</option>
            <option value="in_delivery">En livraison</option>
            <option value="delivered">Livrée</option>
            <option value="cancelled">Annulée</option>
          </select>

          <select 
            value={ordersFilter.date_range}
            onChange={(e) => setOrdersFilter({ ...ordersFilter, date_range: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded text-sm"
          >
            <option value="all">Toutes les dates</option>
            <option value="today">Aujourd'hui</option>
            <option value="week">Dernière semaine</option>
            <option value="month">Ce mois</option>
          </select>

          <select 
            value={ordersFilter.store_id}
            onChange={(e) => setOrdersFilter({ ...ordersFilter, store_id: e.target.value })}
            className="px-3 py-2 border border-gray-300 rounded text-sm"
          >
            <option value="">Tous les magasins</option>
            {stores.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>

          <button 
            onClick={() => loadOrdersData()}
            className="px-3 py-2 bg-blue-500 text-white rounded text-sm hover:bg-blue-600 font-medium"
          >
            Appliquer filtres
          </button>

          <button 
            onClick={() => {
              setOrdersFilter({ status: 'all', city: '', store_id: '', date_range: 'all' });
            }}
            className="px-3 py-2 bg-gray-300 text-gray-700 rounded text-sm hover:bg-gray-400 font-medium"
          >
            Réinitialiser
          </button>
        </div>
      </div>

      {/* Liste des commandes avec aperçu complet */}
      <div className="bg-white shadow-sm rounded-lg p-6 border border-gray-100">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold">Commandes ({ordersList.length})</h2>
          <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">Affichage: {Math.min(ordersList.length, 50)} / {ordersList.length}</span>
        </div>
        
        {ordersList.length === 0 ? (
          <div className="text-center py-12">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
            </svg>
            <p className="mt-2 text-gray-500">Aucune commande trouvée</p>
          </div>
        ) : (
          <div className="space-y-3">
            {ordersList.slice(0, 50).map((o) => (
              <div key={o.id} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between gap-4">
                  {/* Infos principales */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="text-lg font-semibold text-gray-900">
                        Commande #{o.order_number}
                      </h3>
                      <span className={`inline-flex px-2 py-1 rounded text-xs font-medium ${
                        o.status === 'pending' ? 'bg-yellow-50 text-yellow-700' :
                        o.status === 'confirmed' ? 'bg-blue-50 text-blue-700' :
                        o.status === 'preparing' ? 'bg-orange-50 text-orange-700' :
                        o.status === 'assigned' ? 'bg-indigo-50 text-indigo-700' :
                        o.status === 'in_delivery' ? 'bg-purple-50 text-purple-700' :
                        o.status === 'delivered' ? 'bg-green-50 text-green-700' :
                        'bg-red-50 text-red-700'
                      }`}>
                        {o.status}
                      </span>
                      <span className="text-xs px-2 py-1 rounded bg-gray-100 text-gray-700">{o.payment_status}</span>
                    </div>
                    
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm mb-3">
                      <div>
                        <p className="text-gray-500 text-xs">Client</p>
                        <p className="font-semibold text-gray-900">{o.client_name}</p>
                      </div>
                      <div>
                        <p className="text-gray-500 text-xs">Magasin</p>
                        <p className="font-semibold text-gray-900">{o.store_name}</p>
                      </div>
                      <div>
                        <p className="text-gray-500 text-xs">Montant</p>
                        <p className="font-semibold text-gray-900">{(o.total_amount || 0).toLocaleString('fr-FR')} FCFA</p>
                      </div>
                      <div>
                        <p className="text-gray-500 text-xs">Livreur</p>
                        <p className="font-semibold text-gray-900">{o.delivery_agent || '—'}</p>
                      </div>
                    </div>

                    <p className="text-xs text-gray-600">
                      📍 {o.delivery_address || 'Adresse non spécifiée'}
                    </p>
                  </div>

                  {/* Actions */}
                  <div className="flex flex-col gap-2">
                    <button 
                      onClick={() => viewOrderDetail(o.id)}
                      className="px-3 py-2 bg-blue-50 text-blue-600 rounded text-sm hover:bg-blue-100 font-medium whitespace-nowrap"
                    >
                      👁️ Détails
                    </button>

                    {o.status === 'pending' && (
                      <>
                        <button
                          onClick={() => handleOrderStatusChange(o.id, 'confirmed')}
                          className="px-3 py-2 bg-emerald-50 text-emerald-600 rounded text-sm hover:bg-emerald-100 font-medium whitespace-nowrap"
                        >
                          ✅ Confirmer
                        </button>
                        <button
                          onClick={() => handleCancelOrder(o.id)}
                          className="px-3 py-2 bg-red-50 text-red-600 rounded text-sm hover:bg-red-100 font-medium whitespace-nowrap"
                        >
                          ❌ Annuler
                        </button>
                      </>
                    )}

                    {o.status === 'confirmed' && (
                      <>
                        <button
                          onClick={() => handleOrderStatusChange(o.id, 'preparing')}
                          className="px-3 py-2 bg-orange-50 text-orange-600 rounded text-sm hover:bg-orange-100 font-medium whitespace-nowrap"
                        >
                          👨‍🍳 Préparation
                        </button>
                        <button 
                          onClick={() => {
                            setAssigningOrder(o.id);
                            setShowAssignDelivery(true);
                          }}
                          className="px-3 py-2 bg-purple-50 text-purple-600 rounded text-sm hover:bg-purple-100 font-medium whitespace-nowrap"
                        >
                          🚚 Assigner
                        </button>
                        <button
                          onClick={() => handleCancelOrder(o.id)}
                          className="px-3 py-2 bg-red-50 text-red-600 rounded text-sm hover:bg-red-100 font-medium whitespace-nowrap"
                        >
                          ❌ Annuler
                        </button>
                      </>
                    )}

                    {o.status === 'preparing' && (
                      <>
                        <button 
                          onClick={() => {
                            setAssigningOrder(o.id);
                            setShowAssignDelivery(true);
                          }}
                          className="px-3 py-2 bg-purple-50 text-purple-600 rounded text-sm hover:bg-purple-100 font-medium whitespace-nowrap"
                        >
                          🚚 Assigner
                        </button>
                        <button
                          onClick={() => handleCancelOrder(o.id)}
                          className="px-3 py-2 bg-red-50 text-red-600 rounded text-sm hover:bg-red-100 font-medium whitespace-nowrap"
                        >
                          ❌ Annuler
                        </button>
                      </>
                    )}

                    {o.status === 'assigned' && (
                      <>
                        <button
                          onClick={() => handleOrderStatusChange(o.id, 'in_delivery')}
                          className="px-3 py-2 bg-indigo-50 text-indigo-600 rounded text-sm hover:bg-indigo-100 font-medium whitespace-nowrap"
                        >
                          🚗 En livraison
                        </button>
                        <button
                          onClick={() => handleCancelOrder(o.id)}
                          className="px-3 py-2 bg-red-50 text-red-600 rounded text-sm hover:bg-red-100 font-medium whitespace-nowrap"
                        >
                          ❌ Annuler
                        </button>
                      </>
                    )}

                    {o.status === 'in_delivery' && (
                      <>
                        <button
                          onClick={() => handleOrderStatusChange(o.id, 'delivered')}
                          className="px-3 py-2 bg-green-50 text-green-600 rounded text-sm hover:bg-green-100 font-medium whitespace-nowrap"
                        >
                          🎯 Livrée
                        </button>
                        <button
                          onClick={() => handleCancelOrder(o.id)}
                          className="px-3 py-2 bg-red-50 text-red-600 rounded text-sm hover:bg-red-100 font-medium whitespace-nowrap"
                        >
                          ❌ Annuler
                        </button>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Tableau par Magasin */}
      <div className="bg-white shadow-sm rounded-lg p-4 border border-gray-100">
        <h2 className="text-lg font-semibold mb-3">📊 Commandes par Magasin</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b bg-gray-50">
                <th className="py-3 px-3 font-semibold">Magasin</th>
                <th className="py-3 px-3 font-semibold">⏳ En attente</th>
                <th className="py-3 px-3 font-semibold">👨‍🍳 Préparation</th>
                <th className="py-3 px-3 font-semibold">🚚 Assignée</th>
                <th className="py-3 px-3 font-semibold">📦 En cours</th>
                <th className="py-3 px-3 font-semibold">✅ Jour</th>
                <th className="py-3 px-3 font-semibold">📈 Mois</th>
              </tr>
            </thead>
            <tbody>
              {ordersByStore.length > 0 ? ordersByStore.map((s) => (
                <tr key={s.store_id} className="border-b hover:bg-gray-50">
                  <td className="py-3 px-3 font-semibold text-gray-900">{s.store_name}</td>
                  <td className="py-3 px-3"><span className="inline-flex items-center justify-center h-6 w-6 rounded-full bg-yellow-100 text-yellow-700 text-xs font-semibold">{s.pending || 0}</span></td>
                  <td className="py-3 px-3"><span className="inline-flex items-center justify-center h-6 w-6 rounded-full bg-orange-100 text-orange-700 text-xs font-semibold">{s.preparing || 0}</span></td>
                  <td className="py-3 px-3"><span className="inline-flex items-center justify-center h-6 w-6 rounded-full bg-indigo-100 text-indigo-700 text-xs font-semibold">{s.assigned || 0}</span></td>
                  <td className="py-3 px-3"><span className="inline-flex items-center justify-center h-6 w-6 rounded-full bg-purple-100 text-purple-700 text-xs font-semibold">{s.in_delivery || 0}</span></td>
                  <td className="py-3 px-3 font-bold text-blue-600">{s.total_today || 0}</td>
                  <td className="py-3 px-3 font-bold text-gray-700">{s.total_month || 0}</td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="7" className="py-4 px-3 text-center text-gray-500">Aucune donnée</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Tableau Livreurs Actifs */}
      <div className="bg-white shadow-sm rounded-lg p-4 border border-gray-100">
        <h2 className="text-lg font-semibold mb-3">🚚 Livreurs Actifs</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-gray-500 border-b bg-gray-50">
                <th className="py-3 px-3 font-semibold">Livreur</th>
                <th className="py-3 px-3 font-semibold">👤 Nom</th>
                <th className="py-3 px-3 font-semibold">📍 Assignées</th>
                <th className="py-3 px-3 font-semibold">🚗 En transit</th>
                <th className="py-3 px-3 font-semibold">✅ Livrées</th>
                <th className="py-3 px-3 font-semibold">❌ Annulées</th>
                <th className="py-3 px-3 font-semibold">📊 Total</th>
              </tr>
            </thead>
            <tbody>
              {deliveryAgents.length > 0 ? deliveryAgents.map((a) => (
                <tr key={a.id || a.agent_id} className="border-b hover:bg-gray-50">
                  <td className="py-3 px-3 font-semibold text-gray-900">{a.name || a.agent_name || '?'}</td>
                  <td className="py-3 px-3 text-gray-700">{a.email || a.phone || '—'}</td>
                  <td className="py-3 px-3"><span className="inline-flex items-center justify-center h-6 w-6 rounded-full bg-indigo-100 text-indigo-700 text-xs font-semibold">{a.assigned || a.active_orders || 0}</span></td>
                  <td className="py-3 px-3"><span className="inline-flex items-center justify-center h-6 w-6 rounded-full bg-purple-100 text-purple-700 text-xs font-semibold">{a.in_transit || 0}</span></td>
                  <td className="py-3 px-3"><span className="inline-flex items-center justify-center h-6 w-6 rounded-full bg-green-100 text-green-700 text-xs font-semibold">{a.delivered || 0}</span></td>
                  <td className="py-3 px-3"><span className="inline-flex items-center justify-center h-6 w-6 rounded-full bg-red-100 text-red-700 text-xs font-semibold">{a.cancelled || 0}</span></td>
                  <td className="py-3 px-3 font-bold text-gray-700">{a.total_today || 0}</td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="7" className="py-4 px-3 text-center text-gray-500">Aucun livreur</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal Détails Commande */}
      {selectedOrder && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full shadow-xl">
            <div className="sticky top-0 bg-white border-b p-6 flex justify-between items-start">
              <div>
                <h2 className="text-2xl font-bold text-gray-900">Commande #{selectedOrder.order_number}</h2>
                <p className="text-sm text-gray-500 mt-1">ID: {selectedOrder.id}</p>
              </div>
              <button 
                onClick={() => setSelectedOrder(null)} 
                className="text-gray-400 hover:text-gray-600 text-2xl font-light"
              >
                ×
              </button>
            </div>

            <div className="p-6 space-y-6 max-h-[calc(100vh-200px)] overflow-y-auto">
              {/* Status Badges */}
              <div className="flex gap-2 flex-wrap">
                <span className={`inline-flex px-3 py-1 rounded text-sm font-semibold ${
                  selectedOrder.status === 'pending' ? 'bg-yellow-50 text-yellow-700' :
                  selectedOrder.status === 'confirmed' ? 'bg-blue-50 text-blue-700' :
                  selectedOrder.status === 'preparing' ? 'bg-orange-50 text-orange-700' :
                  selectedOrder.status === 'assigned' ? 'bg-indigo-50 text-indigo-700' :
                  selectedOrder.status === 'in_delivery' ? 'bg-purple-50 text-purple-700' :
                  selectedOrder.status === 'delivered' ? 'bg-green-50 text-green-700' :
                  'bg-red-50 text-red-700'
                }`}>
                  {selectedOrder.status}
                </span>
                <span className="inline-flex px-3 py-1 rounded text-sm font-semibold bg-gray-100 text-gray-700">
                  {selectedOrder.payment_status}
                </span>
              </div>

              {/* Customer & Store */}
              <div className="grid grid-cols-2 gap-4">
                <div className="border-l-4 border-blue-500 pl-4">
                  <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">👤 Client</p>
                  <p className="font-bold text-gray-900">{selectedOrder.client?.name}</p>
                  <p className="text-sm text-gray-600">{selectedOrder.client?.phone}</p>
                  <p className="text-sm text-gray-600">{selectedOrder.client?.email}</p>
                </div>
                <div className="border-l-4 border-green-500 pl-4">
                  <p className="text-xs text-gray-500 uppercase tracking-wide mb-1">🏪 Magasin</p>
                  <p className="font-bold text-gray-900">{selectedOrder.store?.name}</p>
                  <p className="text-sm text-gray-600">{selectedOrder.store?.manager}</p>
                  <p className="text-sm text-gray-600">{selectedOrder.store?.phone}</p>
                </div>
              </div>

              {/* Delivery Address */}
              <div className="bg-blue-50 rounded-lg p-4 border-l-4 border-blue-500">
                <p className="text-xs text-gray-600 uppercase tracking-wide font-semibold mb-2">📍 Adresse de Livraison</p>
                <p className="font-semibold text-gray-900">{selectedOrder.delivery_address?.address}</p>
                <p className="text-sm text-gray-700">{selectedOrder.delivery_address?.city}, {selectedOrder.delivery_address?.district}</p>
              </div>

              {/* Products */}
              <div>
                <h3 className="text-sm font-bold text-gray-900 mb-3 uppercase tracking-wide">📦 Produits Commandés</h3>
                <div className="space-y-2 bg-gray-50 rounded-lg p-4">
                  {selectedOrder.items && selectedOrder.items.length > 0 ? selectedOrder.items.map((item, idx) => (
                    <div key={idx} className="flex justify-between text-sm py-2 border-b last:border-0">
                      <div className="flex-1">
                        <p className="font-semibold text-gray-900">{item.product_name}</p>
                        <p className="text-xs text-gray-600">Quantité: {item.quantity} × {(item.price || 0).toLocaleString('fr-FR')} FCFA</p>
                      </div>
                      <p className="font-bold text-gray-900 text-right">{(item.total || 0).toLocaleString('fr-FR')} FCFA</p>
                    </div>
                  )) : (
                    <p className="text-gray-500 text-sm">Aucun produit</p>
                  )}
                </div>
              </div>

              {/* Totals */}
              <div className="bg-green-50 rounded-lg p-4 border-l-4 border-green-500 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-700">Sous-total:</span>
                  <span className="font-semibold text-gray-900">{(selectedOrder.totals?.subtotal || 0).toLocaleString('fr-FR')} FCFA</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-700">Frais livraison:</span>
                  <span className="font-semibold text-gray-900">{(selectedOrder.totals?.delivery_fee || 0).toLocaleString('fr-FR')} FCFA</span>
                </div>
                <div className="flex justify-between text-lg border-t pt-2 mt-2">
                  <span className="font-bold text-gray-900">Total:</span>
                  <span className="font-bold text-green-600 text-xl">{(selectedOrder.totals?.total || 0).toLocaleString('fr-FR')} FCFA</span>
                </div>
              </div>

              {/* Delivery Info */}
              {selectedOrder.delivery_agent && (
                <div className="bg-purple-50 rounded-lg p-4 border-l-4 border-purple-500">
                  <p className="text-xs text-gray-600 uppercase tracking-wide font-semibold mb-2">🚚 Livreur Assigné</p>
                  <p className="font-semibold text-gray-900">{selectedOrder.delivery_agent}</p>
                </div>
              )}

              {/* Actions */}
              <div className="flex flex-wrap gap-2 pt-4 border-t">
                {selectedOrder.status === 'pending' && (
                  <>
                    <button
                      onClick={() => handleOrderStatusChange(selectedOrder.id, 'confirmed')}
                      className="flex-1 px-4 py-2 bg-emerald-50 text-emerald-700 rounded-lg font-semibold hover:bg-emerald-100"
                    >
                      ✅ Confirmer
                    </button>
                    <button
                      onClick={() => handleCancelOrder(selectedOrder.id)}
                      className="flex-1 px-4 py-2 bg-red-50 text-red-700 rounded-lg font-semibold hover:bg-red-100"
                    >
                      ❌ Annuler
                    </button>
                  </>
                )}

                {selectedOrder.status === 'confirmed' && (
                  <>
                    <button
                      onClick={() => handleOrderStatusChange(selectedOrder.id, 'preparing')}
                      className="flex-1 px-4 py-2 bg-orange-50 text-orange-700 rounded-lg font-semibold hover:bg-orange-100"
                    >
                      👨‍🍳 Préparation
                    </button>
                    <button 
                      onClick={() => {
                        setAssigningOrder(selectedOrder.id);
                        setShowAssignDelivery(true);
                        setSelectedOrder(null);
                      }}
                      className="flex-1 px-4 py-2 bg-purple-50 text-purple-700 rounded-lg font-semibold hover:bg-purple-100"
                    >
                      🚚 Assigner Livreur
                    </button>
                    <button
                      onClick={() => handleCancelOrder(selectedOrder.id)}
                      className="flex-1 px-4 py-2 bg-red-50 text-red-700 rounded-lg font-semibold hover:bg-red-100"
                    >
                      ❌ Annuler
                    </button>
                  </>
                )}

                {selectedOrder.status === 'preparing' && (
                  <>
                    <button 
                      onClick={() => {
                        setAssigningOrder(selectedOrder.id);
                        setShowAssignDelivery(true);
                        setSelectedOrder(null);
                      }}
                      className="flex-1 px-4 py-2 bg-purple-50 text-purple-700 rounded-lg font-semibold hover:bg-purple-100"
                    >
                      🚚 Assigner Livreur
                    </button>
                    <button
                      onClick={() => handleCancelOrder(selectedOrder.id)}
                      className="flex-1 px-4 py-2 bg-red-50 text-red-700 rounded-lg font-semibold hover:bg-red-100"
                    >
                      ❌ Annuler
                    </button>
                  </>
                )}

                {selectedOrder.status === 'assigned' && (
                  <>
                    <button
                      onClick={() => handleOrderStatusChange(selectedOrder.id, 'in_delivery')}
                      className="flex-1 px-4 py-2 bg-indigo-50 text-indigo-700 rounded-lg font-semibold hover:bg-indigo-100"
                    >
                      🚗 En livraison
                    </button>
                    <button
                      onClick={() => handleCancelOrder(selectedOrder.id)}
                      className="flex-1 px-4 py-2 bg-red-50 text-red-700 rounded-lg font-semibold hover:bg-red-100"
                    >
                      ❌ Annuler
                    </button>
                  </>
                )}

                {selectedOrder.status === 'in_delivery' && (
                  <>
                    <button
                      onClick={() => handleOrderStatusChange(selectedOrder.id, 'delivered')}
                      className="flex-1 px-4 py-2 bg-green-50 text-green-700 rounded-lg font-semibold hover:bg-green-100"
                    >
                      🎯 Livrée
                    </button>
                    <button
                      onClick={() => handleCancelOrder(selectedOrder.id)}
                      className="flex-1 px-4 py-2 bg-red-50 text-red-700 rounded-lg font-semibold hover:bg-red-100"
                    >
                      ❌ Annuler
                    </button>
                  </>
                )}

                <button 
                  onClick={() => setSelectedOrder(null)}
                  className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-lg font-semibold hover:bg-gray-300"
                >
                  Fermer
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal Attribution Livreur */}
      {showAssignDelivery && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg w-full max-w-md shadow-xl">
            <div className="sticky top-0 bg-white border-b p-6">
              <div className="flex justify-between items-start">
                <div>
                  <h2 className="text-xl font-bold text-gray-900">🚚 Assigner Livreur</h2>
                  {assigningOrder && (
                    <p className="text-sm text-gray-500 mt-2">Commande #{ordersList.find(o => o.id === assigningOrder)?.order_number}</p>
                  )}
                </div>
                <button 
                  onClick={() => { 
                    setShowAssignDelivery(false); 
                    setAssigningOrder(null); 
                    setSelectedDeliveryAgent(''); 
                    setAutoAssign(false); 
                  }} 
                  className="text-gray-400 hover:text-gray-600 text-2xl font-light"
                >
                  ×
                </button>
              </div>
            </div>

            <div className="p-6 space-y-4">
              {/* Mode Selection */}
              <div className="space-y-3">
                <label className="flex items-center p-3 border-2 border-gray-200 rounded-lg cursor-pointer hover:bg-gray-50 transition" htmlFor="autoAssignCheck">
                  <input 
                    id="autoAssignCheck"
                    type="checkbox" 
                    checked={autoAssign}
                    onChange={(e) => {
                      setAutoAssign(e.target.checked);
                      if (e.target.checked) setSelectedDeliveryAgent('');
                    }}
                    className="w-5 h-5 text-blue-600 rounded cursor-pointer"
                  />
                  <span className="ml-3 font-semibold text-gray-700">🤖 Attribution automatique</span>
                </label>

                {autoAssign && (
                  <p className="text-sm text-blue-600 bg-blue-50 p-3 rounded">
                    ℹ️ Meilleur livreur disponible sera sélectionné automatiquement
                  </p>
                )}
              </div>

              {/* Manual Selection */}
              {!autoAssign && (
                <div>
                  <label className="block text-sm font-semibold text-gray-700 mb-3">
                    👤 Sélectionner manuellement:
                  </label>
                  <select 
                    value={selectedDeliveryAgent}
                    onChange={(e) => setSelectedDeliveryAgent(e.target.value)}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="">-- Choisissez un livreur --</option>
                    {deliveryAgents.map((a) => {
                      const agentId = a.id || a.agent_id;
                      const agentName = a.name || a.agent_name || 'Sans nom';
                      const activeOrders = (a.active_deliveries || a.total_today || 0);
                      const agentPhone = a.phone || a.contact || '';
                      
                      return (
                        <option key={agentId} value={agentId}>
                          {agentName} • {activeOrders} commande{activeOrders !== 1 ? 's' : ''} {agentPhone ? `• ${agentPhone}` : ''}
                        </option>
                      );
                    })}
                  </select>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-3 pt-4 border-t">
                <button 
                  onClick={() => { 
                    setShowAssignDelivery(false); 
                    setAssigningOrder(null); 
                    setSelectedDeliveryAgent(''); 
                    setAutoAssign(false); 
                  }}
                  className="flex-1 px-4 py-3 border border-gray-300 rounded-lg text-gray-700 font-semibold hover:bg-gray-50 transition"
                >
                  Annuler
                </button>
                <button 
                  onClick={() => handleAssignDelivery()}
                  disabled={!autoAssign && !selectedDeliveryAgent}
                  className="flex-1 px-4 py-3 bg-green-500 text-white rounded-lg font-semibold hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed transition"
                >
                  ✅ Assigner
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );

  const formatMoney = (amount) => {
    if (amount === undefined || amount === null) return 'N/A';
    return amount.toLocaleString('fr-FR');
  };

  const financesSection = (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard 
           title="📊 Revenus (Mois)" 
           value={`${formatMoney(financeDashboard?.month?.revenue)} FCFA`}
           hint={`${financeDashboard?.month?.orders_count ?? 0} commandes`}
        />
        <StatCard 
           title="💰 Commissions" 
           value={`${formatMoney(financeDashboard?.month?.commissions)} FCFA`}
           hint="Prélevées à la plateforme"
        />
        <StatCard 
           title="🚚 Paiements Livreurs" 
           value={`${formatMoney(financeDashboard?.month?.delivery_payouts)} FCFA`}
           hint="Coût total des livraisons"
        />
        <StatCard 
           title="📈 Bénéfice Réel" 
           value={`${formatMoney(financeDashboard?.month?.platform_profit)} FCFA`}
           hint="Après tous les coûts"
        />
      </div>

      {/* Secondary Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard 
           title="✅ Commandes Payées" 
           value={financeDashboard?.metrics?.paid_orders ?? 'N/A'}
           hint="Statut: success"
        />
        <StatCard 
           title="⏳ Paiements en Attente" 
           value={financeDashboard?.metrics?.pending_payments ?? 'N/A'}
           hint="À confirmer"
        />
        <StatCard 
           title="❌ Paiements Échoués" 
           value={financeDashboard?.metrics?.failed_payments ?? 'N/A'}
           hint="À vérifier"
        />
      </div>

      {/* Revenue Breakdown Pie Chart Data */}
      {revenueBreakdown && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">📊 Répartition des Revenus</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="border-l-4 border-blue-500 pl-4">
              <p className="text-sm text-gray-500">Commissions</p>
              <p className="text-2xl font-bold text-gray-900">{revenueBreakdown.commissions.percentage.toFixed(1)}%</p>
              <p className="text-xs text-gray-400">{revenueBreakdown.commissions.amount.toLocaleString('fr-FR')} FCFA</p>
            </div>
            <div className="border-l-4 border-green-500 pl-4">
              <p className="text-sm text-gray-500">Livraison</p>
              <p className="text-2xl font-bold text-gray-900">{revenueBreakdown.delivery.percentage.toFixed(1)}%</p>
              <p className="text-xs text-gray-400">{revenueBreakdown.delivery.amount.toLocaleString('fr-FR')} FCFA</p>
            </div>
            <div className="border-l-4 border-purple-500 pl-4">
              <p className="text-sm text-gray-500">Abonnements</p>
              <p className="text-2xl font-bold text-gray-900">{revenueBreakdown.subscriptions.percentage.toFixed(1)}%</p>
              <p className="text-xs text-gray-400">{revenueBreakdown.subscriptions.amount.toLocaleString('fr-FR')} FCFA</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
            <div className="border-l-4 border-orange-500 pl-4">
              <p className="text-sm text-gray-500">Sponsoring</p>
              <p className="text-2xl font-bold text-gray-900">{revenueBreakdown.sponsoring.percentage.toFixed(1)}%</p>
              <p className="text-xs text-gray-400">{revenueBreakdown.sponsoring.amount.toLocaleString('fr-FR')} FCFA</p>
            </div>
            <div className="border-l-4 border-red-500 pl-4">
              <p className="text-sm text-gray-500">Frais Service</p>
              <p className="text-2xl font-bold text-gray-900">{revenueBreakdown.service_fees.percentage.toFixed(1)}%</p>
              <p className="text-xs text-gray-400">{revenueBreakdown.service_fees.amount.toLocaleString('fr-FR')} FCFA</p>
            </div>
          </div>
        </div>
      )}

      {/* Transactions List */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="p-6 border-b">
          <h3 className="text-lg font-semibold">💳 Transactions Clients</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Client</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Montant</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Méthode</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Statut</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {transactions.slice(0, 10).map((t) => (
                <tr key={t.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{new Date(t.date).toLocaleDateString('fr-FR')}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{t.client_name || t.client_phone}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{typeof t.amount === 'number' ? t.amount.toLocaleString('fr-FR') : 'N/A'} FCFA</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{t.method}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                      t.status === 'Succès' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                    }`}>
                      {t.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Commissions by Store */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="p-6 border-b">
          <h3 className="text-lg font-semibold">🏪 Commissions par Magasin</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Magasin</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Ventes</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Taux</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Commission</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {commissions.map((c) => (
                <tr key={c.store_id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{c.store_name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{c.total_sales.toLocaleString('fr-FR')} FCFA</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{c.commission_rate}%</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{c.commission_amount.toLocaleString('fr-FR')} FCFA</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Delivery Payouts */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="p-6 border-b">
          <h3 className="text-lg font-semibold">🚚 Coûts Livraison & Salaires Livreurs</h3>
        </div>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Commande</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Livreur</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Distance</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Frais Client</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Salaire Livreur</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Bénéfice</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {payouts.slice(0, 10).map((p) => (
                <tr key={p.id}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{p.order_number}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{p.livreur_name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{p.distance_km} km</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{p.fee_from_client.toLocaleString('fr-FR')} FCFA</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{p.livreur_salary.toLocaleString('fr-FR')} FCFA</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-green-600 font-medium">{p.platform_profit.toLocaleString('fr-FR')} FCFA</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Subscriptions */}
      {subscriptions.length > 0 && (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <div className="p-6 border-b">
            <h3 className="text-lg font-semibold">📅 Abonnements Mode Pro</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Magasin</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Plan</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Prix/mois</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Fin</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Statut</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {subscriptions.map((s) => (
                  <tr key={s.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{s.store_name}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{s.plan}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">{s.price.toLocaleString('fr-FR')} FCFA</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{new Date(s.end_date).toLocaleDateString('fr-FR')}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        s.status === 'Actif' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {s.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );

  const storesSection = (
    <AdminStoresSection
      storesListAdmin={storesListAdmin}
      storesFilter={storesFilter}
      setStoresFilter={setStoresFilter}
      loadStoresData={loadStoresData}
      setShowAddStore={setShowAddStore}
      setEditingStore={setEditingStore}
      viewStoreDetail={viewStoreDetail}
      handleDeactivateStore={handleDeactivateStore}
      handleActivateStore={handleActivateStore}
      handleDeleteStore={handleDeleteStore}
      handleActivateB2B={handleActivateB2B}
      handleDeactivateB2B={handleDeactivateB2B}
      handleCreateB2BProfile={handleCreateB2BProfile}
      b2bLoading={b2bLoading}
      storeCategories={storeCategories}
    />
  );

  const productsSection = (
    <AdminProductsSection
      productsListAdmin={productsListAdmin}
      productsFilter={productsFilter}
      setProductsFilter={setProductsFilter}
      loadProductsData={loadProductsData}
      productStats={productStats}
      setShowAddProduct={setShowAddProduct}
      setEditingProduct={setEditingProduct}
      viewProductDetail={viewProductDetail}
      handleActivateProduct={handleActivateProduct}
      handleDeactivateProduct={handleDeactivateProduct}
      handleDeleteProduct={handleDeleteProduct}
      handleBulkActions={handleBulkActions}
      productCategories={allProductCategories}
      stores={stores}
    />
  );

  const storeCategoriesSection = selectedStoreCategory ? (
    <div className="space-y-4">
      <div className="flex items-center gap-2 mb-4">
        <button
          onClick={() => setSelectedStoreCategory(null)}
          className="px-3 py-2 bg-gray-200 text-gray-700 rounded-md text-sm font-semibold hover:bg-gray-300"
        >
          ← Retour
        </button>
        <h2 className="text-lg font-semibold">Magasins - {selectedStoreCategory.name}</h2>
      </div>
      <div className="bg-white shadow-sm rounded-lg border border-gray-100 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Nom</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Gérant</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Téléphone</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ville</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {stores.filter(s => s.category_id === selectedStoreCategory.id).map((s) => (
              <tr key={s.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{s.name}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{s.manager_name}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{s.phone}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{s.city}</td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <button onClick={() => setEditingStore(s)} className="text-indigo-600 hover:text-indigo-900 mr-4">Modifier</button>
                  <button onClick={() => handleDeleteStore(s.id)} className="text-red-600 hover:text-red-900">Supprimer</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {stores.filter(s => s.category_id === selectedStoreCategory.id).length === 0 && (
          <div className="px-6 py-4 text-center text-sm text-gray-500">
            Aucun magasin dans cette catégorie
          </div>
        )}
      </div>
    </div>
  ) : (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h2 className="text-lg font-semibold">Catégories de magasins</h2>
        <button
          onClick={() => setShowAddStoreCat(true)}
          className="px-4 py-2 bg-indigo-600 text-white rounded-md text-sm font-semibold hover:bg-indigo-700"
        >
          Ajouter
        </button>
      </div>
      <div className="bg-white shadow-sm rounded-lg border border-gray-100 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Nom</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Magasins</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Icône</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actif</th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {storeCategories.map((c) => (
              <tr key={c.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{c.name}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {stores.filter(s => s.category_id === c.id).length}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{c.description}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{c.icon}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {c.is_active ? <span className="text-green-600">Oui</span> : <span className="text-red-600">Non</span>}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <div className="flex items-center justify-end gap-2">
                    <button
                      onClick={() => setSelectedStoreCategory(c)}
                      className="p-1.5 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded"
                      title="Paramètres des magasins"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      </svg>
                    </button>
                    <button
                      onClick={() => setEditingStoreCat(c)}
                      className="p-1.5 text-indigo-600 hover:text-indigo-900 hover:bg-indigo-50 rounded"
                      title="Modifier"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L7.5 19.5 3 21l1.5-4.5 12.232-12.232z" />
                      </svg>
                    </button>
                    <button
                      onClick={() => handleDeleteStoreCat(c.id)}
                      className="p-1.5 text-red-600 hover:text-red-900 hover:bg-red-50 rounded"
                      title="Supprimer"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  const productCategoriesSection = (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Catégories de produits (par magasin)</h2>
      <div className="bg-white shadow-sm rounded-lg border border-gray-100 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Magasin</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Nom</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Description</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Ordre</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {allProductCategories.map((c) => (
              <tr key={c.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{c.store_name}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{c.name}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{c.description}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{c.order}</td>
              </tr>
            ))}
            {allProductCategories.length === 0 && (
              <tr><td colSpan="4" className="px-6 py-4 text-center text-sm text-gray-500">Aucune catégorie trouvée</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );

  const paymentMethodsSection = (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Transactions (Paiements)</h2>
      <div className="bg-white shadow-sm rounded-lg border border-gray-100 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Commande</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Méthode</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Montant</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Statut</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {payments.map((p) => (
              <tr key={p.id}>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{p.order_number}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{p.payment_method}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{p.amount} FCFA</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                    p.status === 'Succès' ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                  }`}>
                    {p.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{new Date(p.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );

  const deliverySection = <AdminDeliverySection />;

  const settingsSection = (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">⚙️ Configuration Globale</h2>
        {!editingSettings ? (
          <button
            onClick={() => setEditingSettings(true)}
            className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 font-medium"
          >
            Modifier les paramètres
          </button>
        ) : (
          <div className="flex gap-2">
            <button
              onClick={() => {
                setEditingSettings(false);
                setSettingsForm(systemSettings);
              }}
              className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
            >
              Annuler
            </button>
            <button
              onClick={handleUpdateSettings}
              className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 font-medium"
            >
              Enregistrer
            </button>
          </div>
        )}
      </div>

      {systemSettings && (
        <form onSubmit={handleUpdateSettings} className="space-y-6">
          {/* 🟦 1. COMMISSIONS */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">🟦 Commissions</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Commission globale par défaut (%)</label>
                <input
                  type="number"
                  step="0.01"
                  value={editingSettings ? settingsForm.commission_global : systemSettings.commission_global}
                  onChange={(e) => setSettingsForm({...settingsForm, commission_global: e.target.value})}
                  disabled={!editingSettings}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Commission événements/promos (%)</label>
                <input
                  type="number"
                  step="0.01"
                  value={editingSettings ? settingsForm.commission_event : systemSettings.commission_event}
                  onChange={(e) => setSettingsForm({...settingsForm, commission_event: e.target.value})}
                  disabled={!editingSettings}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-50"
                />
              </div>
            </div>
          </div>

          {/* 🟧 2. PAIEMENTS */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">🟧 Paiements</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Frais Moov Money (%)</label>
                <input
                  type="number"
                  step="0.01"
                  value={editingSettings ? settingsForm.moov_money_fee : systemSettings.moov_money_fee}
                  onChange={(e) => setSettingsForm({...settingsForm, moov_money_fee: e.target.value})}
                  disabled={!editingSettings}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Frais Airtel Money (%)</label>
                <input
                  type="number"
                  step="0.01"
                  value={editingSettings ? settingsForm.airtel_money_fee : systemSettings.airtel_money_fee}
                  onChange={(e) => setSettingsForm({...settingsForm, airtel_money_fee: e.target.value})}
                  disabled={!editingSettings}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-50"
                />
              </div>
              <div className="col-span-2">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={editingSettings ? settingsForm.payment_before_order : systemSettings.payment_before_order}
                    onChange={(e) => setSettingsForm({...settingsForm, payment_before_order: e.target.checked})}
                    disabled={!editingSettings}
                    className="rounded"
                  />
                  <span className="text-sm font-medium text-gray-700">Paiement requis avant validation de commande</span>
                </label>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Délai expiration commande impayée (minutes)</label>
                <input
                  type="number"
                  value={editingSettings ? settingsForm.unpaid_order_expiry_minutes : systemSettings.unpaid_order_expiry_minutes}
                  onChange={(e) => setSettingsForm({...settingsForm, unpaid_order_expiry_minutes: e.target.value})}
                  disabled={!editingSettings}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-50"
                />
              </div>
            </div>
          </div>

          {/* 🟥 3. VILLES & GÉOLOCALISATION */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">🟥 Villes & Géolocalisation</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="flex items-center gap-2 mb-4">
                  <input
                    type="checkbox"
                    checked={editingSettings ? settingsForm.auto_detect_cities : systemSettings.auto_detect_cities}
                    onChange={(e) => setSettingsForm({...settingsForm, auto_detect_cities: e.target.checked})}
                    disabled={!editingSettings}
                    className="rounded"
                  />
                  <span className="text-sm font-medium text-gray-700">Détection automatique des villes</span>
                </label>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Ville par défaut</label>
                <input
                  type="text"
                  value={editingSettings ? settingsForm.default_city : systemSettings.default_city}
                  onChange={(e) => setSettingsForm({...settingsForm, default_city: e.target.value})}
                  disabled={!editingSettings}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-50"
                />
              </div>
              <div className="col-span-2">
                <label className="block text-sm font-medium text-gray-700 mb-1">Villes activées (séparées par virgules)</label>
                <input
                  type="text"
                  value={editingSettings ? (settingsForm.enabled_cities?.join ? settingsForm.enabled_cities.join(',') : settingsForm.enabled_cities) : (systemSettings.enabled_cities?.join ? systemSettings.enabled_cities.join(',') : systemSettings.enabled_cities)}
                  onChange={(e) => setSettingsForm({...settingsForm, enabled_cities: e.target.value})}
                  disabled={!editingSettings}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Distance max livraison (km)</label>
                <input
                  type="number"
                  step="0.01"
                  value={editingSettings ? settingsForm.max_delivery_distance_km : systemSettings.max_delivery_distance_km}
                  onChange={(e) => setSettingsForm({...settingsForm, max_delivery_distance_km: e.target.value})}
                  disabled={!editingSettings}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-50"
                />
              </div>
            </div>
          </div>

          {/* 🟩 4. LIVRAISON */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">🟩 Livraison</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Prix par km (FCFA)</label>
                <input
                  type="number"
                  step="0.01"
                  value={editingSettings ? settingsForm.price_per_km : systemSettings.price_per_km}
                  onChange={(e) => setSettingsForm({...settingsForm, price_per_km: e.target.value})}
                  disabled={!editingSettings}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Max commandes simultanées par livreur</label>
                <input
                  type="number"
                  value={editingSettings ? settingsForm.max_orders_per_delivery : systemSettings.max_orders_per_delivery}
                  onChange={(e) => setSettingsForm({...settingsForm, max_orders_per_delivery: e.target.value})}
                  disabled={!editingSettings}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-50"
                />
              </div>
              <div className="col-span-2">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={editingSettings ? settingsForm.auto_assign_delivery : systemSettings.auto_assign_delivery}
                    onChange={(e) => setSettingsForm({...settingsForm, auto_assign_delivery: e.target.checked})}
                    disabled={!editingSettings}
                    className="rounded"
                  />
                  <span className="text-sm font-medium text-gray-700">Attribution automatique des livreurs</span>
                </label>
              </div>
            </div>
          </div>

          {/* 🟨 5. COMMANDES */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">🟨 Commandes</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Validité panier (heures)</label>
                <input
                  type="number"
                  value={editingSettings ? settingsForm.cart_validity_hours : systemSettings.cart_validity_hours}
                  onChange={(e) => setSettingsForm({...settingsForm, cart_validity_hours: e.target.value})}
                  disabled={!editingSettings}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Heure ouverture</label>
                <input
                  type="time"
                  value={editingSettings ? settingsForm.order_opening_time : systemSettings.order_opening_time}
                  onChange={(e) => setSettingsForm({...settingsForm, order_opening_time: e.target.value})}
                  disabled={!editingSettings}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Heure fermeture</label>
                <input
                  type="time"
                  value={editingSettings ? settingsForm.order_closing_time : systemSettings.order_closing_time}
                  onChange={(e) => setSettingsForm({...settingsForm, order_closing_time: e.target.value})}
                  disabled={!editingSettings}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-50"
                />
              </div>
            </div>
          </div>

          {/* 🟪 6. MAGASINS */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">🟪 Magasins</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Heure ouverture par défaut</label>
                <input
                  type="time"
                  value={editingSettings ? settingsForm.default_store_opening : systemSettings.default_store_opening}
                  onChange={(e) => setSettingsForm({...settingsForm, default_store_opening: e.target.value})}
                  disabled={!editingSettings}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Heure fermeture par défaut</label>
                <input
                  type="time"
                  value={editingSettings ? settingsForm.default_store_closing : systemSettings.default_store_closing}
                  onChange={(e) => setSettingsForm({...settingsForm, default_store_closing: e.target.value})}
                  disabled={!editingSettings}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-50"
                />
              </div>
              <div>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={editingSettings ? settingsForm.store_verification_required : systemSettings.store_verification_required}
                    onChange={(e) => setSettingsForm({...settingsForm, store_verification_required: e.target.checked})}
                    disabled={!editingSettings}
                    className="rounded"
                  />
                  <span className="text-sm font-medium text-gray-700">Vérification requise pour nouveaux magasins</span>
                </label>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Tarif Mode Pro (FCFA/mois)</label>
                <input
                  type="number"
                  step="0.01"
                  value={editingSettings ? settingsForm.pro_mode_monthly_fee : systemSettings.pro_mode_monthly_fee}
                  onChange={(e) => setSettingsForm({...settingsForm, pro_mode_monthly_fee: e.target.value})}
                  disabled={!editingSettings}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md disabled:bg-gray-50"
                />
              </div>
            </div>
          </div>

          {/* ⚫ 7. NOTIFICATIONS */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">⚫ Notifications</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={editingSettings ? settingsForm.enable_sms : systemSettings.enable_sms}
                    onChange={(e) => setSettingsForm({...settingsForm, enable_sms: e.target.checked})}
                    disabled={!editingSettings}
                    className="rounded"
                  />
                  <span className="text-sm font-medium text-gray-700">Activer notifications SMS</span>
                </label>
              </div>
              <div>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={editingSettings ? settingsForm.enable_email : systemSettings.enable_email}
                    onChange={(e) => setSettingsForm({...settingsForm, enable_email: e.target.checked})}
                    disabled={!editingSettings}
                    className="rounded"
                  />
                  <span className="text-sm font-medium text-gray-700">Activer notifications Email</span>
                </label>
              </div>
            </div>
          </div>
        </form>
      )}
    </div>
  );

  if (loading) return <div className="p-6">Chargement...</div>;
  if (error) return <div className="p-6 text-red-600">{error}</div>;

  return (
    <div className="min-h-screen bg-gray-50">
      <AdminSidebar activeTab={activeTab} onTabChange={setActiveTab} />
      <AdminNavbar onRefresh={() => loadData(false)} onLogout={handleLogout} refreshing={refreshing} />
      <main className="pt-20 pl-64 pr-6 pb-10">
        {/* Navigation désormais uniquement via la sidebar */}
        
        {/* Messages de succès/erreur */}
        {actionSuccess && (
          <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-lg text-green-800 flex justify-between items-center">
            <span>{actionSuccess}</span>
            <button onClick={() => setActionSuccess('')} className="text-green-600 hover:text-green-800">✕</button>
          </div>
        )}
        {actionError && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-800 flex justify-between items-center">
            <span>{actionError}</span>
            <button onClick={() => setActionError('')} className="text-red-600 hover:text-red-800">✕</button>
          </div>
        )}

        {activeTab === 'overview' && overviewSection}
        {activeTab === 'users' && usersSection}
        {activeTab === 'orders' && ordersSection}
        {activeTab === 'finances' && financesSection}
        {activeTab === 'stores' && storesSection}
        {activeTab === 'products' && productsSection}
        {activeTab === 'store_categories' && storeCategoriesSection}
        {activeTab === 'product_categories' && productCategoriesSection}
        {activeTab === 'payment_methods' && paymentMethodsSection}
        {activeTab === 'delivery' && deliverySection}
        {activeTab === 'settings' && settingsSection}
      </main>

      {showAddUser && (
        <div className="fixed inset-0 bg-black bg-opacity-40 z-40 flex items-center justify-center px-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Ajouter un utilisateur</h3>
              <button
                onClick={() => setShowAddUser(false)}
                className="text-gray-400 hover:text-gray-600"
                aria-label="Fermer"
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleAddUser} className="space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="text-sm font-semibold text-gray-700">Prénom</label>
                  <input
                    type="text"
                    value={newUser.first_name}
                    onChange={(e) => setNewUser((prev) => ({ ...prev, first_name: e.target.value }))}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-sm font-semibold text-gray-700">Nom</label>
                  <input
                    type="text"
                    value={newUser.last_name}
                    onChange={(e) => setNewUser((prev) => ({ ...prev, last_name: e.target.value }))}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700">Téléphone</label>
                <input
                  type="text"
                  value={newUser.phone}
                  onChange={(e) => setNewUser((prev) => ({ ...prev, phone: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Ex: +24161234567"
                  required
                />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="text-sm font-semibold text-gray-700">Email</label>
                  <input
                    type="email"
                    value={newUser.email}
                    onChange={(e) => setNewUser((prev) => ({ ...prev, email: e.target.value }))}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-sm font-semibold text-gray-700">Ville</label>
                  <input
                    type="text"
                    value={newUser.city}
                    onChange={(e) => setNewUser((prev) => ({ ...prev, city: e.target.value }))}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700">Mot de passe (optionnel)</label>
                <input
                  type="password"
                  value={newUser.password}
                  onChange={(e) => setNewUser((prev) => ({ ...prev, password: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Par défaut: téléphone"
                />
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700">Rôle</label>
                <select
                  value={newUser.user_type}
                  onChange={(e) => setNewUser((prev) => ({ ...prev, user_type: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                >
                  <option value="client">Client</option>
                  <option value="store_manager">Gérant</option>
                  <option value="delivery_agent">Livreur</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="flex flex-wrap items-center gap-4">
                <label className="flex items-center gap-2 text-sm text-gray-700">
                  <input
                    type="checkbox"
                    checked={!!newUser.is_verified}
                    onChange={(e) => setNewUser((prev) => ({ ...prev, is_verified: e.target.checked }))}
                  />
                  Compte vérifié
                </label>
                <label className="flex items-center gap-2 text-sm text-gray-700">
                  <input
                    type="checkbox"
                    checked={newUser.is_available ?? true}
                    onChange={(e) => setNewUser((prev) => ({ ...prev, is_available: e.target.checked }))}
                  />
                  Disponible (livreur)
                </label>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddUser(false)}
                  className="px-3 py-2 text-sm rounded-md border border-gray-200 bg-white hover:bg-gray-50"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  className="px-3 py-2 text-sm font-semibold rounded-md bg-indigo-600 text-white hover:bg-indigo-700"
                >
                  Ajouter
                </button>
              </div>
            </form>
            {actionError ? <p className="text-sm text-red-600">{actionError}</p> : null}
          </div>
        </div>
      )}

      {selectedUser && (
        <div className="fixed inset-0 bg-black bg-opacity-40 z-40 flex items-center justify-center px-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Détail utilisateur</h3>
              <button onClick={() => setSelectedUser(null)} className="text-gray-400 hover:text-gray-600" aria-label="Fermer">✕</button>
            </div>
            <div className="space-y-1 text-sm text-gray-700">
              <p><span className="font-semibold">Téléphone: </span>{selectedUser.phone}</p>
              <p><span className="font-semibold">Rôle: </span>{selectedUser.user_type}</p>
              <p><span className="font-semibold">Nom: </span>{[selectedUser.first_name, selectedUser.last_name].filter(Boolean).join(' ')}</p>
              <p><span className="font-semibold">Email: </span>{selectedUser.email}</p>
              <p><span className="font-semibold">Ville: </span>{selectedUser.city}</p>
              <p><span className="font-semibold">Actif: </span>{selectedUser.is_active ? 'Oui' : 'Non'}</p>
              <p><span className="font-semibold">Staff: </span>{selectedUser.is_staff ? 'Oui' : 'Non'}</p>
              <p><span className="font-semibold">Vérifié: </span>{selectedUser.is_verified ? 'Oui' : 'Non'}</p>
              <p><span className="font-semibold">Disponible: </span>{selectedUser.is_available ? 'Oui' : 'Non'}</p>
              <p><span className="font-semibold">Créé le: </span>{new Date(selectedUser.created_at).toLocaleString()}</p>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setSelectedUser(null)}
                className="px-3 py-2 text-sm rounded-md border border-gray-200 bg-white hover:bg-gray-50"
              >
                Fermer
              </button>
            </div>
          </div>
        </div>
      )}

      {confirmDeleteUser && (
        <div className="fixed inset-0 bg-black bg-opacity-40 z-50 flex items-center justify-center px-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Confirmer la suppression</h3>
              <button onClick={() => setConfirmDeleteUser(null)} className="text-gray-400 hover:text-gray-600" aria-label="Fermer">✕</button>
            </div>
            <p className="text-sm text-gray-700">Supprimer l'utilisateur {confirmDeleteUser.phone} ? Cette action est définitive.</p>
            <div className="bg-gray-50 rounded-md p-3 text-xs text-gray-600 space-y-1">
              <p><span className="font-semibold">Rôle:</span> {confirmDeleteUser.user_type}</p>
              <p><span className="font-semibold">Nom:</span> {[confirmDeleteUser.first_name, confirmDeleteUser.last_name].filter(Boolean).join(' ')}</p>
              <p><span className="font-semibold">Email:</span> {confirmDeleteUser.email}</p>
              <p><span className="font-semibold">Ville:</span> {confirmDeleteUser.city}</p>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setConfirmDeleteUser(null)}
                className="px-3 py-2 text-sm rounded-md border border-gray-200 bg-white hover:bg-gray-50"
              >
                Annuler
              </button>
              <button
                type="button"
                onClick={() => handleDeleteUser(confirmDeleteUser.id)}
                className="px-3 py-2 text-sm font-semibold rounded-md bg-red-600 text-white hover:bg-red-700"
              >
                Confirmer
              </button>
            </div>
            {actionError ? <p className="text-sm text-red-600">{actionError}</p> : null}
          </div>
        </div>
      )}

      {editingUser && (
        <div className="fixed inset-0 bg-black bg-opacity-40 z-40 flex items-center justify-center px-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Modifier utilisateur</h3>
              <button onClick={() => setEditingUser(null)} className="text-gray-400 hover:text-gray-600" aria-label="Fermer">✕</button>
            </div>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleUpdateUser(editingUser);
              }}
              className="space-y-3"
            >
              <div>
                <label className="text-sm font-semibold text-gray-700">Téléphone</label>
                <input
                  type="text"
                  value={editingUser.phone}
                  onChange={(e) => setEditingUser((prev) => ({ ...prev, phone: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="text-sm font-semibold text-gray-700">Prénom</label>
                  <input
                    type="text"
                    value={editingUser.first_name || ''}
                    onChange={(e) => setEditingUser((prev) => ({ ...prev, first_name: e.target.value }))}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-sm font-semibold text-gray-700">Nom</label>
                  <input
                    type="text"
                    value={editingUser.last_name || ''}
                    onChange={(e) => setEditingUser((prev) => ({ ...prev, last_name: e.target.value }))}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <div>
                  <label className="text-sm font-semibold text-gray-700">Email</label>
                  <input
                    type="email"
                    value={editingUser.email || ''}
                    onChange={(e) => setEditingUser((prev) => ({ ...prev, email: e.target.value }))}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-sm font-semibold text-gray-700">Ville</label>
                  <input
                    type="text"
                    value={editingUser.city || ''}
                    onChange={(e) => setEditingUser((prev) => ({ ...prev, city: e.target.value }))}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700">Nouveau mot de passe (optionnel)</label>
                <input
                  type="password"
                  value={editingUser.password || ''}
                  onChange={(e) => setEditingUser((prev) => ({ ...prev, password: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Laisser vide pour ne pas changer"
                />
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700">Rôle</label>
                <select
                  value={editingUser.user_type}
                  onChange={(e) => setEditingUser((prev) => ({ ...prev, user_type: e.target.value }))}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                >
                  <option value="client">Client</option>
                  <option value="store_manager">Gérant</option>
                  <option value="delivery_agent">Livreur</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div className="flex items-center gap-2">
                <input
                  id="is_active"
                  type="checkbox"
                  checked={!!editingUser.is_active}
                  onChange={(e) => setEditingUser((prev) => ({ ...prev, is_active: e.target.checked }))}
                />
                <label htmlFor="is_active" className="text-sm text-gray-700">Actif</label>
              </div>
              <div className="flex items-center gap-2">
                <input
                  id="is_verified"
                  type="checkbox"
                  checked={!!editingUser.is_verified}
                  onChange={(e) => setEditingUser((prev) => ({ ...prev, is_verified: e.target.checked }))}
                />
                <label htmlFor="is_verified" className="text-sm text-gray-700">Vérifié</label>
              </div>
              <div className="flex items-center gap-2">
                <input
                  id="is_available"
                  type="checkbox"
                  checked={!!editingUser.is_available}
                  onChange={(e) => setEditingUser((prev) => ({ ...prev, is_available: e.target.checked }))}
                />
                <label htmlFor="is_available" className="text-sm text-gray-700">Disponible (livreur)</label>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setEditingUser(null)}
                  className="px-3 py-2 text-sm rounded-md border border-gray-200 bg-white hover:bg-gray-50"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  className="px-3 py-2 text-sm font-semibold rounded-md bg-indigo-600 text-white hover:bg-indigo-700"
                >
                  Mettre à jour
                </button>
              </div>
            </form>
            {actionError ? <p className="text-sm text-red-600">{actionError}</p> : null}
          </div>
        </div>
      )}

      {showAddStoreCat && (
        <div className="fixed inset-0 bg-black bg-opacity-40 z-40 flex items-center justify-center px-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Ajouter une catégorie</h3>
              <button onClick={() => setShowAddStoreCat(false)} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>
            <form onSubmit={handleCreateStoreCat} className="space-y-3">
              <div>
                <label className="text-sm font-semibold text-gray-700">Nom</label>
                <input
                  type="text"
                  value={newStoreCat.name}
                  onChange={(e) => setNewStoreCat({ ...newStoreCat, name: e.target.value })}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                  required
                />
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700">Description</label>
                <textarea
                  value={newStoreCat.description}
                  onChange={(e) => setNewStoreCat({ ...newStoreCat, description: e.target.value })}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700">Icône (FontAwesome)</label>
                <input
                  type="text"
                  value={newStoreCat.icon}
                  onChange={(e) => setNewStoreCat({ ...newStoreCat, icon: e.target.value })}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={newStoreCat.is_active}
                  onChange={(e) => setNewStoreCat({ ...newStoreCat, is_active: e.target.checked })}
                />
                <label className="text-sm text-gray-700">Active</label>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowAddStoreCat(false)} className="px-3 py-2 text-sm rounded-md border border-gray-200 bg-white hover:bg-gray-50">Annuler</button>
                <button type="submit" className="px-3 py-2 text-sm font-semibold rounded-md bg-indigo-600 text-white hover:bg-indigo-700">Créer</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {editingStoreCat && (
        <div className="fixed inset-0 bg-black bg-opacity-40 z-40 flex items-center justify-center px-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Modifier catégorie</h3>
              <button onClick={() => setEditingStoreCat(null)} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>
            <form onSubmit={handleUpdateStoreCat} className="space-y-3">
              <div>
                <label className="text-sm font-semibold text-gray-700">Nom</label>
                <input
                  type="text"
                  value={editingStoreCat.name}
                  onChange={(e) => setEditingStoreCat({ ...editingStoreCat, name: e.target.value })}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                  required
                />
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700">Description</label>
                <textarea
                  value={editingStoreCat.description}
                  onChange={(e) => setEditingStoreCat({ ...editingStoreCat, description: e.target.value })}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700">Icône</label>
                <input
                  type="text"
                  value={editingStoreCat.icon}
                  onChange={(e) => setEditingStoreCat({ ...editingStoreCat, icon: e.target.value })}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={editingStoreCat.is_active}
                  onChange={(e) => setEditingStoreCat({ ...editingStoreCat, is_active: e.target.checked })}
                />
                <label className="text-sm text-gray-700">Active</label>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setEditingStoreCat(null)} className="px-3 py-2 text-sm rounded-md border border-gray-200 bg-white hover:bg-gray-50">Annuler</button>
                <button type="submit" className="px-3 py-2 text-sm font-semibold rounded-md bg-indigo-600 text-white hover:bg-indigo-700">Mettre à jour</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showAddStore && (
        <div className="fixed inset-0 bg-black bg-opacity-40 z-40 flex items-center justify-center px-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 space-y-4 overflow-y-auto max-h-[90vh]">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Ajouter un magasin</h3>
              <button onClick={() => setShowAddStore(false)} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>
            <form onSubmit={handleCreateStore} className="space-y-3">
              <div>
                <label className="text-sm font-semibold text-gray-700">Nom</label>
                <input type="text" value={newStore.name} onChange={(e) => setNewStore({ ...newStore, name: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" required />
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700">Catégorie</label>
                <select value={newStore.category_id} onChange={(e) => setNewStore({ ...newStore, category_id: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" required>
                  <option value="">Sélectionner...</option>
                  {storeCategories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700">Gérant</label>
                <select value={newStore.manager_id} onChange={(e) => setNewStore({ ...newStore, manager_id: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" required>
                  <option value="">Sélectionner...</option>
                  {users.filter(u => u.user_type === 'store_manager').map(u => <option key={u.id} value={u.id}>{u.first_name} {u.last_name} ({u.phone})</option>)}
                </select>
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700">Téléphone</label>
                <input type="text" value={newStore.phone} onChange={(e) => setNewStore({ ...newStore, phone: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" required />
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700">Ville</label>
                <input type="text" value={newStore.city} onChange={(e) => setNewStore({ ...newStore, city: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowAddStore(false)} className="px-3 py-2 text-sm rounded-md border border-gray-200 bg-white hover:bg-gray-50">Annuler</button>
                <button type="submit" className="px-3 py-2 text-sm font-semibold rounded-md bg-indigo-600 text-white hover:bg-indigo-700">Créer</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {editingStore && (
        <div className="fixed inset-0 bg-black bg-opacity-40 z-40 flex items-center justify-center px-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 space-y-4 overflow-y-auto max-h-[90vh]">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Modifier magasin</h3>
              <button onClick={() => setEditingStore(null)} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>
            <form onSubmit={handleUpdateStore} className="space-y-3">
              <div>
                <label className="text-sm font-semibold text-gray-700">Nom</label>
                <input type="text" value={editingStore.name} onChange={(e) => setEditingStore({ ...editingStore, name: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" required />
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700">Catégorie</label>
                <select value={editingStore.category_id} onChange={(e) => setEditingStore({ ...editingStore, category_id: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm">
                  <option value="">Sélectionner...</option>
                  {storeCategories.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700">Gérant</label>
                <select value={editingStore.manager_id} onChange={(e) => setEditingStore({ ...editingStore, manager_id: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm">
                  <option value="">Sélectionner...</option>
                  {users.filter(u => u.user_type === 'store_manager').map(u => <option key={u.id} value={u.id}>{u.first_name} {u.last_name} ({u.phone})</option>)}
                </select>
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700">Téléphone</label>
                <input type="text" value={editingStore.phone} onChange={(e) => setEditingStore({ ...editingStore, phone: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" required />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setEditingStore(null)} className="px-3 py-2 text-sm rounded-md border border-gray-200 bg-white hover:bg-gray-50">Annuler</button>
                <button type="submit" className="px-3 py-2 text-sm font-semibold rounded-md bg-indigo-600 text-white hover:bg-indigo-700">Mettre à jour</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal Ajouter Magasin */}
      {showAddStore && (
        <div className="fixed inset-0 bg-black bg-opacity-40 z-40 flex items-center justify-center px-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl p-6 space-y-4 overflow-y-auto max-h-[90vh]">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Ajouter un magasin</h3>
              <button
                onClick={() => setShowAddStore(false)}
                className="text-gray-400 hover:text-gray-600"
                aria-label="Fermer"
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleCreateStore} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-semibold text-gray-700">Nom du magasin *</label>
                  <input
                    type="text"
                    value={newStore.name}
                    onChange={(e) => setNewStore({ ...newStore, name: e.target.value })}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    required
                  />
                </div>
                <div>
                  <label className="text-sm font-semibold text-gray-700">Catégorie *</label>
                  <select
                    value={newStore.category_id}
                    onChange={(e) => setNewStore({ ...newStore, category_id: e.target.value })}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    required
                  >
                    <option value="">Sélectionner une catégorie</option>
                    {storeCategories.map((cat) => (
                      <option key={cat.id} value={cat.id}>
                        {cat.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="text-sm font-semibold text-gray-700">Description</label>
                <textarea
                  value={newStore.description}
                  onChange={(e) => setNewStore({ ...newStore, description: e.target.value })}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  rows="3"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-semibold text-gray-700">Responsable *</label>
                  <select
                    value={newStore.manager_id}
                    onChange={(e) => setNewStore({ ...newStore, manager_id: e.target.value })}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    required
                  >
                    <option value="">Sélectionner un responsable</option>
                    {users
                      .filter((u) => u.user_type === 'store_manager')
                      .map((u) => (
                        <option key={u.id} value={u.id}>
                          {u.first_name} {u.last_name} ({u.phone})
                        </option>
                      ))}
                  </select>
                </div>
                <div>
                  <label className="text-sm font-semibold text-gray-700">Téléphone *</label>
                  <input
                    type="tel"
                    value={newStore.phone}
                    onChange={(e) => setNewStore({ ...newStore, phone: e.target.value })}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="+24161234567"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-semibold text-gray-700">Email</label>
                  <input
                    type="email"
                    value={newStore.email}
                    onChange={(e) => setNewStore({ ...newStore, email: e.target.value })}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-sm font-semibold text-gray-700">Ville *</label>
                  <input
                    type="text"
                    value={newStore.city}
                    onChange={(e) => setNewStore({ ...newStore, city: e.target.value })}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-semibold text-gray-700">Adresse *</label>
                  <input
                    type="text"
                    value={newStore.address}
                    onChange={(e) => setNewStore({ ...newStore, address: e.target.value })}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    required
                  />
                </div>
                <div>
                  <label className="text-sm font-semibold text-gray-700">Zone</label>
                  <input
                    type="text"
                    value={newStore.zone}
                    onChange={(e) => setNewStore({ ...newStore, zone: e.target.value })}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="text-sm font-semibold text-gray-700">Commission (%)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="100"
                    value={newStore.commission_rate}
                    onChange={(e) => setNewStore({ ...newStore, commission_rate: e.target.value })}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-sm font-semibold text-gray-700">Frais livraison (FCFA)</label>
                  <input
                    type="number"
                    step="100"
                    min="0"
                    value={newStore.delivery_fee}
                    onChange={(e) => setNewStore({ ...newStore, delivery_fee: e.target.value })}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-sm font-semibold text-gray-700">Plan d'abonnement</label>
                  <select
                    value={newStore.subscription_plan}
                    onChange={(e) => setNewStore({ ...newStore, subscription_plan: e.target.value })}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  >
                    <option value="starter">Starter</option>
                    <option value="pro">Pro</option>
                    <option value="business">Business</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={newStore.is_active}
                  onChange={(e) => setNewStore({ ...newStore, is_active: e.target.checked })}
                  id="store_active"
                  className="rounded"
                />
                <label htmlFor="store_active" className="text-sm font-medium text-gray-700">
                  Magasin actif
                </label>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t">
                <button
                  type="button"
                  onClick={() => setShowAddStore(false)}
                  className="px-3 py-2 text-sm rounded-md border border-gray-200 bg-white hover:bg-gray-50"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  className="px-3 py-2 text-sm font-semibold rounded-md bg-indigo-600 text-white hover:bg-indigo-700"
                >
                  Créer le magasin
                </button>
              </div>
            </form>
            {actionError ? <p className="text-sm text-red-600 mt-2">{actionError}</p> : null}
          </div>
        </div>
      )}

      {/* Modal Modifier Magasin */}
      {editingStore && (
        <div className="fixed inset-0 bg-black bg-opacity-40 z-40 flex items-center justify-center px-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl p-6 space-y-4 overflow-y-auto max-h-[90vh]">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Modifier le magasin</h3>
              <button
                onClick={() => setEditingStore(null)}
                className="text-gray-400 hover:text-gray-600"
                aria-label="Fermer"
              >
                ✕
              </button>
            </div>
            <form onSubmit={handleUpdateStore} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-semibold text-gray-700">Nom du magasin *</label>
                  <input
                    type="text"
                    value={editingStore.name}
                    onChange={(e) => setEditingStore({ ...editingStore, name: e.target.value })}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    required
                  />
                </div>
                <div>
                  <label className="text-sm font-semibold text-gray-700">Catégorie *</label>
                  <select
                    value={editingStore.category_id}
                    onChange={(e) => setEditingStore({ ...editingStore, category_id: e.target.value })}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    required
                  >
                    <option value="">Sélectionner une catégorie</option>
                    {storeCategories.map((cat) => (
                      <option key={cat.id} value={cat.id}>
                        {cat.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="text-sm font-semibold text-gray-700">Description</label>
                <textarea
                  value={editingStore.description}
                  onChange={(e) => setEditingStore({ ...editingStore, description: e.target.value })}
                  className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  rows="3"
                />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-semibold text-gray-700">Responsable *</label>
                  <select
                    value={editingStore.manager_id}
                    onChange={(e) => setEditingStore({ ...editingStore, manager_id: e.target.value })}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    required
                  >
                    <option value="">Sélectionner un responsable</option>
                    {users
                      .filter((u) => u.user_type === 'store_manager')
                      .map((u) => (
                        <option key={u.id} value={u.id}>
                          {u.first_name} {u.last_name} ({u.phone})
                        </option>
                      ))}
                  </select>
                </div>
                <div>
                  <label className="text-sm font-semibold text-gray-700">Téléphone *</label>
                  <input
                    type="tel"
                    value={editingStore.phone}
                    onChange={(e) => setEditingStore({ ...editingStore, phone: e.target.value })}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    placeholder="+24161234567"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-semibold text-gray-700">Email</label>
                  <input
                    type="email"
                    value={editingStore.email}
                    onChange={(e) => setEditingStore({ ...editingStore, email: e.target.value })}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-sm font-semibold text-gray-700">Ville *</label>
                  <input
                    type="text"
                    value={editingStore.city}
                    onChange={(e) => setEditingStore({ ...editingStore, city: e.target.value })}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-semibold text-gray-700">Adresse *</label>
                  <input
                    type="text"
                    value={editingStore.address}
                    onChange={(e) => setEditingStore({ ...editingStore, address: e.target.value })}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    required
                  />
                </div>
                <div>
                  <label className="text-sm font-semibold text-gray-700">Zone</label>
                  <input
                    type="text"
                    value={editingStore.zone}
                    onChange={(e) => setEditingStore({ ...editingStore, zone: e.target.value })}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="text-sm font-semibold text-gray-700">Commission (%)</label>
                  <input
                    type="number"
                    step="0.01"
                    min="0"
                    max="100"
                    value={editingStore.commission_rate}
                    onChange={(e) => setEditingStore({ ...editingStore, commission_rate: e.target.value })}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-sm font-semibold text-gray-700">Frais livraison (FCFA)</label>
                  <input
                    type="number"
                    step="100"
                    min="0"
                    value={editingStore.delivery_fee}
                    onChange={(e) => setEditingStore({ ...editingStore, delivery_fee: e.target.value })}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="text-sm font-semibold text-gray-700">Plan d'abonnement</label>
                  <select
                    value={editingStore.subscription_plan}
                    onChange={(e) => setEditingStore({ ...editingStore, subscription_plan: e.target.value })}
                    className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                  >
                    <option value="starter">Starter</option>
                    <option value="pro">Pro</option>
                    <option value="business">Business</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={editingStore.is_active}
                  onChange={(e) => setEditingStore({ ...editingStore, is_active: e.target.checked })}
                  id="store_active_edit"
                  className="rounded"
                />
                <label htmlFor="store_active_edit" className="text-sm font-medium text-gray-700">
                  Magasin actif
                </label>
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t">
                <button
                  type="button"
                  onClick={() => setEditingStore(null)}
                  className="px-3 py-2 text-sm rounded-md border border-gray-200 bg-white hover:bg-gray-50"
                >
                  Annuler
                </button>
                <button
                  type="submit"
                  className="px-3 py-2 text-sm font-semibold rounded-md bg-indigo-600 text-white hover:bg-indigo-700"
                >
                  Mettre à jour
                </button>
              </div>
            </form>
            {actionError ? <p className="text-sm text-red-600 mt-2">{actionError}</p> : null}
          </div>
        </div>
      )}

      {showAddProduct && (
        <div className="fixed inset-0 bg-black bg-opacity-40 z-40 flex items-center justify-center px-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 space-y-4 overflow-y-auto max-h-[90vh]">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Ajouter un produit</h3>
              <button onClick={() => setShowAddProduct(false)} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>
            <form onSubmit={handleCreateProduct} className="space-y-3">
              <div>
                <label className="text-sm font-semibold text-gray-700">Nom</label>
                <input type="text" value={newProduct.name} onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" required />
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700">Description</label>
                <textarea value={newProduct.description} onChange={(e) => setNewProduct({ ...newProduct, description: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" rows="3" />
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700">Image (URL)</label>
                <input type="text" value={newProduct.image || ''} onChange={(e) => setNewProduct({ ...newProduct, image: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" placeholder="https://..." />
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700">Magasin</label>
                <select value={newProduct.store_id} onChange={(e) => setNewProduct({ ...newProduct, store_id: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" required>
                  <option value="">Sélectionner...</option>
                  {stores.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                </select>
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700">Prix</label>
                <input type="number" value={newProduct.price} onChange={(e) => setNewProduct({ ...newProduct, price: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" required />
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700">Stock</label>
                <input type="number" value={newProduct.stock} onChange={(e) => setNewProduct({ ...newProduct, stock: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" required />
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setShowAddProduct(false)} className="px-3 py-2 text-sm rounded-md border border-gray-200 bg-white hover:bg-gray-50">Annuler</button>
                <button type="submit" className="px-3 py-2 text-sm font-semibold rounded-md bg-indigo-600 text-white hover:bg-indigo-700">Créer</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {editingProduct && (
        <div className="fixed inset-0 bg-black bg-opacity-40 z-40 flex items-center justify-center px-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-md p-6 space-y-4 overflow-y-auto max-h-[90vh]">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">Modifier produit</h3>
              <button onClick={() => setEditingProduct(null)} className="text-gray-400 hover:text-gray-600">✕</button>
            </div>
            <form onSubmit={handleUpdateProduct} className="space-y-3">
              <div>
                <label className="text-sm font-semibold text-gray-700">Nom</label>
                <input type="text" value={editingProduct.name} onChange={(e) => setEditingProduct({ ...editingProduct, name: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" required />
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700">Description</label>
                <textarea value={editingProduct.description || ''} onChange={(e) => setEditingProduct({ ...editingProduct, description: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" rows="3" />
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700">Image (URL)</label>
                <input type="text" value={editingProduct.image || ''} onChange={(e) => setEditingProduct({ ...editingProduct, image: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" placeholder="https://..." />
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700">Prix</label>
                <input type="number" value={editingProduct.price} onChange={(e) => setEditingProduct({ ...editingProduct, price: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" required />
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-700">Stock</label>
                <input type="number" value={editingProduct.stock} onChange={(e) => setEditingProduct({ ...editingProduct, stock: e.target.value })} className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm" required />
              </div>
              <div className="flex items-center gap-2">
                <input type="checkbox" checked={editingProduct.is_available} onChange={(e) => setEditingProduct({ ...editingProduct, is_available: e.target.checked })} />
                <label className="text-sm text-gray-700">Disponible</label>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button type="button" onClick={() => setEditingProduct(null)} className="px-3 py-2 text-sm rounded-md border border-gray-200 bg-white hover:bg-gray-50">Annuler</button>
                <button type="submit" className="px-3 py-2 text-sm font-semibold rounded-md bg-indigo-600 text-white hover:bg-indigo-700">Mettre à jour</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal de détails du produit */}
      {viewingProduct && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full flex items-center justify-center z-50">
          <div className="bg-white p-5 rounded-lg shadow-xl max-w-2xl w-full mx-4">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-xl font-semibold text-gray-900">Détails du produit</h3>
              <button onClick={() => setViewingProduct(null)} className="text-gray-400 hover:text-gray-500">
                <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="space-y-4">
              {viewingProduct.image && (
                <div className="flex justify-center">
                  <img src={viewingProduct.image} alt={viewingProduct.name} className="max-h-64 rounded-lg object-cover" />
                </div>
              )}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">Nom</label>
                  <p className="mt-1 text-sm text-gray-900">{viewingProduct.name}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Prix</label>
                  <p className="mt-1 text-sm text-gray-900">{viewingProduct.price} FCFA</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Stock</label>
                  <p className="mt-1 text-sm text-gray-900">{viewingProduct.stock}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700">Disponible</label>
                  <p className="mt-1 text-sm">
                    {viewingProduct.is_available ? 
                      <span className="text-green-600 font-medium">Oui</span> : 
                      <span className="text-red-600 font-medium">Non</span>
                    }
                  </p>
                </div>
                {viewingProduct.store_name && (
                  <div className="col-span-2">
                    <label className="block text-sm font-medium text-gray-700">Magasin</label>
                    <p className="mt-1 text-sm text-gray-900">{viewingProduct.store_name}</p>
                  </div>
                )}
              </div>
              {viewingProduct.description && (
                <div>
                  <label className="block text-sm font-medium text-gray-700">Description</label>
                  <p className="mt-1 text-sm text-gray-900 whitespace-pre-wrap">{viewingProduct.description}</p>
                </div>
              )}
            </div>
            <div className="flex justify-end mt-6">
              <button 
                onClick={() => setViewingProduct(null)} 
                className="px-4 py-2 text-sm font-medium rounded-md bg-gray-100 text-gray-700 hover:bg-gray-200"
              >
                Fermer
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal de confirmation */}
      <Modal
        isOpen={showConfirmModal.isOpen}
        onClose={() => setShowConfirmModal({ isOpen: false, message: '', onConfirm: null })}
        title="Confirmation"
        onConfirm={showConfirmModal.onConfirm}
        confirmText="Confirmer"
        cancelText="Annuler"
        showCancel={true}
        confirmButtonClass="bg-red-600 hover:bg-red-700"
      >
        <p className="text-gray-700">{showConfirmModal.message}</p>
      </Modal>

      {/* Modal détails du store */}
      <Modal
        isOpen={showStoreDetailModal}
        onClose={() => {
          setShowStoreDetailModal(false);
          setSelectedStoreDetail(null);
        }}
        title={selectedStoreDetail ? `Détails - ${selectedStoreDetail.name}` : 'Détails du magasin'}
        size="xl"
        showCancel={false}
      >
        {selectedStoreDetail && (
          <div className="space-y-6">
            {/* Informations générales */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-semibold text-gray-600">Nom</label>
                <p className="text-gray-900">{selectedStoreDetail.name}</p>
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-600">Catégorie</label>
                <p className="text-gray-900">{selectedStoreDetail.category_name || '—'}</p>
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-600">Ville</label>
                <p className="text-gray-900">{selectedStoreDetail.city || '—'}</p>
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-600">Zone</label>
                <p className="text-gray-900">{selectedStoreDetail.zone || '—'}</p>
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-600">Gérant</label>
                <p className="text-gray-900">{selectedStoreDetail.manager_name || '—'}</p>
              </div>
              <div>
                <label className="text-sm font-semibold text-gray-600">Statut</label>
                <p className={`inline-block px-2 py-1 rounded text-xs ${selectedStoreDetail.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                  {selectedStoreDetail.is_active ? 'Actif' : 'Inactif'}
                </p>
              </div>
            </div>

            {/* Section B2B */}
            <div className="border-t pt-4">
              <h4 className="text-lg font-semibold mb-4">Configuration B2B</h4>
              {selectedStoreDetail.b2b_profile ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-3 bg-gray-50 rounded">
                    <div>
                      <p className="font-semibold">Profil B2B</p>
                      <p className="text-sm text-gray-600">
                        Statut: <span className={selectedStoreDetail.b2b_profile.is_active ? 'text-green-600' : 'text-red-600'}>
                          {selectedStoreDetail.b2b_profile.is_active ? 'Actif' : 'Inactif'}
                        </span>
                      </p>
                      <p className="text-sm text-gray-600">
                        Montant minimum: {selectedStoreDetail.b2b_profile.minimum_order_amount?.toLocaleString('fr-FR') || 0} FCFA
                      </p>
                    </div>
                    <div className="flex gap-2">
                      {selectedStoreDetail.b2b_profile.is_active ? (
                        <button
                          onClick={() => handleDeactivateB2B(selectedStoreDetail.id)}
                          disabled={b2bLoading[`b2b_${selectedStoreDetail.id}`]}
                          className="px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700 disabled:opacity-50"
                        >
                          {b2bLoading[`b2b_${selectedStoreDetail.id}`] ? '...' : 'Désactiver B2B'}
                        </button>
                      ) : (
                        <button
                          onClick={() => handleActivateB2B(selectedStoreDetail.id)}
                          disabled={b2bLoading[`b2b_${selectedStoreDetail.id}`]}
                          className="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 disabled:opacity-50"
                        >
                          {b2bLoading[`b2b_${selectedStoreDetail.id}`] ? '...' : 'Activer B2B'}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="p-4 bg-yellow-50 border border-yellow-200 rounded">
                  <p className="text-sm text-yellow-800 mb-3">Aucun profil B2B configuré pour ce magasin.</p>
                  <button
                    onClick={() => handleCreateB2BProfile(selectedStoreDetail.id)}
                    disabled={b2bLoading[`b2b_create_${selectedStoreDetail.id}`]}
                    className="px-4 py-2 bg-indigo-600 text-white rounded text-sm hover:bg-indigo-700 disabled:opacity-50"
                  >
                    {b2bLoading[`b2b_create_${selectedStoreDetail.id}`] ? 'Création...' : 'Créer un profil B2B'}
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default AdminDashboard;
