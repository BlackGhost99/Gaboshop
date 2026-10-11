import { useEffect } from 'react';
import { useLocation, useNavigationType } from 'react-router-dom';

// Une nouvelle page s'ouvre en haut (le bouton retour garde la position du navigateur)
const ScrollToTop = () => {
  const { pathname, search } = useLocation();
  const navigationType = useNavigationType();

  useEffect(() => {
    if (navigationType !== 'POP') window.scrollTo(0, 0);
  }, [pathname, search, navigationType]);

  return null;
};

export default ScrollToTop;
