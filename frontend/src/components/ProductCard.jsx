import React from 'react';
import { Link } from 'react-router-dom';
import { formatCurrency } from '../utils/helpers';

/**
 * Carte produit mobile-first
 * Design moderne avec actions rapides
 */
const ProductCard = ({ product, onAddToCart, onViewDetails }) => {
  if (!product) return null;

  const discount = product.discount || 0;
  const finalPrice = product.price * (1 - discount / 100);

  return (
    <div className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow overflow-hidden group">
      {/* Image Container */}
      <div className="relative overflow-hidden bg-gray-200 aspect-square">
        <img
          src={product.image || '/placeholder.png'}
          alt={product.name}
          className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-300"
          onError={(e) => {
            e.target.src = '/placeholder.png';
          }}
        />

        {/* Badge */}
        {discount > 0 && (
          <div className="absolute top-3 right-3 bg-cta-600 text-white px-3 py-1 rounded-full text-xs font-bold">
            -{discount}%
          </div>
        )}

        {/* Quick Actions */}
        <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
          <button
            onClick={(e) => {
              e.preventDefault();
              onViewDetails?.(product);
            }}
            className="p-2 bg-white rounded-full hover:bg-gray-100 transition-colors"
            title="Voir détails"
          >
            <svg className="w-5 h-5 text-gray-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
              />
            </svg>
          </button>
          <button
            onClick={(e) => {
              e.preventDefault();
              onAddToCart?.(product);
            }}
            className="p-2 bg-cta-600 rounded-full hover:bg-cta-700 transition-colors text-white"
            title="Ajouter au panier"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 4v16m8-8H4"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Store Name */}
        {product.store_name && (
          <p className="text-xs text-gray-500 font-medium mb-1">
            {product.store_name}
          </p>
        )}

        {/* Product Name */}
        <h3 className="font-semibold text-sm text-gray-900 line-clamp-2 mb-2">
          {product.name}
        </h3>

        {/* Rating */}
        {product.rating !== undefined && (
          <div className="flex items-center gap-1 mb-2">
            <div className="flex items-center">
              {[...Array(5)].map((_, i) => (
                <svg
                  key={i}
                  className={`w-3 h-3 ${
                    i < Math.floor(product.rating)
                      ? 'text-amber-400'
                      : 'text-gray-300'
                  }`}
                  fill="currentColor"
                  viewBox="0 0 20 20"
                >
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
              ))}
            </div>
            <span className="text-xs text-gray-600">
              ({product.reviews_count || 0})
            </span>
          </div>
        )}

        {/* Pricing */}
        <div className="flex items-baseline gap-2 mb-3">
          <span className="text-lg font-bold text-primary-600">
            {formatCurrency(finalPrice)}
          </span>
          {discount > 0 && (
            <span className="text-sm text-gray-500 line-through">
              {formatCurrency(product.price)}
            </span>
          )}
        </div>

        {/* CTA */}
        <button
          onClick={() => onAddToCart?.(product)}
          className="w-full py-2 bg-cta-600 text-white font-semibold rounded-lg hover:bg-cta-700 transition-colors text-sm"
        >
          Ajouter au panier
        </button>
      </div>
    </div>
  );
};

export default ProductCard;
