import { useEffect, useRef, useState } from 'react';
import { getEconomicSimulator, runEconomicSimulator } from '../../services/adminService';
import { describeError } from '../../utils/feedback';

// Simulateur « Combien gagne Gaboshop » : on change un taux, on voit tout de suite ce que paie le client
// et ce que reçoivent le commerce, le livreur et Gaboshop. Rien n'est enregistré, aucun prix réel ne change.

const money = (value) => `${Number(value || 0).toLocaleString('fr-FR')} F`;

const FIELDS = [
  ['basket', 'Panier (produits)', 'F', 500],
  ['delivery_fee', 'Livraison', 'F', 100],
  ['commission_percent', 'Commission', '%', 0.5],
  ['courier_share_percent', 'Part du livreur', '%', 5],
  ['client_fee_percent', 'Frais Mobile Money payés par le client', '%', 0.1],
  ['singpay_fee_percent', 'Frais SingPay sur le paiement reçu', '%', 0.1],
  ['singpay_payout_fee_percent', 'Frais SingPay sur les versements', '%', 0.1],
  ['forfait_discount_percent', 'Réduction forfait client', '%', 5],
  ['small_order_fee', 'Frais petit panier (fixe)', 'F', 50],
  ['small_order_threshold', 'Sous ce panier', 'F', 500],
  ['debt_recovery_percent', 'Dettes réellement payées (paiement direct)', '%', 5],
];

function Actor({ label, value, tone }) {
  return (
    <div className={`rounded-lg border p-4 ${tone}`}>
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{label}</p>
      <p className="mt-1 text-2xl font-bold text-gray-900">{money(value)}</p>
    </div>
  );
}

export default function EconomicSimulator() {
  const [form, setForm] = useState(null);
  const [real, setReal] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const timer = useRef(null);

  useEffect(() => {
    getEconomicSimulator().then((res) => {
      setForm(res.data.defaults);
      setReal(res.data.real);
    }).catch((err) => setError(describeError(err).message));
  }, []);

  useEffect(() => {
    if (!form) return undefined;
    clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      runEconomicSimulator(form)
        .then((res) => { setResult(res.data); setError(''); })
        .catch((err) => setError(err?.response?.data?.error || describeError(err).message));
    }, 300);
    return () => clearTimeout(timer.current);
  }, [form]);

  if (!form) return <div className="p-6 text-sm text-gray-600">{error || 'Chargement…'}</div>;
  const set = (name) => (value) => setForm((prev) => ({ ...prev, [name]: value }));
  const online = form.flow === 'online';
  const gain = Number(result?.gaboshop || 0);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Combien gagne Gaboshop ?</h2>
        <p className="mt-1 text-sm text-gray-600">
          Changez un taux et voyez tout de suite ce que paie le client et ce que reçoit chacun. Rien n’est enregistré :
          les vrais prix se règlent dans ⚙️ Configuration, Cat. produits et Livraison.
        </p>
      </div>

      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm space-y-4">
        <div className="flex flex-wrap gap-2">
          {[['online', 'Paiement en ligne (SingPay)'], ['direct', 'Paiement direct ou espèces']].map(([id, label]) => (
            <button key={id} type="button" onClick={() => set('flow')(id)}
              className={`rounded-full px-4 py-2 text-sm font-semibold ${form.flow === id ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-700'}`}>
              {label}
            </button>
          ))}
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {FIELDS.filter(([name]) => online
            ? name !== 'debt_recovery_percent'
            : !['client_fee_percent', 'singpay_fee_percent', 'singpay_payout_fee_percent', 'forfait_discount_percent',
              'small_order_fee', 'small_order_threshold'].includes(name))
            .map(([name, label, suffix, step]) => (
              <label key={name} className="block text-sm font-medium text-gray-700">
                {label}
                <div className="flex items-center gap-2">
                  <input type="number" min={0} step={step} value={form[name] ?? ''} onChange={(e) => set(name)(e.target.value)}
                    className="mt-1 block w-full rounded-md border border-gray-300 p-2 text-sm" />
                  <span className="mt-1 text-sm text-gray-500">{suffix}</span>
                </div>
              </label>
            ))}
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:gap-6">
          <label className="flex items-center gap-2 text-sm text-gray-700">
            <input type="checkbox" checked={!!form.store_delivers} onChange={(e) => set('store_delivers')(e.target.checked)} />
            Le commerce livre lui-même
          </label>
          {!online && (
            <label className="flex items-center gap-2 text-sm text-gray-700">
              <input type="checkbox" checked={!!form.direct_delivery_margin} onChange={(e) => set('direct_delivery_margin')(e.target.checked)} />
              Gaboshop prend sa part de livraison en paiement direct
            </label>
          )}
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
      </section>

      {result && (
        <section className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <Actor label="Le client paie" value={result.client_pays} tone="border-gray-200 bg-white" />
            <Actor label="Le commerce reçoit" value={result.store_receives} tone="border-blue-200 bg-blue-50" />
            <Actor label="Le livreur reçoit" value={result.courier_receives} tone="border-amber-200 bg-amber-50" />
            <Actor label="Gaboshop gagne" value={result.gaboshop}
              tone={gain > 0 ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'} />
          </div>
          <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
            <h3 className="font-semibold text-gray-900">Le détail pour Gaboshop</h3>
            <ul className="mt-3 divide-y divide-gray-100 text-sm">
              {result.lines.map((line) => (
                <li key={line.key} className="flex justify-between gap-4 py-2">
                  <span className="text-gray-700">{line.label}</span>
                  <span className={`font-semibold ${Number(line.amount) < 0 ? 'text-red-600' : 'text-gray-900'}`}>{money(line.amount)}</span>
                </li>
              ))}
              <li className="flex justify-between gap-4 py-2 font-bold">
                <span>Total Gaboshop ({result.gaboshop_percent_of_client} % de ce que paie le client)</span>
                <span className={gain > 0 ? 'text-green-700' : 'text-red-600'}>{money(result.gaboshop)}</span>
              </li>
            </ul>
            {!online && Number(result.debt_to_gaboshop) > 0 && (
              <p className="mt-3 text-xs text-gray-500">
                En paiement direct, l’argent ne passe pas par Gaboshop : {money(result.debt_to_gaboshop)} sont une dette à encaisser après la livraison.
              </p>
            )}
            {gain <= 0 && <p className="mt-3 text-sm font-medium text-red-600">Avec ces réglages, Gaboshop perd de l’argent sur cette commande.</p>}
          </div>
        </section>
      )}

      {real && (
        <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <h3 className="font-semibold text-gray-900">Ce qui s’est vraiment passé ({real.days} derniers jours)</h3>
          {real.delivered_orders === 0 ? (
            <p className="mt-2 text-sm text-gray-600">Aucune commande livrée sur la période : le simulateur part des réglages actuels.</p>
          ) : (
            <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-3">
              <div><dt className="text-gray-500">Commandes livrées</dt><dd className="font-semibold">{real.delivered_orders} ({real.online_orders} en ligne, {real.direct_orders} en direct)</dd></div>
              <div><dt className="text-gray-500">Panier moyen</dt><dd className="font-semibold">{money(real.avg_basket)}</dd></div>
              <div><dt className="text-gray-500">Livraison moyenne</dt><dd className="font-semibold">{money(real.avg_delivery_fee)}</dd></div>
              <div><dt className="text-gray-500">Commission moyenne</dt><dd className="font-semibold">{real.avg_commission_percent} %</dd></div>
              <div><dt className="text-gray-500">Commissions de la période</dt><dd className="font-semibold">{money(real.commission_total)}</dd></div>
              <div><dt className="text-gray-500">Frais SingPay estimés</dt><dd className="font-semibold">{money(real.singpay_cost_estimate)}</dd></div>
            </dl>
          )}
          {real.delivered_orders > 0 && (
            <button type="button" className="mt-4 rounded-md bg-gray-900 px-4 py-2 text-sm font-semibold text-white"
              onClick={() => setForm((prev) => ({ ...prev, basket: real.avg_basket, delivery_fee: real.avg_delivery_fee, commission_percent: real.avg_commission_percent }))}>
              Utiliser ces moyennes
            </button>
          )}
        </section>
      )}
    </div>
  );
}
