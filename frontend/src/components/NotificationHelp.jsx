import { askAI } from '../utils/feedback';

// Pourquoi et quoi faire, sous le texte d'une notification ; « Demander à l'IA » pour un échec.
export default function NotificationHelp({ notification, onAsk }) {
  const meta = notification?.metadata || {};
  const level = meta.level;
  if (!meta.reason && !meta.next_step) return null;
  const failed = level === 'error' || level === 'warning';
  return (
    <div className={`space-y-2 rounded-lg border p-3 text-sm ${failed ? 'border-red-200 bg-red-50' : 'border-green-200 bg-green-50'}`}>
      {meta.reason && (
        <p className="text-gray-800"><span className="font-semibold">Pourquoi : </span>{meta.reason}</p>
      )}
      {meta.next_step && (
        <p className="text-gray-800"><span className="font-semibold">Que faire : </span>{meta.next_step}</p>
      )}
      {failed && (
        <button
          type="button"
          onClick={() => {
            askAI({ action: notification.title, message: notification.body, reason: meta.reason, nextStep: meta.next_step });
            onAsk?.();
          }}
          className="rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white"
        >
          🤖 Demander à l'IA comment régler ça
        </button>
      )}
    </div>
  );
}
