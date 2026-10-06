import authStorage from './authStorage';

// Produit choisi par un visiteur avant de se connecter : ajouté au panier au retour.
const PENDING_CART_KEY = 'gaboshop_pending_cart_item';
const CART_KEY = 'gaboshop_cart';

export const isLoggedIn = () => Boolean(authStorage.getItem('token'));

export const logout = (redirectTo = '/') => {
  ['token', 'refresh_token'].forEach((key) => {
    authStorage.removeItem(key);
    try {
      localStorage.removeItem(key);
      sessionStorage.removeItem(key);
    } catch {
      // stockage indisponible
    }
  });
  window.location.href = redirectTo;
};

// Adresse de retour après connexion, limitée au site lui-même.
export const safeNextPath = (search) => {
  const next = new URLSearchParams(search).get('next') || '';
  return next.startsWith('/') && !next.startsWith('//') ? next : null;
};

export const cartItemFromProduct = (product) => ({
  id: product.id,
  name: product.name,
  price: product.price,
  image: product.image,
  weight_kg: product.weight_kg,
  length_m: product.length_m,
  store_name: product.store_name,
  store_id: product.store,
  quantity: 1,
});

export const savePendingCartItem = (product) => {
  try {
    localStorage.setItem(PENDING_CART_KEY, JSON.stringify(cartItemFromProduct(product)));
  } catch {
    // stockage indisponible
  }
};

// Ajoute au panier enregistré le produit choisi avant la connexion.
// Renvoie son nom (pour le message de confirmation) ou null.
export const applyPendingCartItem = () => {
  if (!isLoggedIn()) return null;
  try {
    const raw = localStorage.getItem(PENDING_CART_KEY);
    if (!raw) return null;
    localStorage.removeItem(PENDING_CART_KEY);
    const item = JSON.parse(raw);
    const cart = JSON.parse(localStorage.getItem(CART_KEY) || '[]');
    const existing = cart.find((c) => c.id === item.id);
    if (existing) existing.quantity += 1;
    else cart.push(item);
    localStorage.setItem(CART_KEY, JSON.stringify(cart));
    return item.name;
  } catch {
    return null;
  }
};

// Hors des espaces commerce / livreur / admin, l'IA est un assistant d'achat
// ouvert à tous (même sans compte) qui cherche dans le catalogue.
export const isShoppingRoute = (path) => !/^\/(store|admin|delivery)(\/|$)/.test(path || '');
