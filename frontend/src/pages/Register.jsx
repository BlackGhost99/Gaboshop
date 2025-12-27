import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { register } from '../services/dashboardService';

const Register = () => {
  const [form, setForm] = useState({
    user_type: 'client',
    phone: '',
    password: '',
    password_confirm: '',
    first_name: '',
    last_name: '',
    email: '',
    city: 'Libreville',
    address: '',
    zone: '',
    // Manager
    store_name: '',
    store_category_id: '',
    store_phone: '',
    store_address: '',
    store_city: 'Libreville',
    store_zone: '',
    // Delivery
    vehicle_type: 'moto',
    vehicle_plate: '',
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const isManager = form.user_type === 'store_manager';
  const isDelivery = form.user_type === 'delivery_agent';

  const updateField = (field, value) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const payload = { ...form };
      if (!isManager) {
        delete payload.store_name;
        delete payload.store_category_id;
        delete payload.store_phone;
        delete payload.store_address;
        delete payload.store_city;
        delete payload.store_zone;
      }
      if (!isDelivery) {
        delete payload.vehicle_type;
        delete payload.vehicle_plate;
      }
      const res = await register(payload);
      if (res.success && res.data?.tokens) {
        sessionStorage.setItem('token', res.data.tokens.access);
        sessionStorage.setItem('refresh_token', res.data.tokens.refresh);
        // If the created user is an admin, redirect to admin dashboard
        const createdUserType = res.data.user?.user_type || res.data.user_type;
        if (createdUserType === 'admin') {
          navigate('/admin/dashboard');
        } else {
          navigate('/dashboard');
        }
      } else {
        setError(res.error?.message || 'Inscription impossible.');
      }
    } catch (err) {
      const msg = err?.error?.details ? JSON.stringify(err.error.details) : err?.error?.message || 'Erreur inscription';
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col justify-center py-8 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-2xl">
        <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">Créer un compte</h2>
        <p className="mt-2 text-center text-sm text-gray-600">Client, Gérant ou Livreur</p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-2xl">
        <div className="bg-white py-8 px-6 shadow sm:rounded-lg">
          <form className="space-y-6" onSubmit={handleSubmit}>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Type de compte</label>
                <select
                  value={form.user_type}
                  onChange={(e) => updateField('user_type', e.target.value)}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                >
                  <option value="client">Client</option>
                  <option value="store_manager">Gérant</option>
                  <option value="delivery_agent">Livreur</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Téléphone</label>
                <input
                  type="text"
                  value={form.phone}
                  onChange={(e) => updateField('phone', e.target.value)}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="+241..."
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Prénom</label>
                <input
                  type="text"
                  value={form.first_name}
                  onChange={(e) => updateField('first_name', e.target.value)}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Nom</label>
                <input
                  type="text"
                  value={form.last_name}
                  onChange={(e) => updateField('last_name', e.target.value)}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Email</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={(e) => updateField('email', e.target.value)}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="(optionnel)"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Ville</label>
                <input
                  type="text"
                  value={form.city}
                  onChange={(e) => updateField('city', e.target.value)}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Adresse</label>
                <input
                  type="text"
                  value={form.address}
                  onChange={(e) => updateField('address', e.target.value)}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Adresse principale"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Zone / Quartier</label>
                <input
                  type="text"
                  value={form.zone}
                  onChange={(e) => updateField('zone', e.target.value)}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                  placeholder="Ex: Mont-Bouët"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">Mot de passe</label>
                <input
                  type="password"
                  value={form.password}
                  onChange={(e) => updateField('password', e.target.value)}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700">Confirmer</label>
                <input
                  type="password"
                  value={form.password_confirm}
                  onChange={(e) => updateField('password_confirm', e.target.value)}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                  required
                />
              </div>
            </div>

            {isManager && (
              <div className="border-t pt-4 space-y-3">
                <h3 className="text-sm font-semibold text-gray-900">Magasin (créé automatiquement)</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Nom du magasin</label>
                    <input
                      type="text"
                      value={form.store_name}
                      onChange={(e) => updateField('store_name', e.target.value)}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                      required={isManager}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Téléphone magasin</label>
                    <input
                      type="text"
                      value={form.store_phone}
                      onChange={(e) => updateField('store_phone', e.target.value)}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                      required={isManager}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Adresse magasin</label>
                    <input
                      type="text"
                      value={form.store_address}
                      onChange={(e) => updateField('store_address', e.target.value)}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                      required={isManager}
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Zone magasin</label>
                    <input
                      type="text"
                      value={form.store_zone}
                      onChange={(e) => updateField('store_zone', e.target.value)}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                      required={isManager}
                    />
                  </div>
                </div>
              </div>
            )}

            {isDelivery && (
              <div className="border-t pt-4 space-y-3">
                <h3 className="text-sm font-semibold text-gray-900">Informations Livreur</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Type de véhicule</label>
                    <select
                      value={form.vehicle_type}
                      onChange={(e) => updateField('vehicle_type', e.target.value)}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                    >
                      <option value="moto">Moto</option>
                      <option value="scooter">Scooter</option>
                      <option value="velo">Vélo</option>
                      <option value="voiture">Voiture</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700">Immatriculation</label>
                    <input
                      type="text"
                      value={form.vehicle_plate}
                      onChange={(e) => updateField('vehicle_plate', e.target.value)}
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500"
                      required={isDelivery}
                    />
                  </div>
                </div>
              </div>
            )}

            {error && <div className="text-sm text-red-600">{error}</div>}

            <div className="flex items-center justify-between">
              <Link to="/login" className="text-sm text-indigo-600 hover:text-indigo-500">Déjà inscrit ? Connexion</Link>
              <button
                type="submit"
                disabled={loading}
                className={`inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 ${loading ? 'opacity-75 cursor-not-allowed' : ''}`}
              >
                {loading ? 'Création...' : 'Créer mon compte'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default Register;
