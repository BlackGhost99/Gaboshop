import React, { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import StoreLayout from '../../components/StoreLayout';
import Modal from '../../components/Modal';
import ConfirmModal from '../../components/ConfirmModal';
import api from '../../services/api';
import { describeError, notifyError, notifySuccess, notifyWarning } from '../../utils/feedback';

// Accès API du grossiste : clés d'intégration pour relier stock et commandes à ses logiciels.
// GET/POST /b2b/api-keys/ et POST /b2b/api-keys/<id>/revoke/ (session normale). La clé complète n'est montrée qu'une fois.

const apiBase = () => {
  const env = import.meta.env.VITE_API_URL;
  const origin = env ? env.replace(/\/$/, '') : window.location.origin;
  return `${origin}/api/v1`;
};

const formatDate = (iso) => (iso
  ? new Date(iso).toLocaleString('fr-FR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  : null);

const formatMoney = (value) => `${Math.round(Number(value) || 0).toLocaleString('fr-FR')} F`;

const ENDPOINTS = [
  { method: 'GET', path: '/b2b/integration/products/', text: 'Vos produits avec stock, prix et statut (filtres : search, is_available, page, page_size).' },
  { method: 'PATCH', path: '/b2b/integration/products/{id}/', text: 'Met à jour le stock et le prix d’un produit (stock 0 ou plus, prix supérieur à 0).' },
  { method: 'GET', path: '/b2b/integration/orders/', text: 'Commandes reçues, du plus récent au plus ancien (filtres : status, page, page_size).' },
  { method: 'GET', path: '/b2b/integration/orders/{id}/', text: 'Détail d’une commande : articles, quantités, prix et adresse de livraison.' },
];

const copyText = async (text) => {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const area = document.createElement('textarea');
  area.value = text;
  area.setAttribute('readonly', '');
  area.style.position = 'fixed';
  area.style.opacity = '0';
  document.body.appendChild(area);
  area.select();
  const ok = document.execCommand('copy');
  document.body.removeChild(area);
  if (!ok) throw new Error('Copie impossible.');
};

const CopyButton = ({ text, label = 'Copier', done = 'Copié dans le presse-papiers.' }) => {
  const [copied, setCopied] = useState(false);
  const onCopy = async () => {
    try {
      await copyText(text);
      setCopied(true);
      notifySuccess(done);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      notifyWarning('La copie automatique a échoué.', 'Sélectionnez le texte à la main, puis copiez-le.');
    }
  };
  return (
    <button
      type="button"
      onClick={onCopy}
      className="shrink-0 rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-semibold text-gray-800 hover:bg-gray-50"
    >
      {copied ? 'Copié' : label}
    </button>
  );
};

const StatusBadge = ({ active, suspended }) => {
  if (!active) return <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-semibold text-gray-600">Révoquée</span>;
  if (suspended) return <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-semibold text-amber-800">Suspendue (forfait)</span>;
  return <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-semibold text-emerald-800">Active</span>;
};

const LockedPanel = ({ data }) => (
  <section className="rounded-2xl border border-indigo-200 bg-indigo-50 p-4 sm:p-6">
    <h3 className="text-lg font-bold text-indigo-900">L’accès API n’est pas inclus dans votre forfait</h3>
    <p className="mt-1 break-words text-sm text-indigo-800">
      {data.message || `L’accès API ne fait pas partie de votre forfait actuel${data.plan_name ? ` (${data.plan_name})` : ''}.`}
    </p>
    {data.required_plan ? (
      <p className="mt-2 text-sm text-indigo-900">
        Forfait qui l’offre : <span className="font-semibold">{data.required_plan.name}</span>
        {' '}({formatMoney(data.required_plan.price)} par mois).
      </p>
    ) : (
      <p className="mt-2 text-sm text-indigo-900">Aucun forfait en vente ne l’offre pour le moment.</p>
    )}
    <Link
      to="/store/subscription"
      className="mt-4 inline-flex items-center rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-md hover:bg-indigo-700"
    >
      Voir mon forfait
    </Link>
  </section>
);

const ApiDocs = ({ sampleKey }) => {
  const base = apiBase();
  const key = sampleKey || 'VOTRE_CLE_API';
  return (
    <section className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm sm:p-6">
      <h3 className="text-lg font-bold text-gray-900">Utiliser l’API</h3>
      <p className="mt-1 text-sm text-gray-600">
        Chaque requête porte votre clé dans l’en-tête <code className="rounded bg-gray-100 px-1">Authorization: Api-Key &lt;clé&gt;</code>{' '}
        (ou <code className="rounded bg-gray-100 px-1">X-API-Key</code>). Limite : 60 requêtes par minute et par clé.
        L’API lit vos produits et vos commandes reçues, et ne modifie que le stock et le prix : aucune action sur l’argent n’est possible.
      </p>
      <ul className="mt-4 space-y-2">
        {ENDPOINTS.map((e) => (
          <li key={e.method + e.path} className="min-w-0 text-sm">
            <p className="break-all">
              <span className="mr-2 rounded bg-slate-900 px-2 py-0.5 text-xs font-bold text-white">{e.method}</span>
              <code className="text-gray-900">{e.path}</code>
            </p>
            <p className="mt-0.5 text-gray-600">{e.text}</p>
          </li>
        ))}
      </ul>
      <p className="mt-5 text-sm font-semibold text-gray-900">Exemple : lire vos commandes payées</p>
      <pre className="mt-1 overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">{`curl -H "Authorization: Api-Key ${key}" \\
  "${base}/b2b/integration/orders/?status=paid"`}</pre>
      <p className="mt-4 text-sm font-semibold text-gray-900">Exemple : mettre à jour le stock et le prix d’un produit</p>
      <pre className="mt-1 overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-100">{`curl -X PATCH \\
  -H "Authorization: Api-Key ${key}" \\
  -H "Content-Type: application/json" \\
  -d '{"stock": 120, "price": "15000"}' \\
  "${base}/b2b/integration/products/12/"`}</pre>
    </section>
  );
};

const ApiAccess = () => {
  const [state, setState] = useState({ loading: true, data: null, error: null });
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState('');
  const [creating, setCreating] = useState(false);
  const [fieldError, setFieldError] = useState('');
  const [created, setCreated] = useState(null);
  const [revoking, setRevoking] = useState(null);

  const load = useCallback(async () => {
    try {
      const res = await api.get('/b2b/api-keys/');
      if (res.data?.success) {
        setState({ loading: false, data: res.data.data, error: null });
      } else {
        setState((prev) => ({ loading: false, data: prev.data, error: describeError(res.data || {}, "L'accès API n'a pas pu être chargé.") }));
      }
    } catch (err) {
      setState((prev) => ({ loading: false, data: prev.data, error: describeError(err, "L'accès API n'a pas pu être chargé.") }));
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const closeCreate = () => {
    setCreateOpen(false);
    setName('');
    setFieldError('');
  };

  const submitCreate = async (event) => {
    event.preventDefault();
    if (!name.trim()) {
      setFieldError('Donnez un nom à cette clé (ex. « Logiciel de caisse »).');
      return;
    }
    setCreating(true);
    try {
      const res = await api.post('/b2b/api-keys/', { name: name.trim() });
      setCreated({ key: res.data.data.api_key, name: res.data.data.key.name, warning: res.data.data.warning });
      closeCreate();
      await load();
    } catch (err) {
      notifyError(err, { action: 'Créer la clé API' });
    } finally {
      setCreating(false);
    }
  };

  const confirmRevoke = async () => {
    try {
      const res = await api.post(`/b2b/api-keys/${revoking.id}/revoke/`);
      notifySuccess(res.data?.message || 'Clé révoquée.');
      await load();
      return true;
    } catch (err) {
      notifyError(err, { action: 'Révoquer la clé API' });
      return false;
    }
  };

  const { loading, data, error } = state;

  if (loading) {
    return (
      <StoreLayout title="Accès API">
        <div className="flex min-h-[40vh] items-center justify-center" role="status" aria-label="Chargement de l'accès API">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent" />
        </div>
      </StoreLayout>
    );
  }

  if (error && !data) {
    return (
      <StoreLayout title="Accès API">
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-red-800 sm:p-6">
          <p className="font-bold">{error.message}</p>
          {error.reason && <p className="mt-1 break-words text-sm">{error.reason}</p>}
          {error.nextStep && <p className="mt-1 break-words text-sm">{error.nextStep}</p>}
          <button
            type="button"
            onClick={() => { setState({ loading: true, data: null, error: null }); load(); }}
            className="mt-4 rounded-lg bg-red-600 px-5 py-2 text-sm font-semibold text-white hover:bg-red-700"
          >
            Réessayer
          </button>
        </div>
      </StoreLayout>
    );
  }

  const keys = data.keys || [];
  const activeKeys = keys.filter((k) => k.is_active);
  const full = data.active_count >= data.max_active_keys;

  return (
    <StoreLayout title="Accès API">
      <div className="space-y-6">
        <p className="max-w-3xl text-sm text-gray-600">
          Reliez votre stock et vos commandes à vos logiciels (caisse, comptabilité, site web) avec des clés d’intégration.
          Chaque clé ne donne accès qu’à votre boutique.
        </p>

        {!data.enabled && <LockedPanel data={data} />}

        {(data.enabled || keys.length > 0) && (
          <section className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm sm:p-6">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="text-lg font-bold text-gray-900">Vos clés</h3>
                <p className="text-sm text-gray-500">{data.active_count} active{data.active_count > 1 ? 's' : ''} sur {data.max_active_keys} au maximum</p>
              </div>
              {data.enabled && (
                <button
                  type="button"
                  onClick={() => setCreateOpen(true)}
                  disabled={full}
                  title={full ? 'Révoquez une clé pour en créer une nouvelle.' : undefined}
                  className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-md hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Créer une clé
                </button>
              )}
            </div>
            {data.enabled && full && (
              <p className="mt-2 text-sm text-amber-700">Vous avez atteint {data.max_active_keys} clés actives : révoquez-en une pour en créer une nouvelle.</p>
            )}

            {keys.length === 0 ? (
              <p className="mt-4 rounded-xl bg-gray-50 p-4 text-sm text-gray-600">
                Aucune clé pour le moment. Créez-en une, puis collez-la dans le logiciel à relier.
              </p>
            ) : (
              <ul className="mt-4 divide-y divide-gray-100">
                {keys.map((k) => (
                  <li key={k.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                    <div className="min-w-0">
                      <p className="break-words font-semibold text-gray-900">{k.name}</p>
                      <p className="text-sm text-gray-600">
                        <code className="rounded bg-gray-100 px-1">{k.prefix}…</code>
                        {' · '}créée le {formatDate(k.created_at)}
                      </p>
                      <p className="text-xs text-gray-500">
                        {k.revoked_at
                          ? `Révoquée le ${formatDate(k.revoked_at)}`
                          : k.last_used_at ? `Dernière utilisation : ${formatDate(k.last_used_at)}` : 'Jamais utilisée'}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <StatusBadge active={k.is_active} suspended={k.is_active && !data.enabled} />
                      {k.is_active && (
                        <button
                          type="button"
                          onClick={() => setRevoking(k)}
                          className="rounded-lg border border-red-300 bg-white px-3 py-1.5 text-sm font-semibold text-red-700 hover:bg-red-50"
                        >
                          Révoquer
                        </button>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
            {!data.enabled && activeKeys.length > 0 && (
              <p className="mt-3 text-sm text-amber-700">
                Ces clés sont suspendues tant que votre forfait n’inclut pas l’accès API : elles repartent dès qu’il le redevient.
              </p>
            )}
          </section>
        )}

        {data.enabled && <ApiDocs />}
      </div>

      <Modal isOpen={createOpen} onClose={closeCreate} title="Créer une clé API" size="sm" loading={creating}>
        <form onSubmit={submitCreate} className="space-y-4">
          <div>
            <label htmlFor="api-key-name" className="block text-sm font-semibold text-gray-800">Nom de la clé</label>
            <input
              id="api-key-name"
              type="text"
              value={name}
              maxLength={80}
              onChange={(e) => { setName(e.target.value); setFieldError(''); }}
              placeholder="Ex. Logiciel de caisse"
              className="mt-1 w-full rounded-lg border border-gray-300 px-3 py-2 text-base focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              autoFocus
            />
            <p className="mt-1 text-xs text-gray-500">Ce nom vous aide à retrouver quel logiciel utilise la clé.</p>
            {fieldError && <p className="mt-1 text-sm text-red-600" role="alert">{fieldError}</p>}
          </div>
          <div className="flex justify-end gap-3">
            <button type="button" onClick={closeCreate} disabled={creating} className="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 hover:bg-gray-50 disabled:opacity-50">
              Annuler
            </button>
            <button type="submit" disabled={creating} className="rounded-lg bg-indigo-600 px-4 py-2 font-semibold text-white hover:bg-indigo-700 disabled:opacity-50">
              {creating ? 'Création…' : 'Créer la clé'}
            </button>
          </div>
        </form>
      </Modal>

      <Modal isOpen={Boolean(created)} onClose={() => setCreated(null)} title="Votre nouvelle clé" size="md" showCloseButton={false}>
        {created && (
          <div className="space-y-4">
            <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
              <p className="font-bold">Copiez cette clé maintenant.</p>
              <p className="mt-1">Elle ne sera plus jamais affichée : Gaboshop n’en garde pas de copie lisible. Si vous la perdez, révoquez-la et créez-en une autre.</p>
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-800">{created.name}</p>
              <div className="mt-1 flex items-center gap-2">
                <code className="min-w-0 flex-1 break-all rounded-lg bg-slate-900 px-3 py-2 text-sm text-slate-100">{created.key}</code>
                <CopyButton text={created.key} done="Clé copiée dans le presse-papiers." />
              </div>
            </div>
            <p className="text-xs text-gray-500">{created.warning}</p>
            <div className="flex justify-end">
              <button type="button" onClick={() => setCreated(null)} className="rounded-lg bg-indigo-600 px-4 py-2 font-semibold text-white hover:bg-indigo-700">
                J’ai copié la clé
              </button>
            </div>
          </div>
        )}
      </Modal>

      <ConfirmModal
        isOpen={Boolean(revoking)}
        onClose={() => setRevoking(null)}
        title="Révoquer cette clé ?"
        message={revoking ? `Les logiciels qui utilisent la clé « ${revoking.name} » (${revoking.prefix}…) perdront l’accès tout de suite. Cette action est définitive.` : ''}
        confirmText="Révoquer la clé"
        variant="danger"
        onConfirm={confirmRevoke}
      />
    </StoreLayout>
  );
};

export default ApiAccess;
