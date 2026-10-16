import { useState } from 'react';
import usePushDevice from '../hooks/usePushDevice';

const DISMISS_KEY = 'gaboshop:push-prompt-dismissed';
const DISMISS_DAYS = 3;

const wasDismissedRecently = () => {
  try {
    const at = Number(localStorage.getItem(DISMISS_KEY) || 0);
    return at && Date.now() - at < DISMISS_DAYS * 24 * 3600 * 1000;
  } catch {
    return false;
  }
};

const ROLE_PITCH = {
  client: 'Soyez prévenu dès que votre commande est confirmée, en route ou livrée.',
  store_manager: 'Soyez prévenu dès qu’une commande arrive dans votre commerce.',
  delivery_agent: 'Soyez prévenu dès qu’une livraison vous est proposée.',
  admin: 'Soyez prévenu des paiements et alertes importantes de la plateforme.',
};

// Bandeau discret en haut des écrans : propose d'activer les alertes tant que ce n'est pas fait.
export function PushPrompt({ role = 'client', className = '' }) {
  const { state, busy, enable } = usePushDevice();
  const [hidden, setHidden] = useState(() => wasDismissedRecently());

  if (!state || hidden) return null;
  const askable = state.support === 'ok' && state.permission === 'default';
  const needsInstall = state.support === 'ios-install';
  if (!askable && !needsInstall) return null;

  const dismiss = () => {
    try { localStorage.setItem(DISMISS_KEY, String(Date.now())); } catch { /* stockage indisponible */ }
    setHidden(true);
  };

  return (
    <div className={`mb-4 flex items-start gap-3 rounded-xl border border-indigo-200 bg-indigo-50 p-3 ${className}`} role="region" aria-label="Activer les alertes">
      <span className="mt-0.5 text-xl" aria-hidden="true">🔔</span>
      <div className="min-w-0 flex-1 text-sm text-indigo-950">
        <p className="font-semibold">Activez les alertes sur cet appareil</p>
        {askable ? (
          <p className="mt-0.5 text-indigo-900">{ROLE_PITCH[role] || ROLE_PITCH.client} Un seul appui, vous pouvez les couper quand vous voulez.</p>
        ) : (
          <p className="mt-0.5 text-indigo-900">Sur iPhone : touchez le bouton Partager, puis « Sur l’écran d’accueil ». Ouvrez ensuite Gaboshop depuis l’écran d’accueil pour recevoir les alertes.</p>
        )}
        <div className="mt-2 flex flex-wrap gap-2">
          {askable && (
            <button type="button" onClick={enable} disabled={busy} className="rounded-lg bg-indigo-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-60">
              {busy ? 'Activation…' : 'Activer les alertes'}
            </button>
          )}
          <button type="button" onClick={dismiss} className="rounded-lg px-3 py-2 text-xs font-semibold text-indigo-900 hover:bg-indigo-100">
            Plus tard
          </button>
        </div>
      </div>
    </div>
  );
}

// Carte complète de la boîte de réception : état, activer / couper, essayer.
export function PushSettingsCard() {
  const { state, busy, enable, disable, test } = usePushDevice();
  if (!state) return null;

  let tone = 'border-gray-200 bg-white';
  let title = 'Alertes sur cet appareil';
  let text = '';
  let actions = null;

  if (state.support === 'native') {
    text = 'Dans l’application Android, les nouveautés s’affichent dans la cloche dès que vous ouvrez Gaboshop. Les alertes application fermée arrivent bientôt. En attendant, vous pouvez les recevoir en ouvrant Gaboshop dans Chrome.';
  } else if (state.support === 'ios-install') {
    text = 'Sur iPhone, touchez le bouton Partager puis « Sur l’écran d’accueil ». Ouvrez ensuite Gaboshop depuis l’écran d’accueil : vous pourrez activer les alertes.';
  } else if (state.support === 'unsupported') {
    text = 'Ce navigateur ne sait pas envoyer d’alertes. Ouvrez Gaboshop avec Chrome, Edge, Firefox ou Safari à jour. Vos notifications restent dans la cloche.';
  } else if (state.permission === 'denied') {
    tone = 'border-amber-200 bg-amber-50';
    text = 'Les alertes sont bloquées. Touchez le cadenas à côté de l’adresse du site, autorisez les notifications, puis rechargez la page.';
  } else if (state.permission === 'granted' && state.subscribed) {
    tone = 'border-green-200 bg-green-50';
    title = 'Alertes activées sur cet appareil';
    text = 'Vous êtes prévenu à chaque nouveauté, même quand Gaboshop est fermé.';
    actions = (
      <>
        <button type="button" onClick={test} disabled={busy} className="rounded-lg bg-slate-900 px-3 py-2 text-xs font-semibold text-white disabled:opacity-60">
          Envoyer une alerte d’essai
        </button>
        <button type="button" onClick={disable} disabled={busy} className="rounded-lg border border-gray-300 bg-white px-3 py-2 text-xs font-semibold text-gray-800 disabled:opacity-60">
          Couper
        </button>
      </>
    );
  } else {
    tone = 'border-indigo-200 bg-indigo-50';
    text = 'Recevez les nouveautés de vos commandes sur cet appareil, même quand Gaboshop est fermé.';
    actions = (
      <button type="button" onClick={enable} disabled={busy} className="rounded-lg bg-indigo-700 px-3 py-2 text-xs font-semibold text-white disabled:opacity-60">
        {busy ? 'Activation…' : 'Activer les alertes'}
      </button>
    );
  }

  return (
    <section className={`mb-4 rounded-xl border p-4 ${tone}`} aria-label={title}>
      <p className="text-sm font-bold text-gray-900">{title}</p>
      <p className="mt-1 text-sm text-gray-700">{text}</p>
      {actions && <div className="mt-3 flex flex-wrap gap-2">{actions}</div>}
    </section>
  );
}
