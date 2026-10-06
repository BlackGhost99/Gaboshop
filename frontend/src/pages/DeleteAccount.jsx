import { useState } from 'react';
import { Link, Navigate } from 'react-router-dom';
import api from '../services/api';
import { isLoggedIn, logout } from '../utils/session';

// Suppression du compte par l'utilisateur lui-même (exigence Google Play).
export default function DeleteAccount() {
  const [password, setPassword] = useState('');
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  if (!isLoggedIn() && !done) return <Navigate to="/login?next=/supprimer-mon-compte" replace />;

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await api.post('/auth/account/delete/', { password });
      setDone(true);
      setTimeout(() => logout('/'), 2500);
    } catch (err) {
      setError(err.response?.data?.error?.message || 'La suppression a échoué, réessayez.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 px-4 py-10">
      <div className="mx-auto max-w-md rounded-2xl bg-white p-6 shadow-sm border border-slate-200">
        <h1 className="text-xl font-bold text-slate-900">Supprimer mon compte</h1>
        {done ? (
          <p className="mt-4 text-green-700">Votre compte a été supprimé. Vous allez être déconnecté.</p>
        ) : (
          <form onSubmit={submit} className="mt-4 space-y-4">
            <div className="text-sm text-slate-600 space-y-2">
              <p>Votre nom, téléphone, e-mail, adresses et photo seront effacés et vous ne pourrez plus vous connecter.</p>
              <p>Les commandes passées restent enregistrées sans vos coordonnées, pour la comptabilité. Un commerce est retiré de la vente.</p>
              <p>Cette action est définitive. <Link to="/suppression-compte" className="text-orange-600 underline">En savoir plus</Link></p>
            </div>
            <label className="block text-sm font-medium text-slate-700">
              Mot de passe
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
                className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
              />
            </label>
            <label className="flex items-start gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} className="mt-1" />
              Je comprends que mon compte sera supprimé définitivement.
            </label>
            {error && <p className="text-sm text-red-600">{error}</p>}
            <button
              type="submit"
              disabled={!confirmed || !password || loading}
              className="w-full rounded-lg bg-red-600 py-2.5 font-semibold text-white disabled:opacity-50"
            >
              {loading ? 'Suppression…' : 'Supprimer définitivement'}
            </button>
            <Link to="/" className="block text-center text-sm text-slate-500">Annuler</Link>
          </form>
        )}
      </div>
    </div>
  );
}
