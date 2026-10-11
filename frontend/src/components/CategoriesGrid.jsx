import React from 'react';
import { Link } from 'react-router-dom';

/**
 * Grille de categories de produits
 * Design mobile-first avec icones et couleurs - DYNAMIQUE
 */
const CATEGORY_ICONS = {
  food: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M6 4h12l-1 15a2 2 0 01-2 2H9a2 2 0 01-2-2L6 4z" />
      <path d="M9 2h6" />
      <path d="M12 2v3" />
    </svg>
  ),
  fashion: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M4 7l4-3 3 3h2l3-3 4 3-2 4v8a2 2 0 01-2 2H8a2 2 0 01-2-2v-8L4 7z" />
    </svg>
  ),
  electronics: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <rect x="3" y="4" width="18" height="12" rx="2" />
      <path d="M8 20h8" />
      <path d="M12 16v4" />
    </svg>
  ),
  grocery: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M4 10h16l-2 9H6l-2-9z" />
      <path d="M9 10l3-6 3 6" />
    </svg>
  ),
  home: ({ className }) => (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
      <path d="M3 10l9-7 9 7v9a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
      <path d="M9 22V12h6v10" />
    </svg>
  ),
};

// Icône choisie d'après le nom de la catégorie (les catégories viennent de la console admin)
const ICON_RULES = [
  ['food', ['ALIMENT', 'BOISSON', 'RESTAU', 'BOULANG', 'PATISS', 'BOUCH']],
  ['grocery', ['EPICER', 'SUPERMARCH', 'HYPERMARCH', 'MARCHE', 'SUPERETTE']],
  ['fashion', ['MODE', 'TEXTILE', 'VETEMENT', 'CHAUSS', 'BEAUTE', 'COSMET', 'COIFF']],
  ['electronics', ['ELECTRO', 'INFORMAT', 'TELEPH', 'MULTIMEDIA']],
  ['home', ['MAISON', 'DECOR', 'MEUBLE', 'QUINCAILL', 'BRICO', 'JARDIN']],
];

const MAX_HOME_CATEGORIES = 8;

const normalizeCategoryName = (value) =>
  (value || '')
    .toString()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toUpperCase()
    .replace(/\s+/g, ' ')
    .trim();

const iconKeyFor = (name) => {
  const normalized = normalizeCategoryName(name);
  const rule = ICON_RULES.find(([, words]) => words.some((word) => normalized.includes(word)));
  return rule ? rule[0] : null;
};

const CategoriesGrid = ({ categories = [] }) => {
  const sourceCategories = Array.isArray(categories) ? categories : [];
  // D'abord les catégories qui ont des boutiques, pour que chaque tuile mène à du contenu
  const withStores = sourceCategories.filter((category) => (category.store_count ?? 1) > 0);
  const displayCategories = (withStores.length > 0 ? withStores : sourceCategories)
    .slice(0, MAX_HOME_CATEGORIES)
    .map((category) => ({ ...category, iconKey: iconKeyFor(category.name) }));

  if (displayCategories.length === 0) return null;

  return (
    <section id="categories" className="py-8 px-4">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8 flex items-end justify-between gap-4">
          <div>
            <h2 className="text-2xl md:text-3xl font-bold text-gray-900">
              Parcourir par categorie
            </h2>
            <p className="text-gray-600 mt-2">
              Trouvez ce que vous cherchez en quelques clics
            </p>
          </div>
          <Link to="/categories" className="shrink-0 text-sm font-semibold text-amber-700 hover:text-amber-800">
            Tout voir
          </Link>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {displayCategories.map((category) => {
            const Icon = CATEGORY_ICONS[category.iconKey];
            return (
              <Link
                key={category.id}
                to={`/boutiques?categorie=${category.id}`}
                className="group"
              >
                <div
                  className="card-3d p-4 text-center cursor-pointer"
                >
                  <div className="mb-3 inline-flex items-center justify-center w-12 h-12 rounded-2xl btn-gold">
                    {Icon ? <Icon className="w-7 h-7" /> : <span className="text-lg font-semibold">{(category.name || '?').charAt(0).toUpperCase()}</span>}
                  </div>
                  <h3
                    className="font-semibold text-sm md:text-base text-slate-900"
                  >
                    {category.name || 'Categorie'}
                  </h3>
                  {typeof category.store_count === 'number' && (
                    <p className="text-xs text-slate-500 mt-1">
                      {category.store_count} boutique{category.store_count > 1 ? 's' : ''}
                    </p>
                  )}
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </section>
  );
};

export default CategoriesGrid;
