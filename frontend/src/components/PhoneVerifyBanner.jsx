import { useEffect, useState } from 'react';
import api from '../services/api';
import { describeError, notifySuccess } from '../utils/feedback';

const DISMISS_KEY = 'gaboshop:phone-verify-later';

/** Vérification facultative du numéro : un code par WhatsApp (ou SMS), puis un badge « Numéro vérifié ». */
export default function PhoneVerifyBanner() {
  const [state, setState] = useState(null);
  const [step, setStep] = useState('idle');
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let later = false;
    try { later = sessionStorage.getItem(DISMISS_KEY) === '1'; } catch { later = false; }
    if (later) return;
    api.get('/auth/phone/verify/').then((res) => setState(res.data?.data || null)).catch(() => setState(null));
  }, []);

  if (!state || !state.available || state.phone_verified || step === 'hidden') return null;

  const send = async () => {
    setBusy(true);
    setError('');
    try {
      await api.post('/auth/phone/verify/');
      setStep('code');
    } catch (err) {
      setError(describeError(err).message);
    } finally {
      setBusy(false);
    }
  };

  const confirm = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      await api.post('/auth/phone/verify/confirm/', { code });
      notifySuccess('Numéro vérifié', 'Le badge « Numéro vérifié » est ajouté à votre compte.');
      setState({ ...state, phone_verified: true });
    } catch (err) {
      setError(describeError(err).message);
    } finally {
      setBusy(false);
    }
  };

  const later = () => {
    try { sessionStorage.setItem(DISMISS_KEY, '1'); } catch { /* rien */ }
    setStep('hidden');
  };

  return (
    <div className="border-b border-indigo-200 bg-indigo-50 px-4 py-3 text-sm text-indigo-900">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-3">
        {step === 'idle' && (
          <>
            <p className="flex-1">Vérifiez votre numéro pour obtenir le badge « Numéro vérifié ». Vous recevrez un code sur WhatsApp.</p>
            <button type="button" disabled={busy} onClick={send} className="rounded-md bg-indigo-600 px-3 py-1.5 font-medium text-white disabled:opacity-60">
              {busy ? 'Envoi…' : 'Recevoir le code'}
            </button>
            <button type="button" onClick={later} className="text-indigo-700">Plus tard</button>
          </>
        )}
        {step === 'code' && (
          <form onSubmit={confirm} className="flex flex-1 flex-wrap items-center gap-2">
            <span>Code reçu :</span>
            <input inputMode="numeric" autoComplete="one-time-code" maxLength={6} required value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
              className="w-28 rounded-md border border-indigo-300 px-2 py-1 tracking-widest" />
            <button type="submit" disabled={busy || code.length !== 6} className="rounded-md bg-indigo-600 px-3 py-1.5 font-medium text-white disabled:opacity-60">Vérifier</button>
            <button type="button" disabled={busy} onClick={send} className="text-indigo-700">Renvoyer</button>
          </form>
        )}
        {error && <p className="w-full text-red-700">{error}</p>}
      </div>
    </div>
  );
}
