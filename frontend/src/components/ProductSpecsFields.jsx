import { useState } from 'react';

// Catégories pour lesquelles on demande marque, modèle et tailles/pointures
const FASHION_RE = /v[eê]tement|habit|chaussure|basket|mode|textile|pr[eê]t[- ]à[- ]porter|sac|accessoire/i;
export const isFashionCategory = (name) => FASHION_RE.test(name || '');

const round = (n, d) => Math.round(n * 10 ** d) / 10 ** d;
const toNumber = (v) => {
  const n = parseFloat(String(v ?? '').replace(',', '.'));
  return Number.isFinite(n) ? n : null;
};

// Par défaut on propose les petites unités (g, cm) : la plupart des articles s'y prêtent.
const initialUnit = (value, small) => {
  const n = toNumber(value);
  return n !== null && n >= 1 ? 'big' : small;
};

/**
 * Poids et taille avec choix de l'unité (g/kg, cm/m), plus marque, modèle et tailles
 * pour les vêtements et chaussures. Les valeurs envoyées restent en kg et en mètres.
 */
export default function ProductSpecsFields({ weightKg, lengthM, attributes = {}, fashion, onChange, required = true, inputClass, labelClass }) {
  const [weightUnit, setWeightUnit] = useState(initialUnit(weightKg, 'g'));
  const [lengthUnit, setLengthUnit] = useState(initialUnit(lengthM, 'cm'));
  const [weightText, setWeightText] = useState(() => {
    const n = toNumber(weightKg);
    if (n === null) return '';
    return String(weightUnit === 'g' ? round(n * 1000, 0) : n);
  });
  const [lengthText, setLengthText] = useState(() => {
    const n = toNumber(lengthM);
    if (n === null) return '';
    return String(lengthUnit === 'cm' ? round(n * 100, 0) : n);
  });

  // Le serveur garde 2 décimales (kg et m) : au minimum 0,01 pour une valeur positive
  const toServer = (n) => (n === null ? '' : String(n > 0 ? Math.max(round(n, 2), 0.01) : round(n, 2)));
  const emitWeight = (text, unit) => {
    const n = toNumber(text);
    onChange({ weight_kg: toServer(n === null ? null : (unit === 'g' ? n / 1000 : n)) });
  };
  const emitLength = (text, unit) => {
    const n = toNumber(text);
    onChange({ length_m: toServer(n === null ? null : (unit === 'cm' ? n / 100 : n)) });
  };
  const setAttr = (key, val) => onChange({ attributes: { ...attributes, [key]: val } });

  const input = inputClass || 'w-full rounded-md border border-gray-300 px-3 py-2 text-sm';
  const label = labelClass || 'text-sm font-semibold text-gray-700';
  const unitSelect = 'rounded-md border border-gray-300 px-2 py-2 text-sm bg-white';

  return (
    <>
      <div>
        <label className={label}>Poids</label>
        <div className="mt-1 flex gap-2">
          <input
            type="text" inputMode="decimal" className={input} value={weightText} required={required}
            placeholder={weightUnit === 'g' ? 'ex : 250' : 'ex : 1,5'}
            onChange={(e) => { setWeightText(e.target.value); emitWeight(e.target.value, weightUnit); }}
          />
          <select className={unitSelect} value={weightUnit} onChange={(e) => { setWeightUnit(e.target.value); emitWeight(weightText, e.target.value); }}>
            <option value="g">g</option>
            <option value="big">kg</option>
          </select>
        </div>
      </div>
      <div>
        <label className={label}>Taille du colis (côté le plus long)</label>
        <div className="mt-1 flex gap-2">
          <input
            type="text" inputMode="decimal" className={input} value={lengthText} required={required}
            placeholder={lengthUnit === 'cm' ? 'ex : 30' : 'ex : 1,2'}
            onChange={(e) => { setLengthText(e.target.value); emitLength(e.target.value, lengthUnit); }}
          />
          <select className={unitSelect} value={lengthUnit} onChange={(e) => { setLengthUnit(e.target.value); emitLength(lengthText, e.target.value); }}>
            <option value="cm">cm</option>
            <option value="big">m</option>
          </select>
        </div>
        <p className="text-xs text-gray-500 mt-1">Sert à calculer la livraison.</p>
      </div>
      {fashion && (
        <>
          <div>
            <label className={label}>Marque</label>
            <input type="text" className={`mt-1 ${input}`} value={attributes.brand || ''} placeholder="ex : Nike" onChange={(e) => setAttr('brand', e.target.value)} />
          </div>
          <div>
            <label className={label}>Modèle</label>
            <input type="text" className={`mt-1 ${input}`} value={attributes.model || ''} placeholder="ex : Air Max 90" onChange={(e) => setAttr('model', e.target.value)} />
          </div>
          <div>
            <label className={label}>Tailles / pointures disponibles</label>
            <input type="text" className={`mt-1 ${input}`} value={attributes.sizes || ''} placeholder="ex : 40, 41, 42 ou S, M, L" onChange={(e) => setAttr('sizes', e.target.value)} />
          </div>
          <div>
            <label className={label}>Couleur</label>
            <input type="text" className={`mt-1 ${input}`} value={attributes.color || ''} placeholder="ex : Noir" onChange={(e) => setAttr('color', e.target.value)} />
          </div>
        </>
      )}
    </>
  );
}
