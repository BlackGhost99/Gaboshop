import { useAIContext } from '../context/AIContext';

/**
 * Hook personnalisé pour accéder au contexte IA
 * Alias pour useAIContext pour une utilisation plus simple
 */
export const useAI = () => useAIContext();

/**
 * Hook pour obtenir le contexte de la page actuelle
 */
export const usePageContext = () => {
  const { pageContext } = useAIContext();
  return pageContext;
};

export default useAIContext;

