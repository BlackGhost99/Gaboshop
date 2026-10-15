import React, { useCallback, useEffect, useState } from 'react';
import api from '../services/api';
import { notifyError, notifySuccess } from '../utils/feedback';
import useVisibleInterval from '../hooks/useVisibleInterval';

// Forfait client : réduction sur la livraison des commandes payées en ligne, payé par Airtel Money ou Moov Money.
const ClientForfaitCard = () => {
  const [catalog, setCatalog] = useState([]);
  const [mine, setMine] = useState(null);
  const [choice, setChoice] = useState(null);
  const [operator, setOperator] = useState('airtel');
  const [phone, setPhone] = useState('');
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    try {
      const [list, current] = await Promise.all([api.get('/forfaits/'), api.get('/my-forfait/')]);
      setCatalog(list.data?.data || []);
      setMine(current.data?.data || null);
    } catch {
      /* carte facultative : rien à afficher en cas d'erreur */
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  // Paiement envoyé : on suit l'activation sans recharger la page.
  useVisibleInterval(load, 10000, Boolean(mine?.pending_payment));

  if (!catalog.length && !mine?.forfait) return null;

  const subscribe = async () => {
    if (!choice) return;
    setSending(true);
    try {
      const res = await api.post('/my-forfait/subscribe/', { forfait_id: choice.id, operator, phone_number: phone.trim() || undefined });
      notifySuccess('Paiement demandé', res.data?.message);
      setChoice(null);
      load();
    } catch (err) {
      notifyError(err, { action: 'Payer le forfait' });
    } finally {
      setSending(false);
    }
  };

  const current = mine?.forfait;
  return (
    <div className="bg-white rounded-lg shadow-md p-5 mb-8">
      <h3 className="text-lg font-bold text-gray-900">Mon forfait</h3>
      {current ? (
        <p className="text-sm text-gray-700 mt-1">
          <span className="font-semibold">{current.name}</span> : {current.discount_rate} % de réduction sur la livraison,
          jusqu’au {new Date(mine.expires_at).toLocaleDateString('fr-FR')}.
        </p>
      ) : (
        <p className="text-sm text-gray-600 mt-1">Payez moins cher la livraison en vous abonnant.</p>
      )}
      <p className="text-xs text-gray-500 mt-1">La réduction s’applique aux commandes payées en ligne (Airtel Money, Moov Money).</p>
      {mine?.pending_payment && (
        <p className="text-sm text-amber-700 mt-2">Paiement de {mine.pending_payment.amount} FCFA en attente : validez-le sur votre téléphone.</p>
      )}

      <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
        {catalog.map((f) => (
          <button
            key={f.id}
            onClick={() => setChoice(f)}
            className={`text-left border rounded-lg p-3 ${choice?.id === f.id ? 'border-indigo-600 bg-indigo-50' : 'border-gray-200'}`}
          >
            <p className="font-semibold text-gray-900">{f.name}</p>
            <p className="text-sm text-gray-700">{Number(f.monthly_price).toLocaleString('fr-FR')} FCFA / {f.days} jours</p>
            <p className="text-sm text-green-700">-{f.discount_rate} % sur la livraison</p>
            {f.description && <p className="text-xs text-gray-500 mt-1 break-words">{f.description}</p>}
          </button>
        ))}
      </div>

      {choice && (
        <div className="mt-4 space-y-2">
          <div className="flex flex-col sm:flex-row gap-2">
            <select value={operator} onChange={(e) => setOperator(e.target.value)} className="rounded-md border border-gray-300 px-3 py-2 text-sm">
              <option value="airtel">Airtel Money</option>
              <option value="moov">Moov Money</option>
            </select>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="Numéro qui paie (vide = le vôtre)"
              className="flex-1 min-w-0 rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
          </div>
          <button onClick={subscribe} disabled={sending} className="w-full sm:w-auto px-4 py-2 rounded-md bg-indigo-600 text-white font-medium disabled:opacity-50">
            {sending ? 'Envoi…' : `Payer ${Number(choice.monthly_price).toLocaleString('fr-FR')} FCFA`}
          </button>
        </div>
      )}
    </div>
  );
};

export default ClientForfaitCard;
