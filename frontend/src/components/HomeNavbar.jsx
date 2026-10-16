import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import authStorage from '../utils/authStorage';
import { logout } from '../utils/session';
import NotificationBell from './NotificationBell';

const HomeNavbar = ({
  cartCount = 0,
  searchTerm = '',
  searchResults = { products: [], stores: [] },
  searchLoading = false,
  onSearchChange,
  onSearchSubmit
}) => {
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);
  const [localSearch, setLocalSearch] = useState('');
  const location = useLocation();

  const isLoggedIn = !!authStorage.getItem('token');
  const canSearch = typeof onSearchChange === 'function' || typeof onSearchSubmit === 'function';
  const currentSearch = canSearch ? searchTerm : localSearch;
  const trimmedSearch = currentSearch.trim();
  const productMatches = searchResults?.products || [];
  const storeMatches = searchResults?.stores || [];
  const hasResults = productMatches.length > 0 || storeMatches.length > 0;
  const showResults = canSearch && trimmedSearch.length > 0;

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
    ...(isLoggedIn ? [{
      key: 'dashboard',
      label: 'Mon espace',
      description: 'Commandes, panier et réglages',
      to: '/dashboard',
      icon: (
        <svg className="w-4 h-4 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
      ),
    }] : []),
    {
      key: 'categories',
      label: 'Catégories',
      description: 'Toutes les catégories',
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
    ...(isLoggedIn ? [{
      key: 'delete-account',
      label: 'Supprimer mon compte',
      description: 'Effacer mon compte et mes données',
      to: '/supprimer-mon-compte',
      icon: (
        <svg className="w-4 h-4 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.87 12.14A2 2 0 0116.14 21H7.86a2 2 0 01-1.99-1.86L5 7m5 4v6m4-6v6M9 7V4a1 1 0 011-1h4a1 1 0 011 1v3M4 7h16" />
        </svg>
      ),
    }, {
      key: 'logout',
      label: 'Se déconnecter',
      description: 'Quitter votre compte',
      action: () => logout(),
      icon: (
        <svg className="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
        </svg>
      ),
    }] : []),
  ];

  return (
    <>
      <nav className="nav-metal sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center space-x-2">
              <img src="/logo.png" alt="Gaboshop" className="w-11 h-11 object-contain" />
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
            <div className="flex items-center space-x-1 sm:space-x-4">
              <div className="sm:relative">
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
                  <div className="absolute left-3 right-3 top-full mt-1 sm:left-0 sm:right-auto sm:top-auto sm:mt-2 sm:w-72 max-h-[75dvh] overflow-y-auto rounded-xl border border-slate-200 bg-white shadow-lg z-50">
                    <div className="px-4 py-3 border-b border-slate-100 bg-slate-50">
                      <p className="text-xs uppercase tracking-wider text-slate-500">Navigation rapide</p>
                      <p className="text-sm font-semibold text-slate-900">Fonctionnalités</p>
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
              {isLoggedIn && <NotificationBell />}

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
              {/* Cart Icon */}
              <Link
                to="/cart"
                className="relative hidden md:block p-2 rounded-lg hover:bg-gray-100 transition-colors"
                aria-label="Mon panier"
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

              {isLoggedIn && (
                <button
                  type="button"
                  onClick={() => logout()}
                  className="hidden md:flex items-center gap-1 px-3 py-2 rounded-lg text-red-600 hover:bg-red-50 transition-colors font-medium text-sm"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                  </svg>
                  <span>Déconnexion</span>
                </button>
              )}

              {/* Visiteur : connexion et inscription */}
              {!isLoggedIn && (
                <div className="flex items-center space-x-0.5 md:space-x-3">
                  <Link
                    to="/login"
                    className="px-1 py-2 text-[13px] sm:text-sm md:px-4 md:text-base text-slate-900 font-medium hover:bg-gray-100 rounded-lg transition-colors"
                  >
                    Connexion
                  </Link>
                  <Link
                    to="/register"
                    className="px-2.5 py-2 text-[13px] sm:text-sm md:px-4 md:text-base bg-slate-900 text-white font-medium rounded-lg hover:bg-slate-800 transition-colors whitespace-nowrap"
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

      </nav>

    </>
  );
};

export default HomeNavbar;
