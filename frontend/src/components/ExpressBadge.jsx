/** Étiquette « EXPRESS » d'une commande ou d'une livraison express (le client a payé pour une livraison en environ 1 h). */
export default function ExpressBadge({ show = true, className = '' }) {
  if (!show) return null;
  return (
    <span
      title="Livraison express : à servir en priorité"
      className={`inline-flex items-center rounded bg-amber-500 px-1.5 py-0.5 text-[11px] font-bold uppercase tracking-wide text-white ${className}`}
    >
      Express
    </span>
  );
}
