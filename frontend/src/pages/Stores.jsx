import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import HomeNavbar from '../components/HomeNavbar';
import Footer from '../components/Footer';
import { getStores } from '../services/storeService';

const normalizeText = (value) => (value || '').toString().toLowerCase();
const formatPlanLabel = (plan) => {
  const normalized = normalizeText(plan);
  const labels = { starter: 'Starter', pro: 'Pro', business: 'Business' };
  return labels[normalized] || (normalized ? normalized.charAt(0).toUpperCase() + normalized.slice(1) : '');
};

const Stores = () => {
  const [stores, setStores] = useState([]);
  const [filteredStores, setFilteredStores] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [searchResults, setSearchResults] = useState({ products: [], stores: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStores = async () => {
      try {
        setLoading(true);
        const response = await getStores();
        let storesData = [];
        if (response.success) {
          storesData = response.data;
        } else if (response.results) {
          storesData = response.results;
        } else if (Array.isArray(response)) {
          storesData = response;
        }
        setStores(storesData);
        setFilteredStores(storesData);
      } catch (err) {
        console.error(err);
        setError('Erreur lors du chargement des boutiques.');
      } finally {
        setLoading(false);
      }
    };

    fetchStores();
  }, []);

  useEffect(() => {
    const term = searchTerm.trim();
    if (!term) {
      setFilteredStores(stores);
      setSearchResults({ products: [], stores: [] });
      return;
    }

    const normalized = normalizeText(term);
    const matches = stores.filter((store) => {
      const name = normalizeText(store.name);
      const category = normalizeText(store.category_name);
      const city = normalizeText(store.city);
      const zone = normalizeText(store.zone);
      return (
        name.includes(normalized) ||
        category.includes(normalized) ||
        city.includes(normalized) ||
        zone.includes(normalized)
      );
    });

    setFilteredStores(matches);
    setSearchResults({ products: [], stores: matches.slice(0, 6) });
  }, [searchTerm, stores]);

  const handleSearchSubmit = (term) => {
    setSearchTerm((term || '').trim());
  };

  const renderStoreGrid = () => {
    if (loading) {
      return (
        <div className="col-span-full flex items-center justify-center py-16">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-slate-200 border-t-slate-900" />
        </div>
      );
    }

    if (error) {
      return (
        <div className="col-span-full text-center text-sm text-red-600 bg-white/70 border border-dashed border-red-200 rounded-2xl p-6">
          {error}
        </div>
      );
    }

    if (filteredStores.length === 0) {
      return (
        <div className="col-span-full text-center text-sm text-slate-500 bg-white/70 border border-dashed border-slate-200 rounded-2xl p-8">
          Aucune boutique disponible pour le moment.
        </div>
      );
    }

    return filteredStores.map((store) => (
      <Link
        key={store.id}
        to={`/stores/${store.id}`}
        className="group rounded-2xl border border-slate-100 bg-white p-5 shadow-sm hover:shadow-md transition-shadow"
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="h-12 w-12 rounded-xl bg-slate-900 text-white flex items-center justify-center font-semibold overflow-hidden">
              {store.logo ? (
                <img src={store.logo} alt={store.name} className="h-full w-full object-cover rounded-xl" />
              ) : (
                store.name?.charAt(0)
              )}
            </div>
            <div>
              <h3 className="text-base font-semibold text-slate-900 group-hover:text-emerald-700">
                {store.name}
              </h3>
              <p className="text-xs text-slate-500">
                {store.category_name || 'Boutique'} - {store.city}
              </p>
            </div>
          </div>
          {store.subscription_plan && (
            <span className="text-[11px] font-semibold uppercase px-2 py-1 rounded-full bg-emerald-100 text-emerald-700">
              {formatPlanLabel(store.subscription_plan)}
            </span>
          )}
        </div>
        <div className="mt-4 flex items-center justify-between text-xs text-slate-500">
          <span>{store.total_products || 0} produits</span>
          <span className={store.is_open ? 'text-emerald-600' : 'text-slate-400'}>
            {store.is_open ? 'Ouvert' : 'Ferme'}
          </span>
        </div>
      </Link>
    ));
  };

  const activeCount = searchTerm.trim() ? filteredStores.length : stores.length;

  return (
    <div className="min-h-screen bg-white">
      <HomeNavbar
        searchTerm={searchTerm}
        searchResults={searchResults}
        onSearchChange={setSearchTerm}
        onSearchSubmit={handleSearchSubmit}
      />

      <section className="relative overflow-hidden py-12">
        <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-white to-emerald-50" />
        <div className="absolute -top-16 left-24 h-40 w-40 rounded-full bg-emerald-200/40 blur-3xl" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Boutiques</p>
              <h1 className="text-3xl font-bold text-slate-900 font-display">
                Toutes les boutiques de GABOSHOP
              </h1>
              <p className="text-sm text-slate-600 mt-2">
                Parcourez les boutiques actives et trouvez vos produits favoris en un instant.
              </p>
            </div>
            <div className="inline-flex items-center gap-2 rounded-full bg-white px-4 py-2 shadow-sm">
              <span className="text-sm font-semibold text-slate-900">{activeCount}</span>
              <span className="text-xs text-slate-500">boutiques disponibles</span>
            </div>
          </div>
          {searchTerm.trim() && (
            <p className="mt-3 text-xs text-slate-500">
              Resultats pour "{searchTerm.trim()}"
            </p>
          )}
          <div className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {renderStoreGrid()}
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default Stores;
