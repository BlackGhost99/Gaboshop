import { useCallback, useEffect, useState } from 'react';
import { assignDeliveryAgent, getDeliveryIncidents, getDeliveryOperations, getAdminDeliveryStats, getDeliveryProofPhoto } from '../../../services/adminService';
import { notifyError, notifySuccess } from '../../../utils/feedback';
import useVisibleInterval from '../../../hooks/useVisibleInterval';

const fcfa = (v) => `${Number(v || 0).toLocaleString('fr-FR')} FCFA`;
const since = (minutes) => {
  if (minutes == null) return '';
  if (minutes < 60) return `${minutes} min`;
  const h = Math.floor(minutes / 60);
  return h < 48 ? `${h} h ${minutes % 60} min` : `${Math.floor(h / 24)} j`;
};

function Empty({ children }) {
  return <p className="rounded-lg border border-dashed border-gray-300 bg-gray-50 p-6 text-center text-sm text-gray-600">{children}</p>;
}

function useOperations() {
  const [data, setData] = useState(null);
  const [tick, setTick] = useState(0);
  const load = useCallback(() => setTick((t) => t + 1), []);
  useEffect(() => {
    let alive = true;
    getDeliveryOperations()
      .then((res) => { if (alive) setData(res.data); })
      .catch((err) => notifyError(err, { action: 'Charger les livraisons' }));
    return () => { alive = false; };
  }, [tick]);
  useVisibleInterval(load, 30000);
  return [data, load];
}

const PROOF_LABELS = { id_card: 'Pièce d’identité', package: 'Photo du colis', photo: 'Photo de livraison', signature: 'Signature' };

function ProofPhotos({ row }) {
  const [shown, setShown] = useState(null);
  useEffect(() => () => { if (shown) URL.revokeObjectURL(shown.url); }, [shown]);
  if (!row.proof_photos?.length) return null;
  const open = async (kind) => {
    try {
      const blob = await getDeliveryProofPhoto(row.id, kind);
      setShown({ kind, url: URL.createObjectURL(blob) });
    } catch (err) {
      notifyError(err, { action: 'Afficher la preuve de livraison' });
    }
  };
  return (
    <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
      <span className="text-gray-600">Preuve :</span>
      {row.proof_photos.map((kind) => (
        <button key={kind} type="button" onClick={() => open(kind)} className="rounded-md border border-gray-300 bg-white px-2 py-1 text-indigo-700 hover:bg-gray-50">
          {PROOF_LABELS[kind] || kind}
        </button>
      ))}
      {shown && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4" onClick={() => setShown(null)}>
          <div className="max-h-full max-w-3xl rounded-lg bg-white p-3" onClick={(e) => e.stopPropagation()}>
            <div className="mb-2 flex items-center justify-between gap-4">
              <p className="font-semibold">{PROOF_LABELS[shown.kind]} · #{row.order_number}</p>
              <button type="button" onClick={() => setShown(null)} className="rounded-md px-2 py-1 text-gray-600 hover:bg-gray-100">Fermer</button>
            </div>
            <img src={shown.url} alt={PROOF_LABELS[shown.kind]} className="max-h-[75vh] w-auto rounded" />
            <p className="mt-2 text-xs text-gray-500">Document privé : ne le partagez pas. Chaque consultation est enregistrée.</p>
          </div>
        </div>
      )}
    </div>
  );
}

function DeliveryCard({ row, children }) {
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <p className="font-semibold">#{row.order_number} · {row.store}</p>
          <p className="text-sm text-gray-600">{row.zone || row.city} · {row.address}</p>
          <p className="text-sm text-gray-600">Client : <a className="text-indigo-600" href={`tel:${row.client_phone}`}>{row.client_phone}</a> · {fcfa(row.delivery_fee)}</p>
        </div>
        <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-700">{row.status_label}</span>
      </div>
      {children}
    </div>
  );
}

export function DeliveryDispatch() {
  const [data, load] = useOperations();
  const [choice, setChoice] = useState({});
  if (!data) return <p className="p-6 text-sm text-gray-600">Chargement…</p>;

  const assign = async (row) => {
    const agentId = choice[row.id];
    if (!agentId) return;
    const courier = data.couriers.find((c) => String(c.id) === String(agentId));
    try {
      await assignDeliveryAgent(row.order_id, agentId);
      notifySuccess('Livreur attribué', `${courier?.name} a reçu la course #${row.order_number}. Il doit l’accepter dans son application.`);
      load();
    } catch (err) {
      notifyError(err, { action: `Attribuer la course #${row.order_number}` });
    }
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600">Courses qui n’ont pas encore de livreur. La liste se met à jour toute seule.</p>
      {data.waiting.length === 0 ? <Empty>Aucune course en attente de livreur.</Empty> : data.waiting.map((row) => (
        <DeliveryCard key={row.id} row={row}>
          <p className="mt-2 text-sm text-amber-700">En attente depuis {since(row.minutes_waiting)}{row.order_status !== 'ready' ? ' · le commerce prépare encore la commande' : ''}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <select className="min-w-0 flex-1 rounded-md border border-gray-300 p-2 text-sm" value={choice[row.id] || ''} onChange={(e) => setChoice({ ...choice, [row.id]: e.target.value })}>
              <option value="">Choisir un livreur…</option>
              {data.couriers.map((c) => (
                <option key={c.id} value={c.id} disabled={c.active_deliveries >= data.max_active_per_courier}>
                  {c.name} · {c.city} · {c.available ? 'disponible' : 'indisponible'} · {c.active_deliveries} en cours{c.has_mobile_money ? '' : ' · sans Mobile Money'}
                </option>
              ))}
            </select>
            <button type="button" disabled={!choice[row.id] || row.order_status !== 'ready'} onClick={() => assign(row)}
              className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50">Attribuer</button>
          </div>
        </DeliveryCard>
      ))}
    </div>
  );
}

export function DeliveryActive() {
  const [data] = useOperations();
  if (!data) return <p className="p-6 text-sm text-gray-600">Chargement…</p>;
  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600">{data.active.length} course(s) en cours.</p>
      {data.active.length === 0 ? <Empty>Aucune livraison en cours.</Empty> : data.active.map((row) => (
        <DeliveryCard key={row.id} row={row}>
          <p className="mt-2 text-sm">Livreur : <b>{row.agent_name}</b> · <a className="text-indigo-600" href={`tel:${row.agent_phone}`}>{row.agent_phone}</a> · depuis {since(row.minutes_waiting)}</p>
          <ProofPhotos row={row} />
        </DeliveryCard>
      ))}
    </div>
  );
}

export function DeliveryStats() {
  const [days, setDays] = useState(7);
  const [data, setData] = useState(null);
  useEffect(() => {
    getAdminDeliveryStats(days).then((res) => setData(res.data)).catch((err) => notifyError(err, { action: 'Charger les statistiques' }));
  }, [days]);
  if (!data) return <p className="p-6 text-sm text-gray-600">Chargement…</p>;
  const tiles = [
    ['Courses', data.total], ['Livrées', data.delivered], ['Échouées ou annulées', data.failed],
    ['Durée moyenne', data.average_minutes == null ? '—' : since(data.average_minutes)],
    ['Frais de livraison encaissés', fcfa(data.delivery_fees)], ['Payé aux livreurs', fcfa(data.courier_paid)],
    ['Reste à payer aux livreurs', fcfa(data.courier_owed)],
  ];
  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        {[1, 7, 30].map((d) => (
          <button key={d} type="button" onClick={() => setDays(d)}
            className={`rounded-full px-3 py-1 text-sm ${days === d ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-700'}`}>
            {d === 1 ? 'Aujourd’hui' : `${d} jours`}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {tiles.map(([label, value]) => (
          <div key={label} className="rounded-lg border border-gray-200 bg-white p-4">
            <p className="text-xs text-gray-500">{label}</p>
            <p className="mt-1 text-lg font-bold text-gray-900">{value}</p>
          </div>
        ))}
      </div>
      <div className="overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table className="min-w-full text-sm">
          <thead><tr className="border-b text-left text-gray-500">
            <th className="p-3">Livreur</th><th className="p-3">Courses</th><th className="p-3">Livrées</th><th className="p-3">Échecs</th><th className="p-3">Payé</th><th className="p-3">À payer</th>
          </tr></thead>
          <tbody>
            {data.per_courier.length === 0 ? (
              <tr><td colSpan="6" className="p-4 text-center text-gray-500">Aucune course sur la période.</td></tr>
            ) : data.per_courier.map((c) => (
              <tr key={c.id} className="border-b">
                <td className="p-3 font-medium">{c.name}</td><td className="p-3">{c.total}</td><td className="p-3">{c.delivered}</td>
                <td className="p-3">{c.failed}</td><td className="p-3">{fcfa(c.paid)}</td><td className="p-3">{fcfa(c.owed)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const KIND_STYLE = {
  late: 'border-amber-200 bg-amber-50', no_courier: 'border-red-200 bg-red-50', failed: 'border-red-200 bg-red-50',
  unconfirmed: 'border-blue-200 bg-blue-50', payout: 'border-purple-200 bg-purple-50',
};

export function DeliveryIncidents() {
  const [items, setItems] = useState(null);
  const load = useCallback(() => {
    getDeliveryIncidents().then((res) => setItems(res.data)).catch((err) => notifyError(err, { action: 'Charger les incidents' }));
  }, []);
  useEffect(() => { load(); }, [load]);
  useVisibleInterval(load, 60000);
  if (!items) return <p className="p-6 text-sm text-gray-600">Chargement…</p>;
  if (!items.length) return <Empty>Aucun incident : tout se passe bien.</Empty>;
  return (
    <div className="space-y-3">
      {items.map((item, i) => (
        <div key={`${item.kind}-${item.id || item.order_number}-${i}`} className={`rounded-lg border p-4 ${KIND_STYLE[item.kind] || 'border-gray-200 bg-white'}`}>
          <p className="font-semibold">{item.title}{item.order_number ? ` · #${item.order_number}` : ''}</p>
          <p className="mt-1 text-sm"><b>Pourquoi : </b>{item.reason}</p>
          <p className="text-sm"><b>Que faire : </b>{item.next_step}</p>
          <p className="mt-1 text-xs text-gray-600">
            {item.store && <>Commerce : {item.store} · </>}
            {item.agent_name && <>Livreur : {item.agent_name} <a className="text-indigo-600" href={`tel:${item.agent_phone}`}>{item.agent_phone}</a> · </>}
            {item.client_phone && <>Client : <a className="text-indigo-600" href={`tel:${item.client_phone}`}>{item.client_phone}</a></>}
            {item.amount != null && <> · {fcfa(item.amount)}</>}
          </p>
          <ProofPhotos row={item} />
        </div>
      ))}
    </div>
  );
}
