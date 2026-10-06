import React, { useEffect, useState } from 'react';
import { getProductDetails } from '../services/productService';
import { formatCurrency } from '../utils/helpers';

/**
 * Fiche produit complète pour le client : photos, prix, stock,
 * caractéristiques (marque, tailles, poids...) et description.
 * Reçoit le produit de la liste puis charge le détail complet.
 * Monter avec key={product.id} pour repartir de zéro à chaque produit.
 */

const formatWeight = (kg) => {
  const n = Number(kg);
  if (!n || n <= 0) return null;
  if (n < 1) return `${Math.round(n * 1000)} g`;
  return `${Number(n.toFixed(2))} kg`;
};

const formatLength = (m) => {
  const n = Number(m);
  if (!n || n <= 0) return null;
  if (n < 1) return `${Math.round(n * 100)} cm`;
  return `${Number(n.toFixed(2))} m`;
};

const splitList = (value) =>
  String(value || '')
    .split(/[,;/]+/)
    .map((s) => s.trim())
    .filter(Boolean);

const ProductDetailModal = ({ product, onClose, onAddToCart }) => {
  const [details, setDetails] = useState(product);
  const [loadingDetails, setLoadingDetails] = useState(true);
  const [activeImage, setActiveImage] = useState(0);

  useEffect(() => {
    if (!product?.id) return undefined;
    let active = true;
    getProductDetails(product.id)
      .then((res) => {
        const data = res?.data || res;
        if (active && data && data.id) setDetails({ ...product, ...data });
      })
      .catch(() => {})
      .finally(() => {
        if (active) setLoadingDetails(false);
      });
    return () => {
      active = false;
    };
  }, [product]);

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose?.();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const p = details || {};
  const attrs = p.attributes || {};

  if (!product) return null;

  const images = [
    ...new Set(
      [p.image, p.image_2, p.image_3, ...(p.images || []).map((i) => i.image_url || i.image)].filter(Boolean)
    ),
  ];

  const sizes = splitList(attrs.sizes);
  const variants = (p.variants || []).filter((v) => v && v.name);
  const stock = Number(p.stock);
  const hasStockInfo = p.stock !== undefined && p.stock !== null && !Number.isNaN(stock);
  const outOfStock = hasStockInfo && stock <= 0;

  const specs = [
    ['Marque', attrs.brand],
    ['Modèle', attrs.model],
    ['Couleur', attrs.color],
    ['Catégorie', p.category_name],
    ['Poids', formatWeight(p.weight_kg)],
    ['Longueur / taille du colis', formatLength(p.length_m)],
    ['Référence', p.sku],
  ].filter(([, v]) => v);

  const currentImage = images[activeImage] || images[0];

  return (
    <div
      className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-end sm:items-center justify-center z-[60] sm:px-4"
      onClick={onClose}
    >
      <div
        className="bg-white w-full sm:max-w-3xl rounded-t-2xl sm:rounded-2xl shadow-2xl max-h-[92dvh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label={p.name}
      >
        <div className="overflow-y-auto flex-1">
          <div className="flex flex-col md:flex-row">
            {/* Photos */}
            <div className="md:w-1/2 bg-gray-100">
              <div className="relative aspect-[4/3] md:aspect-square">
                {currentImage ? (
                  <img
                    src={currentImage}
                    alt={p.name}
                    className="w-full h-full object-contain bg-white"
                    onError={(e) => { e.currentTarget.src = '/placeholder.svg'; }}
                  />
                ) : (
                  <img src="/placeholder.svg" alt="" className="w-full h-full object-cover" />
                )}
                {p.has_discount && (
                  <span className="absolute top-3 left-3 bg-red-500 text-white text-xs font-bold px-3 py-1 rounded-full">
                    -{p.discount_percentage}%
                  </span>
                )}
                <button
                  onClick={onClose}
                  className="absolute top-3 right-3 bg-white/90 rounded-full p-2 shadow text-gray-700"
                  aria-label="Fermer"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              {images.length > 1 && (
                <div className="flex gap-2 p-3 overflow-x-auto bg-white">
                  {images.map((src, i) => (
                    <button
                      key={src}
                      onClick={() => setActiveImage(i)}
                      className={`w-16 h-16 flex-shrink-0 rounded-lg overflow-hidden border-2 ${i === activeImage ? 'border-indigo-600' : 'border-transparent'}`}
                      aria-label={`Photo ${i + 1}`}
                    >
                      <img
                        src={src}
                        alt=""
                        className="w-full h-full object-cover"
                        onError={(e) => { e.currentTarget.src = '/placeholder.svg'; }}
                      />
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Infos */}
            <div className="md:w-1/2 p-5 flex flex-col gap-4">
              <div>
                <p className="text-xs font-semibold text-indigo-600 uppercase tracking-wide">
                  {p.store_name}
                  {p.store_zone ? <span className="text-gray-500 normal-case font-normal"> · {p.store_zone}</span> : null}
                </p>
                <h3 className="text-xl sm:text-2xl font-bold text-gray-900 leading-tight">{p.name}</h3>
              </div>

              <div className="flex items-center gap-3 flex-wrap">
                <span className="text-2xl font-bold text-gray-900">{formatCurrency(p.price)}</span>
                {p.has_discount && (
                  <span className="text-sm text-gray-400 line-through">{formatCurrency(p.compare_price)}</span>
                )}
              </div>

              {hasStockInfo && (
                <p className={`text-sm font-medium ${outOfStock ? 'text-red-600' : 'text-green-700'}`}>
                  {outOfStock ? 'Rupture de stock' : stock <= 5 ? `Plus que ${stock} en stock` : 'En stock'}
                </p>
              )}

              {sizes.length > 0 && (
                <div>
                  <p className="text-sm font-semibold text-gray-900 mb-2">Tailles / pointures disponibles</p>
                  <div className="flex flex-wrap gap-2">
                    {sizes.map((s) => (
                      <span key={s} className="px-3 py-1 rounded-lg border border-gray-300 text-sm text-gray-800">{s}</span>
                    ))}
                  </div>
                </div>
              )}

              {variants.length > 0 && (
                <div>
                  <p className="text-sm font-semibold text-gray-900 mb-2">Variantes</p>
                  <div className="flex flex-wrap gap-2">
                    {variants.map((v) => (
                      <span key={v.id || v.name} className="px-3 py-1 rounded-lg bg-gray-100 text-sm text-gray-800">
                        {v.name}{v.price ? ` · ${formatCurrency(v.price)}` : ''}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {specs.length > 0 && (
                <div>
                  <p className="text-sm font-semibold text-gray-900 mb-2">Caractéristiques</p>
                  <dl className="divide-y divide-gray-100 border border-gray-100 rounded-lg text-sm">
                    {specs.map(([label, value]) => (
                      <div key={label} className="flex justify-between gap-3 px-3 py-2">
                        <dt className="text-gray-500">{label}</dt>
                        <dd className="text-gray-900 font-medium text-right">{value}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              )}

              <div>
                <p className="text-sm font-semibold text-gray-900 mb-1">Description</p>
                <p className="text-gray-600 text-sm leading-relaxed whitespace-pre-line">
                  {p.description || "Le commerçant n'a pas encore ajouté de description."}
                </p>
              </div>

              {loadingDetails && <p className="text-xs text-gray-400">Chargement des détails…</p>}
            </div>
          </div>
        </div>

        {/* Boutons toujours visibles */}
        <div className="border-t border-gray-100 bg-white p-3 flex gap-3" style={{ paddingBottom: 'max(0.75rem, env(safe-area-inset-bottom))' }}>
          <button
            onClick={() => onAddToCart?.(p)}
            disabled={outOfStock}
            className="flex-1 inline-flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-300 text-white px-4 py-3 rounded-lg shadow"
          >
            {outOfStock ? 'Indisponible' : 'Ajouter au panier'}
          </button>
          <button
            onClick={onClose}
            className="inline-flex items-center justify-center px-4 py-3 rounded-lg border border-gray-200 text-gray-700 hover:bg-gray-50"
          >
            Fermer
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProductDetailModal;
