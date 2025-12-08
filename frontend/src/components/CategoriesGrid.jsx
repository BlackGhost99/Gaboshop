import React from 'react';
import { Link } from 'react-router-dom';

/**
 * Grille de catégories de produits
 * Design mobile-first avec icônes et couleurs - DYNAMIQUE
 */
const CategoriesGrid = ({ categories = [] }) => {
  const defaultCategories = [
    {
      id: 1,
      name: 'Électronique',
      icon: '📱',
      color: 'bg-blue-100',
      textColor: 'text-blue-700',
      slug: 'electronique',
    },
    {
      id: 2,
      name: 'Mode & Vêtements',
      icon: '👕',
      color: 'bg-purple-100',
      textColor: 'text-purple-700',
      slug: 'mode',
    },
    {
      id: 3,
      name: 'Maison & Décoration',
      icon: '🏠',
      color: 'bg-amber-100',
      textColor: 'text-amber-700',
      slug: 'maison',
    },
    {
      id: 4,
      name: 'Beauté & Soins',
      icon: '💅',
      color: 'bg-pink-100',
      textColor: 'text-pink-700',
      slug: 'beaute',
    },
    {
      id: 5,
      name: 'Sports & Loisirs',
      icon: '⚽',
      color: 'bg-green-100',
      textColor: 'text-green-700',
      slug: 'sports',
    },
    {
      id: 6,
      name: 'Alimentation',
      icon: '🍔',
      color: 'bg-red-100',
      textColor: 'text-red-700',
      slug: 'alimentation',
    },
  ];

  // Utiliser les catégories reçues ou les defaults
  const displayCategories = categories && categories.length > 0 ? categories : defaultCategories;

  return (
    <section className="py-8 px-4 bg-gray-50">
      <div className="max-w-6xl mx-auto">
        <div className="mb-8">
          <h2 className="text-2xl md:text-3xl font-bold text-gray-900">
            Parcourir par catégorie
          </h2>
          <p className="text-gray-600 mt-2">
            Trouvez ce que vous cherchez en quelques clics
          </p>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {displayCategories.map((category) => (
            <Link
              key={category.id}
              to={`/products?category=${category.slug || category.id}`}
              className="group"
            >
              <div className={`${category.color || 'bg-gray-100'} rounded-lg p-4 text-center hover:shadow-lg transition-all duration-300 cursor-pointer transform group-hover:scale-105`}>
                <div className="text-4xl md:text-5xl mb-3 inline-block">
                  {category.icon || '📦'}
                </div>
                <h3
                  className={`font-semibold text-sm md:text-base ${
                    category.textColor || 'text-gray-700'
                  } group-hover:underline`}
                >
                  {category.name || 'Catégorie'}
                </h3>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
};

export default CategoriesGrid;
