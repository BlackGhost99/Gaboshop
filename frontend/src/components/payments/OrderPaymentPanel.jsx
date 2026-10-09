import { useCallback, useEffect, useRef, useState } from 'react';
import api from '../../services/api';
import { askAI, describeError } from '../../utils/feedback';
import { formatCurrency } from '../../utils/helpers';
import {
  METHOD_LABELS, ROLE_LABELS, KIND_LABELS, RECEIPT_STATUS, newIdempotencyKey, apiErrorMessage,
} from './paymentLabels';

const OPEN = ['unpaid', 'partially_paid', 'overdue', 'pending'];

// Paiement d'une commande payée directement (espèces ou Mobile Money au code marchand du vendeur).
// - Le payeur (client, ou commerce acheteur en B2B) voit le code marchand, le motif à indiquer,
//   puis déclare l'ID de transaction reçu par SMS.
// - Le bénéficiaire (commerce, fournisseur B2B, livreur) confirme ou refuse, ou note des espèces reçues.
export default function OrderPaymentPanel({ orderId, onChange }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const res = await api.get(`/payments/arrangements/order/${orderId}/`);
      setData(res.data?.data || null);
      setError('');
    } catch (err) {
      if (err?.response?.status === 404) setData(null);
      else setError(apiErrorMessage(err, 'Impossible de charger le paiement.'));
    } finally {
      setLoading(false);
    }
  }, [orderId]);

  useEffect(() => {
    load();
  }, [load]);

  const refresh = () => {
    load();
    onChange?.();
  };

  if (loading) return <p className="text-sm text-gray-500">Chargement du paiement…</p>;
  // Une erreur de rafraîchissement ne cache pas un paiement déjà affiché.
  if (error && !data) {
    return (
      <p className="text-sm text-red-600">
        {error}{' '}
        <button type="button" onClick={() => { setLoading(true); load(); }} className="font-semibold underline">
          Réessayer
        </button>
      </p>
    );
  }
  if (!data) return null;
  if (data.flow === 'platform_online') {
    return data.online_payment ? (
      <OnlinePaymentCard orderId={orderId} arrangement={data} online={data.online_payment} onDone={refresh} />
    ) : null;
  }

  const mine = data.obligations.filter(
    (o) => o.kind !== 'commission' && (o.i_am_payer || o.i_am_payee) && o.status !== 'not_due',
  );
  if (!mine.length) return null;

  return (
    <div className="space-y-3">
      {mine.map((ob) => (
        <ObligationCard key={ob.id} arrangement={data} obligation={ob} onDone={refresh} />
      ))}
    </div>
  );
}

const ONLINE_WAITING = ['pending', 'processing'];
const ONLINE_METHODS = ['airtel_money', 'moov_money'];
const AUTO_CHECK_EVERY_MS = 10000;
const AUTO_CHECK_MAX = 18; // 3 minutes

// Paiement en ligne Gaboshop (SingPay) : le client reçoit une demande sur son téléphone et la valide
// avec son code secret. L'app redemande régulièrement le statut à SingPay ; seule sa réponse compte.
function OnlinePaymentCard({ orderId, arrangement, online, onDone }) {
  const [checking, setChecking] = useState(false);
  const [message, setMessage] = useState('');
  const [retry, setRetry] = useState(false);
  // Chaque nouvelle demande relance la vérification automatique.
  const [round, setRound] = useState(0);
  const onDoneRef = useRef(onDone);
  const waiting = ONLINE_WAITING.includes(online.status);
  const orderClosed = ['cancelled', 'refunded'].includes(online.order_status);
  const label = METHOD_LABELS[online.method || arrangement.method] || 'Mobile Money';

  useEffect(() => {
    onDoneRef.current = onDone;
  });

  const verify = useCallback(async (silent) => {
    if (!silent) {
      setChecking(true);
      setMessage('');
    }
    try {
      const res = await api.post(`/orders/${orderId}/payments/verify/`);
      const status = res.data?.data?.payment_status;
      if (status && status !== online.status) onDoneRef.current?.();
      else if (!silent) setMessage('Pas encore confirmé. Validez la demande avec votre code secret, puis réessayez.');
    } catch (err) {
      if (!silent) setMessage(apiErrorMessage(err, 'Vérification impossible, réessayez.'));
    } finally {
      if (!silent) setChecking(false);
    }
  }, [orderId, online.status]);

  useEffect(() => {
    if (!waiting || !online.i_am_client) return undefined;
    let count = 0;
    const timer = setInterval(() => {
      count += 1;
      if (count > AUTO_CHECK_MAX) {
        clearInterval(timer);
        return;
      }
      verify(true);
    }, AUTO_CHECK_EVERY_MS);
    return () => clearInterval(timer);
  }, [waiting, online.i_am_client, verify, round]);

  // Échec affiché alors que le client a peut-être validé sur son téléphone : on redemande une fois à SingPay.
  const failed = online.status === 'failed';
  useEffect(() => {
    if (failed && online.i_am_client) verify(true);
  }, [failed, online.i_am_client, verify]);

  if (online.status === 'success') {
    return (
      <div className="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800">
        ✓ Payé en ligne par {label} : <strong>{formatCurrency(online.amount)}</strong>
      </div>
    );
  }

  if (!online.i_am_client) {
    return (
      <div className="rounded-lg border border-gray-200 p-3 text-sm text-gray-700">
        Paiement en ligne {waiting ? 'en attente de validation par le client' : 'pas encore abouti'}.
        Ne préparez la commande qu'une fois le paiement confirmé.
      </div>
    );
  }

  if (orderClosed) return null;

  if (waiting && !retry) {
    return (
      <div className="space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm">
        <p className="text-amber-900">
          Une demande de paiement de <strong>{formatCurrency(online.amount)}</strong> par {label} a été envoyée
          {online.phone ? <> au <strong>{online.phone}</strong></> : null}. Validez-la sur votre téléphone avec votre
          code secret.
        </p>
        <p className="text-xs text-amber-800">La confirmation arrive ici automatiquement, cela peut prendre une minute.</p>
        <button type="button" disabled={checking} onClick={() => verify(false)} className="w-full rounded bg-indigo-600 py-2 font-semibold text-white disabled:opacity-50">
          {checking ? 'Vérification…' : "J'ai validé, vérifier"}
        </button>
        {message && <p className="text-gray-700">{message}</p>}
        <button
          type="button"
          onClick={() => { setMessage(''); setRetry(true); }}
          className="w-full rounded border border-indigo-300 bg-white py-2 font-semibold text-indigo-700"
        >
          Demande expirée ou pas reçue ? La renvoyer
        </button>
      </div>
    );
  }

  return (
    <PayOnlineForm
      orderId={orderId}
      online={online}
      defaultMethod={ONLINE_METHODS.includes(arrangement.method) ? arrangement.method : 'airtel_money'}
      failed={online.status === 'failed' || online.status === 'cancelled'}
      onCancel={waiting ? () => setRetry(false) : null}
      onDone={() => {
        setRetry(false);
        setRound((n) => n + 1);
        onDone();
      }}
    />
  );
}

function PayOnlineForm({ orderId, online, defaultMethod, failed, onDone, onCancel }) {
  const [method, setMethod] = useState(defaultMethod);
  const [phone, setPhone] = useState(online.phone || '');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setSending(true);
    setError('');
    try {
      await api.post(`/orders/${orderId}/payments/init/`, { payment_method: method, phone_number: phone.trim() });
      onDone();
    } catch (err) {
      setError(describeError(err, "La demande de paiement n'a pas pu être envoyée."));
    } finally {
      setSending(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-2 rounded-lg border border-gray-200 p-3 text-sm">
      {failed && (
        <p className="text-red-700">
          Le paiement n'a pas abouti (demande expirée, refusée ou code erroné). Renvoyez la demande ci-dessous, puis
          validez-la vite sur votre téléphone.
        </p>
      )}
      <p className="text-gray-700">
        Payez <strong>{formatCurrency(online.amount)}</strong> par Mobile Money : vous recevrez une demande à valider sur
        votre téléphone.
      </p>
      <select value={method} onChange={(e) => setMethod(e.target.value)} className="w-full rounded border border-gray-300 px-3 py-2">
        {ONLINE_METHODS.map((m) => <option key={m} value={m}>{METHOD_LABELS[m]}</option>)}
      </select>
      <input
        value={phone}
        onChange={(e) => setPhone(e.target.value)}
        placeholder="Numéro Mobile Money (ex. 077 12 34 56)"
        inputMode="tel"
        required
        className="w-full rounded border border-gray-300 px-3 py-2"
      />
      {error && <InlineError error={error} action="Recevoir la demande de paiement" />}
      <button type="submit" disabled={sending || !phone.trim()} className="w-full rounded bg-indigo-600 py-2 font-semibold text-white disabled:opacity-50">
        {sending ? 'Envoi…' : 'Recevoir la demande de paiement'}
      </button>
      {onCancel && (
        <button type="button" onClick={onCancel} className="w-full text-xs text-gray-600 underline">
          Retour
        </button>
      )}
      <p className="text-xs text-gray-500">Gaboshop ne vous demandera jamais votre code secret Mobile Money.</p>
    </form>
  );
}

// Échec affiché sur place : ce qui s'est passé, pourquoi, quoi faire, et l'aide de l'IA.
function InlineError({ error, action }) {
  return (
    <div className="space-y-1 rounded border border-red-200 bg-red-50 p-2 text-red-800">
      <p className="font-semibold">{error.message}</p>
      {error.reason && <p><span className="font-semibold">Pourquoi : </span>{error.reason}</p>}
      {error.nextStep && <p><span className="font-semibold">Que faire : </span>{error.nextStep}</p>}
      <button type="button" onClick={() => askAI({ ...error, action })} className="text-xs font-semibold underline">
        🤖 Demander à l'IA comment régler ça
      </button>
    </div>
  );
}

function ObligationCard({ arrangement, obligation, onDone }) {
  const method = arrangement.method;
  const isCash = method === 'cash';
  const remaining = Number(obligation.remaining_amount);
  const open = OPEN.includes(obligation.status) && remaining > 0;
  const pending = obligation.receipts.filter((r) => r.status === 'pending');
  const payeeLabel = ROLE_LABELS[obligation.payee] || 'le vendeur';

  return (
    <div className="rounded-lg border border-gray-200 p-3 text-sm">
      <div className="flex items-center justify-between gap-2">
        <p className="font-semibold text-gray-900">
          {KIND_LABELS[obligation.kind] || 'Paiement'} · {METHOD_LABELS[method] || method}
        </p>
        <p className="font-semibold">{formatCurrency(obligation.amount)}</p>
      </div>
      {obligation.status === 'paid' && <p className="mt-1 text-green-700">✓ Payé et confirmé</p>}

      {obligation.i_am_payer && open && (
        isCash ? (
          <p className="mt-2 text-gray-700">
            À régler en espèces à {payeeLabel} : {formatCurrency(remaining)}. Rien à faire maintenant.
          </p>
        ) : (
          <PayerSteps arrangement={arrangement} obligation={obligation} pending={pending} onDone={onDone} />
        )
      )}

      {obligation.can_review && obligation.i_am_payee && pending.map((r) => (
        <ReviewReceipt key={r.id} receipt={r} onDone={onDone} />
      ))}

      {obligation.i_am_payee && open && pending.length === 0 && (
        <RecordReceived arrangement={arrangement} obligation={obligation} onDone={onDone} />
      )}

      <ReceiptHistory receipts={obligation.receipts.filter((r) => r.status !== 'pending' || !obligation.i_am_payee)} />
    </div>
  );
}

function PayerSteps({ arrangement, obligation, pending, onDone }) {
  const [reference, setReference] = useState('');
  const [phone, setPhone] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const remaining = Number(obligation.remaining_amount);

  if (pending.length) {
    return (
      <p className="mt-2 rounded bg-amber-50 p-2 text-amber-800">
        Paiement déclaré (réf. {pending[0].reference}). {arrangement.is_b2b ? 'Le fournisseur' : 'Le commerce'} vérifie
        son SMS puis confirme. Votre commande avance dès la confirmation.
      </p>
    );
  }

  const submit = async (e) => {
    e.preventDefault();
    setSending(true);
    setError('');
    try {
      await api.post('/payments/receipts/', {
        obligation_id: obligation.id,
        amount: obligation.remaining_amount,
        method: arrangement.method,
        reference: reference.trim(),
        comment: phone ? `Payé depuis le ${phone.trim()}` : '',
        idempotency_key: newIdempotencyKey(),
      });
      onDone();
    } catch (err) {
      setError(apiErrorMessage(err, 'La déclaration a échoué, réessayez.'));
    } finally {
      setSending(false);
    }
  };

  return (
    <form onSubmit={submit} className="mt-2 space-y-2">
      <ol className="list-decimal space-y-1 pl-5 text-gray-700">
        <li>
          Payez <strong>{formatCurrency(remaining)}</strong> par {METHOD_LABELS[arrangement.method]} à{' '}
          <strong>{arrangement.store_name}</strong>
          {arrangement.instructions ? <> : <strong>{arrangement.instructions}</strong></> : (
            <> (code marchand pas encore renseigné, appelez le {arrangement.store_phone})</>
          )}.
        </li>
        <li>Dans le motif, écrivez <strong>{arrangement.order_number}</strong>.</li>
        <li>Recopiez ci-dessous l'ID de transaction du SMS de confirmation Airtel ou Moov (pas le numéro de commande).</li>
      </ol>
      <input
        value={reference}
        onChange={(e) => setReference(e.target.value)}
        placeholder="ID de transaction (ex. MP241006.1234.A12345)"
        required
        className="w-full rounded border border-gray-300 px-3 py-2"
      />
      <input
        value={phone}
        onChange={(e) => setPhone(e.target.value)}
        placeholder="Numéro qui a payé (facultatif)"
        inputMode="tel"
        className="w-full rounded border border-gray-300 px-3 py-2"
      />
      {error && <p className="text-red-600">{error}</p>}
      <button type="submit" disabled={sending || !reference.trim()} className="w-full rounded bg-indigo-600 py-2 font-semibold text-white disabled:opacity-50">
        {sending ? 'Envoi…' : "J'ai payé"}
      </button>
      <p className="text-xs text-gray-500">Gaboshop ne vous demandera jamais votre code PIN Mobile Money.</p>
    </form>
  );
}

export function ReviewReceipt({ receipt, onDone, context }) {
  const [busy, setBusy] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');

  const act = async (kind) => {
    setBusy(true);
    setError('');
    try {
      await api.post(`/payments/receipts/${receipt.id}/${kind}/`, kind === 'reject' ? { reason } : {});
      onDone();
    } catch (err) {
      setError(apiErrorMessage(err, 'Action impossible, réessayez.'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="mt-2 rounded border border-amber-200 bg-amber-50 p-2">
      {context}
      <p className="text-gray-800">
        <strong>{formatCurrency(receipt.amount)}</strong> par {METHOD_LABELS[receipt.method] || receipt.method}, réf.{' '}
        <strong className="break-all">{receipt.reference}</strong>
      </p>
      {receipt.comment && <p className="text-xs text-gray-600">{receipt.comment}</p>}
      <p className="text-xs text-amber-800">Vérifiez sur votre téléphone que ce paiement est bien arrivé avant de confirmer.</p>
      {rejecting ? (
        <div className="mt-2 space-y-2">
          <input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Pourquoi ? (ex. aucun paiement reçu)"
            className="w-full rounded border border-gray-300 px-3 py-2"
          />
          <div className="flex gap-2">
            <button type="button" disabled={busy || !reason.trim()} onClick={() => act('reject')} className="flex-1 rounded bg-red-600 py-2 font-semibold text-white disabled:opacity-50">
              Refuser
            </button>
            <button type="button" onClick={() => setRejecting(false)} className="flex-1 rounded border border-gray-300 py-2">Retour</button>
          </div>
        </div>
      ) : (
        <div className="mt-2 flex gap-2">
          <button type="button" disabled={busy} onClick={() => act('confirm')} className="flex-1 rounded bg-green-600 py-2 font-semibold text-white disabled:opacity-50">
            Paiement reçu
          </button>
          <button type="button" disabled={busy} onClick={() => setRejecting(true)} className="flex-1 rounded border border-red-300 py-2 font-semibold text-red-700">
            Pas reçu
          </button>
        </div>
      )}
      {error && <p className="mt-1 text-red-600">{error}</p>}
    </div>
  );
}

function RecordReceived({ arrangement, obligation, onDone }) {
  const isCash = arrangement.method === 'cash';
  const [reference, setReference] = useState('');
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const submit = async () => {
    setBusy(true);
    setError('');
    try {
      await api.post('/payments/receipts/', {
        obligation_id: obligation.id,
        amount: obligation.remaining_amount,
        method: arrangement.method,
        reference: reference.trim(),
        idempotency_key: newIdempotencyKey(),
      });
      onDone();
    } catch (err) {
      setError(apiErrorMessage(err, 'Enregistrement impossible, réessayez.'));
    } finally {
      setBusy(false);
    }
  };

  if (!open) {
    return (
      <button type="button" onClick={() => setOpen(true)} className="mt-2 w-full rounded border border-green-300 py-2 font-semibold text-green-700">
        {isCash ? `J'ai reçu ${formatCurrency(obligation.remaining_amount)} en espèces` : 'Paiement déjà reçu ? Le noter'}
      </button>
    );
  }
  return (
    <div className="mt-2 space-y-2">
      {!isCash && (
        <input
          value={reference}
          onChange={(e) => setReference(e.target.value)}
          placeholder="ID de transaction du SMS reçu"
          className="w-full rounded border border-gray-300 px-3 py-2"
        />
      )}
      <div className="flex gap-2">
        <button type="button" disabled={busy || (!isCash && !reference.trim())} onClick={submit} className="flex-1 rounded bg-green-600 py-2 font-semibold text-white disabled:opacity-50">
          Confirmer la réception
        </button>
        <button type="button" onClick={() => setOpen(false)} className="flex-1 rounded border border-gray-300 py-2">Annuler</button>
      </div>
      {error && <p className="text-red-600">{error}</p>}
    </div>
  );
}

function ReceiptHistory({ receipts }) {
  if (!receipts.length) return null;
  return (
    <ul className="mt-2 space-y-1">
      {receipts.map((r) => {
        const status = RECEIPT_STATUS[r.status] || RECEIPT_STATUS.pending;
        return (
          <li key={r.id} className="flex flex-wrap items-center gap-2 text-xs text-gray-600">
            <span className={`rounded-full px-2 py-0.5 ${status.className}`}>{status.label}</span>
            <span className="break-all">{formatCurrency(r.amount)} · réf. {r.reference}</span>
            {r.status === 'rejected' && r.rejection_reason && <span className="text-red-700">({r.rejection_reason})</span>}
          </li>
        );
      })}
    </ul>
  );
}
