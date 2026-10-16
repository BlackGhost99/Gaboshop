import { getPushConfig, subscribePush, unsubscribePush } from '../services/notificationService';

// Alertes sur l'appareil (Web Push) : une notification s'affiche même quand Gaboshop est fermé.
// L'application Android (APK) n'a pas Web Push : ses alertes viendront de Firebase (pas encore branché).

const SW_URL = '/sw.js';

export const isNativeApp = () => Boolean(window.Capacitor?.isNativePlatform?.());

const isIOS = () => /iphone|ipad|ipod/i.test(navigator.userAgent)
  || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

export const isInstalledApp = () => Boolean(
  window.matchMedia?.('(display-mode: standalone)')?.matches || window.navigator.standalone,
);

// 'ok' | 'native' | 'ios-install' | 'unsupported'
export const pushSupport = () => {
  if (isNativeApp()) return 'native';
  const capable = 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
  if (capable) return 'ok';
  return isIOS() && !isInstalledApp() ? 'ios-install' : 'unsupported';
};

export class PushError extends Error {
  constructor(code, message) {
    super(message);
    this.code = code;
  }
}

const MESSAGES = {
  denied: {
    message: 'Les alertes sont bloquées sur cet appareil.',
    nextStep: 'Touchez le cadenas (ou les réglages du site) à côté de l’adresse, autorisez les notifications, puis revenez ici.',
  },
  dismissed: {
    message: 'Vous n’avez pas autorisé les alertes.',
    nextStep: 'Touchez « Activer les alertes » puis « Autoriser » dans la fenêtre qui s’ouvre.',
  },
  unsupported: {
    message: 'Ce navigateur ne sait pas envoyer d’alertes.',
    nextStep: 'Ouvrez Gaboshop avec Chrome, Edge, Firefox ou Safari à jour. Vous gardez les notifications dans la cloche.',
  },
  server_disabled: {
    message: 'Les alertes sont coupées sur le site pour le moment.',
    nextStep: 'Les notifications restent dans la cloche. Réessayez plus tard.',
  },
  failed: {
    message: 'Les alertes n’ont pas pu être activées.',
    nextStep: 'Vérifiez votre connexion et réessayez. Si cela recommence, rechargez la page.',
  },
};

export const pushErrorText = (error) => MESSAGES[error?.code] || MESSAGES.failed;

const toKey = (base64) => {
  const padded = `${base64}${'='.repeat((4 - (base64.length % 4)) % 4)}`.replace(/-/g, '+').replace(/_/g, '/');
  const raw = atob(padded);
  return Uint8Array.from(raw, (char) => char.charCodeAt(0));
};

const sameKey = (subscription, publicKey) => {
  const current = subscription?.options?.applicationServerKey;
  if (!current) return true; // le navigateur ne dit pas : on garde
  const a = new Uint8Array(current);
  const b = toKey(publicKey);
  return a.length === b.length && a.every((value, index) => value === b[index]);
};

// Enregistre le service qui reçoit les alertes (à appeler une fois au démarrage).
export const registerServiceWorker = () => {
  if (isNativeApp() || !('serviceWorker' in navigator)) return Promise.resolve(null);
  return navigator.serviceWorker.register(SW_URL).catch(() => null);
};

const readyRegistration = async () => {
  await registerServiceWorker();
  return navigator.serviceWorker.ready;
};

// { support, permission: 'default'|'granted'|'denied', subscribed }
export const getPushState = async () => {
  const support = pushSupport();
  if (support !== 'ok') return { support, permission: 'unsupported', subscribed: false };
  const permission = Notification.permission;
  let subscribed = false;
  if (permission === 'granted') {
    try {
      const registration = await navigator.serviceWorker.getRegistration();
      subscribed = Boolean(registration && await registration.pushManager.getSubscription());
    } catch {
      subscribed = false;
    }
  }
  return { support, permission, subscribed };
};

const subscribeBrowser = async (registration, publicKey) => {
  let subscription = await registration.pushManager.getSubscription();
  if (subscription && !sameKey(subscription, publicKey)) {
    await subscription.unsubscribe();
    subscription = null;
  }
  return subscription || registration.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: toKey(publicKey),
  });
};

// Demande l'autorisation, abonne cet appareil et prévient le serveur.
export const enablePush = async () => {
  if (pushSupport() !== 'ok') throw new PushError('unsupported');
  let config;
  try {
    config = await getPushConfig();
  } catch {
    throw new PushError('failed');
  }
  if (!config.enabled || !config.public_key) throw new PushError('server_disabled');

  const permission = await Notification.requestPermission();
  if (permission !== 'granted') throw new PushError(permission === 'denied' ? 'denied' : 'dismissed');

  try {
    const registration = await readyRegistration();
    const subscription = await subscribeBrowser(registration, config.public_key);
    await subscribePush(subscription.toJSON());
    return true;
  } catch {
    throw new PushError('failed');
  }
};

// Remet à jour l'inscription de cet appareil pour la personne connectée (clé changée, autre compte sur l'appareil).
export const syncPush = async () => {
  if (pushSupport() !== 'ok' || Notification.permission !== 'granted') return false;
  try {
    const config = await getPushConfig();
    if (!config.enabled || !config.public_key) return false;
    const registration = await readyRegistration();
    const subscription = await subscribeBrowser(registration, config.public_key);
    await subscribePush(subscription.toJSON());
    return true;
  } catch {
    return false;
  }
};

// Cet appareil n'est plus alerté pour ce compte (le navigateur garde son autorisation).
export const disablePush = async ({ keepBrowserSubscription = false } = {}) => {
  if (pushSupport() !== 'ok') return;
  try {
    const registration = await navigator.serviceWorker.getRegistration();
    const subscription = registration && await registration.pushManager.getSubscription();
    if (!subscription) return;
    await unsubscribePush(subscription.endpoint);
    if (!keepBrowserSubscription) await subscription.unsubscribe();
  } catch {
    // appareil injoignable : rien d'autre à faire
  }
};
