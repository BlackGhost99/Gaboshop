import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../services/api';
import { useCompany } from '../legal/legalInfo';
import { describeError, notifySuccess } from '../utils/feedback';

const input = 'mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-indigo-500 sm:text-sm';
const button = 'flex w-full justify-center rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-60';

function SupportContact() {
  const company = useCompany();
  const whatsapp = company.whatsapp && `https://wa.me/${company.whatsapp.replace(/\D/g, '')}`;
  return (
    <div className="rounded-md bg-gray-50 p-3 text-sm text-gray-700">
      <p>Pas de code ? Contactez le support : il vérifiera votre identité et vous donnera un nouveau mot de passe.</p>
      <p className="mt-1 font-medium">
        {whatsapp && <a className="text-indigo-600" href={whatsapp}>WhatsApp</a>}
        {whatsapp && company.phone && ' · '}
        {company.phone && <a className="text-indigo-600" href={`tel:${company.phone.replace(/\s/g, '')}`}>{company.phone}</a>}
        {!whatsapp && !company.phone && company.contact}
      </p>
    </div>
  );
}

export default function ForgotPassword() {
  const navigate = useNavigate();
  const [step, setStep] = useState('phone');
  const [available, setAvailable] = useState(null);
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.get('/auth/password-reset/')
      .then((res) => setAvailable(res.data?.data || {}))
      .catch(() => setAvailable({}));
  }, []);
  const canSend = available && (available.sms_available || available.email_available);

  const sendCode = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await api.post('/auth/password-reset/', { phone });
      setMessage(res.data?.message || '');
      setStep('code');
    } catch (err) {
      setError(describeError(err).message || 'Envoi impossible. Réessayez.');
    } finally {
      setLoading(false);
    }
  };

  const reset = async (e) => {
    e.preventDefault();
    setError('');
    if (password !== confirm) {
      setError('Les deux mots de passe ne sont pas identiques.');
      return;
    }
    setLoading(true);
    try {
      await api.post('/auth/password-reset/confirm/', { phone, code, password });
      notifySuccess('Mot de passe changé', 'Connectez-vous avec votre nouveau mot de passe.');
      navigate('/login');
    } catch (err) {
      setError(describeError(err).message || 'Code incorrect ou expiré.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col justify-center bg-gray-100 px-4 py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <h2 className="text-center text-3xl font-extrabold text-gray-900">Mot de passe oublié</h2>
        <p className="mt-2 text-center text-sm text-gray-600">
          {step === 'phone' ? 'Recevez un code pour choisir un nouveau mot de passe.' : 'Entrez le code reçu et votre nouveau mot de passe.'}
        </p>
      </div>
      <div className="mt-8 space-y-4 bg-white px-4 py-8 shadow sm:mx-auto sm:w-full sm:max-w-md sm:rounded-lg sm:px-10">
        {available === null && <p className="text-center text-sm text-gray-600">Chargement…</p>}
        {available && !canSend && (
          <>
            <p className="text-sm text-gray-700">L’envoi de code par SMS n’est pas encore disponible.</p>
            <SupportContact />
          </>
        )}
        {canSend && step === 'phone' && (
          <form className="space-y-4" onSubmit={sendCode}>
            <label className="block text-sm font-medium text-gray-700">
              Numéro de téléphone du compte
              <input type="tel" autoComplete="tel" required className={input} placeholder="+241…" value={phone} onChange={(e) => setPhone(e.target.value)} />
            </label>
            <button type="submit" disabled={loading} className={button}>{loading ? 'Envoi…' : 'Recevoir un code'}</button>
          </form>
        )}
        {canSend && step === 'code' && (
          <form className="space-y-4" onSubmit={reset}>
            {message && <p className="rounded-md bg-green-50 p-3 text-sm text-green-800">{message}</p>}
            <label className="block text-sm font-medium text-gray-700">
              Code à 6 chiffres
              <input inputMode="numeric" autoComplete="one-time-code" maxLength={6} required className={input} value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Nouveau mot de passe
              <input type="password" autoComplete="new-password" minLength={6} required className={input} value={password} onChange={(e) => setPassword(e.target.value)} />
            </label>
            <label className="block text-sm font-medium text-gray-700">
              Confirmer le mot de passe
              <input type="password" autoComplete="new-password" minLength={6} required className={input} value={confirm} onChange={(e) => setConfirm(e.target.value)} />
            </label>
            <button type="submit" disabled={loading} className={button}>{loading ? 'Enregistrement…' : 'Changer le mot de passe'}</button>
            <button type="button" onClick={() => { setStep('phone'); setCode(''); setError(''); }} className="w-full text-sm text-indigo-600">Renvoyer un code</button>
            <SupportContact />
          </form>
        )}
        {error && <p className="text-center text-sm text-red-600">{error}</p>}
        <p className="text-center text-sm"><Link to="/login" className="font-medium text-indigo-600">Retour à la connexion</Link></p>
      </div>
    </div>
  );
}
