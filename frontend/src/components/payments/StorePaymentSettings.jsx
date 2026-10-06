import { useEffect, useState } from 'react';
import api from '../../services/api';
import { apiErrorMessage } from './paymentLabels';

const FIELDS = [
  { key: 'airtel_money', label: 'Airtel Money', placeholder: 'Ex. Code marchand 123456 ou 07 12 34 56 (nom du titulaire)' },
  { key: 'moov_money', label: 'Moov Money', placeholder: 'Ex. Code marchand 654321 ou 06 12 34 56 (nom du titulaire)' },
];

// Le commerce indique où ses clients le paient. Sans ces informations, l'app ne propose que les espèces.
export default function StorePaymentSettings() {
  const [prefs, setPrefs] = useState(null);
  const [values, setValues] = useState({});
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get('/payments/preferences/')
      .then((res) => {
        const current = res.data?.data?.preferences || {};
        setPrefs(current);
        setValues(current.instructions || {});
        if (!Object.values(current.instructions || {}).some(Boolean)) setOpen(true);
      })
      .catch(() => setPrefs(null));
  }, []);

  if (prefs === null) return null;

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    setMessage('');
    try {
      const instructions = Object.fromEntries(Object.entries(values).filter(([, v]) => v && v.trim()).map(([k, v]) => [k, v.trim()]));
      const res = await api.patch('/payments/preferences/', { preferences: { ...prefs, instructions } });
      setPrefs(res.data?.data?.preferences || { ...prefs, instructions });
      setMessage('Enregistré. Vos clients verront ces informations au moment de payer.');
    } catch (err) {
      setMessage(apiErrorMessage(err, "L'enregistrement a échoué."));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mb-6 rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
      <button type="button" onClick={() => setOpen(!open)} className="flex w-full items-center justify-between text-left">
        <span className="text-lg font-bold text-gray-900">💳 Mes moyens de paiement</span>
        <span className="text-sm text-indigo-600">{open ? 'Fermer' : 'Modifier'}</span>
      </button>
      {open && (
        <form onSubmit={save} className="mt-3 space-y-3 text-sm">
          <p className="text-gray-600">
            Indiquez votre code marchand ou numéro Mobile Money. Vos clients (et les commerces qui vous achètent en B2B)
            vous paient directement, puis déclarent l'ID de transaction : vous confirmez dans « Paiements à vérifier ».
          </p>
          {FIELDS.map((f) => (
            <label key={f.key} className="block font-medium text-gray-700">
              {f.label}
              <input
                value={values[f.key] || ''}
                onChange={(e) => setValues({ ...values, [f.key]: e.target.value })}
                placeholder={f.placeholder}
                maxLength={160}
                className="mt-1 w-full rounded border border-gray-300 px-3 py-2 font-normal"
              />
            </label>
          ))}
          {message && <p className="text-indigo-700">{message}</p>}
          <button type="submit" disabled={saving} className="w-full rounded bg-indigo-600 py-2 font-semibold text-white disabled:opacity-50">
            {saving ? 'Enregistrement…' : 'Enregistrer'}
          </button>
        </form>
      )}
    </div>
  );
}
