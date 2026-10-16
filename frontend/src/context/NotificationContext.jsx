import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import authStorage from '../utils/authStorage';
import useVisibleInterval from '../hooks/useVisibleInterval';
import {
  deleteNotification,
  fetchNotifications,
  fetchUnreadCount,
  markAllNotificationsRead,
  markNotificationRead,
} from '../services/notificationService';
import { getPushState, syncPush } from '../utils/push';
import NotificationToast from '../components/NotificationToast';

// Une seule source pour la cloche, la boîte de réception, la barre du bas et les alertes à l'écran :
// le compteur se met à jour partout en même temps.

const POLL_MS = 20000;
const PAGE_SIZE = 30;

const NotificationContext = createContext(null);

const BASE_TITLE_PATTERN = /^\(\d+\+?\)\s*/;

export function NotificationProvider({ children }) {
  const location = useLocation();
  const navigate = useNavigate();
  const token = authStorage.getItem('token');
  const loggedIn = Boolean(token);

  const [unread, setUnread] = useState(0);
  const [items, setItems] = useState([]);
  const [hasMore, setHasMore] = useState(false);
  const [status, setStatus] = useState('idle'); // idle | loading | ready | error
  const [toast, setToast] = useState(null);

  const latestSeen = useRef(null);
  const loaded = useRef(false);
  const alertsOn = useRef(false);
  const itemsRef = useRef([]);
  useEffect(() => { itemsRef.current = items; }, [items]);

  const reset = useCallback(() => {
    setUnread(0);
    setItems([]);
    setHasMore(false);
    setStatus('idle');
    setToast(null);
    latestSeen.current = null;
    loaded.current = false;
  }, []);

  const reload = useCallback(async () => {
    if (!authStorage.getItem('token')) return;
    setStatus((current) => (current === 'ready' ? current : 'loading'));
    try {
      const res = await fetchNotifications({ limit: PAGE_SIZE });
      const rows = Array.isArray(res?.data) ? res.data : [];
      setItems(rows);
      setHasMore(Boolean(res?.has_more));
      if (typeof res?.unread_count === 'number') setUnread(res.unread_count);
      if (rows.length) latestSeen.current = Math.max(latestSeen.current || 0, rows[0].id);
      loaded.current = true;
      setStatus('ready');
    } catch {
      setStatus((current) => (current === 'ready' ? current : 'error'));
    }
  }, []);

  const ensureLoaded = useCallback(() => {
    if (!loaded.current) reload();
  }, [reload]);

  const loadMore = useCallback(async () => {
    const oldest = itemsRef.current[itemsRef.current.length - 1];
    if (!oldest) return;
    try {
      const res = await fetchNotifications({ limit: PAGE_SIZE, before: oldest.id });
      const rows = Array.isArray(res?.data) ? res.data : [];
      setItems((current) => {
        const known = new Set(current.map((n) => n.id));
        return [...current, ...rows.filter((n) => !known.has(n.id))];
      });
      setHasMore(Boolean(res?.has_more));
    } catch {
      // la page suivante se redemande au prochain appui
    }
  }, []);

  // Regarde s'il y a du nouveau (appel léger). Une nouvelle notification s'ajoute en haut et s'annonce à l'écran.
  const poll = useCallback(async () => {
    if (!authStorage.getItem('token')) return;
    try {
      const { unread_count: count = 0, latest_id: latest = 0 } = await fetchUnreadCount();
      setUnread(count);
      const previous = latestSeen.current;
      latestSeen.current = Math.max(previous || 0, latest);
      if (previous === null || latest <= previous) return;

      const res = await fetchNotifications({ limit: 5 });
      const fresh = (Array.isArray(res?.data) ? res.data : []).filter((n) => n.id > previous);
      if (!fresh.length) return;
      if (loaded.current) {
        setItems((current) => {
          const known = new Set(current.map((n) => n.id));
          return [...fresh.filter((n) => !known.has(n.id)), ...current];
        });
      }
      const newest = fresh.find((n) => !n.is_read);
      // Si les alertes de l'appareil sont activées, le système les affiche déjà : pas de double message.
      if (newest && !alertsOn.current && !document.hidden) setToast(newest);
    } catch {
      // réseau coupé : on réessaie au prochain passage
    }
  }, []);

  useVisibleInterval(poll, POLL_MS, loggedIn);

  // Connexion, changement de compte ou déconnexion.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    reset();
    if (!token) return undefined;
    let active = true;
    getPushState().then((state) => {
      if (!active) return;
      alertsOn.current = state.permission === 'granted' && state.subscribed;
      // Appareil déjà autorisé : on rattache ses alertes à ce compte (autre compte, clé renouvelée…).
      if (state.permission === 'granted') {
        syncPush().then((ok) => { if (active && ok) alertsOn.current = true; });
      }
    });
    return () => { active = false; };
  }, [token, reset]);

  // Un changement de page est un bon moment pour rafraîchir le compteur.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (token) poll();
  }, [location.pathname, token, poll]);

  // Le service des alertes prévient la page : une alerte arrive, ou une alerte touchée demande d'ouvrir une page.
  useEffect(() => {
    if (!('serviceWorker' in navigator)) return undefined;
    const onMessage = (event) => {
      const data = event.data || {};
      if (data.type === 'gaboshop-push') {
        poll();
        if (loaded.current) reload();
      } else if (data.type === 'gaboshop-open' && typeof data.path === 'string' && data.path.startsWith('/')) {
        navigate(data.path);
      }
    };
    navigator.serviceWorker.addEventListener('message', onMessage);
    return () => navigator.serviceWorker.removeEventListener('message', onMessage);
  }, [poll, reload, navigate]);

  // Pastille sur l'onglet et sur l'icône de l'application.
  useEffect(() => {
    const count = loggedIn ? unread : 0;
    const clean = document.title.replace(BASE_TITLE_PATTERN, '');
    document.title = count > 0 ? `(${count > 99 ? '99+' : count}) ${clean}` : clean;
    try {
      if (count > 0) navigator.setAppBadge?.(count);
      else navigator.clearAppBadge?.();
    } catch {
      // pastille non gérée par ce navigateur
    }
  }, [unread, loggedIn, location.pathname]);

  const markRead = useCallback(async (id) => {
    const target = itemsRef.current.find((n) => n.id === id);
    if (target && target.is_read) return;
    const now = new Date().toISOString();
    setItems((current) => current.map((n) => (n.id === id ? { ...n, is_read: true, read_at: now } : n)));
    setUnread((count) => Math.max(0, count - 1));
    try {
      await markNotificationRead(id);
    } catch {
      poll(); // la prochaine lecture du compteur remet les choses d'aplomb
    }
  }, [poll]);

  const markAllRead = useCallback(async () => {
    const now = new Date().toISOString();
    setItems((current) => current.map((n) => (n.is_read ? n : { ...n, is_read: true, read_at: now })));
    setUnread(0);
    try {
      await markAllNotificationsRead();
    } catch {
      poll();
    }
  }, [poll]);

  const remove = useCallback(async (id) => {
    const target = itemsRef.current.find((n) => n.id === id);
    setItems((current) => current.filter((n) => n.id !== id));
    if (target && !target.is_read) setUnread((count) => Math.max(0, count - 1));
    try {
      await deleteNotification(id);
    } catch {
      reload();
    }
  }, [reload]);

  // Ouvre une notification : elle passe en « lue », puis on va là où elle mène (ou on la lit dans la boîte).
  const open = useCallback((notification) => {
    markRead(notification.id);
    setToast(null);
    const link = notification.link;
    if (link && link.startsWith('/') && !link.startsWith('//')) navigate(link);
    else navigate(`/notifications?open=${notification.id}`);
  }, [markRead, navigate]);

  const value = useMemo(() => ({
    loggedIn, unread, items, hasMore, status,
    reload, ensureLoaded, loadMore, poll, markRead, markAllRead, remove, open,
  }), [loggedIn, unread, items, hasMore, status, reload, ensureLoaded, loadMore, poll, markRead, markAllRead, remove, open]);

  return (
    <NotificationContext.Provider value={value}>
      {children}
      {toast && loggedIn && (
        <NotificationToast
          notification={toast}
          onOpen={() => open(toast)}
          onClose={() => setToast(null)}
        />
      )}
    </NotificationContext.Provider>
  );
}

const FALLBACK = {
  loggedIn: false, unread: 0, items: [], hasMore: false, status: 'idle',
  reload() {}, ensureLoaded() {}, loadMore() {}, poll() {}, markRead() {}, markAllRead() {}, remove() {}, open() {},
};

// eslint-disable-next-line react-refresh/only-export-components
export const useNotifications = () => useContext(NotificationContext) || FALLBACK;
