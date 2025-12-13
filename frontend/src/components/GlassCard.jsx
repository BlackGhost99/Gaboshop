import React from 'react';

const GlassCard = ({ children, className = '' }) => {
    return (
        <div
            className={`
        bg-white/70 backdrop-blur-lg border border-white/50 shadow-xl 
        rounded-2xl overflow-hidden transition-all duration-300
        hover:shadow-2xl hover:bg-white/80 ${className}
      `}
        >
            {children}
        </div>
    );
};

export default GlassCard;
