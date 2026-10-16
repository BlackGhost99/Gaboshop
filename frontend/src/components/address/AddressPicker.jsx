import { useEffect, useMemo } from 'react';
import SearchSelect from './SearchSelect';

/** Province › Ville › Arrondissement › Quartier › Zone phare : chaque liste dépend de la précédente, avec recherche.
 *  Le client ne tape jamais sa zone. `value` : { province_id, city_id, arrondissement_id, neighborhood, landmark } ;
 *  `onChange(patch)` reçoit aussi `city` et `zone` (noms) pour le devis et la commande. */
export default function AddressPicker({ geo, value = {}, onChange }) {
  const cities = useMemo(() => (geo?.cities || []).filter((c) => !value.province_id || c.province_id === Number(value.province_id)), [geo, value.province_id]);
  const city = (geo?.cities || []).find((c) => c.id === Number(value.city_id));
  const arrondissements = useMemo(() => (geo?.arrondissements || []).filter((a) => a.city_id === Number(value.city_id)), [geo, value.city_id]);
  const hasArr = arrondissements.length > 0;
  // Ville à arrondissements : seuls les quartiers de l'arrondissement choisi. Sinon : tous ceux de la ville.
  const neighborhoods = useMemo(() => (geo?.neighborhoods || []).filter((n) => n.city_id === Number(value.city_id)
    && (hasArr ? !!value.arrondissement_id && n.arrondissement_id === Number(value.arrondissement_id) : true)), [geo, value.city_id, value.arrondissement_id, hasArr]);
  const landmarks = useMemo(() => (geo?.landmarks || []).filter((l) => l.neighborhood_id === Number(value.neighborhood)), [geo, value.neighborhood]);
  const quartersOf = (arrId) => (geo?.neighborhoods || []).filter((n) => n.arrondissement_id === arrId).map((n) => n.name);

  // Par défaut : la première ville ouverte (Libreville au lancement).
  useEffect(() => {
    if (!geo || value.city_id) return;
    const first = geo.cities.find((c) => c.is_open);
    if (first) onChange({ province_id: first.province_id, city_id: first.id, city: first.name, arrondissement_id: '', neighborhood: '', zone: '' });
  }, [geo]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!geo) return null;
  // Changer d'adresse retire aussi la position GPS partagée : elle désignait l'ancienne adresse.
  const reset = { neighborhood: '', landmark: '', zone: '', latitude: null, longitude: null };

  return (
    <>
      <SearchSelect
        label="Province"
        options={geo.provinces.map((p) => ({ value: p.id, label: p.name }))}
        value={value.province_id}
        onChange={(id) => onChange({ province_id: id, city_id: '', city: '', arrondissement_id: '', ...reset })}
      />
      <SearchSelect
        label="Ville"
        options={cities.map((c) => ({ value: c.id, label: c.name, disabled: !c.is_open, hint: c.is_open ? '' : 'Bientôt disponible' }))}
        value={value.city_id}
        onChange={(id) => {
          const c = geo.cities.find((x) => x.id === Number(id));
          onChange({ province_id: c?.province_id || value.province_id, city_id: id, city: c?.name || '', arrondissement_id: '', ...reset });
        }}
      />
      {hasArr && (
        <SearchSelect
          label="Arrondissement"
          placeholder="Arrondissement (tapez aussi votre quartier)"
          options={arrondissements.map((a) => {
            const names = quartersOf(a.id);
            return { value: a.id, label: a.name, hint: names.slice(0, 4).join(', ') + (names.length > 4 ? '…' : ''), search: names.join(' ') };
          })}
          value={value.arrondissement_id}
          onChange={(id) => onChange({ arrondissement_id: id, ...reset })}
        />
      )}
      <SearchSelect
        label="Quartier"
        placeholder={!city ? "Choisissez d'abord la ville" : hasArr && !value.arrondissement_id ? "Choisissez d'abord l'arrondissement" : 'Tapez votre quartier'}
        emptyText="Quartier absent de la liste : choisissez le plus proche et précisez dans le repère."
        options={neighborhoods.map((n) => ({ value: n.id, label: n.name }))}
        value={value.neighborhood}
        onChange={(id) => {
          const n = geo.neighborhoods.find((x) => x.id === Number(id));
          onChange({ neighborhood: id, landmark: '', zone: n?.name || '', latitude: null, longitude: null });
        }}
      />
      {landmarks.length > 0 && (
        <SearchSelect
          label="Zone phare"
          placeholder="Zone phare la plus proche (facultatif)"
          options={[{ value: '', label: 'Aucune' }, ...landmarks.map((l) => ({ value: l.id, label: l.name }))]}
          value={value.landmark}
          onChange={(id) => onChange({ landmark: id })}
        />
      )}
      {geo.message && <p className="md:col-span-2 -mt-1 text-xs text-gray-500">{geo.message}</p>}
    </>
  );
}
