import React from 'react';

const StatCard = ({ title, value, icon }) => {
  return (
    <div className="card-3d p-5 sm:p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-gray-600 uppercase tracking-wider">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{value}</p>
        </div>
        <div className="p-4 rounded-2xl btn-gold">
          {icon}
        </div>
      </div>
    </div>
  );
};

export default StatCard;
