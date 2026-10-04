import { useEffect, useRef } from 'react';

// setInterval that only runs while the app/tab is visible, and fires once
// immediately when it comes back to the foreground (e.g. after confirming a
// Mobile Money PIN in another app). Saves battery and data on mobile.
export default function useVisibleInterval(callback, delayMs, enabled = true) {
  const saved = useRef(callback);
  useEffect(() => {
    saved.current = callback;
  }, [callback]);

  useEffect(() => {
    if (!enabled) return undefined;
    let timer = null;

    const stop = () => {
      if (timer) {
        clearInterval(timer);
        timer = null;
      }
    };
    const start = () => {
      stop();
      timer = setInterval(() => saved.current(), delayMs);
    };
    const onVisibility = () => {
      if (document.hidden) {
        stop();
      } else {
        saved.current();
        start();
      }
    };

    if (!document.hidden) start();
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      stop();
      document.removeEventListener('visibilitychange', onVisibility);
    };
  }, [delayMs, enabled]);
}
