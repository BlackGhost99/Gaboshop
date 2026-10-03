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

const FEATURED_CATEGORIES = [
  {
    id: 1,
    name: 'ALIMENTATION & BOISSON',
    iconKey: 'food',
    color: 'bg-red-100',
    textColor: 'text-red-700',
    slug: 'alimentation-boisson',
  },
  {
    id: 2,
    name: 'MODE & TEXTILE',
    iconKey: 'fashion',
    color: 'bg-purple-100',
    textColor: 'text-purple-700',
    slug: 'mode-textile',
  },
  {
    id: 3,
    name: 'ELECTRONIQUE & INFORMATIQUE',
    iconKey: 'electronics',
    color: 'bg-blue-100',
    textColor: 'text-blue-700',
    slug: 'electronique-informatique',
  },
  {
    id: 4,
    name: 'EPICERIE',
    iconKey: 'grocery',
    color: 'bg-amber-100',
    textColor: 'text-amber-700',
    slug: 'epicerie',
  },
  {
    id: 5,
    name: 'MAISON & DECORATION',
    iconKey: 'home',
    color: 'bg-emerald-100',
    textColor: 'text-emerald-700',
    slug: 'maison-decoration',
  },
];

const normalizeCategoryName = (value) =>
  (value || '')
    .toString()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toUpperCase()
    .replace(/\s+/g, ' ')
    .trim();

const CategoriesGrid = ({ categories = [] }) => {
  const sourceCategories = Array.isArray(categories) ? categories : [];
  const sourceMap = new Map(
    sourceCategories.map((category) => [normalizeCategoryName(category.name), category])
  );

  const displayCategories = FEATURED_CATEGORIES.map((category) => {
    const match = sourceMap.get(normalizeCategoryName(category.name));
    return {
      ...category,
      id: match?.id ?? category.id,
      slug: match?.slug ?? category.slug,
    };
  });

  return (
    <section id="categories" className="py-8 px-4 bg-gray-50">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h2 className="text-2xl md:text-3xl font-bold text-gray-900">
            Parcourir par categorie
          </h2>
          <p className="text-gray-600 mt-2">
            Trouvez ce que vous cherchez en quelques clics
          </p>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          {displayCategories.map((category) => {
            const Icon = CATEGORY_ICONS[category.iconKey];
            return (
              <Link
                key={category.id}
                to={`/products?category=${category.slug || category.id}`}
                className="group"
              >
                <div
                  className={`${category.color || 'bg-gray-100'} rounded-lg p-4 text-center hover:shadow-lg transition-all duration-300 cursor-pointer transform group-hover:scale-105`}
                >
                  <div className="mb-3 inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-white/70 text-slate-700 shadow-sm">
                    {Icon ? <Icon className="w-7 h-7" /> : <span className="text-xs">CAT</span>}
                  </div>
                  <h3
                    className={`font-semibold text-sm md:text-base ${
                      category.textColor || 'text-gray-700'
                    } group-hover:underline`}
                  >
                    {category.name || 'Categorie'}
                  </h3>
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
