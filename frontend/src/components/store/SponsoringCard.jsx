import { useEffect, useState } from 'react';
import api from '../../services/api';
import { formatCurrency, formatDateTime } from '../../utils/helpers';
import { notifyError, notifySuccess, notifyWarning } from '../../utils/feedback';

const STATUS_LABELS = {
  pending_payment: 'En attente du paiement',
  active: 'En cours',
  scheduled: 'Programmée',
  expired: 'Terminée',
  paused: 'Suspendue',
  cancelled: 'Annulée',
};

/** « Mettre en avant » : le commerce paie pour passer en tête des listes, marqué « Sponsorisé ».
 *  Tant que Gaboshop n'a pas ouvert l'offre, elle est affichée grisée « Bientôt disponible ». */
export default function SponsoringCard() {
  const [data, setData] = useState(null);
  const [form, setForm] = useState({ target: 'product', product_id: '', weeks: 1, operator: 'airtel', phone_number: '' });
  const [sending, setSending] = useState(false);

  const load = () => api.get('/store/sponsoring/').then((res) => setData(res.data?.data)).catch(() => setData(null));
  useEffect(() => { load(); }, []);

  if (!data) return null;
  const enabled = data.enabled;
  const weekPrice = Number(data.prices?.[form.target] || 0);
  const amount = weekPrice * Number(form.weeks || 1);
  const set = (key, value) => setForm((prev) => ({ ...prev, [key]: value }));

  const submit = async (e) => {
    e.preventDefault();
    if (form.target === 'product' && !form.product_id) {
      notifyWarning('Choisissez le produit à mettre en avant');
      return;
    }
    setSending(true);
    try {
      const res = await api.post('/store/sponsoring/', form);
      notifySuccess('Demande de paiement envoyée', res.data?.message || '');
      load();
      // Le paiement se confirme sur le téléphone : on revérifie un peu plus tard.
      setTimeout(load, 12000);
      setTimeout(load, 30000);
    } catch (err) {
      notifyError(err, { action: 'Mettre en avant' });
    } finally {
      setSending(false);
    }
  };

  return (
    <div className={`mb-8 rounded-lg border bg-white p-4 shadow-sm ${enabled ? 'border-indigo-200' : 'border-gray-200'}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-bold text-gray-900">⭐ Mettre en avant</p>
          <p className="text-sm text-gray-600">
            Votre produit ou votre commerce passe en tête des listes pendant la durée choisie, avec la mention « Sponsorisé » visible par les clients.
          </p>
        </div>
        {!enabled && <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-semibold text-gray-600">Bientôt disponible</span>}
      </div>

      <form onSubmit={submit} className={`mt-3 grid grid-cols-1 gap-3 md:grid-cols-2 ${enabled ? '' : 'pointer-events-none opacity-50'}`} aria-disabled={!enabled}>
        <fieldset disabled={!enabled || sending} className="contents">
          <select className="w-full rounded-md border border-gray-200 px-3 py-2" value={form.target} onChange={(e) => set('target', e.target.value)}>
            <option value="product">Un produit — {formatCurrency(data.prices?.product)} / semaine</option>
            <option value="store">Tout mon commerce — {formatCurrency(data.prices?.store)} / semaine</option>
          </select>
          {form.target === 'product' ? (
            <select className="w-full rounded-md border border-gray-200 px-3 py-2" value={form.product_id} onChange={(e) => set('product_id', e.target.value)}>
              <option value="">Choisir le produit</option>
              {(data.products || []).map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          ) : <div className="hidden md:block" />}
          <select className="w-full rounded-md border border-gray-200 px-3 py-2" value={form.weeks} onChange={(e) => set('weeks', Number(e.target.value))}>
            {Array.from({ length: data.max_weeks || 8 }, (_, i) => i + 1).map((w) => (
              <option key={w} value={w}>{w} semaine{w > 1 ? 's' : ''}</option>
            ))}
          </select>
          <select className="w-full rounded-md border border-gray-200 px-3 py-2" value={form.operator} onChange={(e) => set('operator', e.target.value)}>
            <option value="airtel">Airtel Money</option>
            <option value="moov">Moov Money</option>
          </select>
          <input
            className="w-full rounded-md border border-gray-200 px-3 py-2"
            placeholder="Numéro Mobile Money qui paie"
            inputMode="tel"
            value={form.phone_number}
            onChange={(e) => set('phone_number', e.target.value)}
          />
          <button type="submit" className="w-full rounded-md bg-indigo-600 px-4 py-2 font-semibold text-white disabled:opacity-60">
            {sending ? 'Envoi…' : `Payer ${formatCurrency(amount)}`}
          </button>
        </fieldset>
      </form>

      {data.mine?.length > 0 && (
        <ul className="mt-3 divide-y divide-gray-100 rounded border border-gray-100 text-sm">
          {data.mine.map((s) => (
            <li key={s.id} className="flex flex-wrap items-center justify-between gap-2 px-3 py-2">
              <span className="min-w-0 font-medium">{s.target === 'store' ? 'Tout le commerce' : s.product_name}</span>
              <span className="text-gray-600">{STATUS_LABELS[s.status] || s.status}</span>
              <span className="text-gray-600">{s.end_date ? `jusqu’au ${formatDateTime(s.end_date)}` : `${s.weeks} sem.`}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
