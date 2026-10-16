import { useEffect, useMemo, useRef, useState } from 'react';

const fold = (text) => String(text || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

/** Liste de choix avec recherche : on tape « lib », Libreville apparaît. Les options `disabled` restent visibles. */
export default function SearchSelect({ label, placeholder, options, value, onChange, emptyText = 'Aucun résultat' }) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const box = useRef(null);
  const selected = options.find((o) => String(o.value) === String(value));

  useEffect(() => {
    if (!open) return undefined;
    const close = (e) => { if (box.current && !box.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', close);
    document.addEventListener('touchstart', close);
    return () => {
      document.removeEventListener('mousedown', close);
      document.removeEventListener('touchstart', close);
    };
  }, [open]);

  const shown = useMemo(() => {
    const q = fold(query);
    return q ? options.filter((o) => fold(o.label).includes(q)) : options;
  }, [options, query]);

  return (
    <div className="relative w-full min-w-0" ref={box}>
      <button
        type="button"
        className="flex w-full items-center justify-between gap-2 rounded-md border border-gray-200 bg-white px-3 py-2 text-left"
        onClick={() => { setOpen((v) => !v); setQuery(''); }}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className={`min-w-0 truncate ${selected ? 'text-gray-900' : 'text-gray-400'}`}>
          {selected ? selected.label : (placeholder || label)}
        </span>
        <span className="text-gray-400" aria-hidden>▾</span>
      </button>
      {open && (
        <div className="absolute left-0 right-0 z-30 mt-1 rounded-md border border-gray-200 bg-white shadow-lg">
          <input
            autoFocus
            className="w-full border-b border-gray-100 px-3 py-2 outline-none"
            placeholder={`🔎 Rechercher ${label ? label.toLowerCase() : ''}`}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <ul role="listbox" className="max-h-60 overflow-y-auto py-1">
            {shown.length === 0 && <li className="px-3 py-2 text-sm text-gray-500">{emptyText}</li>}
            {shown.map((o) => (
              <li key={o.value}>
                <button
                  type="button"
                  disabled={o.disabled}
                  className={`flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-sm ${
                    o.disabled ? 'cursor-not-allowed text-gray-400' : 'hover:bg-indigo-50'
                  } ${String(o.value) === String(value) ? 'font-semibold text-indigo-700' : ''}`}
                  onClick={() => { if (!o.disabled) { onChange(o.value); setOpen(false); } }}
                >
                  <span className="min-w-0 truncate">{o.label}</span>
                  {o.hint && <span className="shrink-0 text-xs text-gray-400">{o.hint}</span>}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
