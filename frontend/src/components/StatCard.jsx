import React from 'react';

const StatCard = ({ title, value, icon, bgColor = 'bg-slate-500' }) => {
  return (
    <div className="bg-white/70 backdrop-blur-lg border border-white/50 rounded-2xl p-6 shadow-xl hover:shadow-2xl transition-all duration-300 hover:-translate-y-1">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-gray-600 uppercase tracking-wider">{title}</p>
          <p className="text-3xl font-bold text-gray-900 mt-2">{value}</p>
        </div>
        <div className={`p-4 rounded-2xl shadow-lg text-white ${bgColor} bg-gradient-to-br from-white/20 to-transparent`}>
          {icon}
        </div>
      </div>
    </div>
  );
};

export default StatCard;
