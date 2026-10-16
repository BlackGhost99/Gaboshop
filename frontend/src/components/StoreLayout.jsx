import React, { useState } from 'react';
import Sidebar from './Sidebar';
import Navbar from './Navbar';
import { PushPrompt } from './PushControls';

const StoreLayout = ({ children, title, userName }) => {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <div className="h-[100dvh] bg-gray-100 flex overflow-hidden pb-[calc(4rem+env(safe-area-inset-bottom))] md:pb-0">
      {menuOpen && (
        <div className="fixed inset-0 bg-black/50 z-30 md:hidden" onClick={() => setMenuOpen(false)} />
      )}
      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
      
      <div className="flex-1 flex flex-col overflow-hidden">
        <Navbar 
            userRole="GERANT" 
            userName={userName || 'Commerçant'} 
            onMenuClick={() => setMenuOpen(true)}
        />

        <main className="flex-1 overflow-x-hidden overflow-y-auto bg-gray-100">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-8">
                {title && (
                    <div className="mb-4 sm:mb-8">
                <h2 className="text-2xl sm:text-3xl font-bold text-gray-900">{title}</h2>
                    </div>
                )}
                <PushPrompt role="store_manager" />
                {children}
            </div>
        </main>
      </div>
    </div>
  );
};

export default StoreLayout;
