import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import ClientLayout from '../components/ClientLayout';
import StoreLayout from '../components/StoreLayout';
import LoadingSpinner from '../components/LoadingSpinner';
import NotificationHelp from '../components/NotificationHelp';
import { PushPrompt, PushSettingsCard } from '../components/PushControls';
import { useNotifications } from '../context/NotificationContext';
import { getNotificationPreferences, setAnnouncementsPreference } from '../services/notificationService';
import { notifyError, notifySuccess } from '../utils/feedback';
import { ROLE_HOME, useRole } from '../utils/currentUser';
import { FILTERS, dayGroup, statusLabel, timeAgo, typeIcon, typeLabel, typeTone } from '../utils/notificationLabels';
import { formatDateTime } from '../utils/helpers';

const EMPTY_TEXT = {
  all: 'Vos nouvelles de commande, de paiement et de livraison apparaîtront ici.',
  unread: 'Vous avez tout lu. Bravo !',
};

function Detail({ label, children }) {
  return (
    <div className="flex items-baseline justify-between gap-3 text-sm">
      <span className="text-gray-500">{label}</span>
      <span className="text-right font-medium text-gray-900">{children}</span>
    </div>
  );
}

function NotificationCard({ notification, expanded, onToggle, onDelete }) {
  const { open } = useNotifications();
  const [confirming, setConfirming] = useState(false);
  const meta = notification.metadata || {};
  const unread = !notification.is_read;

  return (
    <li id={`notification-${notification.id}`} className={`overflow-hidden rounded-xl border ${unread ? 'border-indigo-200 bg-indigo-50/50' : 'border-gray-200 bg-white'}`}>
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={expanded}
        className="flex w-full items-start gap-3 p-3 text-left sm:p-4"
      >
        <span className={`mt-0.5 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full text-xl ${typeTone(notification)}`} aria-hidden="true">
          {typeIcon(notification)}
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex items-start justify-between gap-2">
            <span className={`text-sm text-gray-900 sm:text-base ${unread ? 'font-bold' : 'font-medium'}`}>{notification.title}</span>
            {unread && <span className="mt-1.5 h-2.5 w-2.5 flex-shrink-0 rounded-full bg-indigo-600" aria-label="Non lue" />}
          </span>
          <span className={`mt-0.5 block whitespace-pre-line text-sm text-gray-600 ${expanded ? '' : 'line-clamp-2'}`}>{notification.body}</span>
          <span className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-gray-500">
            <span>{timeAgo(notification.created_at)}</span>
            <span aria-hidden="true">·</span>
            <span>{typeLabel(notification)}</span>
            {notification.order_number && (<><span aria-hidden="true">·</span><span className="font-mono">{notification.order_number}</span></>)}
          </span>
        </span>
      </button>

      {expanded && (
        <div className="space-y-3 border-t border-gray-100 px-3 pb-3 pt-3 sm:px-4 sm:pb-4">
          <NotificationHelp notification={notification} />

          {(meta.from || meta.to || meta.amount || meta.distance) && (
            <div className="space-y-1 rounded-lg bg-gray-50 p-3">
              {meta.from && <Detail label="Ancien statut">{statusLabel(meta.from)}</Detail>}
              {meta.to && <Detail label="Nouveau statut">{statusLabel(meta.to)}</Detail>}
              {meta.amount && <Detail label="Montant">{meta.amount}</Detail>}
              {meta.distance && <Detail label="Distance">{meta.distance}</Detail>}
            </div>
          )}

          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <span className="hidden text-xs text-gray-500 sm:inline">{formatDateTime(notification.created_at)}</span>
            <div className="flex flex-col-reverse gap-2 sm:flex-row sm:items-center">
              {confirming ? (
                <div className="flex items-center justify-end gap-2">
                  <span className="text-xs text-gray-600">Supprimer ?</span>
                  <button type="button" onClick={onDelete} className="rounded-lg bg-red-600 px-3 py-2 text-xs font-semibold text-white">Oui</button>
                  <button type="button" onClick={() => setConfirming(false)} className="rounded-lg border border-gray-300 px-3 py-2 text-xs font-semibold text-gray-700">Non</button>
                </div>
              ) : (
                <button type="button" onClick={() => setConfirming(true)} className="rounded-lg px-3 py-2 text-xs font-semibold text-red-600 hover:bg-red-50">
                  Supprimer
                </button>
              )}
              {notification.link && !confirming && (
                <button type="button" onClick={() => open(notification)} className="w-full rounded-lg bg-slate-900 px-4 py-3 text-sm font-semibold text-white sm:w-auto sm:py-2">
                  {notification.action_label || 'Ouvrir'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </li>
  );
}

function AnnouncementsSwitch() {
  const [enabled, setEnabled] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    getNotificationPreferences()
      .then((prefs) => { if (active) setEnabled(prefs.announcements !== false); })
      .catch(() => { if (active) setEnabled(null); });
    return () => { active = false; };
  }, []);

  if (enabled === null) return null;

  const toggle = async () => {
    setBusy(true);
    try {
      const prefs = await setAnnouncementsPreference(!enabled);
      setEnabled(prefs.announcements !== false);
      notifySuccess(
        prefs.announcements === false ? 'Annonces coupées' : 'Annonces activées',
        prefs.announcements === false
          ? 'Vous ne recevrez plus les annonces de Gaboshop. Les alertes de vos commandes continuent.'
          : 'Vous recevrez de nouveau les annonces et bons plans de Gaboshop.',
      );
    } catch (error) {
      notifyError(error, { action: 'Changer mes réglages d’annonces' });
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="mb-4 flex items-center justify-between gap-4 rounded-xl border border-gray-200 bg-white p-4">
      <div className="min-w-0">
        <p className="text-sm font-bold text-gray-900">Annonces et bons plans</p>
        <p className="mt-0.5 text-sm text-gray-600">
          Nouveautés et offres de Gaboshop. Les alertes de vos commandes, paiements et livraisons ne peuvent pas être coupées.
        </p>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={enabled}
        aria-label="Recevoir les annonces"
        onClick={toggle}
        disabled={busy}
        className={`relative inline-flex h-7 w-12 flex-shrink-0 items-center rounded-full transition-colors disabled:opacity-60 ${enabled ? 'bg-green-500' : 'bg-gray-300'}`}
      >
        <span className={`inline-block h-5 w-5 transform rounded-full bg-white shadow transition-transform ${enabled ? 'translate-x-6' : 'translate-x-1'}`} />
      </button>
    </section>
  );
}

function Inbox() {
  const { items, status, hasMore, unread, reload, loadMore, markRead, markAllRead, remove } = useNotifications();
  const [params] = useSearchParams();
  const openId = Number(params.get('open')) || null;
  const [filter, setFilter] = useState('all');
  const [chosenId, setChosenId] = useState(undefined); // undefined : on suit l'adresse (?open=…)
  const [loadingMore, setLoadingMore] = useState(false);
  const applied = useRef(null);

  useEffect(() => { reload(); }, [reload]);

  const expandedId = chosenId === undefined ? (items.some((n) => n.id === openId) ? openId : null) : chosenId;

  // Lit la notification demandée par l'adresse (?open=12) et l'amène à l'écran.
  useEffect(() => {
    if (!openId || applied.current === openId) return;
    const target = items.find((n) => n.id === openId);
    if (!target) return;
    applied.current = openId;
    if (!target.is_read) markRead(openId);
    requestAnimationFrame(() => document.getElementById(`notification-${openId}`)?.scrollIntoView({ block: 'center', behavior: 'smooth' }));
  }, [openId, items, markRead]);

  const visible = useMemo(() => items.filter((n) => {
    if (filter === 'all') return true;
    if (filter === 'unread') return !n.is_read;
    return n.notif_type === filter;
  }), [items, filter]);

  const groups = useMemo(() => {
    const result = [];
    visible.forEach((n) => {
      const label = dayGroup(n.created_at);
      const last = result[result.length - 1];
      if (last && last.label === label) last.rows.push(n);
      else result.push({ label, rows: [n] });
    });
    return result;
  }, [visible]);

  const toggle = (notification) => {
    const opening = expandedId !== notification.id;
    setChosenId(opening ? notification.id : null);
    if (opening && !notification.is_read) markRead(notification.id);
  };

  const more = useCallback(async () => {
    setLoadingMore(true);
    await loadMore();
    setLoadingMore(false);
  }, [loadMore]);

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-3 flex items-center justify-between gap-3">
        <p className="text-sm text-gray-600">{unread ? `${unread} non lue${unread > 1 ? 's' : ''}` : 'Tout est à jour'}</p>
        {unread > 0 && (
          <button type="button" onClick={markAllRead} className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-xs font-semibold text-gray-800 hover:bg-gray-50">
            Tout marquer lu
          </button>
        )}
      </div>

      <div className="-mx-4 mb-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:px-0" role="tablist" aria-label="Filtrer les notifications">
        {FILTERS.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={filter === item.id}
            onClick={() => setFilter(item.id)}
            className={`whitespace-nowrap rounded-full px-4 py-2 text-sm font-semibold ${filter === item.id ? 'bg-slate-900 text-white' : 'border border-gray-300 bg-white text-gray-700'}`}
          >
            {item.label}
          </button>
        ))}
      </div>

      {status === 'loading' && !items.length && <LoadingSpinner />}
      {status === 'error' && !items.length && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-800">
          <p className="font-semibold">Vos notifications n’ont pas pu être chargées.</p>
          <p className="mt-1">Vérifiez votre connexion puis réessayez.</p>
          <button type="button" onClick={reload} className="mt-2 rounded-lg bg-red-700 px-3 py-2 text-xs font-semibold text-white">Réessayer</button>
        </div>
      )}

      {status === 'ready' && !visible.length && (
        <div className="rounded-xl border border-dashed border-gray-300 bg-white p-8 text-center">
          <p className="text-3xl" aria-hidden="true">🔔</p>
          <p className="mt-2 text-sm font-semibold text-gray-900">{filter === 'all' ? 'Rien pour le moment' : 'Aucune notification ici'}</p>
          <p className="mt-1 text-sm text-gray-500">{EMPTY_TEXT[filter] || 'Rien dans cette catégorie pour le moment.'}</p>
        </div>
      )}

      {groups.map((group) => (
        <section key={group.label} className="mb-5">
          <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-gray-500">{group.label}</h3>
          <ul className="space-y-2">
            {group.rows.map((notification) => (
              <NotificationCard
                key={notification.id}
                notification={notification}
                expanded={expandedId === notification.id}
                onToggle={() => toggle(notification)}
                onDelete={() => { remove(notification.id); setChosenId(null); }}
              />
            ))}
          </ul>
        </section>
      ))}

      {hasMore && (
        <button type="button" onClick={more} disabled={loadingMore} className="mb-6 w-full rounded-xl border border-gray-300 bg-white py-3 text-sm font-semibold text-gray-800 hover:bg-gray-50 disabled:opacity-60">
          {loadingMore ? 'Chargement…' : 'Voir les plus anciennes'}
        </button>
      )}

      <details className="mb-6 rounded-xl border border-gray-200 bg-white" open={params.get('reglages') === '1'}>
        <summary className="cursor-pointer select-none px-4 py-3 text-sm font-bold text-gray-900">⚙️ Réglages des alertes</summary>
        <div className="border-t border-gray-100 p-3">
          <PushSettingsCard />
          <AnnouncementsSwitch />
        </div>
      </details>
    </div>
  );
}

// Livreur et administrateur n'ont pas de menu latéral commun : un en-tête simple avec retour.
function PlainShell({ role, children }) {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen bg-gray-100">
      <header className="sticky top-0 z-30 flex items-center gap-3 border-b border-gray-200 bg-white px-4 py-3">
        <button
          type="button"
          onClick={() => (window.history.length > 1 ? navigate(-1) : navigate(ROLE_HOME[role] || '/dashboard'))}
          className="rounded-full p-2 text-xl leading-none hover:bg-gray-100"
          aria-label="Retour"
        >
          ←
        </button>
        <h1 className="flex-1 text-lg font-bold text-gray-900">Notifications</h1>
        <Link to={ROLE_HOME[role] || '/dashboard'} className="text-sm font-semibold text-slate-900 underline-offset-2 hover:underline">Mon espace</Link>
      </header>
      <main className="px-4 py-4 sm:px-6">
        <div className="mx-auto max-w-2xl"><PushPrompt role={role} /></div>
        {children}
      </main>
    </div>
  );
}

export default function Notifications() {
  const role = useRole();
  if (!role) return <LoadingSpinner />;
  if (role === 'client') return <ClientLayout title="Notifications"><Inbox /></ClientLayout>;
  if (role === 'store_manager') return <StoreLayout title="Notifications"><Inbox /></StoreLayout>;
  return <PlainShell role={role}><Inbox /></PlainShell>;
}
