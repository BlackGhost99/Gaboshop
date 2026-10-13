import { useState } from 'react';
import { setStoreTrustAdmin } from '../../services/adminService';
import { notifyError, notifySuccess } from '../../utils/feedback';

/**
 * Protection contre les faux commerces : un commerce non validé n'est visible de personne ;
 * un commerce « de confiance » est payé dès la préparation (les autres après la réception confirmée) ;
 * les versements peuvent être gelés sans arrêter les ventes.
 */
export default function StoreTrustControls({ store, onChanged }) {
  const [busy, setBusy] = useState(false);

  const update = async (payload, confirmText) => {
    if (confirmText && !window.confirm(confirmText)) return;
    setBusy(true);
    try {
      const res = await setStoreTrustAdmin(store.id, payload);
      notifySuccess(store.name, res.message || 'Enregistré.');
      onChanged?.();
    } catch (err) {
      notifyError(err, { action: 'Modifier la confiance du commerce' });
    } finally {
      setBusy(false);
    }
  };

  const chip = 'px-2 py-0.5 text-xs rounded-full border disabled:opacity-50';
  return (
    <div className="flex flex-wrap gap-1">
      {store.is_verified ? (
        <button type="button" disabled={busy} className={`${chip} border-green-200 bg-green-50 text-green-700`}
          title="Retirer la validation : la boutique disparaît et ne peut plus vendre"
          onClick={() => update({ is_verified: false }, `Retirer la validation de « ${store.name} » ? La boutique ne sera plus visible.`)}>
          ✓ Validé
        </button>
      ) : (
        <button type="button" disabled={busy} className={`${chip} border-amber-300 bg-amber-50 text-amber-800 font-semibold`}
          title="Après avoir vérifié l'identité, le téléphone, l'adresse et les moyens de paiement"
          onClick={() => update({ is_verified: true }, `Valider « ${store.name} » ? La boutique deviendra visible et pourra vendre.`)}>
          À valider
        </button>
      )}
      <button type="button" disabled={busy}
        className={`${chip} ${store.is_trusted ? 'border-indigo-200 bg-indigo-50 text-indigo-700' : 'border-gray-200 bg-white text-gray-500'}`}
        title={store.is_trusted ? 'Payé dès la préparation. Cliquer pour revenir au paiement après réception.' : 'Payé après la réception confirmée par le client. Cliquer pour le payer dès la préparation.'}
        onClick={() => update({ is_trusted: !store.is_trusted })}>
        {store.is_trusted ? '★ Confiance' : '☆ Confiance'}
      </button>
      <button type="button" disabled={busy}
        className={`${chip} ${store.payouts_frozen ? 'border-red-300 bg-red-50 text-red-700 font-semibold' : 'border-gray-200 bg-white text-gray-500'}`}
        title={store.payouts_frozen ? 'Les versements sont retenus. Cliquer pour les reprendre.' : 'Retenir l’argent de ce commerce (plainte, doute) sans arrêter ses ventes.'}
        onClick={() => update({ payouts_frozen: !store.payouts_frozen },
          store.payouts_frozen ? null : `Geler les versements de « ${store.name} » ?`)}>
        {store.payouts_frozen ? '❄ Versements gelés' : 'Geler versements'}
      </button>
    </div>
  );
}
