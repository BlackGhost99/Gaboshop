import React from 'react';
import Sidebar from './Sidebar';
import Navbar from './Navbar';

const StoreLayout = ({ children, title, userName }) => {
  return (
    <div className="h-screen bg-gray-100 flex overflow-hidden">
      <Sidebar role="store_manager" />
      
      <div className="flex-1 flex flex-col overflow-hidden">
        <Navbar 
            userRole="GERANT" 
            userName={userName || 'Gérant'} 
        />

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

export default StoreLayout;
