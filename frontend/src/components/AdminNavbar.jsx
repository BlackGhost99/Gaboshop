import React from 'react';

const AdminNavbar = ({ onRefresh, onLogout, refreshing }) => (
  <header className="fixed top-0 left-64 right-0 h-16 bg-white border-b border-gray-200 z-20 flex items-center px-6">
    <div className="flex-1">
      <h1 className="text-xl font-bold text-gray-900">Console Admin</h1>
      <p className="text-xs text-gray-500">Pilotage global users / commandes / finances</p>
    </div>
    <div className="flex items-center gap-2">
      <button
        onClick={onRefresh}
        className="px-3 py-2 rounded-md text-sm font-semibold bg-white border border-gray-200 shadow-sm hover:bg-gray-50"
      >
        {refreshing ? 'Rafraîchissement...' : 'Rafraîchir'}
      </button>
      <button
        onClick={onLogout}
        className="px-3 py-2 rounded-md text-sm font-semibold bg-gray-900 text-white hover:bg-gray-800"
      >
        Déconnexion
      </button>
    </div>
  </header>
);

export default AdminNavbar;
