import React from 'react';
import { Link } from 'react-router-dom';
import NotificationBell from './NotificationBell';
import { logout } from '../utils/session';

const ROLE_NAMES = {
  CLIENT: 'Client',
  GERANT: 'Commerçant',
  LIVREUR: 'Livreur',
  ADMIN: 'Admin',
};

// En-tête des espaces client et commerce. Sur téléphone : menu, logo et cloche seulement
// (la déconnexion est dans le menu, la navigation dans la barre du bas).
const Navbar = ({ userRole, userName, onMenuClick }) => (
  <nav className="nav-metal">
    <div className="mx-auto max-w-7xl px-3 sm:px-6 lg:px-8">
      <div className="flex h-14 items-center justify-between sm:h-16">
        <div className="flex items-center gap-1 sm:gap-6">
          {onMenuClick && (
            <button
              type="button"
              onClick={onMenuClick}
              className="-ml-1 rounded-lg p-2 hover:bg-gray-100 md:hidden"
              aria-label="Ouvrir le menu"
            >
              <svg className="h-6 w-6 text-slate-900" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          )}
          <Link to="/" className="flex items-center gap-2" aria-label="Gaboshop, accueil">
            <img src="/logo.png" alt="" className="h-9 w-9 object-contain" />
            <span className="hidden text-lg font-bold text-slate-900 sm:block sm:text-2xl">GABOSHOP</span>
          </Link>
          <Link to="/" className="hidden text-base font-medium text-slate-900 hover:text-slate-700 sm:block">
            Accueil
          </Link>
        </div>
        <div className="flex items-center gap-1 sm:gap-4">
          <NotificationBell />
          <span className="hidden text-sm text-slate-900 sm:inline">
            {ROLE_NAMES[userRole] || 'Utilisateur'} - {userName}
          </span>
          <button
            type="button"
            className="hidden whitespace-nowrap rounded-md bg-red-500 px-4 py-2 text-sm font-medium text-white hover:bg-red-600 md:inline-flex"
            onClick={() => logout('/login')}
          >
            Déconnexion
          </button>
        </div>
      </div>
    </div>
  </nav>
);

export default Navbar;
