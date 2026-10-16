// Web: the session ends with the tab (sessionStorage), as before.
// Android app: the WebView is closed whenever the app is killed, so keep the
// session in localStorage to avoid logging in again on every launch.
// Capacitor injects window.Capacitor in the native WebView; reading it from the
// global keeps the web build independent from the @capacitor/core package.
const isNativeApp = Boolean(window.Capacitor?.isNativePlatform?.());
// Application installée sur l'écran d'accueil (PWA) : même logique que l'application Android, la personne l'a
// installée exprès sur son appareil et n'a pas à se reconnecter à chaque ouverture.
const isInstalledWebApp = Boolean(
  window.matchMedia?.('(display-mode: standalone)')?.matches || window.navigator.standalone,
);

const authStorage = isNativeApp || isInstalledWebApp ? window.localStorage : window.sessionStorage;

export default authStorage;
