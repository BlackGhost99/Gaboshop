import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { login } from '../services/dashboardService';
import authStorage from '../utils/authStorage';
import { safeNextPath } from '../utils/session';

const Login = () => {
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const nextPath = safeNextPath(location.search);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = await login(phone, password);
      
      if (response.success && response.data && response.data.tokens) {
        // Stocker le token
        authStorage.setItem('token', response.data.tokens.access);
        authStorage.setItem('refresh_token', response.data.tokens.refresh);

        // Direct redirect for admin users, otherwise go to /dashboard
        const userType = response.data.user?.user_type || response.data.user_type;
        if (userType === 'admin') {
          navigate('/admin/dashboard');
        } else if (nextPath && userType === 'client') {
          // Retour là où le client était (ex. produit qu'il voulait ajouter au panier)
          navigate(nextPath);
        } else {
          navigate('/dashboard');
        }
      } else {
        setError('Réponse du serveur invalide.');
      }
      
    } catch (err) {
      console.error(err);
      if (!err.response) {
        // Pas de réponse : serveur endormi, réseau coupé ou accès refusé (CORS)
        setError('Impossible de joindre le serveur. Vérifiez votre connexion et réessayez dans une minute.');
      } else if (err.response.status >= 500) {
        setError('Le serveur rencontre un problème. Réessayez dans un instant.');
      } else {
        setError('Identifiants invalides. Veuillez réessayer.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
          Connexion à GABOSHOP
        </h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          Accédez à votre espace personnel
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          <form className="space-y-6" onSubmit={handleSubmit}>
            <div>
              <label htmlFor="phone" className="block text-sm font-medium text-gray-700">
                Numéro de téléphone
              </label>
              <div className="mt-1">
                <input
                  id="phone"
                  name="phone"
                  type="text"
                  autoComplete="tel"
                  required
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                  placeholder="+241..."
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Mot de passe
              </label>
              <div className="mt-1">
                <input
                  id="password"
                  name="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
                />
              </div>
            </div>

            <div className="-mt-3 text-right text-sm">
              <a href="/mot-de-passe-oublie" className="font-medium text-indigo-600 hover:text-indigo-500">Mot de passe oublié ?</a>
            </div>

            {error && (
              <div className="text-red-600 text-sm text-center">
                {error}
              </div>
            )}

            <div>
              <button
                type="submit"
                disabled={loading}
                className={`w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 ${
                  loading ? 'opacity-75 cursor-not-allowed' : ''
                }`}
              >
                {loading ? 'Connexion...' : 'Se connecter'}
              </button>
            </div>
            <div className="text-center text-sm text-gray-600">
              Pas de compte ?{' '}
              <a href={`/register${location.search}`} className="text-indigo-600 hover:text-indigo-500 font-medium">Créer un compte</a>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Login;
