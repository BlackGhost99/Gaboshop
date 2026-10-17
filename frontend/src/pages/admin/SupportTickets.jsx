import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { fetchTicket, fetchTickets, replyToTicket, setTicketStatus } from '../../services/supportService';
import { notifyError, notifySuccess } from '../../utils/feedback';
import { formatDateTime } from '../../utils/helpers';
import { PRIORITY_LABELS, STATUS_LABELS } from '../support/supportLabels';
import { PriorityBadge, StatusBadge, TicketThread } from '../support/TicketParts';

const STATUS_FILTERS = [['active', 'À traiter'], ['resolved', 'Résolues'], ['', 'Toutes']];
const PRIORITY_FILTERS = [['', 'Toutes priorités'], ...Object.entries(PRIORITY_LABELS)];

// Console du support : les demandes arrivent triées priorité d'abord, puis les plus anciennes en premier.
export default function SupportTickets() {
  const [params, setParams] = useSearchParams();
  const [tickets, setTickets] = useState(null);
  const [current, setCurrent] = useState(null);
  const [state, setState] = useState('active');
  const [priority, setPriority] = useState('');
  const selectedId = Number(params.get('ticket')) || null;

  const load = useCallback(async () => {
    try {
      const query = {};
      if (state) query.status = state;
      if (priority) query.priority = priority;
      setTickets(await fetchTickets(query));
    } catch (err) {
      setTickets([]);
      notifyError(err, { action: 'Charger les demandes' });
    }
  }, [state, priority]);

  useEffect(() => {
    let active = true;
    const query = {};
    if (state) query.status = state;
    if (priority) query.priority = priority;
    fetchTickets(query)
      .then((rows) => { if (active) setTickets(rows); })
      .catch((err) => {
        if (!active) return;
        setTickets([]);
        notifyError(err, { action: 'Charger les demandes' });
      });
    return () => { active = false; };
  }, [state, priority]);

  useEffect(() => {
    let active = true;
    if (!selectedId) return undefined;
    fetchTicket(selectedId)
      .then((ticket) => { if (active) setCurrent(ticket); })
      .catch((err) => {
        if (!active) return;
        setCurrent(null);
        notifyError(err, { action: 'Ouvrir la demande' });
      });
    return () => { active = false; };
  }, [selectedId]);

  const reply = async (message) => {
    try {
      const data = await replyToTicket(current.id, message);
      setCurrent(data.ticket);
      load();
      notifySuccess('Réponse envoyée.', 'La personne est prévenue dans ses notifications.');
    } catch (err) {
      notifyError(err, { action: 'Envoyer la réponse' });
      throw err;
    }
  };

  const changeStatus = async (status) => {
    try {
      setCurrent(await setTicketStatus(current.id, status));
      load();
      notifySuccess(`Demande n° ${current.id} : ${STATUS_LABELS[status].toLowerCase()}.`);
    } catch (err) {
      notifyError(err, { action: 'Changer le statut' });
    }
  };

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="flex items-center justify-between bg-gray-900 px-4 py-3 text-white">
        <h1 className="text-lg font-bold">Support : demandes</h1>
        <Link to="/admin/dashboard" className="text-sm font-semibold underline-offset-2 hover:underline">Retour à la console</Link>
      </header>
      <main className="mx-auto max-w-7xl space-y-4 px-4 py-4 sm:py-8">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <div className="flex gap-1" role="group" aria-label="Filtrer par état">
            {STATUS_FILTERS.map(([value, label]) => (
              <button
                key={label}
                type="button"
                onClick={() => setState(value)}
                aria-pressed={state === value}
                className={`rounded-lg px-3 py-2 text-sm font-semibold ${state === value ? 'bg-gray-900 text-white' : 'bg-white text-gray-700'}`}
              >
                {label}
              </button>
            ))}
          </div>
          <label className="sr-only" htmlFor="priority-filter">Priorité</label>
          <select id="priority-filter" value={priority} onChange={(e) => setPriority(e.target.value)} className="rounded-lg border border-gray-300 bg-white p-2 text-sm">
            {PRIORITY_FILTERS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </div>

        <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
          <section aria-label="Demandes">
            {tickets === null && <p className="text-sm text-gray-500">Chargement…</p>}
            {tickets && tickets.length === 0 && (
              <p className="rounded-xl border border-dashed border-gray-300 bg-white p-4 text-sm text-gray-600">Aucune demande pour ce filtre.</p>
            )}
            <ul className="space-y-2">
              {(tickets || []).map((ticket) => (
                <li key={ticket.id}>
                  <button
                    type="button"
                    onClick={() => setParams({ ticket: String(ticket.id) })}
                    aria-current={ticket.id === selectedId ? 'true' : undefined}
                    className={`w-full rounded-xl border p-3 text-left ${ticket.id === selectedId ? 'border-gray-900 bg-gray-50' : 'border-gray-200 bg-white hover:bg-gray-50'}`}
                  >
                    <span className="flex flex-wrap items-center gap-2">
                      <PriorityBadge priority={ticket.priority} />
                      <StatusBadge status={ticket.status} />
                      <span className="text-xs text-gray-500">{ticket.category_label}</span>
                    </span>
                    <span className="mt-1 block text-sm font-semibold text-gray-900">{ticket.subject}</span>
                    <span className="mt-0.5 block text-xs text-gray-500">
                      n° {ticket.id} · {ticket.author_name}{ticket.store_name ? ` · ${ticket.store_name}` : ''} · {formatDateTime(ticket.created_at)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </section>

          {selectedId && current?.id === selectedId && (
            <section aria-label="Détail de la demande" className="space-y-3 rounded-xl border border-gray-200 bg-white p-4">
              <div>
                <div className="flex flex-wrap items-center gap-2">
                  <PriorityBadge priority={current.priority} />
                  <StatusBadge status={current.status} />
                  <span className="text-xs text-gray-500">{current.category_label}</span>
                </div>
                <h2 className="mt-1 text-lg font-bold text-gray-900">{current.subject}</h2>
                <p className="text-sm text-gray-600">
                  {current.author_name} · {current.author_phone}
                  {current.store_name ? ` · ${current.store_name}` : ''}
                  {current.plan_name ? ` · forfait ${current.plan_name}` : ''}
                </p>
              </div>
              <div className="flex flex-wrap gap-2" role="group" aria-label="Changer le statut">
                {Object.entries(STATUS_LABELS).map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    disabled={current.status === value}
                    onClick={() => changeStatus(value)}
                    className="rounded-lg border border-gray-300 px-3 py-2 text-sm font-semibold text-gray-800 disabled:bg-gray-900 disabled:text-white"
                  >
                    {label}
                  </button>
                ))}
              </div>
              <TicketThread ticket={current} viewer="admin" onReply={reply} />
            </section>
          )}
        </div>
      </main>
    </div>
  );
}
