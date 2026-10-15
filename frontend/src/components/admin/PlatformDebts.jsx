import { useEffect, useState } from 'react';
import { collectPlatformDebt, getPlatformDebts } from '../../services/adminService';
import { describeError, notifyError, notifySuccess } from '../../utils/feedback';
import { KIND_LABELS, METHOD_LABELS, newIdempotencyKey } from '../payments/paymentLabels';

// Ce que les commerces (commission) et les livreurs (part Gaboshop de la livraison) doivent à Gaboshop
// sur les commandes payées en direct ou en espèces. L'admin note ici l'argent qu'il a reçu.

const money = (value) => `${Number(value || 0).toLocaleString('fr-FR')} F`;

function CollectForm({ row, onDone }) {
  const [amount, setAmount] = useState(row.total_due);
  const [method, setMethod] = useState('cash');
  const [reference, setReference] = useState('');
  const [busy, setBusy] = useState(false);
  const [key] = useState(newIdempotencyKey);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const res = await collectPlatformDebt({ party: row.party, id: row.id, amount, method, reference, idempotency_key: key });
      notifySuccess('Encaissement enregistré', `${money(res.data.collected)} reçus de ${row.name}. Reste dû : ${money(res.data.total_due)}.`);
      onDone();
    } catch (err) {
      notifyError(err, { action: 'Encaissement' });
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="mt-3 grid gap-2 rounded bg-gray-50 p-3 sm:grid-cols-4">
      <input type="number" min={1} max={row.total_due} value={amount} onChange={(e) => setAmount(e.target.value)} required
        className="rounded border border-gray-300 px-2 py-1 text-sm" aria-label="Montant reçu" />
      <select value={method} onChange={(e) => setMethod(e.target.value)} className="rounded border border-gray-300 px-2 py-1 text-sm">
        {Object.entries(METHOD_LABELS).map(([id, label]) => <option key={id} value={id}>{label}</option>)}
      </select>
      <input value={reference} onChange={(e) => setReference(e.target.value)} required={method !== 'cash'}
        placeholder={method === 'cash' ? 'Référence (facultatif)' : 'ID de transaction du SMS'} className="rounded border border-gray-300 px-2 py-1 text-sm" />
      <button type="submit" disabled={busy} className="rounded bg-gray-900 px-3 py-1 text-sm font-semibold text-white disabled:opacity-50">
        {busy ? 'Envoi…' : 'J’ai reçu cet argent'}
      </button>
    </form>
  );
}

export default function PlatformDebts() {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState('');
  const [open, setOpen] = useState(null);

  const load = () => getPlatformDebts()
    .then((res) => { setRows(res.data); setError(''); })
    .catch((err) => setError(describeError(err).message));
  useEffect(() => { load(); }, []);

  if (!rows) return <div className="p-6 text-sm text-gray-600">{error || 'Chargement…'}</div>;
  const total = rows.reduce((sum, row) => sum + Number(row.total_due), 0);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Dettes à encaisser</h2>
        <p className="mt-1 text-sm text-gray-600">
          Commandes payées en direct ou en espèces : la commission (due par le commerce) et la part Gaboshop de la livraison
          (due par le livreur, ou par le commerce s’il encaisse tout) deviennent exigibles à la livraison.
          Notez ici l’argent reçu : il règle d’abord les plus vieilles dettes.
        </p>
        <p className="mt-2 text-lg font-semibold">Total dû à Gaboshop : {money(total)}</p>
      </div>
      {rows.length === 0 && <p className="rounded border border-gray-200 bg-white p-4 text-sm text-gray-600">Personne ne doit rien à Gaboshop.</p>}
      {rows.map((row) => {
        const id = `${row.party}-${row.id}`;
        return (
          <section key={id} className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div className="min-w-0">
                <p className="font-semibold text-gray-900">{row.name} <span className="text-xs font-normal text-gray-500">({row.party === 'store' ? 'commerce' : 'livreur'} · {row.phone})</span></p>
                {Number(row.overdue) > 0 && <p className="text-sm font-medium text-red-600">Dont {money(row.overdue)} en retard</p>}
              </div>
              <div className="text-right">
                <p className="text-xl font-bold">{money(row.total_due)}</p>
                <button type="button" className="text-sm font-semibold text-indigo-600" onClick={() => setOpen(open === id ? null : id)}>
                  {open === id ? 'Fermer' : 'Encaisser'}
                </button>
              </div>
            </div>
            <ul className="mt-2 divide-y divide-gray-100 text-sm">
              {row.items.map((item) => (
                <li key={item.obligation_id} className="flex flex-wrap justify-between gap-2 py-1">
                  <span>{item.order_number}</span>
                  <span className="text-gray-600">{KIND_LABELS[item.kind] || item.kind}</span>
                  <span className={item.status === 'overdue' ? 'font-semibold text-red-600' : 'font-semibold'}>{money(item.remaining)}</span>
                </li>
              ))}
            </ul>
            {open === id && <CollectForm row={row} onDone={() => { setOpen(null); load(); }} />}
          </section>
        );
      })}
    </div>
  );
}
