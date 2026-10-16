import { useCallback, useEffect, useMemo, useState } from 'react';
import { getAdminAnnouncements, sendAdminAnnouncement } from '../services/notificationService';
import { notifyError, notifySuccess } from '../utils/feedback';
import { formatDateTime } from '../utils/helpers';

const AUDIENCES = [
  { id: 'clients', label: 'Tous les clients', hint: 'Les personnes qui commandent' },
  { id: 'stores', label: 'Tous les commerces', hint: 'Les gérants de boutiques' },
  { id: 'drivers', label: 'Tous les livreurs', hint: 'Les agents de livraison' },
  { id: 'everyone', label: 'Tout le monde', hint: 'Clients, commerces et livreurs' },
  { id: 'me', label: 'Moi seul (essai)', hint: 'Pour voir le rendu sur votre téléphone' },
];

// Où mène le bouton de l'annonce. Seules des pages de Gaboshop : jamais de lien extérieur.
const DESTINATIONS = {
  clients: [
    { path: '/boutiques', label: 'Découvrir les boutiques', button: 'Voir les boutiques' },
    { path: '/client/orders', label: 'Mes commandes', button: 'Voir mes commandes' },
    { path: '/', label: 'Accueil', button: 'Aller à l’accueil' },
  ],
  stores: [
    { path: '/store/products', label: 'Mes produits', button: 'Voir mes produits' },
    { path: '/store/orders', label: 'Mes commandes', button: 'Voir mes commandes' },
    { path: '/store/subscription', label: 'Mon forfait', button: 'Voir mon forfait' },
    { path: '/store/finance', label: 'Ma finance', button: 'Voir ma finance' },
  ],
  drivers: [{ path: '/delivery/dashboard', label: 'Mes livraisons', button: 'Voir mes livraisons' }],
  everyone: [{ path: '/dashboard', label: 'Mon espace', button: 'Ouvrir Gaboshop' }],
  me: [
    { path: '/boutiques', label: 'Découvrir les boutiques', button: 'Voir les boutiques' },
    { path: '/notifications', label: 'Mes notifications', button: 'Voir mes notifications' },
  ],
};

const EMPTY = { audience: 'clients', title: '', body: '', link: '', action_label: '', send_push: true, urgent: false };

const pushSummary = (item) => {
  if (item.push_state === 'off') return 'Sans alerte téléphone';
  if (item.push_state === 'deferred') return 'Alerte téléphone programmée à 7 h';
  if (item.push_state === 'pending') return 'Alerte téléphone en cours d’envoi';
  return `${item.push_delivered} / ${item.push_attempted} appareil${item.push_attempted > 1 ? 's' : ''} alerté${item.push_delivered > 1 ? 's' : ''}`;
};

export default function AdminAnnouncementsSection() {
  const [form, setForm] = useState(EMPTY);
  const [data, setData] = useState(null);
  const [loadError, setLoadError] = useState('');
  const [confirming, setConfirming] = useState(false);
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    try {
      setData(await getAdminAnnouncements());
      setLoadError('');
    } catch {
      setLoadError('L’historique des annonces n’a pas pu être chargé. Vérifiez votre connexion puis réessayez.');
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const set = (patch) => {
    setConfirming(false);
    setForm((current) => ({ ...current, ...patch }));
  };

  const audience = AUDIENCES.find((item) => item.id === form.audience);
  const counts = data?.audiences?.[form.audience] || (form.audience === 'me' ? { recipients: 1, with_alerts: 0 } : null);
  const destinations = DESTINATIONS[form.audience] || [];
  const titleOk = form.title.trim().length >= 3;
  const bodyOk = form.body.trim().length >= 5;
  const canSend = titleOk && bodyOk && !sending;

  const chooseDestination = (path) => {
    const found = destinations.find((item) => item.path === path);
    set({ link: path, action_label: found ? found.button : '' });
  };

  const chooseAudience = (id) => {
    const keep = (DESTINATIONS[id] || []).some((item) => item.path === form.link);
    set({ audience: id, link: keep ? form.link : '', action_label: keep ? form.action_label : '' });
  };

  const submit = async () => {
    setSending(true);
    try {
      const sent = await sendAdminAnnouncement({
        ...form,
        title: form.title.trim(),
        body: form.body.trim(),
        send_push: form.send_push,
      });
      const where = `${sent.recipients_count} personne${sent.recipients_count > 1 ? 's' : ''}`;
      if (sent.push_mode === 'deferred') {
        notifySuccess('Annonce envoyée', `Elle est dans la cloche de ${where}. Il est tard : l’alerte sur les téléphones partira demain à 7 h, pour ne réveiller personne.`);
      } else if (sent.push_mode === 'now') {
        notifySuccess('Annonce envoyée', `Elle est dans la cloche de ${where}. L’alerte part à l’instant sur les téléphones et ordinateurs qui ont activé les alertes.`);
      } else {
        notifySuccess('Annonce envoyée', `Elle est dans la cloche de ${where}. Aucune alerte téléphone n’a été envoyée.`);
      }
      setForm((current) => ({ ...EMPTY, audience: current.audience }));
      setConfirming(false);
      load();
    } catch (error) {
      notifyError(error, { action: 'Envoyer l’annonce' });
    } finally {
      setSending(false);
    }
  };

  const onSend = () => {
    if (!canSend) return;
    if (form.audience === 'me') submit();
    else setConfirming(true);
  };

  const noAlertsWarning = useMemo(() => (
    data && data.push_enabled === false
      ? 'Les alertes téléphone sont coupées sur ce site : les annonces arrivent seulement dans la cloche.'
      : ''
  ), [data]);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Annonces</h2>
        <p className="mt-1 text-sm text-gray-600">
          Écrivez un message, choisissez à qui l’envoyer : il arrive dans la cloche de chacun et, pour ceux qui ont activé les alertes,
          sur leur téléphone ou leur ordinateur. Testez toujours d’abord avec « Moi seul ».
        </p>
      </div>

      {noAlertsWarning && <p className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">{noAlertsWarning}</p>}

      <div className="grid gap-6 lg:grid-cols-5">
        <section className="space-y-5 rounded-xl border border-gray-200 bg-white p-4 shadow-sm sm:p-6 lg:col-span-3" aria-label="Nouvelle annonce">
          <fieldset>
            <legend className="mb-2 text-sm font-bold text-gray-900">1. À qui ?</legend>
            <div className="grid gap-2 sm:grid-cols-2">
              {AUDIENCES.map((item) => {
                const stat = data?.audiences?.[item.id];
                const selected = form.audience === item.id;
                return (
                  <label
                    key={item.id}
                    className={`cursor-pointer rounded-lg border p-3 text-sm ${selected ? 'border-slate-900 bg-slate-50 ring-1 ring-slate-900' : 'border-gray-200 hover:bg-gray-50'}`}
                  >
                    <input type="radio" name="audience" value={item.id} checked={selected} onChange={() => chooseAudience(item.id)} className="sr-only" />
                    <span className="block font-semibold text-gray-900">{item.label}</span>
                    <span className="block text-xs text-gray-500">
                      {stat ? `${stat.recipients} personne${stat.recipients > 1 ? 's' : ''} · ${stat.with_alerts} avec alertes` : item.hint}
                    </span>
                  </label>
                );
              })}
            </div>
          </fieldset>

          <div>
            <label htmlFor="ann-title" className="mb-1 block text-sm font-bold text-gray-900">2. Titre</label>
            <input
              id="ann-title"
              type="text"
              maxLength={120}
              value={form.title}
              onChange={(e) => set({ title: e.target.value })}
              placeholder="Ex. 10 % sur les boissons ce week-end"
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
            />
            <p className="mt-1 text-right text-xs text-gray-400">{form.title.length} / 120</p>
          </div>

          <div>
            <label htmlFor="ann-body" className="mb-1 block text-sm font-bold text-gray-900">3. Message</label>
            <textarea
              id="ann-body"
              rows={4}
              maxLength={600}
              value={form.body}
              onChange={(e) => set({ body: e.target.value })}
              placeholder="Deux ou trois phrases simples : ce qui change, et ce que la personne peut faire."
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
            />
            <p className="mt-1 text-right text-xs text-gray-400">{form.body.length} / 600</p>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label htmlFor="ann-link" className="mb-1 block text-sm font-bold text-gray-900">4. Bouton (facultatif)</label>
              <select
                id="ann-link"
                value={form.link}
                onChange={(e) => chooseDestination(e.target.value)}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
              >
                <option value="">Aucun bouton</option>
                {destinations.map((item) => <option key={item.path} value={item.path}>{item.label}</option>)}
              </select>
            </div>
            {form.link && (
              <div>
                <label htmlFor="ann-label" className="mb-1 block text-sm font-bold text-gray-900">Texte du bouton</label>
                <input
                  id="ann-label"
                  type="text"
                  maxLength={40}
                  value={form.action_label}
                  onChange={(e) => set({ action_label: e.target.value })}
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-900"
                />
              </div>
            )}
          </div>

          <div className="space-y-2 text-sm">
            <label className="flex items-start gap-2">
              <input type="checkbox" checked={form.send_push} onChange={(e) => set({ send_push: e.target.checked })} className="mt-1" />
              <span><span className="font-semibold text-gray-900">Alerter aussi sur les téléphones et ordinateurs</span><br /><span className="text-gray-500">Pour ceux qui ont activé les alertes. Sinon, l’annonce reste dans la cloche.</span></span>
            </label>
            {form.send_push && (
              <label className="flex items-start gap-2">
                <input type="checkbox" checked={form.urgent} onChange={(e) => set({ urgent: e.target.checked })} className="mt-1" />
                <span><span className="font-semibold text-gray-900">Urgent : alerter même la nuit</span><br /><span className="text-gray-500">Sans cela, entre 21 h et 7 h, l’alerte téléphone attend 7 h (heure de Libreville).</span></span>
              </label>
            )}
          </div>

          {confirming ? (
            <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950" role="alertdialog" aria-label="Confirmer l’envoi">
              <p className="font-bold">Envoyer cette annonce à {counts ? counts.recipients : '?'} personne{counts && counts.recipients > 1 ? 's' : ''} ({audience.label.toLowerCase()}) ?</p>
              <p className="mt-1">
                {form.send_push && counts ? `${counts.with_alerts} seront alertées sur leur téléphone ou ordinateur. ` : ''}
                Un envoi ne peut pas être repris : vérifiez le texte.
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                <button type="button" onClick={submit} disabled={sending} className="rounded-lg bg-slate-900 px-4 py-2 font-semibold text-white disabled:opacity-60">
                  {sending ? 'Envoi…' : 'Oui, envoyer maintenant'}
                </button>
                <button type="button" onClick={() => setConfirming(false)} disabled={sending} className="rounded-lg border border-gray-300 bg-white px-4 py-2 font-semibold text-gray-800">
                  Modifier
                </button>
              </div>
            </div>
          ) : (
            <button
              type="button"
              onClick={onSend}
              disabled={!canSend}
              className="w-full rounded-lg bg-slate-900 px-4 py-3 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
            >
              {form.audience === 'me' ? 'M’envoyer un essai' : 'Envoyer l’annonce'}
            </button>
          )}
          {!canSend && (form.title || form.body) && (
            <p className="text-xs text-gray-500">
              {!titleOk ? 'Le titre doit faire au moins 3 caractères. ' : ''}{!bodyOk ? 'Le message doit faire au moins 5 caractères.' : ''}
            </p>
          )}
        </section>

        <aside className="lg:col-span-2" aria-label="Aperçu">
          <p className="mb-2 text-sm font-bold text-gray-900">Aperçu chez le destinataire</p>
          <div className="rounded-xl border border-indigo-200 bg-indigo-50/50 p-3">
            <div className="flex items-start gap-3">
              <span className="mt-0.5 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xl" aria-hidden="true">📣</span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-bold text-gray-900">{form.title.trim() || 'Votre titre apparaît ici'}</p>
                <p className="mt-0.5 whitespace-pre-line text-sm text-gray-600">{form.body.trim() || 'Votre message apparaît ici.'}</p>
                <p className="mt-1.5 text-xs text-gray-500">à l’instant · Annonce</p>
                {form.link && (
                  <span className="mt-2 inline-block rounded-lg bg-slate-900 px-3 py-1.5 text-xs font-semibold text-white">{form.action_label || 'Voir'}</span>
                )}
              </div>
            </div>
          </div>
          <p className="mt-2 text-xs text-gray-500">Les personnes qui ont coupé les annonces ou dont le compte est désactivé ne la reçoivent pas.</p>
        </aside>
      </div>

      <section aria-label="Historique des annonces">
        <h3 className="mb-3 text-lg font-bold text-gray-900">Historique</h3>
        {loadError && (
          <div className="mb-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            {loadError} <button type="button" onClick={load} className="ml-1 font-semibold underline">Réessayer</button>
          </div>
        )}
        {data && !data.announcements.length && <p className="rounded-lg border border-dashed border-gray-300 bg-white p-6 text-center text-sm text-gray-500">Aucune annonce envoyée pour le moment.</p>}
        <ul className="space-y-2">
          {(data?.announcements || []).map((item) => {
            const readRate = item.recipients_count ? Math.round((item.read_count / item.recipients_count) * 100) : 0;
            return (
              <li key={item.id} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <p className="font-semibold text-gray-900">{item.title}</p>
                  <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-semibold text-gray-700">{item.audience_label}</span>
                </div>
                <p className="mt-1 line-clamp-2 text-sm text-gray-600">{item.body}</p>
                <p className="mt-2 text-xs text-gray-500">
                  {formatDateTime(item.created_at)}{item.created_by_name ? ` · par ${item.created_by_name}` : ''}
                </p>
                <p className="mt-1 text-xs text-gray-700">
                  <strong>{item.recipients_count}</strong> reçue{item.recipients_count > 1 ? 's' : ''} · <strong>{item.read_count}</strong> lue{item.read_count > 1 ? 's' : ''} ({readRate} %) · {pushSummary(item)}
                </p>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}
