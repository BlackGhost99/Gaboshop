// Web: the session ends with the tab (sessionStorage), as before.
// Android app: the WebView is closed whenever the app is killed, so keep the
// session in localStorage to avoid logging in again on every launch.
// Capacitor injects window.Capacitor in the native WebView; reading it from the
// global keeps the web build independent from the @capacitor/core package.
const isNativeApp = Boolean(window.Capacitor?.isNativePlatform?.());

const authStorage = isNativeApp ? window.localStorage : window.sessionStorage;

export default authStorage;
