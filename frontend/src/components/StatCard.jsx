import React from 'react';

// Carte de chiffre clé. Sur téléphone elle est compacte (deux par ligne) ; l'icône passe à droite sur grand écran.
const StatCard = ({ title, value, icon }) => {
  return (
    <div className="card-3d p-3 sm:p-6">
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[11px] sm:text-sm font-semibold text-gray-600 uppercase tracking-wider">{title}</p>
          <p className="text-xl sm:text-3xl font-bold text-gray-900 mt-1 sm:mt-2 truncate">{value}</p>
        </div>
        <div className="hidden sm:block p-4 rounded-2xl btn-gold">
          {icon}
        </div>
      </div>
    </div>
  );
};

export default StatCard;
