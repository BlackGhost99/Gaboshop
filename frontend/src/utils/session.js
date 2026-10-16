import { lineKey } from './productOptions';
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
  // Appareil partagé : le panier et le dernier message d'erreur ne restent pas pour la personne suivante.
  [CART_KEY, PENDING_CART_KEY, 'last_api_error'].forEach((key) => {
    try {
      localStorage.removeItem(key);
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
  attributes: product.attributes || {},
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

export const savePendingCartItem = (product, options = null) => {
  try {
    const item = cartItemFromProduct(product);
    if (options && Object.keys(options).length) item.options = options;
    localStorage.setItem(PENDING_CART_KEY, JSON.stringify(item));
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
    const existing = cart.find((c) => lineKey(c) === lineKey(item));
    if (existing) existing.quantity += 1;
    else cart.push(item);
    localStorage.setItem(CART_KEY, JSON.stringify(cart));
    window.dispatchEvent(new Event('gaboshop:cart-updated'));
    return item.name;
  } catch {
    return null;
  }
};

// Hors des espaces commerce / livreur / admin, l'IA est un assistant d'achat
// ouvert à tous (même sans compte) qui cherche dans le catalogue.
export const isShoppingRoute = (path) => !/^\/(store|admin|delivery)(\/|$)/.test(path || '');

// Panier enregistré sur l'appareil, partagé par l'accueil, la page commerce,
// l'espace client et l'assistant. Chaque changement prévient les pages ouvertes.
export const CART_EVENT = 'gaboshop:cart-updated';

export const readCart = () => {
  try {
    return JSON.parse(localStorage.getItem(CART_KEY) || '[]');
  } catch {
    return [];
  }
};

const writeCart = (cart) => {
  try {
    localStorage.setItem(CART_KEY, JSON.stringify(cart));
  } catch {
    // stockage indisponible
  }
  window.dispatchEvent(new Event(CART_EVENT));
};

// `options` : { size, color } choisis par le client ; une pointure différente fait une ligne à part.
export const addToCart = (product, quantity = 1, options = null) => {
  const cart = readCart();
  const qty = Math.max(1, Number(quantity) || 1);
  const chosen = options && typeof options === 'object' ? options : (options ? { size: options } : {});
  const item = { ...cartItemFromProduct(product), quantity: qty, ...(Object.keys(chosen).length ? { options: chosen } : {}) };
  const existing = cart.find((line) => lineKey(line) === lineKey(item));
  if (existing) existing.quantity = (Number(existing.quantity) || 0) + qty;
  else cart.push(item);
  writeCart(cart);
};

export const removeFromCart = (productId) => {
  writeCart(readCart().filter((item) => item.id !== productId));
};
