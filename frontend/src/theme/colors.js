/**
 * Palette de couleurs GABOSHOP
 * Thème: Mobile-first / PWA moderne + Marketplace Africain
 * 
 * Design pensé pour:
 * - Clarté et lisibilité
 * - Accessibilité
 * - Performance (couleurs simples)
 * - Warmth local (touches africaines)
 */

export const colors = {
  // Neutres - Base
  white: '#FFFFFF',
  black: '#000000',
  
  // Gris (contexte)
  gray: {
    50: '#F9FAFB',
    100: '#F3F4F6',
    200: '#E5E7EB',
    300: '#D1D5DB',
    400: '#9CA3AF',
    500: '#6B7280',
    600: '#4B5563',
    700: '#374151',
    800: '#1F2937',
    900: '#111827',
  },

  // Primaire - Bleu vif (action, liens, CTA)
  primary: {
    50: '#EFF6FF',
    100: '#DBEAFE',
    200: '#BFDBFE',
    300: '#93C5FD',
    400: '#60A5FA',
    500: '#3B82F6',
    600: '#2563EB',
    700: '#1D4ED8',
    800: '#1E40AF',
    900: '#1E3A8A',
    main: '#1E88E5',
    light: '#2196F3',
    dark: '#1565C0',
  },

  // Accentuation - Vert africain (secondaire, positif)
  accent: {
    50: '#F0FDF4',
    100: '#DCFCE7',
    200: '#BBF7D0',
    300: '#86EFAC',
    400: '#4ADE80',
    500: '#22C55E',
    600: '#16A34A',
    700: '#15803D',
    800: '#166534',
    900: '#145231',
    main: '#00A859',
    light: '#4CAF50',
    dark: '#00796B',
  },

  // CTA - Orange chaud (boutons panier, achat, urgence)
  cta: {
    50: '#FFF7ED',
    100: '#FFEDD5',
    200: '#FED7AA',
    300: '#FDBA74',
    400: '#FB923C',
    500: '#F97316',
    600: '#EA580C',
    700: '#C2410C',
    800: '#9A360E',
    900: '#7C2D12',
    main: '#FF5722',
    light: '#FF7043',
    dark: '#E64A19',
  },

  // Signaux de statut
  status: {
    success: '#10B981', // Vert (succès, livré)
    warning: '#F59E0B', // Ambre (attention, en cours)
    error: '#EF4444',   // Rouge (erreur, problème)
    info: '#3B82F6',    // Bleu (info)
    pending: '#8B5CF6', // Violet (en attente)
  },

  // Spécifique au contexte
  delivery: {
    active: '#10B981',
    inactive: '#6B7280',
    busy: '#F59E0B',
    offline: '#EF4444',
  },

  order: {
    pending: '#8B5CF6',
    confirmed: '#3B82F6',
    preparing: '#F59E0B',
    ready: '#10B981',
    delivered: '#059669',
    cancelled: '#EF4444',
  },
};

/**
 * Classe Tailwind dynamiques par contexte
 */
export const getStatusColor = (status) => {
  const statusMap = {
    success: 'bg-green-100 text-green-800',
    warning: 'bg-amber-100 text-amber-800',
    error: 'bg-red-100 text-red-800',
    info: 'bg-blue-100 text-blue-800',
    pending: 'bg-purple-100 text-purple-800',
  };
  return statusMap[status] || statusMap.info;
};

export const getOrderStatusColor = (status) => {
  const map = {
    pending: 'bg-purple-100 text-purple-800 border-purple-300',
    confirmed: 'bg-blue-100 text-blue-800 border-blue-300',
    preparing: 'bg-amber-100 text-amber-800 border-amber-300',
    ready: 'bg-green-100 text-green-800 border-green-300',
    delivered: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    cancelled: 'bg-red-100 text-red-800 border-red-300',
  };
  return map[status] || map.pending;
};

export const getDeliveryStatusColor = (status) => {
  const map = {
    available: 'bg-green-100 text-green-800',
    busy: 'bg-amber-100 text-amber-800',
    offline: 'bg-gray-100 text-gray-800',
    suspended: 'bg-red-100 text-red-800',
  };
  return map[status] || map.offline;
};

/**
 * Tailwind config extension
 * À ajouter dans tailwind.config.js
 */
export const tailwindExtend = {
  colors: {
    primary: colors.primary,
    accent: colors.accent,
    cta: colors.cta,
    status: colors.status,
  },
  fontFamily: {
    sans: [
      'system-ui',
      '-apple-system',
      'Segoe UI',
      'Roboto',
      'Helvetica Neue',
      'Arial',
      'sans-serif',
    ],
  },
};
