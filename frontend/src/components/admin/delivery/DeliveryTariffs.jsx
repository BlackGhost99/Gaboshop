import { useCallback, useEffect, useState } from 'react';
import {
  deleteCityDistance, deleteDeliveryZone, getDeliveryTariffs, saveCityDistance, saveDeliveryZone,
  simulateDeliveryPrice, updateDeliveryDefaults, updateVehicleType,
} from '../../../services/adminService';
import { notifyError, notifySuccess, notifyWarning } from '../../../utils/feedback';

// Tarifs de livraison : tout ce qui fixe le prix payé par le client se règle ici.
const input = 'mt-1 block w-full rounded-md border border-gray-300 p-2 text-sm';
const fcfa = (v) => (v == null || v === '' ? '—' : `${Number(v).toLocaleString('fr-FR')} FCFA`);

function Section({ title, description, action, children }) {
  return (
    <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
          {description && <p className="mt-1 text-sm text-gray-600">{description}</p>}
        </div>
        {action}
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function ZoneEditor({ zone, vehicles, cities, onClose, onSaved }) {
  const [form, setForm] = useState(() => ({
    id: zone?.id, name: zone?.name || '', city: zone?.city || cities[0] || 'Libreville', description: zone?.description || '',
    is_active: zone?.is_active ?? true, inter_city_surcharge: zone?.inter_city_surcharge ?? 1000,
    rates: vehicles.map((v) => ({ vehicle_id: v.id, vehicle: v.label, price: zone?.rates?.find((r) => r.vehicle_id === v.id)?.price ?? '' })),
  }));
  const [saving, setSaving] = useState(false);
  const setRate = (vehicleId, price) => setForm((f) => ({ ...f, rates: f.rates.map((r) => (r.vehicle_id === vehicleId ? { ...r, price } : r)) }));

  const save = async () => {
    if (!form.name.trim()) { notifyWarning('Donnez un nom à la zone.', 'Par exemple : Akanda, Owendo, Centre-ville.'); return; }
    setSaving(true);
    try {
      const res = await saveDeliveryZone(form);
      notifySuccess(zone ? 'Zone modifiée' : 'Zone créée', `${res.data.name} (${res.data.city}) : les nouveaux prix s’appliquent aux prochaines commandes.`);
      onSaved();
    } catch (err) {
      notifyError(err, { action: 'Enregistrer la zone' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/40 p-0 sm:items-center sm:p-4">
      <div className="max-h-[92vh] w-full max-w-lg overflow-y-auto rounded-t-2xl bg-white p-5 sm:rounded-2xl">
        <h3 className="text-lg font-semibold">{zone ? `Modifier ${zone.name}` : 'Nouvelle zone de livraison'}</h3>
        <div className="mt-4 space-y-3">
          <label className="block text-sm font-medium">Nom de la zone
            <input className={input} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Ex. Akanda" />
          </label>
          <label className="block text-sm font-medium">Ville
            <select className={input} value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })}>
              {[...new Set([...cities, form.city])].map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </label>
          <label className="block text-sm font-medium">Quartiers couverts (facultatif)
            <input className={input} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </label>
          <div>
            <p className="text-sm font-medium">Prix de livraison payé par le client</p>
            <p className="text-xs text-gray-500">Laissez vide : le prix du commerce s’applique pour ce véhicule.</p>
            <div className="mt-2 grid grid-cols-2 gap-3">
              {form.rates.map((r) => (
                <label key={r.vehicle_id} className="block text-sm">{r.vehicle}
                  <input type="number" min="0" step="100" className={input} value={r.price ?? ''} onChange={(e) => setRate(r.vehicle_id, e.target.value)} placeholder="FCFA" />
                </label>
              ))}
            </div>
          </div>
          <label className="block text-sm font-medium">Supplément si le commerce est dans une autre ville (FCFA)
            <input type="number" min="0" step="100" className={input} value={form.inter_city_surcharge} onChange={(e) => setForm({ ...form, inter_city_surcharge: e.target.value })} />
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} />
            Zone proposée aux clients
          </label>
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-md bg-gray-200 px-4 py-2 text-sm">Annuler</button>
          <button type="button" disabled={saving} onClick={save} className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-60">
            {saving ? 'Enregistrement…' : 'Enregistrer'}
          </button>
        </div>
      </div>
    </div>
  );
}

function VehicleRow({ vehicle, onSaved }) {
  const [form, setForm] = useState(vehicle);
  const dirty = JSON.stringify(form) !== JSON.stringify(vehicle);
  const save = async () => {
    try {
      await updateVehicleType(vehicle.id, form);
      notifySuccess(`${vehicle.label} enregistré`, 'Les nouvelles limites et prix s’appliquent aux prochaines commandes.');
      onSaved();
    } catch (err) {
      notifyError(err, { action: `Enregistrer ${vehicle.label}` });
    }
  };
  const num = (key, label, step = 1) => (
    <label className="block text-xs text-gray-600">{label}
      <input type="number" min="0" step={step} className={input} value={form[key]} onChange={(e) => setForm({ ...form, [key]: e.target.value })} />
    </label>
  );
  return (
    <div className="rounded-lg border border-gray-200 p-4">
      <div className="flex items-center justify-between">
        <p className="font-semibold">{vehicle.label}</p>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} /> Actif
        </label>
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        {num('max_weight_kg', 'Poids max (kg)')}
        {num('max_length_m', 'Longueur max (m)', 0.1)}
        {num('max_items', 'Articles max (0 = sans limite)')}
        {num('max_distance_km', 'Distance max (km)')}
        {num('base_price_intra_city', 'Prix de base, même ville', 100)}
        {num('price_per_km_intra_city', 'Prix par km, même ville', 10)}
        {num('base_price_inter_city', 'Prix de base, autre ville', 100)}
        {num('price_per_km_inter_city', 'Prix par km, autre ville', 10)}
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2">
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={form.allow_intercity} onChange={(e) => setForm({ ...form, allow_intercity: e.target.checked })} /> Peut livrer dans une autre ville
        </label>
        {dirty && <button type="button" onClick={save} className="rounded-md bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white">Enregistrer</button>}
      </div>
    </div>
  );
}

function Simulator({ data }) {
  const [form, setForm] = useState({ zone_id: data.zones[0]?.id || '', vehicle_id: data.vehicles[0]?.id || '', store_city: data.cities[0] || 'Libreville', delivery_type: 'standard' });
  const [result, setResult] = useState(null);
  const run = async () => {
    try {
      const res = await simulateDeliveryPrice(form);
      setResult(res.data);
    } catch (err) {
      notifyError(err, { action: 'Calculer le prix' });
    }
  };
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <label className="block text-sm">Zone du client
          <select className={input} value={form.zone_id} onChange={(e) => setForm({ ...form, zone_id: e.target.value })}>
            {data.zones.map((z) => <option key={z.id} value={z.id}>{z.name} ({z.city})</option>)}
          </select>
        </label>
        <label className="block text-sm">Véhicule
          <select className={input} value={form.vehicle_id} onChange={(e) => setForm({ ...form, vehicle_id: e.target.value })}>
            {data.vehicles.map((v) => <option key={v.id} value={v.id}>{v.label}</option>)}
          </select>
        </label>
        <label className="block text-sm">Ville du commerce
          <select className={input} value={form.store_city} onChange={(e) => setForm({ ...form, store_city: e.target.value })}>
            {data.cities.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <label className="block text-sm">Type
          <select className={input} value={form.delivery_type} onChange={(e) => setForm({ ...form, delivery_type: e.target.value })}>
            <option value="standard">Standard</option>
            <option value="express">Express</option>
          </select>
        </label>
      </div>
      <button type="button" onClick={run} className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white">Calculer</button>
      {result && (
        <div className="rounded-lg bg-indigo-50 p-4 text-sm">
          <p className="text-lg font-bold text-indigo-900">Le client paie {fcfa(result.price)}</p>
          <p className="text-indigo-900">Livreur : {fcfa(result.courier_share)} · Gaboshop : {fcfa(result.gaboshop_share)}</p>
          <ul className="mt-2 list-disc pl-5 text-gray-700">{result.steps.map((s) => <li key={s}>{s}</li>)}</ul>
        </div>
      )}
    </div>
  );
}

export default function DeliveryTariffs() {
  const [data, setData] = useState(null);
  const [editingZone, setEditingZone] = useState(undefined);
  const [defaults, setDefaults] = useState(null);
  const [newDistance, setNewDistance] = useState({ from_city: '', to_city: '', distance_km: '', estimated_time_minutes: '' });

  const [tick, setTick] = useState(0);
  const load = useCallback(() => setTick((t) => t + 1), []);
  useEffect(() => {
    let alive = true;
    getDeliveryTariffs()
      .then((res) => { if (alive) { setData(res.data); setDefaults(res.data.defaults); } })
      .catch((err) => notifyError(err, { action: 'Charger les tarifs de livraison' }));
    return () => { alive = false; };
  }, [tick]);

  if (!data) return <p className="p-6 text-sm text-gray-600">Chargement des tarifs…</p>;

  const saveDefaults = async (applyToAll) => {
    try {
      const res = await updateDeliveryDefaults({ ...defaults, apply_to_all_stores: applyToAll });
      notifySuccess('Prix par défaut enregistrés', applyToAll
        ? `Appliqués aux ${res.data.stores_updated} commerces.`
        : 'Ils s’appliquent aux nouveaux commerces.');
      load();
    } catch (err) {
      notifyError(err, { action: 'Enregistrer les prix par défaut' });
    }
  };

  const removeZone = async (zone) => {
    if (!window.confirm(`Supprimer la zone ${zone.name} ?`)) return;
    try {
      await deleteDeliveryZone(zone.id);
      notifySuccess('Zone supprimée', `${zone.name} n’est plus proposée aux clients.`);
      load();
    } catch (err) {
      notifyError(err, { action: `Supprimer ${zone.name}` });
    }
  };

  const addDistance = async () => {
    try {
      await saveCityDistance(newDistance);
      notifySuccess('Distance ajoutée', `${newDistance.from_city} → ${newDistance.to_city} : ${newDistance.distance_km} km.`);
      setNewDistance({ from_city: '', to_city: '', distance_km: '', estimated_time_minutes: '' });
      load();
    } catch (err) {
      notifyError(err, { action: 'Ajouter la distance' });
    }
  };

  const removeDistance = async (row) => {
    try {
      await deleteCityDistance(row.id);
      notifySuccess('Distance supprimée', `${row.from_city} → ${row.to_city}`);
      load();
    } catch (err) {
      notifyError(err, { action: 'Supprimer la distance' });
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-lg bg-blue-50 p-4 text-sm text-blue-900">
        <p className="font-semibold">Comment le prix est calculé</p>
        <p className="mt-1">1. Si la zone du client a un prix pour le véhicule choisi, c’est ce prix. 2. Sinon, c’est le prix du commerce. 3. Si le commerce est dans une autre ville, le supplément s’ajoute. Le livreur reçoit {data.defaults.courier_share_percent} % (réglable dans Réglages).</p>
      </div>

      <Section title="Zones et prix" description="Les zones que le client choisit à la commande, avec le prix par véhicule."
        action={<button type="button" onClick={() => setEditingZone(null)} className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white">+ Nouvelle zone</button>}>
        {data.zones.length === 0 ? (
          <p className="text-sm text-gray-600">Aucune zone : le prix de chaque commerce s’applique partout. Créez une zone pour fixer vos prix.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-left text-gray-500">
                  <th className="py-2 pr-3">Zone</th>
                  {data.vehicles.map((v) => <th key={v.id} className="py-2 pr-3">{v.label}</th>)}
                  <th className="py-2 pr-3">Autre ville</th>
                  <th className="py-2" />
                </tr>
              </thead>
              <tbody>
                {data.zones.map((z) => (
                  <tr key={z.id} className={`border-b ${z.is_active ? '' : 'text-gray-400'}`}>
                    <td className="py-2 pr-3"><p className="font-medium">{z.name}</p><p className="text-xs text-gray-500">{z.city}{z.is_active ? '' : ' · désactivée'}</p></td>
                    {z.rates.map((r) => <td key={r.vehicle_id} className="py-2 pr-3 whitespace-nowrap">{r.price == null ? <span className="text-gray-400">prix du commerce</span> : fcfa(r.price)}</td>)}
                    <td className="py-2 pr-3 whitespace-nowrap">+{fcfa(z.inter_city_surcharge)}</td>
                    <td className="py-2 whitespace-nowrap text-right">
                      <button type="button" onClick={() => setEditingZone(z)} className="mr-2 text-indigo-600">Modifier</button>
                      <button type="button" onClick={() => removeZone(z)} className="text-red-600">Supprimer</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      <Section title="Prix quand aucune zone ne correspond" description="Prix d’un nouveau commerce. Chaque commerce garde ensuite son propre prix.">
        <div className="grid gap-3 md:grid-cols-3">
          <label className="block text-sm">Livraison standard (FCFA)
            <input type="number" min="0" step="100" className={input} value={defaults.default_delivery_fee} onChange={(e) => setDefaults({ ...defaults, default_delivery_fee: e.target.value })} />
          </label>
          <label className="block text-sm">Livraison express (FCFA)
            <input type="number" min="0" step="100" className={input} value={defaults.default_express_delivery_fee} onChange={(e) => setDefaults({ ...defaults, default_express_delivery_fee: e.target.value })} />
          </label>
          <label className="block text-sm">Supplément autre ville (FCFA)
            <input type="number" min="0" step="100" className={input} value={defaults.default_intercity_surcharge} onChange={(e) => setDefaults({ ...defaults, default_intercity_surcharge: e.target.value })} />
          </label>
        </div>
        <div className="mt-3 flex flex-wrap gap-2">
          <button type="button" onClick={() => saveDefaults(false)} className="rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white">Enregistrer</button>
          <button type="button" onClick={() => { if (window.confirm(`Mettre ces prix sur les ${data.stores_count} commerces ?`)) saveDefaults(true); }}
            className="rounded-md border border-indigo-600 px-3 py-2 text-sm font-medium text-indigo-700">Enregistrer et appliquer à tous les commerces</button>
        </div>
      </Section>

      <Section title="Simulateur" description="Vérifiez le prix qu’un client paierait avant de changer vos tarifs.">
        {data.zones.length && data.vehicles.length ? <Simulator data={data} /> : <p className="text-sm text-gray-600">Créez au moins une zone pour simuler un prix.</p>}
      </Section>

      <Section title="Véhicules" description="Ce que chaque véhicule peut transporter. Gaboshop choisit le plus petit véhicule qui convient à la commande.">
        <div className="space-y-3">{data.vehicles.map((v) => <VehicleRow key={`${v.id}-${JSON.stringify(v)}`} vehicle={v} onSaved={load} />)}</div>
      </Section>

      <Section title="Distances entre villes" description="Utilisées pour les livraisons d’une ville à une autre.">
        <div className="space-y-2">
          {data.distances.map((d) => (
            <div key={d.id} className="flex items-center justify-between rounded-md border border-gray-100 px-3 py-2 text-sm">
              <span>{d.from_city} → {d.to_city} : <b>{d.distance_km} km</b>, environ {d.estimated_time_minutes} min</span>
              <button type="button" onClick={() => removeDistance(d)} className="text-red-600">Supprimer</button>
            </div>
          ))}
          <div className="grid grid-cols-2 gap-2 pt-2 md:grid-cols-5">
            <select className={input} value={newDistance.from_city} onChange={(e) => setNewDistance({ ...newDistance, from_city: e.target.value })}>
              <option value="">De…</option>{data.cities.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <select className={input} value={newDistance.to_city} onChange={(e) => setNewDistance({ ...newDistance, to_city: e.target.value })}>
              <option value="">Vers…</option>{data.cities.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
            <input type="number" min="0" className={input} placeholder="km" value={newDistance.distance_km} onChange={(e) => setNewDistance({ ...newDistance, distance_km: e.target.value })} />
            <input type="number" min="1" className={input} placeholder="minutes" value={newDistance.estimated_time_minutes} onChange={(e) => setNewDistance({ ...newDistance, estimated_time_minutes: e.target.value })} />
            <button type="button" onClick={addDistance} className="mt-1 rounded-md bg-indigo-600 px-3 py-2 text-sm font-medium text-white">Ajouter</button>
          </div>
        </div>
      </Section>

      {editingZone !== undefined && (
        <ZoneEditor zone={editingZone} vehicles={data.vehicles} cities={data.cities}
          onClose={() => setEditingZone(undefined)} onSaved={() => { setEditingZone(undefined); load(); }} />
      )}
    </div>
  );
}
