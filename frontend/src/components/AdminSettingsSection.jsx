import { useEffect, useMemo, useState } from 'react';
import PaymentPolicySettings from './PaymentPolicySettings';
import { getSystemSettings, updateSystemSettings } from '../services/adminService';
import { notifyError, notifySuccess, notifyWarning } from '../utils/feedback';

// Réglages de l'application. Chaque champ ici change vraiment le comportement de Gaboshop.
// Les clés secrètes et les interrupteurs SingPay restent dans Render : ils sont seulement affichés.

const inputClass = 'mt-1 block w-full rounded-md border border-gray-300 p-2 text-sm disabled:bg-gray-100';

function Card({ title, description, children }) {
  return (
    <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
      <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
      {description && <p className="mt-1 text-sm text-gray-600">{description}</p>}
      <div className="mt-4 space-y-4">{children}</div>
    </section>
  );
}

function NumberField({ label, help, value, onChange, min, max, step = 1, suffix }) {
  return (
    <label className="block text-sm font-medium text-gray-700">
      {label}
      <div className="flex items-center gap-2">
        <input type="number" className={inputClass} value={value ?? ''} min={min} max={max} step={step} onChange={(e) => onChange(e.target.value)} />
        {suffix && <span className="mt-1 whitespace-nowrap text-sm text-gray-500">{suffix}</span>}
      </div>
      {help && <span className="mt-1 block text-xs font-normal text-gray-500">{help}</span>}
    </label>
  );
}

function TextField({ label, value, onChange, type = 'text', placeholder, help }) {
  return (
    <label className="block text-sm font-medium text-gray-700">
      {label}
      <input type={type} className={inputClass} value={value || ''} placeholder={placeholder} onChange={(e) => onChange(e.target.value)} />
      {help && <span className="mt-1 block text-xs font-normal text-gray-500">{help}</span>}
    </label>
  );
}

function TimeField({ label, value, onChange, disabled }) {
  return (
    <label className="block text-sm font-medium text-gray-700">
      {label}
      <input type="time" className={inputClass} value={value || ''} disabled={disabled} onChange={(e) => onChange(e.target.value)} />
    </label>
  );
}

function Toggle({ label, help, checked, onChange }) {
  return (
    <label className="flex items-start gap-3 rounded-md border border-gray-200 p-3">
      <input type="checkbox" className="mt-1 h-4 w-4" checked={!!checked} onChange={(e) => onChange(e.target.checked)} />
      <span>
        <span className="block text-sm font-medium text-gray-800">{label}</span>
        {help && <span className="block text-xs text-gray-500">{help}</span>}
      </span>
    </label>
  );
}

function StatusRow({ label, ok, text }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-gray-100 py-2 text-sm last:border-0">
      <span className="text-gray-700">{label}</span>
      <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${ok ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-700'}`}>{text}</span>
    </div>
  );
}

function CitiesEditor({ cities, defaultCity, onChange, onDefaultChange }) {
  const [draft, setDraft] = useState('');
  const add = () => {
    const name = draft.trim();
    if (!name) return;
    if (cities.some((c) => c.toLowerCase() === name.toLowerCase())) {
      notifyWarning(`${name} est déjà dans la liste.`);
      return;
    }
    onChange([...cities, name]);
    setDraft('');
  };
  const remove = (city) => {
    if (city === defaultCity) {
      notifyWarning(`${city} est la ville par défaut.`, 'Choisissez une autre ville par défaut avant de la retirer.');
      return;
    }
    onChange(cities.filter((c) => c !== city));
  };
  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium text-gray-700">
        Ville par défaut
        <select className={inputClass} value={defaultCity || ''} onChange={(e) => onDefaultChange(e.target.value)}>
          {cities.map((city) => <option key={city} value={city}>{city}</option>)}
        </select>
        <span className="mt-1 block text-xs font-normal text-gray-500">Proposée en premier aux nouveaux clients et commerces.</span>
      </label>
      <div>
        <p className="text-sm font-medium text-gray-700">Villes où Gaboshop est ouvert</p>
        <div className="mt-2 flex flex-wrap gap-2">
          {cities.map((city) => (
            <span key={city} className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-3 py-1 text-sm text-indigo-800">
              {city}
              <button type="button" aria-label={`Retirer ${city}`} onClick={() => remove(city)} className="text-indigo-500 hover:text-red-600">×</button>
            </span>
          ))}
        </div>
        <div className="mt-2 flex gap-2">
          <input className="block w-full rounded-md border border-gray-300 p-2 text-sm" placeholder="Ajouter une ville" value={draft}
            onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); add(); } }} />
          <button type="button" onClick={add} className="rounded-md bg-indigo-600 px-3 text-sm font-medium text-white">Ajouter</button>
        </div>
      </div>
    </div>
  );
}

export default function AdminSettingsSection({ initial = null, onSaved }) {
  const [saved, setSaved] = useState(initial);
  const [form, setForm] = useState(initial);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (initial) return;
    getSystemSettings()
      .then((res) => { if (res?.success) { setSaved(res.data); setForm(res.data); } })
      .catch((err) => notifyError(err, { action: 'Charger les réglages' }));
  }, [initial]);

  const dirty = useMemo(() => JSON.stringify(form) !== JSON.stringify(saved), [form, saved]);
  if (!form) return <p className="p-6 text-sm text-gray-600">Chargement des réglages…</p>;

  const set = (key) => (value) => setForm((prev) => ({ ...prev, [key]: value }));
  const status = form.technical_status;
  const legalForms = [...(form.legal_forms || [])];
  if (form.company_legal_form && !legalForms.includes(form.company_legal_form)) legalForms.push(form.company_legal_form);

  const save = async () => {
    setSaving(true);
    try {
      const { technical_status: _ignored, legal_forms: _forms, ...payload } = form;
      const res = await updateSystemSettings(payload);
      if (res?.success) {
        setSaved(res.data);
        setForm(res.data);
        onSaved?.(res.data);
        notifySuccess('Réglages enregistrés', 'Ils s’appliquent tout de suite aux nouvelles commandes et actions.');
      }
    } catch (err) {
      notifyError(err, { action: 'Enregistrer les réglages' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6 pb-20">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">⚙️ Réglages de l’application</h2>
        <p className="mt-1 text-sm text-gray-600">Chaque réglage ci-dessous agit vraiment sur Gaboshop. Les changements s’appliquent dès l’enregistrement.</p>
      </div>

      {status && (
        <Card title="État technique" description="Ces interrupteurs restent dans Render pour la sécurité : ils sont affichés ici, mais se changent seulement dans Render.">
          <div>
            <StatusRow label="Compte marchand SingPay" ok={status.singpay_ready} text={status.singpay_ready ? 'Configuré' : 'Clés manquantes'} />
            <StatusRow label="Versements automatiques (commerces, livreurs)" ok={status.singpay_transfers_enabled} text={status.singpay_transfers_enabled ? 'Activés' : 'Désactivés : versement manuel'} />
            <StatusRow label="Mode simulation des paiements" ok={!status.payment_simulation_mode} text={status.payment_simulation_mode ? 'Simulation (pas d’argent réel)' : 'Paiements réels'} />
            <StatusRow label="Assistant IA" ok={status.ai_provider !== 'local'} text={status.ai_provider} />
            <StatusRow label="Fournisseur SMS" ok={!!status.sms_provider} text={status.sms_provider || 'Aucun'} />
          </div>
        </Card>
      )}

      <Card title="Commissions Gaboshop" description="Les nouveaux taux s’appliquent aux nouvelles commandes ; les commandes passées gardent leur montant.">
        <div className="grid gap-4 md:grid-cols-2">
          <NumberField label="Commission d’un nouveau commerce ou d’une nouvelle catégorie" suffix="%" step="0.1" min={0} max={100}
            value={form.commission_global} onChange={set('commission_global')} help="Chaque catégorie de produits peut ensuite avoir son propre taux." />
          <NumberField label="Commission sur les commandes entre commerces (B2B)" suffix="%" step="0.1" min={0} max={100}
            value={form.b2b_commission_rate} onChange={set('b2b_commission_rate')} help="Avant la réduction du plan B2B du grossiste." />
        </div>
        <p className="text-sm font-medium text-gray-800">Plan Business</p>
        <div className="grid gap-4 md:grid-cols-3">
          <NumberField label="Commandes B2B" suffix="%" step="0.1" min={0} max={100} value={form.business_b2b_commission_rate} onChange={set('business_b2b_commission_rate')} />
          <NumberField label="Alimentaire vendu aux clients" suffix="%" step="0.1" min={0} max={100} value={form.business_food_commission_rate} onChange={set('business_food_commission_rate')} />
          <NumberField label="Autres produits vendus aux clients" suffix="%" step="0.1" min={0} max={100} value={form.business_other_commission_rate} onChange={set('business_other_commission_rate')} />
        </div>
        <label className="block text-sm font-medium text-gray-700">
          Catégories comptées comme alimentaires
          <input className={inputClass} value={form.food_category_keywords || ''} onChange={(e) => set('food_category_keywords')(e.target.value)} />
          <span className="mt-1 block text-xs font-normal text-gray-500">Mots séparés par des virgules, cherchés dans le nom de la catégorie du commerce. Sert aussi à la limite de produits alimentaires des forfaits.</span>
        </label>
      </Card>

      <Card title="Paiements">
        <div className="grid gap-4 md:grid-cols-3">
          <NumberField label="Frais Airtel Money" suffix="%" step="0.1" min={0} max={100} value={form.airtel_money_fee} onChange={set('airtel_money_fee')} />
          <NumberField label="Frais Moov Money" suffix="%" step="0.1" min={0} max={100} value={form.moov_money_fee} onChange={set('moov_money_fee')} />
          <NumberField label="Validité d’une demande de paiement" suffix="min" min={5} max={1440} value={form.unpaid_order_expiry_minutes}
            onChange={set('unpaid_order_expiry_minutes')} help="Après ce délai, le client doit relancer le paiement." />
        </div>
      </Card>
      <PaymentPolicySettings value={form.payment_policy} onChange={set('payment_policy')} />

      <Card title="Villes" description="Liste des villes du Gabon où l’app fonctionne.">
        <CitiesEditor cities={form.enabled_cities || []} defaultCity={form.default_city} onChange={set('enabled_cities')} onDefaultChange={set('default_city')} />
      </Card>

      <Card title="Livraison">
        <Toggle label="Attribuer automatiquement un livreur" help="Quand une commande est prête, Gaboshop propose la course au livreur disponible le plus proche."
          checked={form.auto_assign_delivery} onChange={set('auto_assign_delivery')} />
        <div className="grid gap-4 md:grid-cols-2">
          <NumberField label="Part des frais de livraison pour le livreur" suffix="%" step="1" min={0} max={100} value={form.courier_share_percent}
            onChange={set('courier_share_percent')} help="Le reste revient à Gaboshop. Non appliqué quand le commerce livre lui-même." />
          <NumberField label="Livraisons en cours maximum par livreur" min={1} max={20} value={form.max_orders_per_delivery} onChange={set('max_orders_per_delivery')}
            help="Au-delà, Gaboshop ne lui propose plus de nouvelle course tant qu’il n’a pas livré." />
          <NumberField label="Temps pour accepter une course" suffix="min" min={1} max={120} value={form.assignment_timeout_minutes}
            onChange={set('assignment_timeout_minutes')} help="Ensuite la course passe au livreur suivant." />
          <NumberField label="Proposer à tous les livreurs après" suffix="min" min={1} max={1440} value={form.broadcast_after_minutes}
            onChange={set('broadcast_after_minutes')} help="Si personne n’a accepté la course." />
          <NumberField label="Nouvel essai quand aucun livreur n’est libre" suffix="min" min={1} max={120} value={form.assignment_retry_minutes} onChange={set('assignment_retry_minutes')} />
          <NumberField label="Livraison signalée en retard après" suffix="heures" min={1} max={72} value={form.late_delivery_hours} onChange={set('late_delivery_hours')} />
          <NumberField label="Codes PIN faux avant blocage" min={1} max={20} value={form.pin_max_attempts} onChange={set('pin_max_attempts')} />
          <NumberField label="Durée du blocage PIN" suffix="min" min={1} max={1440} value={form.pin_lock_minutes} onChange={set('pin_lock_minutes')} />
        </div>
      </Card>

      <Card title="Commandes">
        <NumberField label="Annuler une commande toujours en attente après" suffix="heures" min={1} max={720} value={form.cart_validity_hours}
          onChange={set('cart_validity_hours')} help="Une commande que personne n’a traitée est annulée automatiquement." />
        <NumberField label="Rappeler au client une commande en attente après" suffix="heures" min={1} max={72} value={form.pending_reminder_hours} onChange={set('pending_reminder_hours')} />
        <div className="grid gap-4 md:grid-cols-2">
          <NumberField label="Déclarations de paiement refusées avant blocage" min={1} max={20} value={form.max_rejected_declarations}
            onChange={set('max_rejected_declarations')} help="Évite les fausses déclarations répétées." />
          <NumberField label="Comptées sur" suffix="jours" min={1} max={365} value={form.rejected_window_days} onChange={set('rejected_window_days')} />
        </div>
        <Toggle label="Limiter les commandes à une plage horaire" help="Désactivé : chaque commerce suit seulement ses propres horaires."
          checked={form.order_hours_enabled} onChange={set('order_hours_enabled')} />
        <div className="grid gap-4 md:grid-cols-2">
          <TimeField label="Commandes ouvertes à partir de" value={form.order_opening_time} disabled={!form.order_hours_enabled} onChange={set('order_opening_time')} />
          <TimeField label="Jusqu’à" value={form.order_closing_time} disabled={!form.order_hours_enabled} onChange={set('order_closing_time')} />
        </div>
      </Card>

      <Card title="Commerces">
        <div className="grid gap-4 md:grid-cols-2">
          <TimeField label="Ouverture par défaut d’un nouveau commerce" value={form.default_store_opening} onChange={set('default_store_opening')} />
          <TimeField label="Fermeture par défaut" value={form.default_store_closing} onChange={set('default_store_closing')} />
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <NumberField label="Durée d’un abonnement payé" suffix="jours" min={1} max={366} value={form.subscription_days} onChange={set('subscription_days')} />
          <NumberField label="Rappel avant la fin de l’abonnement" suffix="jours" min={1} max={60} value={form.subscription_reminder_days} onChange={set('subscription_reminder_days')} />
        </div>
        <Toggle label="Un nouveau commerce attend l’activation par l’admin" help="Désactivé : un commerce inscrit peut vendre tout de suite."
          checked={form.store_verification_required} onChange={set('store_verification_required')} />
      </Card>

      <Card title="Notifications" description="Les codes de connexion sont toujours envoyés, quel que soit ce réglage.">
        <div className="grid gap-3 md:grid-cols-3">
          <Toggle label="WhatsApp" checked={form.enable_whatsapp} onChange={set('enable_whatsapp')} />
          <Toggle label="SMS" checked={form.enable_sms} onChange={set('enable_sms')} />
          <Toggle label="E-mail" checked={form.enable_email} onChange={set('enable_email')} />
        </div>
      </Card>

      <Card title="Entreprise et support" description="Affiché dans le pied de page et les pages légales (CGU, mentions légales, confidentialité).">
        <div className="grid gap-4 md:grid-cols-2">
          <TextField label="Nom commercial" placeholder="Gaboshop" value={form.company_trade_name} onChange={set('company_trade_name')}
            help="Le nom affiché partout dans l’app et sur le site." />
          <TextField label="Nom / identité juridique" value={form.company_name} onChange={set('company_name')}
            help="Exactement comme sur le document d’immatriculation. Pour une entreprise individuelle : le nom du titulaire." />
          <label className="block text-sm font-medium text-gray-700">
            Forme juridique
            <select className={inputClass} value={form.company_legal_form || ''} onChange={(e) => set('company_legal_form')(e.target.value)}>
              <option value="">Pas encore choisie</option>
              {legalForms.map((f) => <option key={f} value={f}>{f}</option>)}
            </select>
            <span className="mt-1 block text-xs font-normal text-gray-500">Celle déposée au GNI. Ne mettez pas SARL ou SAS en attendant.</span>
          </label>
          <TextField label="Numéro RCCM" placeholder="GA-LBV-…" value={form.company_rccm} onChange={set('company_rccm')}
            help="Vide tant que l’entreprise n’est pas immatriculée : le site affiche alors « Entreprise en cours de formalisation au Gabon »." />
          <TextField label="NIF" value={form.company_nif} onChange={set('company_nif')}
            help="Vide tant que le numéro fiscal officiel n’est pas attribué. Il n’est pas affiché s’il est vide." />
          <TextField label="Adresse du siège" value={form.company_address} onChange={set('company_address')}
            help="L’adresse physique déclarée officiellement pour l’entreprise." />
          <TextField label="Ville" value={form.company_city} onChange={set('company_city')} />
          <TextField label="Directeur de la publication" value={form.publication_director} onChange={set('publication_director')}
            help="Le nom complet de la personne légalement responsable du site. Pour une entreprise individuelle, en général le titulaire." />
          <TextField label="E-mail du support" type="email" value={form.support_email} onChange={set('support_email')}
            help="Uniquement une boîte qui existe et reçoit vraiment les mails." />
          <TextField label="Téléphone du support" type="tel" placeholder="+241 77 12 34 56" value={form.support_phone} onChange={set('support_phone')} />
          <TextField label="WhatsApp du support" type="tel" placeholder="+241 77 12 34 56" value={form.support_whatsapp} onChange={set('support_whatsapp')}
            help="Peut être le même numéro que le téléphone." />
        </div>
      </Card>

      <Card title="Assistant IA" description="Les clés des fournisseurs restent dans Render. Ici, vous choisissez lequel utiliser et ce que l’assistant doit savoir.">
        <Toggle label="Utiliser l’IA en ligne" help="Désactivée, l’assistant répond quand même avec son moteur intégré, plus simple."
          checked={form.ai_enabled} onChange={set('ai_enabled')} />
        <div className="grid gap-4 md:grid-cols-2">
          <label className="block text-sm font-medium text-gray-700">
            Fournisseur
            <select className={inputClass} value={form.ai_provider || ''} onChange={(e) => set('ai_provider')(e.target.value)}>
              <option value="">Celui de Render{status ? ` (${status.ai_provider})` : ''}</option>
              {(status?.ai_providers_available || []).map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
            <span className="mt-1 block text-xs font-normal text-gray-500">Seuls les fournisseurs dont la clé est dans Render sont proposés.</span>
          </label>
          <TextField label="Modèle (facultatif)" placeholder="Vide = modèle par défaut" value={form.ai_model} onChange={set('ai_model')} />
        </div>
        <label className="block text-sm font-medium text-gray-700">
          Consignes pour l’assistant
          <textarea rows={4} maxLength={2000} className={inputClass} value={form.ai_instructions || ''} onChange={(e) => set('ai_instructions')(e.target.value)}
            placeholder="Ex. : Mettez en avant la livraison gratuite ce week-end à Akanda. Ne parlez jamais de concurrents." />
          <span className="mt-1 block text-xs font-normal text-gray-500">Ajoutées à chaque conversation : ton, promotions du moment, sujets à éviter…</span>
        </label>
        {status && <p className="text-xs text-gray-500">IA utilisée en ce moment : <b>{status.ai_active}</b></p>}
      </Card>

      {dirty && (
        <div className="fixed inset-x-0 bottom-0 z-40 border-t border-gray-200 bg-white/95 p-3 shadow-lg lg:pl-64">
          <div className="mx-auto flex max-w-5xl items-center justify-between gap-3">
            <span className="text-sm text-gray-700">Modifications non enregistrées</span>
            <div className="flex gap-2">
              <button type="button" onClick={() => setForm(saved)} className="rounded-md bg-gray-200 px-4 py-2 text-sm text-gray-800">Annuler</button>
              <button type="button" disabled={saving} onClick={save} className="rounded-md bg-green-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-60">
                {saving ? 'Enregistrement…' : 'Enregistrer'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
