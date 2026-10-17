import { formatCurrency } from '../../utils/helpers';

/** Choix Standard / Express du panier. Affiché seulement quand le serveur dit que le commerce propose l'express
 *  (quote.express_available) ; les prix viennent du devis, donc le total affiché est le total payé. */
export default function DeliveryTypePicker({ quote = {}, value = 'standard', onChange }) {
  const options = quote.delivery_options || [];
  if (!quote.express_available) return null;
  const known = {
    standard: { label: 'Standard', estimate: '2 à 3 h' },
    express: { label: 'Express', estimate: 'environ 1 h' },
  };
  const list = options.length ? options : Object.keys(known).map((type) => ({ type, ...known[type], fee: null }));
  return (
    <fieldset className="mt-3 rounded-md border border-gray-200 p-3">
      <legend className="px-1 text-xs font-semibold uppercase tracking-wide text-gray-600">Mode de livraison</legend>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {list.map((option) => {
          const selected = (quote.delivery_type || value) === option.type;
          return (
            <label
              key={option.type}
              className={`flex cursor-pointer items-start gap-2 rounded-md border p-2 text-sm ${selected ? 'border-indigo-600 bg-indigo-50' : 'border-gray-200 bg-white'}`}
            >
              <input
                type="radio"
                name="delivery_type"
                className="mt-1"
                checked={selected}
                onChange={() => onChange?.(option.type)}
              />
              <span className="min-w-0">
                <span className="flex flex-wrap items-center gap-2 font-semibold text-gray-900">
                  {option.label}
                  {option.type === 'express' && (
                    <span className="rounded bg-amber-100 px-1.5 py-0.5 text-[11px] font-bold uppercase text-amber-800">Express</span>
                  )}
                </span>
                <span className="block text-xs text-gray-600">
                  Livraison en {option.estimate}{option.fee != null ? ` · ${formatCurrency(Number(option.fee) || 0)}` : ''}
                </span>
              </span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
