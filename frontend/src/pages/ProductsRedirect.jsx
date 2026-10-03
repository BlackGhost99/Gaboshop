import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import LoadingSpinner from '../components/LoadingSpinner';

const ProductsRedirect = () => {
  const navigate = useNavigate();

  useEffect(() => {
    navigate('/', { state: { scrollTo: 'produits' }, replace: true });
  }, [navigate]);

  return <LoadingSpinner />;
};

export default ProductsRedirect;
