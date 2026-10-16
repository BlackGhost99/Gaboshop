import { useEffect, useMemo } from 'react';
import SearchSelect from './SearchSelect';

/** Province › Ville › Arrondissement › Quartier, chaque liste avec recherche. Le client ne tape jamais sa zone.
 *  `value` : { province_id, city_id, arrondissement_id, neighborhood } ; `onChange(patch)` reçoit aussi
 *  `city` et `zone` (noms) pour le devis et la commande. */
export default function AddressPicker({ geo, value = {}, onChange }) {
  const cities = useMemo(() => (geo?.cities || []).filter((c) => !value.province_id || c.province_id === Number(value.province_id)), [geo, value.province_id]);
  const city = (geo?.cities || []).find((c) => c.id === Number(value.city_id));
  const arrondissements = useMemo(() => (geo?.arrondissements || []).filter((a) => a.city_id === Number(value.city_id)), [geo, value.city_id]);
  const neighborhoods = useMemo(() => (geo?.neighborhoods || []).filter((n) => n.city_id === Number(value.city_id)
    && (!value.arrondissement_id || n.arrondissement_id === Number(value.arrondissement_id) || !n.arrondissement_id)), [geo, value.city_id, value.arrondissement_id]);

  // Par défaut : la première ville ouverte (Libreville au lancement).
  useEffect(() => {
    if (!geo || value.city_id) return;
    const first = geo.cities.find((c) => c.is_open);
    if (first) onChange({ province_id: first.province_id, city_id: first.id, city: first.name, arrondissement_id: '', neighborhood: '', zone: '' });
  }, [geo]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!geo) return null;
  const arrName = (id) => (geo.arrondissements.find((a) => a.id === id) || {}).name;

  return (
    <>
      <SearchSelect
        label="Province"
        options={geo.provinces.map((p) => ({ value: p.id, label: p.name }))}
        value={value.province_id}
        onChange={(id) => onChange({ province_id: id, city_id: '', city: '', arrondissement_id: '', neighborhood: '', zone: '' })}
      />
      <SearchSelect
        label="Ville"
        options={cities.map((c) => ({ value: c.id, label: c.name, disabled: !c.is_open, hint: c.is_open ? '' : 'Bientôt disponible' }))}
        value={value.city_id}
        onChange={(id) => {
          const c = geo.cities.find((x) => x.id === Number(id));
          onChange({ province_id: c?.province_id || value.province_id, city_id: id, city: c?.name || '', arrondissement_id: '', neighborhood: '', zone: '' });
        }}
      />
      {arrondissements.length > 0 && (
        <SearchSelect
          label="Arrondissement"
          placeholder="Arrondissement (facultatif)"
          options={[{ value: '', label: 'Je ne sais pas' }, ...arrondissements.map((a) => ({ value: a.id, label: a.name }))]}
          value={value.arrondissement_id}
          onChange={(id) => onChange({ arrondissement_id: id, neighborhood: '', zone: '' })}
        />
      )}
      <SearchSelect
        label="Quartier"
        placeholder={city ? 'Tapez votre quartier' : "Choisissez d'abord la ville"}
        emptyText="Quartier absent de la liste : choisissez le plus proche et précisez dans le repère."
        options={neighborhoods.map((n) => ({ value: n.id, label: n.name, hint: n.arrondissement_id && !value.arrondissement_id ? arrName(n.arrondissement_id) : '' }))}
        value={value.neighborhood}
        onChange={(id) => {
          const n = geo.neighborhoods.find((x) => x.id === Number(id));
          onChange({ neighborhood: id, zone: n?.name || '', arrondissement_id: value.arrondissement_id || n?.arrondissement_id || '' });
        }}
      />
      {geo.message && <p className="md:col-span-2 -mt-1 text-xs text-gray-500">{geo.message}</p>}
    </>
  );
}
