import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { getStoreDashboard } from '../services/dashboardService';

const Sidebar = () => {
  const location = useLocation();
  const [storeData, setStoreData] = useState(null);
  
  useEffect(() => {
    const fetchStoreData = async () => {
      try {
        const response = await getStoreDashboard();
        if (response.success) {
          setStoreData(response.data);
        }
      } catch (err) {
        console.error('Erreur chargement store:', err);
      }
    };
    fetchStoreData();
  }, []);
  
  const isActive = (path) => {
    return location.pathname === path ? 'bg-slate-800 text-white' : 'text-slate-300 hover:bg-slate-700';
  };

  const links = [
    { name: 'Dashboard', path: '/store/dashboard', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
    { name: 'Produits', path: '/store/products', icon: 'M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4' },
    { name: 'Commandes', path: '/store/orders', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2' },
    { name: 'Paramètres', path: '/store/settings', icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z' },
  ];

  return (
    <div className="bg-slate-900 w-64 space-y-6 py-7 px-2 absolute inset-y-0 left-0 transform -translate-x-full md:relative md:translate-x-0 transition duration-200 ease-in-out z-20 overflow-y-auto">
      {/* Profil utilisateur */}
      <div className="px-4 pb-4 border-b border-slate-700">
        <div className="flex items-center space-x-3 mb-3">
          <div className="w-12 h-12 rounded-full bg-slate-700 flex items-center justify-center overflow-hidden">
            {storeData?.store?.logo ? (
              <img src={storeData.store.logo} alt="Logo" className="w-full h-full object-cover" />
            ) : (
              <svg className="w-6 h-6 text-slate-400" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
              </svg>
            )}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-white font-semibold text-sm truncate">
              {storeData?.store?.name || 'Mon magasin'}
            </p>
            <p className="text-slate-400 text-xs truncate">
              {storeData?.owner?.email || 'Gérant'}
            </p>
          </div>
        </div>
        
        {/* Forfait */}
        {storeData?.subscription && (
          <div className="bg-slate-800 rounded-lg p-3 mt-3">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-slate-400">Forfait</span>
              <span className={`text-xs px-2 py-0.5 rounded-full ${
                storeData.subscription.status === 'active' 
                  ? 'bg-emerald-500/20 text-emerald-400' 
                  : 'bg-gray-500/20 text-gray-400'
              }`}>
                {storeData.subscription.status === 'active' ? 'Actif' : 'Inactif'}
              </span>
            </div>
            <p className="text-white font-semibold text-sm">
              {storeData.subscription.plan_name || 'Standard'}
            </p>
            {storeData.subscription.monthly_fee && (
              <p className="text-slate-400 text-xs mt-1">
                {storeData.subscription.monthly_fee} FCFA/mois
              </p>
            )}
          </div>
        )}
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

export default Sidebar;
