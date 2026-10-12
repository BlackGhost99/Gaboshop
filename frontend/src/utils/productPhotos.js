export const MAX_EXTRA_PHOTOS = 5;

/** Autres photos déjà enregistrées : anciens champs image_2 / image_3 puis la galerie. */
export function extraPhotos(product) {
  if (!product) return [];
  const legacy = ['image_2', 'image_3'].filter((k) => product[k]).map((k) => ({ key: k, src: product[k] }));
  const gallery = (product.images || []).map((img) => ({ key: String(img.id), src: img.image_url || img.image }));
  return [...legacy, ...gallery];
}

/** Toutes les photos d'un produit, la principale en premier. */
export function allPhotos(product) {
  if (!product) return [];
  return [product.image, ...extraPhotos(product).map((p) => p.src)].filter(Boolean);
}
