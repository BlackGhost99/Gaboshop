import { useEffect, useState } from 'react';
import { askAI, onFeedback } from '../utils/feedback';

const STYLES = {
  success: { box: 'border-green-200 bg-green-50', title: 'text-green-900', icon: '✓', iconBox: 'bg-green-600' },
  error: { box: 'border-red-200 bg-red-50', title: 'text-red-900', icon: '!', iconBox: 'bg-red-600' },
  warning: { box: 'border-amber-200 bg-amber-50', title: 'text-amber-900', icon: '!', iconBox: 'bg-amber-500' },
  info: { box: 'border-slate-200 bg-white', title: 'text-slate-900', icon: 'i', iconBox: 'bg-slate-700' },
};
const AUTO_CLOSE_MS = { success: 6000, info: 6000, warning: 9000 };

// Affiche les messages de l'application (réussites détaillées, échecs expliqués).
// Un échec reste affiché jusqu'à ce que la personne le ferme ou demande de l'aide à l'IA.
export default function FeedbackCenter() {
  const [items, setItems] = useState([]);

  useEffect(() => onFeedback((item) => {
    setItems((prev) => [...prev.slice(-2), item]);
    const delay = AUTO_CLOSE_MS[item.level];
    if (delay) setTimeout(() => setItems((prev) => prev.filter((i) => i.id !== item.id)), delay);
  }), []);

  const close = (id) => setItems((prev) => prev.filter((i) => i.id !== id));

  if (!items.length) return null;
  return (
    <div className="pointer-events-none fixed inset-x-0 top-3 z-[1000] flex flex-col items-center gap-2 px-4" role="status" aria-live="polite">
      {items.map((item) => {
        const style = STYLES[item.level] || STYLES.info;
        return (
          <div key={item.id} className={`pointer-events-auto w-full max-w-md rounded-xl border p-3 shadow-lg ${style.box}`}>
            <div className="flex items-start gap-3">
              <span className={`mt-0.5 flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full text-sm font-bold text-white ${style.iconBox}`}>
                {style.icon}
              </span>
              <div className="min-w-0 flex-1 text-sm">
                <p className={`font-semibold ${style.title}`}>{item.title}</p>
                {item.message && <p className="mt-0.5 text-gray-800">{item.message}</p>}
                {item.reason && (
                  <p className="mt-1 text-gray-700"><span className="font-semibold">Pourquoi : </span>{item.reason}</p>
                )}
                {item.nextStep && (
                  <p className="mt-1 text-gray-700"><span className="font-semibold">Que faire : </span>{item.nextStep}</p>
                )}
                {item.level === 'error' && (
                  <button
                    type="button"
                    onClick={() => { askAI(item); close(item.id); }}
                    className="mt-2 rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white"
                  >
                    🤖 Demander à l'IA comment régler ça
                  </button>
                )}
              </div>
              <button type="button" onClick={() => close(item.id)} aria-label="Fermer" className="text-lg leading-none text-gray-500">
                ×
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
