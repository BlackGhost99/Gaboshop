import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { getClientDashboard } from '../services/dashboardService';

const ClientSidebar = () => {
  const location = useLocation();
  const [clientData, setClientData] = useState(null);

  useEffect(() => {
    const fetchClientData = async () => {
      try {
        const response = await getClientDashboard();
        if (response.success) {
          setClientData(response.data);
        }
      } catch (err) {
        console.error('Erreur chargement client:', err);
      }
    };
    fetchClientData();
  }, []);

  const isActive = (path) =>
    location.pathname === path ? 'bg-slate-800 text-white' : 'text-slate-300 hover:bg-slate-700';

  const links = [
    {
      name: 'Dashboard',
      path: '/client/dashboard',
      icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6',
    },
    {
      name: 'Mes commandes',
      path: '/client/orders',
      icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2',
    },
  ];

  return (
    <div className="bg-slate-900 w-64 space-y-6 py-7 px-2 absolute inset-y-0 left-0 transform -translate-x-full md:relative md:translate-x-0 transition duration-200 ease-in-out z-20 overflow-y-auto">
      {/* Profil client */}
      <div className="px-4 pb-4 border-b border-slate-700">
        <div className="flex items-center space-x-3">
          <div className="w-12 h-12 rounded-full bg-slate-700 flex items-center justify-center overflow-hidden">
            {clientData?.profile?.avatar ? (
              <img src={clientData.profile.avatar} alt="Avatar" className="w-full h-full object-cover" />
            ) : (
              <svg className="w-6 h-6 text-slate-400" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
              </svg>
            )}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-white font-semibold text-sm truncate">
              {clientData?.profile?.name || 'Client'}
            </p>
            <p className="text-slate-400 text-xs truncate">
              {clientData?.profile?.email || 'client@gaboshop.ga'}
            </p>
          </div>
        </div>
      </div>

      <nav>
        {links.map((link) => (
          <Link
            key={link.name}
            to={link.path}
            className={`block py-2.5 px-4 rounded transition duration-200 ${isActive(link.path)} flex items-center space-x-2`}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={link.icon} />
            </svg>
            <span>{link.name}</span>
          </Link>
        ))}
      </nav>
    </div>
  );
};

export default ClientSidebar;
