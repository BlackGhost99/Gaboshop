import React, { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { fetchNotifications, markNotificationRead, deleteNotification } from '../services/notificationService';
import { formatDateTime } from '../utils/helpers';

const POLL_INTERVAL_MS = 20000;

const HomeNavbar = ({
  cartCount = 0,
  searchTerm = '',
  searchResults = { products: [], stores: [] },
  searchLoading = false,
  onSearchChange,
  onSearchSubmit
}) => {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [localSearch, setLocalSearch] = useState('');
  const location = useLocation();
  
  // Notification Detail Modal
  const [selectedNotification, setSelectedNotification] = useState(null);
  const [showNotificationModal, setShowNotificationModal] = useState(false);

  const isLoggedIn = !!sessionStorage.getItem('token');
  const canSearch = typeof onSearchChange === 'function' || typeof onSearchSubmit === 'function';
  const currentSearch = canSearch ? searchTerm : localSearch;
  const trimmedSearch = currentSearch.trim();
  const productMatches = searchResults?.products || [];
  const storeMatches = searchResults?.stores || [];
  const hasResults = productMatches.length > 0 || storeMatches.length > 0;
  const showResults = canSearch && trimmedSearch.length > 0;

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  const handleSearchChange = (event) => {
    const value = event.target.value;
    if (onSearchChange) {
      onSearchChange(value);
    } else {
      setLocalSearch(value);
    }
  };

  const handleSearchSubmit = (event) => {
    if (event) event.preventDefault();
    if (onSearchSubmit) {
      onSearchSubmit(currentSearch);
    }
  };

  const submitQuickSearch = (value) => {
    const trimmed = (value || '').trim();
    if (!trimmed) return;
    if (onSearchChange) onSearchChange(trimmed);
    if (onSearchSubmit) onSearchSubmit(trimmed);
  };

  const loadNotifications = useCallback(async (isBackground = false) => {
    if (!isBackground) {
      setLoading(true);
    }
    try {
      const res = await fetchNotifications();
      const items = res?.data || res?.results || [];
      setNotifications(Array.isArray(items) ? items : []);
    } catch {
      // Silent fail
    } finally {
      if (!isBackground) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    if (isLoggedIn) {
      let mounted = true;
      loadNotifications();
      const intervalId = setInterval(() => {
        if (mounted) {
          loadNotifications(true);
        }
      }, POLL_INTERVAL_MS);
      return () => {
        mounted = false;
        clearInterval(intervalId);
      };
    }
  }, [isLoggedIn, loadNotifications]);

  const handleOpenNotification = async (notif) => {
    setSelectedNotification(notif);
    setShowNotificationModal(true);
    setOpen(false);
    if (!notif.is_read) {
      try {
        await markNotificationRead(notif.id);
        setNotifications((prev) =>
          prev.map((n) => (n.id === notif.id ? { ...n, is_read: true } : n))
        );
      } catch {
        // Silent fail
      }
    }
  };

  const handleDeleteNotification = async (id) => {
    if (!window.confirm('Supprimer cette notification ?')) return;
    try {
      await deleteNotification(id);
      setNotifications((prev) => prev.filter((n) => n.id !== id));
      setShowNotificationModal(false);
      setSelectedNotification(null);
    } catch (error) {
      console.error('Erreur:', error);
      alert('Erreur lors de la suppression');
    }
  };

  const getBadgeColor = (type) => {
    const map = {
      order: 'bg-blue-100 text-blue-800',
      delivery: 'bg-emerald-100 text-emerald-800',
      payment: 'bg-green-100 text-green-800',
      warning: 'bg-amber-100 text-amber-800',
      info: 'bg-gray-100 text-gray-700',
    };
    return map[type] || map.info;
  };

  const navigateToSection = (targetId) => {
    setMenuOpen(false);
    if (location.pathname === '/') {
      const section = document.getElementById(targetId);
      if (section) {
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
      }
    }
    navigate('/', { state: { scrollTo: targetId } });
  };

  const handleBoutiquesClick = () => {
    setMenuOpen(false);
    if (location.pathname !== '/boutiques') {
      navigate('/boutiques');
    }
  };
  const handleCategoriesClick = () => {
    setMenuOpen(false);
    if (location.pathname !== '/categories') {
      navigate('/categories');
    }
  };
  const handlePromotionsClick = () => navigateToSection('promotions');
  const handleProduitsClick = () => navigateToSection('produits');

  const renderSearchResults = () => {
    if (!showResults) return null;

    return (
      <div className="absolute z-50 mt-2 w-full overflow-hidden rounded-xl border border-gray-200 bg-white shadow-lg">
        {searchLoading && (
          <div className="px-4 py-3 text-sm text-gray-500">Recherche en cours...</div>
        )}
        {!searchLoading && !hasResults && (
          <div className="px-4 py-3 text-sm text-gray-500">Aucun résultat trouvé.</div>
        )}
        {storeMatches.length > 0 && (
          <div className="border-b border-gray-100">
            <div className="px-4 py-2 text-xs uppercase tracking-wider text-gray-500 bg-gray-50">
              Boutiques
            </div>
            <div className="divide-y divide-gray-100">
              {storeMatches.slice(0, 4).map((store) => (
                <Link
                  key={store.id}
                  to={`/stores/${store.id}`}
                  className="flex items-center gap-3 px-4 py-3 hover:bg-gray-50"
                >
                  <div className="h-8 w-8 rounded-lg bg-slate-900 text-white flex items-center justify-center text-xs font-semibold">
                    {store.name?.charAt(0)}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-gray-900">{store.name}</p>
                    <p className="text-xs text-gray-500">
                      {store.category_name || 'Boutique'} - {store.city}
                    </p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        )}
        {productMatches.length > 0 && (
          <div>
            <div className="px-4 py-2 text-xs uppercase tracking-wider text-gray-500 bg-gray-50">
              Produits
            </div>
            <div className="divide-y divide-gray-100">
              {productMatches.slice(0, 4).map((product) => (
                <button
                  key={product.id}
                  type="button"
                  onClick={() => submitQuickSearch(product.name)}
                  className="w-full text-left flex items-center gap-3 px-4 py-3 hover:bg-gray-50"
                >
                  <div className="h-10 w-10 rounded-lg overflow-hidden bg-gray-100 flex items-center justify-center">
                    {product.image ? (
                      <img src={product.image} alt={product.name} className="h-full w-full object-cover" />
                    ) : (
                      <span className="text-[10px] text-gray-400">Produit</span>
                    )}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-semibold text-gray-900 line-clamp-1">{product.name}</p>
                    <p className="text-xs text-gray-500">{product.store_name}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  const menuItems = [
    {
      key: 'categories',
      label: 'Categories',
      description: 'Toutes les categories',
      action: handleCategoriesClick,
      icon: (
        <svg className="w-4 h-4 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h7v7H4zM13 6h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z" />
        </svg>
      ),
    },
    {
      key: 'boutiques',
      label: 'Boutiques',
      description: 'Toutes les boutiques',
      action: handleBoutiquesClick,
      icon: (
        <svg className="w-4 h-4 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 9l9-6 9 6v11a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 22V12h6v10" />
        </svg>
      ),
    },
    {
      key: 'promotions',
      label: 'Promotions',
      description: 'Offres en avant',
      action: handlePromotionsClick,
      icon: (
        <svg className="w-4 h-4 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v13m0-13V6a2 2 0 112 2h-2zm0 0V5.5A2.5 2.5 0 109.5 8H12zM5 12h14" />
        </svg>
      ),
    },
    {
      key: 'produits',
      label: 'Produits',
      description: 'Catalogue complet',
      action: handleProduitsClick,
      icon: (
        <svg className="w-4 h-4 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 3h18v4H3zM5 7v14h14V7" />
        </svg>
      ),
    },
    {
      key: 'plans',
      label: 'Plans',
      description: 'Offres pour boutiques',
      to: '/plans',
      icon: (
        <svg className="w-4 h-4 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h8M8 11h8M7 19h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      ),
    },
  ];

  return (
    <>
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-40 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center space-x-2">
              <div className="w-10 h-10 bg-slate-900 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-lg">G</span>
              </div>
              <span className="hidden sm:inline-block font-bold text-lg text-slate-900 font-display">
                GABOSHOP
              </span>
            </Link>

            {/* Search (Desktop) */}
            <div className="hidden md:flex flex-1 max-w-md mx-6">
              <form onSubmit={handleSearchSubmit} className="relative w-full">
                <div className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 focus-within:ring-2 focus-within:ring-slate-900">
                  <svg
                    className="w-4 h-4 text-slate-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M21 21l-4.35-4.35m1.1-5.4a6.5 6.5 0 11-13 0 6.5 6.5 0 0113 0z"
                    />
                  </svg>
                  <input
                    type="text"
                    placeholder="Rechercher produits, boutiques..."
                    value={currentSearch}
                    onChange={handleSearchChange}
                    className="w-full bg-transparent focus:outline-none text-sm"
                  />
                </div>
                {renderSearchResults()}
              </form>
            </div>

            {/* Right Actions */}
            <div className="flex items-center space-x-4">
              <div className="relative">
                <button
                  onClick={() => setMenuOpen((prev) => !prev)}
                  className="flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-200 bg-white text-slate-900 hover:bg-slate-50 transition-colors text-sm font-semibold"
                  aria-haspopup="true"
                  aria-expanded={menuOpen}
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                  <span className="hidden sm:inline">Menu</span>
                </button>
                {menuOpen && (
                  <div className="absolute right-0 mt-2 w-72 rounded-xl border border-slate-200 bg-white shadow-lg overflow-hidden z-50">
                    <div className="px-4 py-3 border-b border-slate-100 bg-slate-50">
                      <p className="text-xs uppercase tracking-wider text-slate-500">Navigation rapide</p>
                      <p className="text-sm font-semibold text-slate-900">Fonctionnalites</p>
                    </div>
                    <div className="py-2">
                      {menuItems.map((item) => (
                        item.to ? (
                          <Link
                            key={item.key}
                            to={item.to}
                            onClick={() => setMenuOpen(false)}
                            className="flex items-start gap-3 px-4 py-3 hover:bg-slate-50 transition-colors"
                          >
                            <span className="mt-0.5">{item.icon}</span>
                            <span className="flex-1">
                              <span className="block text-sm font-semibold text-slate-900">{item.label}</span>
                              <span className="block text-xs text-slate-500">{item.description}</span>
                            </span>
                          </Link>
                        ) : (
                          <button
                            key={item.key}
                            type="button"
                            onClick={item.action}
                            className="w-full text-left flex items-start gap-3 px-4 py-3 hover:bg-slate-50 transition-colors"
                          >
                            <span className="mt-0.5">{item.icon}</span>
                            <span className="flex-1">
                              <span className="block text-sm font-semibold text-slate-900">{item.label}</span>
                              <span className="block text-xs text-slate-500">{item.description}</span>
                            </span>
                          </button>
                        )
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Dashboard Link */}
              {isLoggedIn && (
                <Link
                  to="/dashboard"
                  className="hidden md:flex items-center space-x-1 px-3 py-2 rounded-lg bg-slate-50 text-slate-900 hover:bg-slate-100 transition-colors font-medium text-sm"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
                    />
                  </svg>
                  <span>Dashboard</span>
                </Link>
              )}
              
              {/* Notifications */}
              {isLoggedIn && (
                <div className="relative">
                  <button
                    onClick={() => setOpen(!open)}
                    className="relative p-2 rounded-lg hover:bg-gray-100 transition-colors"
                    aria-label="Notifications"
                  >
                    <svg
                      className="w-6 h-6 text-slate-900"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M15 17h5l-1.4-1.4A2 2 0 0118 14.2V11a6 6 0 10-12 0v3.2a2 2 0 01-.6 1.4L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                      />
                    </svg>
                    {unreadCount > 0 && (
                      <span className="absolute -top-1 -right-1 inline-flex items-center justify-center px-1.5 py-0.5 text-xs font-bold leading-none text-white bg-cta-600 rounded-full">
                        {unreadCount}
                      </span>
                    )}
                  </button>

                  {/* Notifications Dropdown */}
                  {open && (
                    <div className="absolute right-0 mt-2 w-96 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
                      <div className="flex items-center justify-between px-4 py-3 border-b bg-gray-50">
                        <h3 className="font-semibold text-slate-900">Notifications</h3>
                        {unreadCount > 0 && (
                          <span className="text-xs text-slate-600">
                            {unreadCount} non lue(s)
                          </span>
                        )}
                      </div>
                      <div className="max-h-96 overflow-y-auto">
                        {loading && (
                          <div className="p-4 text-sm text-gray-500">Chargement...</div>
                        )}
                        {!loading && notifications.length === 0 && (
                          <div className="p-4 text-sm text-gray-500">
                            Aucune notification
                          </div>
                        )}
                        {notifications.map((notif) => (
                          <button
                            key={notif.id}
                            onClick={() => handleOpenNotification(notif)}
                            className={`w-full text-left px-4 py-3 hover:bg-gray-50 transition border-b ${
                              notif.is_read ? 'bg-white' : 'bg-slate-50'
                            }`}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div className="flex-1">
                                <div className="flex items-center gap-2">
                                  {!notif.is_read && (
                                    <span className="w-2 h-2 bg-slate-900 rounded-full flex-shrink-0" />
                                  )}
                                  <p className="font-semibold text-sm text-slate-900">
                                    {notif.title}
                                  </p>
                                </div>
                                <p className="text-sm text-gray-600 mt-1 line-clamp-2">
                                  {notif.body}
                                </p>
                                <p className="text-xs text-gray-500 mt-1">
                                  {formatDateTime(notif.created_at)}
                                </p>
                              </div>
                              <span
                                className={`text-xs px-2 py-1 rounded-full whitespace-nowrap ${getBadgeColor(
                                  notif.notif_type
                                )}`}
                              >
                                {notif.notif_type}
                              </span>
                            </div>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <button
                onClick={handleBoutiquesClick}
                className="hidden md:flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-50 text-slate-900 hover:bg-slate-100 transition-colors font-medium text-sm"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3 9l9-6 9 6v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"
                  />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 22V12h6v10" />
                </svg>
                <span>Boutique</span>
              </button>
              <button
                onClick={handleBoutiquesClick}
                className="md:hidden p-2 rounded-lg hover:bg-gray-100 transition-colors"
                aria-label="Boutique"
              >
                <svg className="w-6 h-6 text-slate-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3 9l9-6 9 6v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"
                  />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 22V12h6v10" />
                </svg>
              </button>

              {/* Cart Icon */}
              <Link
                to="/cart"
                className="relative p-2 rounded-lg hover:bg-gray-100 transition-colors"
              >
                <svg
                  className="w-6 h-6 text-slate-900"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"
                  />
                </svg>
                {cartCount > 0 && (
                  <span className="absolute -top-1 -right-1 inline-flex items-center justify-center px-1.5 py-0.5 text-xs font-bold leading-none text-white bg-cta-600 rounded-full">
                    {cartCount}
                  </span>
                )}
              </Link>

              {/* Auth Buttons / Menu */}
              {isLoggedIn ? (
                <button
                  onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                  className="md:hidden p-2 rounded-lg hover:bg-gray-100"
                >
                  <svg
                    className="w-6 h-6 text-slate-900"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 6h16M4 12h16M4 18h16"
                    />
                  </svg>
                </button>
              ) : (
                <div className="hidden md:flex items-center space-x-3">
                  <Link
                    to="/login"
                    className="px-4 py-2 text-slate-900 font-medium hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    Connexion
                  </Link>
                  <Link
                    to="/register"
                    className="px-4 py-2 bg-slate-900 text-white font-medium rounded-lg hover:bg-slate-800 transition-colors"
                  >
                    S'inscrire
                  </Link>
                </div>
              )}
            </div>
          </div>

          {/* Search Mobile */}
          <div className="md:hidden pb-4">
            <form onSubmit={handleSearchSubmit} className="relative">
              <div className="flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 focus-within:ring-2 focus-within:ring-slate-900">
                <svg
                  className="w-4 h-4 text-slate-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M21 21l-4.35-4.35m1.1-5.4a6.5 6.5 0 11-13 0 6.5 6.5 0 0113 0z"
                  />
                </svg>
                <input
                  type="text"
                  placeholder="Rechercher produits, boutiques..."
                  value={currentSearch}
                  onChange={handleSearchChange}
                  className="w-full bg-transparent focus:outline-none text-sm"
                />
              </div>
              {renderSearchResults()}
            </form>
          </div>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && isLoggedIn && (
          <div className="md:hidden border-t border-gray-200 bg-gray-50 px-4 py-3">
            <Link
              to="/dashboard"
              onClick={() => setMobileMenuOpen(false)}
              className="flex items-center space-x-2 px-4 py-3 rounded-lg bg-slate-900 text-white hover:bg-slate-800 transition-colors font-medium"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6"
                />
              </svg>
              <span>Mon Dashboard</span>
            </Link>
          </div>
        )}
      </nav>

      {/* Notification Detail Modal */}
      {showNotificationModal && selectedNotification && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
            {/* Header */}
            <div className={`px-6 py-4 border-b ${
              selectedNotification.is_read ? 'bg-gray-50' : 'bg-primary-50'
            }`}>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    {!selectedNotification.is_read && (
                      <span className="w-2 h-2 bg-primary-600 rounded-full"></span>
                    )}
                    <h3 className="text-lg font-bold text-gray-900">
                      {selectedNotification.title}
                    </h3>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    {new Date(selectedNotification.created_at).toLocaleString('fr-FR', {
                      day: '2-digit',
                      month: 'long',
                      year: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </p>
                </div>
                <button
                  onClick={() => setShowNotificationModal(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                </button>
              </div>
            </div>

            {/* Body */}
            <div className="px-6 py-4 overflow-y-auto" style={{ maxHeight: 'calc(90vh - 180px)' }}>
              <div className="space-y-4">
                {/* Type Badge */}
                <div className="flex items-center gap-2">
                  <span
                    className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold ${getBadgeColor(
                      selectedNotification.notif_type
                    )}`}
                  >
                    {selectedNotification.notif_type === 'delivery' && '?? Livraison'}
                    {selectedNotification.notif_type === 'order' && '?? Commande'}
                    {selectedNotification.notif_type === 'payment' && '?? Paiement'}
                    {selectedNotification.notif_type === 'warning' && '?? Alerte'}
                    {selectedNotification.notif_type === 'info' && '?? Info'}
                  </span>
                  {selectedNotification.is_read && (
                    <span className="text-xs text-gray-500">? Lu</span>
                  )}
                </div>

                {/* Message */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-sm text-gray-800 whitespace-pre-wrap leading-relaxed">
                    {selectedNotification.body}
                  </p>
                </div>

                {/* Metadata */}
                {(selectedNotification.order || selectedNotification.metadata) && (
                  <div className="border-t pt-4 space-y-2">
                    <h4 className="text-sm font-semibold text-gray-700">Détails</h4>
                    {selectedNotification.order && (
                      <div className="flex items-center gap-2 text-sm">
                        <span className="font-medium text-gray-600">Commande:</span>
                        <span className="text-gray-900 font-mono">
                          #{selectedNotification.order}
                        </span>
                      </div>
                    )}
                    {selectedNotification.metadata?.from && (
                      <div className="flex items-center gap-2 text-sm">
                        <span className="font-medium text-gray-600">Départ:</span>
                        <span className="text-gray-900">
                          {selectedNotification.metadata.from}
                        </span>
                      </div>
                    )}
                    {selectedNotification.metadata?.to && (
                      <div className="flex items-center gap-2 text-sm">
                        <span className="font-medium text-gray-600">Arrivée:</span>
                        <span className="text-gray-900">
                          {selectedNotification.metadata.to}
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Actions */}
            <div className="px-6 py-4 bg-gray-50 border-t flex items-center justify-between">
              <button
                onClick={() => handleDeleteNotification(selectedNotification.id)}
                className="flex items-center gap-2 text-sm font-medium text-red-600 hover:text-red-700 hover:bg-red-50 px-3 py-2 rounded-md transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                  />
                </svg>
                Supprimer
              </button>
              <button
                onClick={() => setShowNotificationModal(false)}
                className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 font-medium text-sm"
              >
                Fermer
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default HomeNavbar;
