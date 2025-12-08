import React from 'react';

const StatCard = ({ title, value, icon, bgColor = 'bg-slate-500' }) => {
  return (
    <div className="bg-white rounded-lg shadow-md p-6 border-l-4 border-slate-500 hover:shadow-lg transition-shadow">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-slate-600 font-medium">{title}</p>
          <p className="text-2xl font-bold text-slate-900 mt-2">{value}</p>
        </div>
        <div className={`${bgColor} rounded-full p-3 text-white`}>
          {icon}
        </div>
      </div>
    </div>
  );
};

export default StatCard;
