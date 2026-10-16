import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Link, useLocation } from 'react-router-dom';
import { useNotifications } from '../context/NotificationContext';
import { timeAgo, typeIcon } from '../utils/notificationLabels';

const PREVIEW_COUNT = 8;

export const BellIcon = ({ className = 'h-6 w-6' }) => (
  <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.7"
      d="M15 17h5l-1.4-1.4A2 2 0 0118 14.2V11a6 6 0 10-12 0v3.2a2 2 0 01-.6 1.4L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
    />
  </svg>
);

export const CountBadge = ({ count, className = '' }) => {
  if (!count) return null;
  return (
    <span className={`inline-flex min-w-[1.15rem] items-center justify-center rounded-full bg-red-600 px-1 text-[11px] font-bold leading-[1.15rem] text-white ${className}`}>
      {count > 99 ? '99+' : count}
    </span>
  );
};

// Cloche des en-têtes : un appui ouvre les dernières notifications (feuille en bas sur téléphone).
export default function NotificationBell({ className = '', iconClassName = 'h-6 w-6 text-slate-900' }) {
  const { loggedIn, unread, items, status, ensureLoaded, markAllRead, open: openNotification } = useNotifications();
  const { pathname } = useLocation();
  // La feuille est liée à la page où elle a été ouverte : changer de page la ferme.
  const [openOn, setOpenOn] = useState(null);
  const shown = openOn === pathname;
  const setShown = (value) => setOpenOn((typeof value === 'function' ? value(shown) : value) ? pathname : null);

  useEffect(() => {
    if (!shown) return undefined;
    ensureLoaded();
    const onKey = (event) => { if (event.key === 'Escape') setOpenOn(null); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [shown, ensureLoaded]);

  if (!loggedIn) return null;
  const preview = items.slice(0, PREVIEW_COUNT);

  return (
    <>
      <button
        type="button"
        onClick={() => setShown((value) => !value)}
        className={`relative rounded-full p-2 hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-gray-300 ${className}`}
        aria-label={unread ? `Notifications : ${unread} non lue${unread > 1 ? 's' : ''}` : 'Notifications'}
        aria-haspopup="dialog"
        aria-expanded={shown}
      >
        <BellIcon className={iconClassName} />
        <CountBadge count={unread} className="absolute -right-0.5 -top-0.5" />
      </button>

      {shown && createPortal(
        <div className="fixed inset-0 z-[70]" role="dialog" aria-modal="true" aria-label="Notifications">
          <button
            type="button"
            className="absolute inset-0 h-full w-full cursor-default bg-black/40"
            aria-label="Fermer les notifications"
            onClick={() => setShown(false)}
          />
          <div className="absolute inset-x-0 bottom-0 flex max-h-[85dvh] flex-col rounded-t-2xl bg-white shadow-2xl sm:inset-x-auto sm:bottom-auto sm:right-4 sm:top-16 sm:max-h-[70vh] sm:w-[26rem] sm:rounded-xl sm:border sm:border-gray-100">
            <div className="mx-auto mt-2 h-1 w-10 rounded-full bg-gray-300 sm:hidden" aria-hidden="true" />
            <div className="flex items-center justify-between gap-3 px-4 pb-2 pt-3">
              <div>
                <p className="text-base font-bold text-gray-900">Notifications</p>
                <p className="text-xs text-gray-500">{unread ? `${unread} non lue${unread > 1 ? 's' : ''}` : 'Tout est à jour'}</p>
              </div>
              <div className="flex items-center gap-3">
                {unread > 0 && (
                  <button type="button" onClick={markAllRead} className="text-xs font-semibold text-slate-900 underline-offset-2 hover:underline">
                    Tout marquer lu
                  </button>
                )}
                <button type="button" onClick={() => setShown(false)} aria-label="Fermer" className="rounded-full p-1 text-xl leading-none text-gray-500 hover:bg-gray-100">
                  ×
                </button>
              </div>
            </div>

            <div className="min-h-[6rem] flex-1 divide-y divide-gray-100 overflow-y-auto border-t border-gray-100">
              {status === 'loading' && !preview.length && <p className="p-6 text-center text-sm text-gray-500">Chargement…</p>}
              {status === 'error' && !preview.length && (
                <p className="p-6 text-center text-sm text-gray-500">Impossible de charger vos notifications. Vérifiez votre connexion et rouvrez la cloche.</p>
              )}
              {status === 'ready' && !preview.length && (
                <div className="p-8 text-center">
                  <p className="text-3xl" aria-hidden="true">🔔</p>
                  <p className="mt-2 text-sm font-semibold text-gray-900">Rien de nouveau</p>
                  <p className="mt-1 text-sm text-gray-500">Vos nouvelles de commande, de paiement et de livraison apparaîtront ici.</p>
                </div>
              )}
              {preview.map((notification) => (
                <button
                  key={notification.id}
                  type="button"
                  onClick={() => openNotification(notification)}
                  className={`flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-gray-50 ${notification.is_read ? 'bg-white' : 'bg-indigo-50/60'}`}
                >
                  <span className="mt-0.5 flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-full bg-gray-100 text-lg" aria-hidden="true">
                    {typeIcon(notification)}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-start justify-between gap-2">
                      <span className={`text-sm text-gray-900 ${notification.is_read ? 'font-medium' : 'font-bold'}`}>{notification.title}</span>
                      {!notification.is_read && <span className="mt-1.5 h-2 w-2 flex-shrink-0 rounded-full bg-indigo-600" aria-label="Non lue" />}
                    </span>
                    <span className="mt-0.5 line-clamp-2 block text-sm text-gray-600">{notification.body}</span>
                    <span className="mt-1 flex items-center gap-2 text-xs text-gray-500">
                      <span>{timeAgo(notification.created_at)}</span>
                      {notification.action_label && <span className="font-semibold text-indigo-700">· {notification.action_label}</span>}
                    </span>
                  </span>
                </button>
              ))}
            </div>

            <Link
              to="/notifications"
              onClick={() => setShown(false)}
              className="block border-t border-gray-100 px-4 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] text-center text-sm font-semibold text-slate-900 hover:bg-gray-50"
            >
              Voir toutes mes notifications
            </Link>
          </div>
        </div>,
        document.body,
      )}
    </>
  );
}
