import { useEffect, useRef } from 'react';
import { typeIcon } from '../utils/notificationLabels';

const SHOW_MS = 9000;

// Message qui apparaît quand une notification arrive pendant que la personne utilise l'application.
export default function NotificationToast({ notification, onOpen, onClose }) {
  const closeRef = useRef(onClose);
  useEffect(() => { closeRef.current = onClose; });

  useEffect(() => {
    try {
      navigator.vibrate?.(80);
    } catch {
      // vibration non gérée
    }
    const timer = setTimeout(() => closeRef.current(), SHOW_MS);
    return () => clearTimeout(timer);
  }, [notification.id]);

  return (
    <div
      className="pointer-events-none fixed inset-x-0 top-3 z-[999] flex justify-center px-3 sm:justify-end sm:px-6"
      role="status"
      aria-live="polite"
    >
      <div className="notif-toast pointer-events-auto flex w-full max-w-md items-start gap-3 rounded-2xl border border-slate-200 bg-white p-3 shadow-xl">
        <button type="button" onClick={onOpen} className="flex min-w-0 flex-1 items-start gap-3 text-left">
          <span className="mt-0.5 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-slate-100 text-lg" aria-hidden="true">
            {typeIcon(notification)}
          </span>
          <span className="min-w-0 flex-1">
            <span className="block truncate text-sm font-semibold text-slate-900">{notification.title}</span>
            <span className="mt-0.5 line-clamp-2 block text-sm text-slate-600">{notification.body}</span>
            {notification.action_label && (
              <span className="mt-1 inline-block text-xs font-semibold text-indigo-700">{notification.action_label} →</span>
            )}
          </span>
        </button>
        <button type="button" onClick={onClose} aria-label="Fermer" className="px-1 text-xl leading-none text-gray-400 hover:text-gray-600">
          ×
        </button>
      </div>
    </div>
  );
}
