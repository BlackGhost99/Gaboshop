// Messages de l'application : ce qui s'est passé, pourquoi, et quoi faire.
// Remplace les alert() : FeedbackCenter (monté une fois dans App) affiche les messages,
// et un échec propose toujours « Demander à l'IA », qui reçoit le problème en contexte.

const EVENT = 'gaboshop:feedback';
export const ASK_AI_EVENT = 'gaboshop:ask-ai';

const FIELD_LABELS = {
  phone: 'Téléphone', phone_number: 'Numéro', password: 'Mot de passe', email: 'E-mail', name: 'Nom',
  price: 'Prix', stock: 'Stock', quantity: 'Quantité', address: 'Adresse', delivery_address: 'Adresse de livraison',
  delivery_phone: 'Téléphone de livraison', delivery_zone: 'Zone', reference: 'Référence', amount: 'Montant',
  category: 'Catégorie', description: 'Description', non_field_errors: '', detail: '',
};

const SKIPPED_KEYS = new Set(['success', 'code', 'status']);

function flatten(value) {
  if (value == null) return [];
  if (typeof value === 'string') return [value];
  if (Array.isArray(value)) return value.flatMap(flatten);
  if (typeof value === 'object') {
    return Object.entries(value).filter(([key]) => !SKIPPED_KEYS.has(key)).flatMap(([key, v]) => {
      const label = FIELD_LABELS[key] ?? key.replace(/_/g, ' ');
      return flatten(v).map((text) => (label ? `${label} : ${text}` : text));
    });
  }
  return [String(value)];
}

// Transforme n'importe quelle erreur (réseau, serveur, validation) en message clair.
export function describeError(err, fallback = "L'action n'a pas abouti.") {
  if (typeof err === 'string') return { message: err, reason: '', nextStep: '', status: '' };
  if (err && !err.response && !err.isAxiosError && !err.request) {
    // Erreur déjà mise en forme par un service ({ error: { message, details } }) ou erreur JavaScript.
    const inner = err.error && typeof err.error === 'object' ? err.error : null;
    const details = inner?.details ? flatten(inner.details).slice(0, 4) : [];
    return {
      message: (typeof err.error === 'string' ? err.error : '') || inner?.message || err.message || fallback,
      reason: inner?.reason || details.join(' · '),
      nextStep: inner?.next_step || (details.length ? 'Corrigez les champs indiqués, puis validez à nouveau.' : ''),
      status: inner?.code ? String(inner.code) : '',
    };
  }
  const response = err?.response;
  const data = response?.data;
  const status = response?.status ? String(response.status) : '';
  const apiError = data?.error && typeof data.error === 'object' ? data.error : null;

  let message = apiError?.message
    || (typeof data?.error === 'string' ? data.error : '')
    || data?.message
    || data?.detail
    || '';
  let reason = apiError?.reason || data?.reason || '';
  let nextStep = apiError?.next_step || data?.next_step || '';

  const plainFields = data && typeof data === 'object' && !Array.isArray(data) && !data.error && !data.message && !data.detail;
  const fieldErrors = apiError?.details || (plainFields ? data : null);
  const fields = fieldErrors && typeof fieldErrors === 'object' ? flatten(fieldErrors).slice(0, 4) : [];

  if (!response) {
    // Pas de réponse : téléphone hors connexion, ou serveur qui se réveille (hébergement gratuit).
    const offline = typeof navigator !== 'undefined' && navigator.onLine === false;
    return {
      message: offline ? "Pas de connexion Internet." : "Le serveur Gaboshop n'a pas répondu.",
      reason: offline
        ? 'Votre téléphone est hors connexion.'
        : "Le serveur peut être en train de se réveiller après une pause (jusqu'à une minute), ou la connexion est faible.",
      nextStep: offline ? 'Vérifiez vos données mobiles ou le Wi-Fi, puis réessayez.' : 'Patientez une minute, puis réessayez.',
      status: 'network',
    };
  }
  if (!reason && fields.length) reason = fields.join(' · ');
  if (!message) message = fields.length ? 'Certaines informations ne sont pas valides.' : fallback;

  if (!nextStep) {
    if (status === '400') nextStep = fields.length ? 'Corrigez les champs indiqués, puis validez à nouveau.' : 'Vérifiez les informations saisies, puis réessayez.';
    else if (status === '401') nextStep = 'Votre session a expiré : reconnectez-vous, puis refaites l’action.';
    else if (status === '403') nextStep = "Ce compte n'a pas le droit de faire cette action. Demandez à l'IA ce qu'il faut faire.";
    else if (status === '404') nextStep = "L'élément n'existe plus ou a été déplacé : rechargez la page.";
    else if (status === '409') nextStep = 'Les données ont changé entre-temps : rechargez la page, puis réessayez.';
    else if (status === '429') nextStep = 'Trop de tentatives : patientez une minute, puis réessayez.';
    else if (status.startsWith('5')) nextStep = 'Problème passager du serveur : réessayez dans une minute.';
  }
  if (!reason && status.startsWith('5')) reason = `Erreur du serveur (code ${status}).`;
  return { message, reason, nextStep, status };
}

function emit(item) {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent(EVENT, { detail: { id: `${Date.now()}-${Math.random()}`, ...item } }));
}

export function onFeedback(handler) {
  const listener = (event) => handler(event.detail);
  window.addEventListener(EVENT, listener);
  return () => window.removeEventListener(EVENT, listener);
}

// Réussite : dire précisément ce qui a été fait.
export function notifySuccess(title, details = '') {
  emit({ level: 'success', title, message: details });
}

export function notifyInfo(title, details = '') {
  emit({ level: 'info', title, message: details });
}

// Échec : `action` dit ce que l'utilisateur essayait de faire (« Enregistrer le produit »).
export function notifyError(err, { action = '', fallback } = {}) {
  const info = describeError(err, fallback);
  emit({
    level: 'error',
    title: action ? `${action} : échec` : "Ça n'a pas marché",
    message: info.message,
    reason: info.reason,
    nextStep: info.nextStep,
    status: info.status,
    action,
  });
  return info;
}

// Avertissement d'une saisie incomplète (aucun appel serveur).
export function notifyWarning(title, nextStep = '') {
  emit({ level: 'warning', title, message: '', nextStep });
}

// Ouvre l'assistant IA avec le problème en contexte.
export function askAI(problem = {}) {
  const what = problem.action ? `« ${problem.action} » n'a pas marché` : "Quelque chose n'a pas marché";
  const question = `${what} : ${problem.message || 'erreur'}. Pourquoi, et que dois-je faire ?`;
  window.dispatchEvent(new CustomEvent(ASK_AI_EVENT, {
    detail: {
      question,
      problem: {
        action: problem.action || '',
        message: problem.message || '',
        reason: problem.reason || '',
        next_step: problem.nextStep || problem.next_step || '',
        status: problem.status || '',
        page: typeof window !== 'undefined' ? window.location.pathname : '',
      },
    },
  }));
}
