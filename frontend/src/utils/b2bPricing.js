// Prix de gros par palier de quantité. Le serveur recalcule toujours le prix à la commande :
// ce calcul ne sert qu'à afficher à l'acheteur ce qu'il va payer.

export const minimumQuantity = (product) =>
  Number(product?.min_quantity || product?.min_order_quantity || product?.b2b_pricings?.[0]?.min_quantity || 1);

export const baseUnitPrice = (product) =>
  Number(product?.b2b_price ?? product?.b2b_pricings?.[0]?.b2b_price ?? product?.price ?? 0);

// Palier atteint par cette quantité : le plus haut dont le seuil est franchi.
export const tierForQuantity = (product, quantity) => {
  const tiers = product?.pricing_tiers;
  if (!Array.isArray(tiers) || tiers.length < 2) return null;
  let reached = null;
  tiers.forEach((tier) => {
    if (Number(quantity) >= Number(tier.min_qty)) reached = tier;
  });
  return reached;
};

export const unitPriceForQuantity = (product, quantity) => {
  const tier = tierForQuantity(product, quantity);
  return tier ? Number(tier.price) : baseUnitPrice(product);
};

// Prochain palier à atteindre (pour inviter à commander un peu plus), ou null.
export const nextTier = (product, quantity) => {
  const tiers = product?.pricing_tiers;
  if (!Array.isArray(tiers) || tiers.length < 2) return null;
  return tiers.find((tier) => Number(tier.min_qty) > Number(quantity)) || null;
};

export const lineTotal = (item) => unitPriceForQuantity(item, item.quantity) * item.quantity;
