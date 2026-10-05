import { useEffect, useRef } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Capacitor } from '@capacitor/core';
import { App } from '@capacitor/app';

// Pages "racine" : un retour ici ne remonte plus dans l'historique.
const ROOT_PATHS = ['/', '/login', '/dashboard', '/client/dashboard', '/store/dashboard', '/admin', '/admin/dashboard', '/wholesaler/dashboard', '/delivery/dashboard'];

/**
 * Bouton "retour" Android : revient à l'écran précédent au lieu de fermer l'app.
 * Sur un écran racine, un premier appui affiche un message, un second (dans les 2 s) quitte l'app.
 */
export default function AndroidBackButton() {
  const navigate = useNavigate();
  const location = useLocation();
  const pathRef = useRef(location.pathname);
  const lastPressRef = useRef(0);
  const toastRef = useRef(null);

  useEffect(() => {
    pathRef.current = location.pathname;
  }, [location.pathname]);

  useEffect(() => {
    if (!Capacitor.isNativePlatform()) return undefined;

    const showToast = (text) => {
      if (toastRef.current) toastRef.current.remove();
      const el = document.createElement('div');
      el.textContent = text;
      el.style.cssText = 'position:fixed;left:50%;bottom:80px;transform:translateX(-50%);background:rgba(17,24,39,.9);color:#fff;padding:8px 16px;border-radius:9999px;font-size:14px;z-index:99999;pointer-events:none';
      document.body.appendChild(el);
      toastRef.current = el;
      setTimeout(() => { el.remove(); if (toastRef.current === el) toastRef.current = null; }, 2000);
    };

    const handle = App.addListener('backButton', () => {
      // Fermer d'abord une fenêtre/menu ouvert si un composant l'écoute
      const evt = new CustomEvent('gaboshop:back', { cancelable: true });
      if (!window.dispatchEvent(evt)) return;

      const isRoot = ROOT_PATHS.includes(pathRef.current);
      const canGoBack = (window.history.state?.idx ?? 0) > 0;
      if (!isRoot) {
        if (canGoBack) navigate(-1);
        else navigate('/', { replace: true });
        return;
      }
      const now = Date.now();
      if (now - lastPressRef.current < 2000) {
        App.exitApp();
      } else {
        lastPressRef.current = now;
        showToast("Appuyez encore sur retour pour quitter");
      }
    });

    return () => { handle.then((h) => h.remove()); };
  }, [navigate]);

  return null;
}
