import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useNotifications } from '../context/NotificationContext';
import { CountBadge } from './NotificationBell';
import { CART_EVENT, isLoggedIn, readCart } from '../utils/session';
import { readRole, useRole } from '../utils/currentUser';

// Barre du bas des téléphones : les 4 ou 5 endroits où l'on va le plus souvent, toujours à portée du pouce.
// Livreur et administrateur gardent leur propre écran (pas de barre).

const ICONS = {
  home: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6',
  shops: 'M3 9l9-6 9 6v11a2 2 0 01-2 2H5a2 2 0 01-2-2z',
  cart: 'M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z',
  orders: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2',
  bell: 'M15 17h5l-1.4-1.4A2 2 0 0118 14.2V11a6 6 0 10-12 0v3.2a2 2 0 01-.6 1.4L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9',
  login: 'M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1',
  products: 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4',
  money: 'M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  dashboard: 'M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z',
};

// Pages où la barre apparaît (sur téléphone) : achats, espace client, espace commerce, notifications.
const SHOWN_ON = /^\/($|boutiques|categories|stores\/|cart|client\/|store\/|plans|notifications)/;
// Pages qui défilent avec la fenêtre (pas de cadre fixe) : la barre fixe leur ajoute une marge en bas.
const WINDOW_SCROLL = /^\/($|boutiques|categories|stores\/)/;

const useCartCount = () => {
  const [count, setCount] = useState(() => readCart().reduce((sum, line) => sum + (Number(line.quantity) || 0), 0));
  useEffect(() => {
    const update = () => setCount(readCart().reduce((sum, line) => sum + (Number(line.quantity) || 0), 0));
    window.addEventListener(CART_EVENT, update);
    window.addEventListener('storage', update);
    return () => {
      window.removeEventListener(CART_EVENT, update);
      window.removeEventListener('storage', update);
    };
  }, []);
  return count;
};

const tabsFor = (role, { cartCount, unread }) => {
  if (role === 'store_manager') {
    return [
      { to: '/store/dashboard', label: 'Accueil', icon: ICONS.dashboard },
      { to: '/store/orders', label: 'Commandes', icon: ICONS.orders },
      { to: '/store/products', label: 'Produits', icon: ICONS.products },
      { to: '/store/finance', label: 'Finance', icon: ICONS.money },
      { to: '/notifications', label: 'Alertes', icon: ICONS.bell, badge: unread },
    ];
  }
  if (role === 'client') {
    return [
      { to: '/', label: 'Accueil', icon: ICONS.home },
      { to: '/boutiques', label: 'Boutiques', icon: ICONS.shops },
      { to: '/cart', label: 'Panier', icon: ICONS.cart, badge: cartCount },
      { to: '/client/orders', label: 'Commandes', icon: ICONS.orders },
      { to: '/notifications', label: 'Alertes', icon: ICONS.bell, badge: unread },
    ];
  }
  return [
    { to: '/', label: 'Accueil', icon: ICONS.home },
    { to: '/boutiques', label: 'Boutiques', icon: ICONS.shops },
    { to: '/cart', label: 'Panier', icon: ICONS.cart, badge: cartCount },
    { to: '/login', label: 'Connexion', icon: ICONS.login },
  ];
};

const isActive = (tab, pathname) => {
  if (tab.to === '/') return pathname === '/';
  if (tab.to === '/cart') return pathname === '/cart';
  if (tab.to === '/boutiques') return pathname === '/boutiques' || pathname.startsWith('/stores/') || pathname.startsWith('/categories');
  return pathname === tab.to || pathname.startsWith(`${tab.to}/`);
};

export default function MobileTabBar() {
  const { pathname } = useLocation();
  const role = useRole();
  const { unread } = useNotifications();
  const cartCount = useCartCount();

  const visitor = !isLoggedIn();
  // Livreur et administrateur : pas de barre. Rôle encore inconnu : on attend (pas de barre qui clignote).
  const known = visitor || Boolean(role || readRole());
  const hidden = !SHOWN_ON.test(pathname) || !known || role === 'delivery_agent' || role === 'admin';

  useEffect(() => {
    document.body.classList.toggle('has-tabbar', !hidden);
    document.body.classList.toggle('tabbar-pad', !hidden && WINDOW_SCROLL.test(pathname));
    return () => document.body.classList.remove('has-tabbar', 'tabbar-pad');
  }, [hidden, pathname]);

  if (hidden) return null;
  const tabs = tabsFor(visitor ? null : role, { cartCount, unread });

  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-[25] border-t border-gray-200 bg-white/95 pb-[env(safe-area-inset-bottom)] shadow-[0_-4px_14px_-8px_rgba(15,15,20,0.35)] backdrop-blur md:hidden"
      aria-label="Navigation principale"
    >
      <ul className="mx-auto flex max-w-lg items-stretch justify-around">
        {tabs.map((tab) => {
          const active = isActive(tab, pathname);
          return (
            <li key={tab.label} className="flex-1">
              <Link
                to={tab.to}
                aria-current={active ? 'page' : undefined}
                className={`relative flex h-16 flex-col items-center justify-center gap-0.5 text-[11px] font-semibold ${active ? 'text-slate-900' : 'text-gray-500'}`}
              >
                <span className="relative">
                  <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={active ? 2.2 : 1.7} d={tab.icon} />
                  </svg>
                  <CountBadge count={tab.badge} className="absolute -right-2.5 -top-1.5" />
                </span>
                <span>{tab.label}</span>
                {active && <span className="absolute inset-x-6 top-0 h-0.5 rounded-full bg-amber-500" aria-hidden="true" />}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
