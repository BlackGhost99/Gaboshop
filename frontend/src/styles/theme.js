/**
 * Thème principal Gaboshop - Slate/Gris-bleu foncé
 * Couleur principale: Slate-900 (rgb(15, 23, 42))
 * Palette cohérente pour tous les dashboards utilisateur
 */

export const THEME = {
  // Couleurs principales
  primary: {
    900: 'from-slate-900 via-slate-800 to-slate-900',
    800: 'bg-slate-800',
    700: 'bg-slate-700',
    600: 'bg-slate-600',
    500: 'bg-slate-500',
  },
  
  // Cartes KPI - couleurs secondaires vibrantes (partenaires de slate)
  kpi: {
    blue: 'bg-blue-500',
    green: 'bg-emerald-500',
    amber: 'bg-amber-500',
    indigo: 'bg-indigo-600',
    cyan: 'bg-cyan-500',
    rose: 'bg-rose-500',
    violet: 'bg-violet-500',
    teal: 'bg-teal-500',
  },

  // Accents et actions
  accent: {
    primary: 'text-slate-900',
    secondary: 'text-slate-600',
    light: 'text-slate-300',
    hover: 'hover:bg-slate-700',
  },

  // Gradients slate
  gradient: {
    main: 'from-slate-900 via-slate-800 to-slate-900',
    light: 'from-slate-800 to-slate-900',
    subtle: 'from-slate-50 to-slate-100',
  },

  // Badges & status
  badges: {
    success: 'bg-emerald-100 text-emerald-700',
    warning: 'bg-amber-100 text-amber-700',
    error: 'bg-rose-100 text-rose-700',
    info: 'bg-blue-100 text-blue-700',
    neutral: 'bg-slate-100 text-slate-700',
  }
};

// Helper pour les couleurs KPI en séquence
export const KPI_COLORS = [
  'bg-blue-500',
  'bg-emerald-500',
  'bg-amber-500',
  'bg-indigo-600',
  'bg-cyan-500',
  'bg-rose-500',
];
