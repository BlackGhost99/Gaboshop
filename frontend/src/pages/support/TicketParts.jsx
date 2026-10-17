import { useState } from 'react';
import { formatDateTime } from '../../utils/helpers';
import { PRIORITY_LABELS, PRIORITY_TONES, STATUS_LABELS, STATUS_TONES } from './supportLabels';

export function PriorityBadge({ priority }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${PRIORITY_TONES[priority] || PRIORITY_TONES.standard}`}>
      {PRIORITY_LABELS[priority] || 'Standard'}
    </span>
  );
}

export function StatusBadge({ status }) {
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${STATUS_TONES[status] || STATUS_TONES.open}`}>
      {STATUS_LABELS[status] || status}
    </span>
  );
}

// Le fil d'une demande : le message de départ, puis les réponses, puis la zone d'écriture.
export function TicketThread({ ticket, viewer = 'author', onReply }) {
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);

  const send = async (event) => {
    event.preventDefault();
    if (!text.trim() || busy) return;
    setBusy(true);
    try {
      await onReply(text.trim());
      setText('');
    } finally {
      setBusy(false);
    }
  };

  const bubble = (key, name, mine, body, date) => (
    <li key={key} className={`flex ${mine ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-[90%] rounded-xl px-3 py-2 text-sm sm:max-w-[80%] ${mine ? 'bg-slate-900 text-white' : 'bg-gray-100 text-gray-900'}`}>
        <p className={`mb-1 text-xs font-semibold ${mine ? 'text-slate-300' : 'text-gray-500'}`}>{name} · {formatDateTime(date)}</p>
        <p className="whitespace-pre-line break-words">{body}</p>
      </div>
    </li>
  );

  const authorIsViewer = viewer === 'author';
  return (
    <div className="space-y-4">
      <ul className="space-y-3">
        {bubble('first', authorIsViewer ? 'Vous' : ticket.author_name, authorIsViewer, ticket.message, ticket.created_at)}
        {(ticket.replies || []).map((reply) => bubble(
          reply.id,
          reply.is_staff_reply ? reply.author_name : (authorIsViewer ? 'Vous' : reply.author_name),
          reply.is_staff_reply !== authorIsViewer,
          reply.message,
          reply.created_at,
        ))}
      </ul>
      <form onSubmit={send} className="space-y-2">
        <label htmlFor="ticket-reply" className="sr-only">Votre réponse</label>
        <textarea
          id="ticket-reply"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={3}
          maxLength={4000}
          placeholder={authorIsViewer ? 'Ajouter une précision ou répondre à Gaboshop…' : 'Votre réponse à la personne…'}
          className="w-full rounded-lg border border-gray-300 p-3 text-sm focus:border-slate-900 focus:outline-none focus:ring-1 focus:ring-slate-900"
        />
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={busy || !text.trim()}
            className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {busy ? 'Envoi…' : 'Envoyer'}
          </button>
        </div>
      </form>
    </div>
  );
}
