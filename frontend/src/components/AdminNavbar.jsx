import React from 'react';

const AdminNavbar = ({ onRefresh, onLogout, refreshing, onMenuClick }) => (
  <header className="fixed top-0 left-0 lg:left-64 right-0 h-16 bg-white border-b border-gray-200 z-20 flex items-center gap-2 px-3 sm:px-6">
    <button
      onClick={onMenuClick}
      className="lg:hidden p-2 -ml-1 rounded-md text-gray-700 hover:bg-gray-100"
      aria-label="Ouvrir le menu"
    >
      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
      </svg>
    </button>
    <div className="flex-1 min-w-0">
      <h1 className="text-lg sm:text-xl font-bold text-gray-900 truncate">Console Admin</h1>
      <p className="hidden sm:block text-xs text-gray-500 truncate">Pilotage global users / commandes / finances</p>
    </div>
    <div className="flex items-center gap-2 shrink-0">
      <button
        onClick={onRefresh}
        className="px-2 sm:px-3 py-2 rounded-md text-xs sm:text-sm font-semibold bg-white border border-gray-200 shadow-sm hover:bg-gray-50"
      >
        {refreshing ? 'Rafraîchissement...' : 'Rafraîchir'}
      </button>
      <button
        onClick={onLogout}
        className="px-2 sm:px-3 py-2 rounded-md text-xs sm:text-sm font-semibold bg-gray-900 text-white hover:bg-gray-800"
      >
        Déconnexion
      </button>
    </div>
  </header>
);

export default AdminNavbar;
