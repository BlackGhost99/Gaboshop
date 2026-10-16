import { useCallback, useEffect, useMemo, useState } from 'react';
import api from '../../../services/api';
import SearchSelect from '../../address/SearchSelect';
import { notifyError, notifySuccess, notifyWarning } from '../../../utils/feedback';

// Adresses : Province › Ville › Arrondissement › Quartier. Chaque quartier se rattache à une zone de prix
// (onglet Tarifs) : plusieurs quartiers partagent un tarif, changer le prix de la zone change tous ses quartiers.
const input = 'block w-full min-w-0 rounded-md border border-gray-300 p-2 text-sm';

export default function DeliveryAddresses() {
  const [data, setData] = useState(null);
  const [cityId, setCityId] = useState('');
  const [newCity, setNewCity] = useState({ province_id: '', name: '' });
  const [newArr, setNewArr] = useState('');
  const [newQuarter, setNewQuarter] = useState('');
  const [newQuarterArr, setNewQuarterArr] = useState('');
  const [arrFilter, setArrFilter] = useState('');
  const [filter, setFilter] = useState('');

  const load = useCallback(() => api.get('/admin/geo/all/').then((res) => {
    const d = res.data?.data;
    setData(d);
    setCityId((prev) => prev || (d?.cities.find((c) => c.is_open) || d?.cities[0] || {}).id || '');
  }).catch((err) => notifyError(err, { action: 'Charger les adresses' })), []);
  useEffect(() => { load(); }, [load]);

  const save = async (level, id, payload, done = 'Enregistré') => {
    try {
      if (id) await api.patch(`/admin/geo/${level}/${id}/`, payload);
      else await api.post(`/admin/geo/${level}/`, payload);
      notifySuccess(done);
      await load();
      return true;
    } catch (err) {
      notifyError(err, { action: 'Enregistrer' });
      return false;
    }
  };

  const city = data?.cities.find((c) => c.id === Number(cityId));
  const provinceName = (id) => (data?.provinces.find((p) => p.id === id) || {}).name || '';
  const arrs = useMemo(() => (data?.arrondissements || []).filter((a) => a.city_id === Number(cityId)), [data, cityId]);
  const zones = useMemo(() => (data?.zones || []).filter((z) => !city || (z.city || '').toLowerCase() === city.name.toLowerCase()), [data, city]);
  const quarters = useMemo(() => {
    const q = filter.trim().toLowerCase();
    return (data?.neighborhoods || []).filter((n) => n.city_id === Number(cityId) && (!q || n.name.toLowerCase().includes(q))
      && (!arrFilter || (arrFilter === 'none' ? !n.arrondissement_id : n.arrondissement_id === Number(arrFilter))));
  }, [data, cityId, filter, arrFilter]);
  const landmarksOf = (id) => (data?.landmarks || []).filter((l) => l.neighborhood_id === id);

  if (!data) return <p className="text-sm text-gray-500">Chargement…</p>;

  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
        <h3 className="text-lg font-semibold text-gray-900">Villes desservies</h3>
        <p className="mt-1 text-sm text-gray-600">
          Une ville fermée reste visible chez le client avec « Bientôt disponible ». Ouvrez-la quand ses quartiers et ses zones de prix sont prêts.
        </p>
        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
          <SearchSelect
            label="Ville"
            options={data.cities.map((c) => ({ value: c.id, label: c.name, hint: `${provinceName(c.province_id)}${c.is_open ? ' · ouverte' : ''}` }))}
            value={cityId}
            onChange={setCityId}
          />
          {city && (
            <div className="flex flex-wrap items-center gap-3 text-sm">
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={city.is_open} onChange={(e) => save('cities', city.id, { is_open: e.target.checked }, e.target.checked ? `${city.name} est ouverte aux livraisons` : `${city.name} est fermée`)} />
                Gaboshop livre à {city.name}
              </label>
              <label className="flex items-center gap-2">
                <input type="checkbox" checked={city.is_active} onChange={(e) => save('cities', city.id, { is_active: e.target.checked })} />
                Visible
              </label>
            </div>
          )}
        </div>
        <div className="mt-4 grid grid-cols-1 gap-2 md:grid-cols-3">
          <select className={input} value={newCity.province_id} onChange={(e) => setNewCity((v) => ({ ...v, province_id: e.target.value }))}>
            <option value="">Province de la nouvelle ville</option>
            {data.provinces.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <input className={input} placeholder="Nom de la ville" value={newCity.name} onChange={(e) => setNewCity((v) => ({ ...v, name: e.target.value }))} />
          <button type="button" className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white"
            onClick={async () => {
              if (!newCity.province_id || !newCity.name.trim()) { notifyWarning('Choisissez la province et tapez le nom.'); return; }
              if (await save('cities', null, newCity, 'Ville ajoutée (fermée)')) setNewCity({ province_id: '', name: '' });
            }}>Ajouter la ville</button>
        </div>
      </section>

      {city && (
        <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-900">Arrondissements de {city.name}</h3>
          <div className="mt-3 flex flex-wrap gap-2">
            {arrs.length === 0 && <span className="text-sm text-gray-500">Aucun : le client choisit directement son quartier.</span>}
            {arrs.map((a) => <span key={a.id} className="rounded-full bg-gray-100 px-3 py-1 text-sm">{a.name}</span>)}
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <input className={`${input} max-w-xs`} placeholder="Ex. 7e arrondissement" value={newArr} onChange={(e) => setNewArr(e.target.value)} />
            <button type="button" className="rounded-md border border-indigo-300 px-4 py-2 text-sm font-semibold text-indigo-700"
              onClick={async () => {
                if (!newArr.trim()) return;
                const number = parseInt(newArr, 10) || arrs.length + 1;
                if (await save('arrondissements', null, { city_id: city.id, name: newArr, number }, 'Arrondissement ajouté')) setNewArr('');
              }}>Ajouter</button>
          </div>
        </section>
      )}

      {city && (
        <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <h3 className="text-lg font-semibold text-gray-900">Quartiers de {city.name}</h3>
          <p className="mt-1 text-sm text-gray-600">
            Chaque quartier est rangé dans son arrondissement : le client voit seulement les quartiers de l'arrondissement choisi
            (un quartier « À préciser » n'est pas proposé). Le rangement de départ est une estimation, corrigez-le ici.
            Les zones phares (carrefour, marché…) aident le livreur. Sans zone de prix, le client paie le prix de livraison du commerce.
            {zones.length === 0 && ' Aucune zone de prix pour cette ville : créez-en dans l’onglet Tarifs.'}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {arrs.length > 0 && (
              <select className={`${input} max-w-xs`} value={newQuarterArr} onChange={(e) => setNewQuarterArr(e.target.value)}>
                <option value="">Arrondissement du quartier</option>
                {arrs.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
              </select>
            )}
            <input className={`${input} max-w-xs`} placeholder="Nouveau quartier" value={newQuarter} onChange={(e) => setNewQuarter(e.target.value)} />
            <button type="button" className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-semibold text-white"
              onClick={async () => {
                if (!newQuarter.trim()) return;
                if (arrs.length > 0 && !newQuarterArr) { notifyWarning("Choisissez l'arrondissement du quartier."); return; }
                if (await save('neighborhoods', null, { city_id: city.id, name: newQuarter, arrondissement_id: newQuarterArr || null }, 'Quartier ajouté')) setNewQuarter('');
              }}>Ajouter le quartier</button>
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            <input className={`${input} max-w-xs`} placeholder="🔎 Rechercher un quartier" value={filter} onChange={(e) => setFilter(e.target.value)} />
            {arrs.length > 0 && (
              <select className={`${input} max-w-xs`} value={arrFilter} onChange={(e) => setArrFilter(e.target.value)}>
                <option value="">Tous les arrondissements</option>
                {arrs.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
                <option value="none">À préciser</option>
              </select>
            )}
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500">
                  <th className="py-2 pr-3">Quartier</th>
                  <th className="py-2 pr-3">Arrondissement</th>
                  <th className="py-2 pr-3">Zone de prix</th>
                  <th className="py-2 pr-3">Zones phares</th>
                  <th className="py-2">Actif</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {quarters.map((n) => (
                  <tr key={n.id}>
                    <td className="py-2 pr-3">
                      <input className={input} defaultValue={n.name}
                        onBlur={(e) => { if (e.target.value.trim() && e.target.value.trim() !== n.name) save('neighborhoods', n.id, { name: e.target.value }, 'Quartier renommé'); }} />
                    </td>
                    <td className="py-2 pr-3">
                      <select className={input} value={n.arrondissement_id || ''} onChange={(e) => save('neighborhoods', n.id, { arrondissement_id: e.target.value || null })}>
                        <option value="">À préciser</option>
                        {arrs.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
                      </select>
                    </td>
                    <td className="py-2 pr-3">
                      <select className={input} value={n.zone_id || ''} onChange={(e) => save('neighborhoods', n.id, { zone_id: e.target.value || null })}>
                        <option value="">Prix du commerce</option>
                        {zones.map((z) => <option key={z.id} value={z.id}>{z.name}{z.is_active ? '' : ' (désactivée)'}</option>)}
                      </select>
                    </td>
                    <td className="py-2 pr-3">
                      <div className="flex min-w-[12rem] flex-wrap gap-1">
                        {landmarksOf(n.id).map((l) => (
                          <button key={l.id} type="button" title={l.is_active ? 'Masquer' : 'Réafficher'}
                            className={`rounded-full px-2 py-0.5 text-xs ${l.is_active ? 'bg-amber-100 text-amber-800' : 'bg-gray-100 text-gray-400 line-through'}`}
                            onClick={() => save('landmarks', l.id, { is_active: !l.is_active }, l.is_active ? 'Zone phare masquée' : 'Zone phare réaffichée')}>
                            {l.name}
                          </button>
                        ))}
                        <input className="w-32 rounded-md border border-gray-200 px-2 py-0.5 text-xs" placeholder="+ zone phare"
                          onKeyDown={async (e) => {
                            if (e.key !== 'Enter' || !e.currentTarget.value.trim()) return;
                            const box = e.currentTarget;
                            if (await save('landmarks', null, { neighborhood_id: n.id, name: box.value }, 'Zone phare ajoutée')) box.value = '';
                          }} />
                      </div>
                    </td>
                    <td className="py-2">
                      <input type="checkbox" checked={n.is_active} onChange={(e) => save('neighborhoods', n.id, { is_active: e.target.checked })} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
