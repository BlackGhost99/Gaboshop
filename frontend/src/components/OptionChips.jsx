import { useState } from 'react';
import { splitValues } from '../utils/productOptions';

/** Choix multiple par boutons (pointures, tailles, couleurs) : plus de liste tapée à la main.
 *  `value` / `onChange` : texte « 40, 41, 42 » (format enregistré). Un choix absent s'ajoute avec « Autre ». */
export default function OptionChips({ label, groups, value, onChange, otherPlaceholder }) {
  const selected = splitValues(value);
  const [group, setGroup] = useState(() => {
    const hit = groups.find((g) => g.values.some((v) => selected.includes(v)));
    return (hit || groups[0]).key;
  });
  const [other, setOther] = useState('');
  const current = groups.find((g) => g.key === group) || groups[0];
  const extra = selected.filter((v) => !groups.some((g) => g.values.includes(v)));
  const emit = (list) => onChange(list.join(', '));
  const toggle = (v) => emit(selected.includes(v) ? selected.filter((x) => x !== v) : [...selected, v]);
  const addOther = () => {
    const added = splitValues(other).filter((v) => !selected.includes(v));
    if (added.length) emit([...selected, ...added]);
    setOther('');
  };

  return (
    <div className="sm:col-span-2">
      <p className="text-sm font-semibold text-gray-700">{label}</p>
      {groups.length > 1 && (
        <div className="mt-1 flex flex-wrap gap-1">
          {groups.map((g) => (
            <button key={g.key} type="button" onClick={() => setGroup(g.key)}
              className={`rounded-full px-3 py-1 text-xs font-semibold ${g.key === group ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-700'}`}>
              {g.label}
            </button>
          ))}
        </div>
      )}
      <div className="mt-2 flex flex-wrap gap-1.5">
        {[...current.values, ...extra].map((v) => {
          const on = selected.includes(v);
          return (
            <button key={v} type="button" onClick={() => toggle(v)} aria-pressed={on}
              className={`min-w-[2.5rem] rounded-md border px-2.5 py-1 text-sm ${on ? 'border-indigo-600 bg-indigo-600 text-white' : 'border-gray-300 bg-white text-gray-800'}`}>
              {v}
            </button>
          );
        })}
      </div>
      <div className="mt-2 flex gap-2">
        <input className="min-w-0 flex-1 rounded-md border border-gray-300 px-3 py-1.5 text-sm" placeholder={otherPlaceholder || 'Autre'}
          value={other} onChange={(e) => setOther(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addOther(); } }} />
        <button type="button" onClick={addOther} className="rounded-md border border-indigo-300 px-3 py-1.5 text-sm font-semibold text-indigo-700">Ajouter</button>
      </div>
      <p className="mt-1 text-xs text-gray-500">
        {selected.length ? `Choisi : ${selected.join(', ')}` : 'Touchez les valeurs disponibles. Le client choisira parmi elles.'}
      </p>
    </div>
  );
}
