import React, { useEffect, useState } from 'react';
import HomeNavbar from '../components/HomeNavbar';
import Footer from '../components/Footer';
import { getStoreCategories } from '../services/storeService';

const normalizeText = (value) => (value || '').toString().toLowerCase();

const COLOR_SWATCHES = [
  { bg: 'bg-amber-100', text: 'text-amber-700' },
  { bg: 'bg-emerald-100', text: 'text-emerald-700' },
  { bg: 'bg-sky-100', text: 'text-sky-700' },
  { bg: 'bg-rose-100', text: 'text-rose-700' },
  { bg: 'bg-indigo-100', text: 'text-indigo-700' },
  { bg: 'bg-orange-100', text: 'text-orange-700' },
];

const StoreCategories = () => {
  const [categories, setCategories] = useState([]);
  const [filteredCategories, setFilteredCategories] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchCategories = async () => {
      try {
        setLoading(true);
        const response = await getStoreCategories();
        let categoriesData = [];
        if (response?.success) {
          categoriesData = response.data || [];
        } else if (response?.results) {
          categoriesData = response.results;
        } else if (Array.isArray(response)) {
          categoriesData = response;
        }
        setCategories(categoriesData);
        setFilteredCategories(categoriesData);
      } catch (err) {
        console.error(err);
        setError('Erreur lors du chargement des categories.');
      } finally {
        setLoading(false);
      }
    };

    fetchCategories();
  }, []);

  useEffect(() => {
    const term = searchTerm.trim();
    if (!term) {
      setFilteredCategories(categories);
      return;
    }

    const normalized = normalizeText(term);
    const matches = categories.filter((category) => {
      const name = normalizeText(category.name);
      const description = normalizeText(category.description);
      return name.includes(normalized) || description.includes(normalized);
    });

    setFilteredCategories(matches);
  }, [searchTerm, categories]);

  const activeCount = searchTerm.trim() ? filteredCategories.length : categories.length;

  return (
    <div className="min-h-screen bg-white">
      <HomeNavbar />

      <section className="relative overflow-hidden py-12">
        <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-white to-amber-50" />
        <div className="absolute -top-16 right-24 h-40 w-40 rounded-full bg-amber-200/40 blur-3xl" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Categories</p>
              <h1 className="text-3xl font-bold text-slate-900 font-display">
                Toutes les categories de magasins
              </h1>
              <p className="text-sm text-slate-600 mt-2">
                Explorez les categories pour trouver les boutiques qui vous interessent.
              </p>
            </div>
            <div className="inline-flex items-center gap-2 rounded-full bg-white px-4 py-2 shadow-sm">
              <span className="text-sm font-semibold text-slate-900">{activeCount}</span>
              <span className="text-xs text-slate-500">categories disponibles</span>
            </div>
          </div>

          <div className="mt-6 flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <input
                type="text"
                value={searchTerm}
                onChange={(event) => setSearchTerm(event.target.value)}
                placeholder="Rechercher une categorie..."
                className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 shadow-sm focus:border-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-200"
              />
            </div>
            {searchTerm.trim() && (
              <button
                type="button"
                onClick={() => setSearchTerm('')}
                className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50"
              >
                Reinitialiser
              </button>
            )}
          </div>

          {searchTerm.trim() && (
            <p className="mt-3 text-xs text-slate-500">
              Resultats pour "{searchTerm.trim()}"
            </p>
          )}

          <div className="mt-6 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {loading && (
              <div className="col-span-full flex items-center justify-center py-16">
                <div className="h-12 w-12 animate-spin rounded-full border-4 border-slate-200 border-t-slate-900" />
              </div>
            )}
            {!loading && error && (
              <div className="col-span-full text-center text-sm text-red-600 bg-white/70 border border-dashed border-red-200 rounded-2xl p-6">
                {error}
              </div>
            )}
            {!loading && !error && filteredCategories.length === 0 && (
              <div className="col-span-full text-center text-sm text-slate-500 bg-white/70 border border-dashed border-slate-200 rounded-2xl p-8">
                Aucune categorie disponible pour le moment.
              </div>
            )}
            {!loading && !error && filteredCategories.map((category, index) => {
              const swatch = COLOR_SWATCHES[index % COLOR_SWATCHES.length];
              const iconValue = category.icon?.trim();
              const iconLabel =
                iconValue && iconValue.length <= 2
                  ? iconValue
                  : (category.name || '?').charAt(0).toUpperCase();

              return (
                <div
                  key={category.id || `${category.name}-${index}`}
                  className="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div
                        className={`h-12 w-12 rounded-xl ${swatch.bg} ${swatch.text} flex items-center justify-center font-semibold text-lg`}
                      >
                        {iconLabel}
                      </div>
                      <div>
                        <h3 className="text-base font-semibold text-slate-900">
                          {category.name || 'Categorie'}
                        </h3>
                        {category.description && (
                          <p className="text-xs text-slate-500 mt-1">
                            {category.description}
                          </p>
                        )}
                      </div>
                    </div>
                    {typeof category.store_count === 'number' && (
                      <span className="text-xs font-semibold text-slate-500">
                        {category.store_count} boutiques
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
};

export default StoreCategories;
