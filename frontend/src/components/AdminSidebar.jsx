import React from 'react';

const AdminSidebar = ({ activeTab, onTabChange }) => {
  const links = [
    { id: 'overview', label: 'Vue globale', icon: 'M3 12l2-2 7-7 7 7-2 2v7a1 1 0 01-1 1h-3m-6 0h6m-6 0a1 1 0 01-1-1v-7' },
    { id: 'users', label: 'Utilisateurs', icon: 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2a3 3 0 00-.879-2.121M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2a3 3 0 01.879-2.121m0 0a3 3 0 014.242 0M12 6a3 3 0 110 6 3 3 0 010-6zm-5 3a3 3 0 105.879 1.121' },
    { id: 'orders', label: 'Commandes', icon: 'M9 5H7a2 2 0 00-2 2v11a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2m-6 0a2 2 0 104 0m-4 0a2 2 0 114 0' },
    { id: 'finances', label: 'Finances', icon: 'M12 8c-4.418 0-8 1.79-8 4s3.582 4 8 4 8-1.79 8-4-3.582-4-8-4zm0 8c-4.418 0-8-1.79-8-4m8 4v4m0-4c4.418 0 8-1.79 8-4m-8-4V4' },
    { id: 'stores', label: 'Magasins', icon: 'M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z' },
    { id: 'products', label: 'Produits', icon: 'M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z' },
    { id: 'store_categories', label: 'Cat. magasins', icon: 'M4 6h16M4 12h16M4 18h7' },
    { id: 'product_categories', label: 'Cat. produits', icon: 'M3 7h18M3 12h18M3 17h18' },
    { id: 'payment_methods', label: 'Paiements', icon: 'M4 7h16M4 11h16M4 15h10m-6 4h6' },
    { id: 'delivery', label: 'Livraison', icon: 'M3 13l2 2 4-4 4 4 6-6' },
    { id: 'settings', label: '⚙️ Configuration', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z' },
  ];

  return (
    <aside className="fixed inset-y-0 left-0 w-64 bg-gray-900 text-white z-30 border-r border-gray-800">
      <div className="h-16 flex items-center px-5 border-b border-gray-800">
        <span className="text-xl font-extrabold tracking-tight">Gabo Admin</span>
      </div>
      <nav className="p-3 space-y-1">
        {links.map((link) => {
          const active = activeTab === link.id;
          return (
            <button
              key={link.id}
              onClick={() => onTabChange(link.id)}
              className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-semibold transition ${
                active ? 'bg-gray-100 text-gray-900' : 'text-gray-200 hover:bg-gray-800'
              }`}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={link.icon} />
              </svg>
              <span>{link.label}</span>
            </button>
          );
        })}
      </nav>
    </aside>
  );
};

export default AdminSidebar;
