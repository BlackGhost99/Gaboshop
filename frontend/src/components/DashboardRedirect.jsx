import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import LoadingSpinner from './LoadingSpinner';

const DashboardRedirect = () => {
  const navigate = useNavigate();
  const [error, setError] = useState(null);

  useEffect(() => {
    const checkUserRole = async () => {
      const token = sessionStorage.getItem('token');
      if (!token) {
        navigate('/login');
        return;
      }

      try {
        const response = await api.get('/auth/profile/');
        if (response.data.success) {
          const user = response.data.data;
          switch (user.user_type) {
            case 'client':
              navigate('/client/dashboard');
              break;
            case 'store_manager':
              navigate('/store/dashboard');
              break;
            case 'delivery_agent':
              navigate('/delivery/dashboard');
              break;
            case 'admin':
              navigate('/admin/dashboard');
              break;
            default:
              setError('Rôle utilisateur inconnu');
          }
        } else {
          setError('Impossible de récupérer le profil');
        }
      } catch (err) {
        console.error(err);
        // Si erreur (ex: 401), on redirige vers login
        localStorage.removeItem('token');
        navigate('/login');
      }
    };

    checkUserRole();
  }, [navigate]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-100">
        <div className="bg-white p-8 rounded-lg shadow-md">
          <h2 className="text-red-600 text-xl font-bold mb-4">Erreur</h2>
          <p>{error}</p>
          <button 
            onClick={() => navigate('/')}
            className="mt-4 bg-indigo-600 text-white px-4 py-2 rounded"
          >
            Retour à l'accueil
          </button>
        </div>
      </div>
    );
  }

  return <LoadingSpinner />;
};

export default DashboardRedirect;
