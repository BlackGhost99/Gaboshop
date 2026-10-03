import { PAYMENT_FLOW_LABELS, PAYMENT_METHOD_LABELS, validatePaymentPolicy } from '../utils/paymentPolicy';

const descriptions = {
  direct_split: 'Le client règle les produits au commerce et la livraison au livreur. Le commerce doit sa commission à Gaboshop.',
  store_collects_all: 'Le commerce reçoit produits et livraison, puis règle le livreur et sa commission Gaboshop.',
  courier_cash: 'Le livreur reçoit le total en espèces, conserve sa rémunération et remet le montant des produits au commerce.',
  platform_online: 'Disponible uniquement lorsque les opérateurs et le compte marchand Gaboshop sont opérationnels.',
};

export default function PaymentPolicySettings({ value, onChange, disabled = false }) {
  if (!value) return <p className="rounded-lg bg-amber-50 p-4 text-sm text-amber-800">Configuration des paiements indisponible. Vérifiez la connexion au serveur.</p>;
  const change = (key, next) => onChange({ ...value, [key]: next });
  const toggle = (key, option) => {
    const list = value[key] || [];
    change(key, list.includes(option) ? list.filter((item) => item !== option) : [...list, option]);
  };
  const validation = validatePaymentPolicy(value);
  return (
    <fieldset disabled={disabled} className="space-y-5 rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <legend className="px-2 text-lg font-semibold text-gray-900">Circuits et moyens de paiement</legend>
      <p className="text-sm text-gray-600">Ces règles s’appliquent aux nouvelles commandes. Les montants et engagements des commandes existantes restent conservés.</p>
      <div className="grid gap-3 md:grid-cols-2">
        {Object.entries(PAYMENT_FLOW_LABELS).map(([key, label]) => (
          <label key={key} className="flex items-start gap-3 rounded-md border border-gray-200 p-3">
            <input type="checkbox" className="mt-1" checked={value.enabled_flows?.includes(key) || false} onChange={() => toggle('enabled_flows', key)} />
            <span><span className="block font-medium">{label}</span><span className="text-sm text-gray-600">{descriptions[key]}</span></span>
          </label>
        ))}
      </div>
      <label className="block text-sm font-medium">Circuit proposé par défaut
        <select className="mt-1 block w-full rounded-md border p-2" value={value.default_flow || ''} onChange={(event) => change('default_flow', event.target.value)}>
          <option value="" disabled>Choisir un circuit actif</option>
          {(value.enabled_flows || []).map((flow) => <option key={flow} value={flow}>{PAYMENT_FLOW_LABELS[flow] || flow}</option>)}
        </select>
      </label>
      <div className="flex flex-wrap gap-4">
        {Object.entries(PAYMENT_METHOD_LABELS).map(([method, label]) => (
          <label key={method} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={value.enabled_methods?.includes(method) || false} onChange={() => toggle('enabled_methods', method)} />{label}</label>
        ))}
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <label className="text-sm font-medium">Paiement des produits
          <select className="mt-1 block w-full rounded-md border p-2" value={value.payment_timing || 'on_delivery'} onChange={(event) => change('payment_timing', event.target.value)}>
            <option value="on_delivery">À la remise / au retrait</option><option value="before_dispatch">Avant le départ en livraison</option>
          </select>
        </label>
        <label className="text-sm font-medium">Délai de règlement des commissions (jours)
          <input className="mt-1 block w-full rounded-md border p-2" type="number" min="1" step="1" value={value.commission_settlement_days ?? ''} onChange={(event) => change('commission_settlement_days', event.target.value)} />
        </label>
        <label className="text-sm font-medium">Plafond des commissions dues par commerce (FCFA)
          <input className="mt-1 block w-full rounded-md border p-2" type="number" min="0" step="1" value={value.merchant_debt_limit ?? ''} onChange={(event) => change('merchant_debt_limit', event.target.value)} />
        </label>
        <label className="text-sm font-medium">Plafond des espèces confiées à un livreur (FCFA)
          <input className="mt-1 block w-full rounded-md border p-2" type="number" min="0" step="1" value={value.courier_cash_limit ?? ''} onChange={(event) => change('courier_cash_limit', event.target.value)} />
        </label>
      </div>
      <p className="text-xs text-gray-500">Un reçu confirme une somme réellement reçue. La validation d’une commande ou de sa livraison ne constitue pas une preuve de paiement.</p>
      {validation && <p role="alert" className="text-sm text-red-700">{validation}</p>}
    </fieldset>
  );
}
