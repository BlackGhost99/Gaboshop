// Tailles/pointures et couleurs d'un produit (même découpage que products/options.py côté serveur).
const SEP = /[,;/|\n]+/;
const NUMBER = /^\d+(?:[.,]5)?$/;

export const splitValues = (text) => {
  const values = [];
  String(text || '').split(SEP).forEach((raw) => {
    const part = raw.trim();
    if (!part) return;
    const words = part.split(/\s+/);
    if (words.length > 1 && words.every((w) => NUMBER.test(w) || (w.length <= 4 && w === w.toUpperCase()))) values.push(...words);
    else values.push(part);
  });
  const seen = new Set();
  return values.filter((v) => { const k = v.toLowerCase(); if (seen.has(k)) return false; seen.add(k); return true; });
};

export const productOptions = (product) => {
  const attrs = product?.attributes || {};
  return { size: splitValues(attrs.sizes), color: splitValues(attrs.color) };
};

// Il faut ouvrir la fiche pour choisir avant d'ajouter au panier.
export const needsChoice = (product) => {
  const o = productOptions(product);
  return o.size.length > 1 || o.color.length > 1;
};

// Une seule valeur possible : prise d'office.
export const defaultChoice = (product) => {
  const o = productOptions(product);
  const choice = {};
  if (o.size.length === 1) [choice.size] = o.size;
  if (o.color.length === 1) [choice.color] = o.color;
  return choice;
};

export const describeOptions = (options) => [options?.size && `Taille ${options.size}`, options?.color].filter(Boolean).join(' · ');

// Une ligne du panier = un produit + son choix (la pointure 41 et la 42 sont deux lignes).
export const lineKey = (item) => [item?.id, item?.options?.size || '', item?.options?.color || ''].join('|');
