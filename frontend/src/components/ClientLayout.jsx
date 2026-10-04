import React, { useState } from 'react';
import ClientSidebar from './ClientSidebar';
import Navbar from './Navbar';

const ClientLayout = ({ children, title, userName }) => {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <div className="h-screen bg-gray-100 flex overflow-hidden">
      {menuOpen && (
        <div className="fixed inset-0 bg-black/50 z-30 md:hidden" onClick={() => setMenuOpen(false)} />
      )}
      <ClientSidebar open={menuOpen} onClose={() => setMenuOpen(false)} />

      <div className="flex-1 flex flex-col overflow-hidden">
        <Navbar userRole="CLIENT" userName={userName || 'Client'} onMenuClick={() => setMenuOpen(true)} />

        <main className="flex-1 overflow-x-hidden overflow-y-auto bg-gray-100">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {title && (
              <div className="mb-8">
                <h2 className="text-3xl font-bold text-gray-900">{title}</h2>
              </div>
            )}
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};

export default ClientLayout;
