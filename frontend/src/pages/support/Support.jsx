import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import ClientLayout from '../../components/ClientLayout';
import StoreLayout from '../../components/StoreLayout';
import {
  createTicket, fetchSupportContact, fetchTicket, fetchTickets, replyToTicket,
} from '../../services/supportService';
import { notifyError, notifySuccess } from '../../utils/feedback';
import { ROLE_HOME, useRole } from '../../utils/currentUser';
import { formatDateTime } from '../../utils/helpers';
import { CATEGORIES } from './supportLabels';
import { PriorityBadge, StatusBadge, TicketThread } from './TicketParts';

const digits = (value) => String(value || '').replace(/[^\d]/g, '');

function ContactCard({ contact }) {
  if (!contact) return null;
  if (!contact.direct) {
    return (
      <section className="rounded-xl border border-gray-200 bg-white p-4">
        <h3 className="text-base font-bold text-gray-900">Nous contacter</h3>
        <p className="mt-1 text-sm text-gray-600">{contact.message}</p>
        {contact.email && (
          <a href={`mailto:${contact.email}`} className="mt-3 inline-block text-sm font-semibold text-slate-900 underline">
            {contact.email}
          </a>
        )}
      </section>
    );
  }
  return (
    <section className="rounded-xl border border-indigo-200 bg-indigo-50/60 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="text-base font-bold text-gray-900">Contact direct</h3>
        <span className="rounded-full bg-indigo-600 px-2 py-0.5 text-xs font-semibold text-white">{contact.priority_label}</span>
      </div>
      <p className="mt-1 text-sm text-gray-700">{contact.message}</p>
      <div className="mt-3 flex flex-col gap-2 sm:flex-row sm:flex-wrap">
        {contact.whatsapp && (
          <a href={`https://wa.me/${digits(contact.whatsapp)}`} target="_blank" rel="noopener noreferrer" className="rounded-lg bg-emerald-600 px-4 py-2 text-center text-sm font-semibold text-white">
            WhatsApp {contact.whatsapp}
          </a>
        )}
        {contact.phone && (
          <a href={`tel:${contact.phone.replace(/\s/g, '')}`} className="rounded-lg bg-slate-900 px-4 py-2 text-center text-sm font-semibold text-white">
            Appeler {contact.phone}
          </a>
        )}
        {contact.email && (
          <a href={`mailto:${contact.email}`} className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-center text-sm font-semibold text-gray-800">
            {contact.email}
          </a>
        )}
      </div>
    </section>
  );
}

function NewTicketForm({ onCreated, onCancel }) {
  const [form, setForm] = useState({ subject: '', message: '', category: 'other' });
  const [busy, setBusy] = useState(false);
  const set = (key) => (e) => setForm((prev) => ({ ...prev, [key]: e.target.value }));

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    try {
      const res = await createTicket(form);
      notifySuccess(res.message || 'Votre demande est enregistrée.', 'Vous serez prévenu dans vos notifications dès la réponse.');
      onCreated(res.data);
    } catch (err) {
      notifyError(err, { action: 'Envoyer ma demande' });
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-3 rounded-xl border border-gray-200 bg-white p-4">
      <h3 className="text-base font-bold text-gray-900">Nouvelle demande</h3>
      <div>
        <label htmlFor="support-category" className="mb-1 block text-sm font-medium text-gray-700">Sujet concerné</label>
        <select id="support-category" value={form.category} onChange={set('category')} className="w-full rounded-lg border border-gray-300 p-2.5 text-sm">
          {CATEGORIES.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
      </div>
      <div>
        <label htmlFor="support-subject" className="mb-1 block text-sm font-medium text-gray-700">Titre</label>
        <input id="support-subject" value={form.subject} onChange={set('subject')} maxLength={150} required placeholder="Ex. : paiement Airtel non reçu" className="w-full rounded-lg border border-gray-300 p-2.5 text-sm" />
      </div>
      <div>
        <label htmlFor="support-message" className="mb-1 block text-sm font-medium text-gray-700">Votre message</label>
        <textarea id="support-message" value={form.message} onChange={set('message')} rows={5} maxLength={4000} required placeholder="Expliquez ce qui s'est passé, avec le numéro de commande si vous l'avez." className="w-full rounded-lg border border-gray-300 p-3 text-sm" />
      </div>
      <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <button type="button" onClick={onCancel} className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-semibold text-gray-700">Annuler</button>
        <button type="submit" disabled={busy} className="rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50">
          {busy ? 'Envoi…' : 'Envoyer ma demande'}
        </button>
      </div>
    </form>
  );
}

function TicketRow({ ticket, active, onOpen }) {
  return (
    <li>
      <button
        type="button"
        onClick={() => onOpen(ticket.id)}
        aria-current={active ? 'true' : undefined}
        className={`w-full rounded-xl border p-3 text-left ${active ? 'border-slate-900 bg-slate-50' : 'border-gray-200 bg-white hover:bg-gray-50'}`}
      >
        <span className="flex flex-wrap items-center gap-2">
          <StatusBadge status={ticket.status} />
          {ticket.priority !== 'standard' && <PriorityBadge priority={ticket.priority} />}
          <span className="text-xs text-gray-500">{ticket.category_label}</span>
        </span>
        <span className="mt-1 block text-sm font-semibold text-gray-900">{ticket.subject}</span>
        <span className="mt-0.5 block text-xs text-gray-500">
          n° {ticket.id} · {formatDateTime(ticket.updated_at)} · {ticket.replies_count} réponse{ticket.replies_count > 1 ? 's' : ''}
        </span>
      </button>
    </li>
  );
}

function SupportContent() {
  const [params, setParams] = useSearchParams();
  const [tickets, setTickets] = useState(null);
  const [contact, setContact] = useState(null);
  const [current, setCurrent] = useState(null);
  const [creating, setCreating] = useState(false);
  const selectedId = Number(params.get('ticket')) || null;

  const loadTickets = useCallback(async () => {
    try {
      setTickets(await fetchTickets());
    } catch (err) {
      setTickets([]);
      notifyError(err, { action: 'Charger mes demandes' });
    }
  }, []);

  useEffect(() => {
    fetchTickets()
      .then(setTickets)
      .catch((err) => {
        setTickets([]);
        notifyError(err, { action: 'Charger mes demandes' });
      });
    fetchSupportContact().then(setContact).catch(() => setContact(null));
  }, []);

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

  const open = (id) => {
    setCreating(false);
    setParams(id ? { ticket: String(id) } : {});
  };

  const reply = async (message) => {
    try {
      const data = await replyToTicket(current.id, message);
      setCurrent(data.ticket);
      loadTickets();
      notifySuccess('Votre réponse est envoyée à Gaboshop.');
    } catch (err) {
      notifyError(err, { action: 'Envoyer ma réponse' });
      throw err;
    }
  };

  return (
    <div className="space-y-4">
      <ContactCard contact={contact} />

      {creating ? (
        <NewTicketForm
          onCancel={() => setCreating(false)}
          onCreated={(ticket) => { setCreating(false); loadTickets(); open(ticket.id); }}
        />
      ) : (
        <div className="flex justify-end">
          <button type="button" onClick={() => setCreating(true)} className="w-full rounded-lg bg-slate-900 px-4 py-3 text-sm font-semibold text-white sm:w-auto sm:py-2">
            Nouvelle demande
          </button>
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <section aria-label="Mes demandes">
          <h3 className="mb-2 text-base font-bold text-gray-900">Mes demandes</h3>
          {tickets === null && <p className="text-sm text-gray-500">Chargement…</p>}
          {tickets && tickets.length === 0 && (
            <p className="rounded-xl border border-dashed border-gray-300 bg-white p-4 text-sm text-gray-600">
              Vous n&apos;avez encore aucune demande. Utilisez « Nouvelle demande » pour écrire à l&apos;équipe Gaboshop.
            </p>
          )}
          <ul className="space-y-2">
            {(tickets || []).map((ticket) => (
              <TicketRow key={ticket.id} ticket={ticket} active={ticket.id === selectedId} onOpen={open} />
            ))}
          </ul>
        </section>

        {selectedId && current?.id === selectedId && (
          <section aria-label="Détail de la demande" className="space-y-3 rounded-xl border border-gray-200 bg-white p-4">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={current.status} />
                <PriorityBadge priority={current.priority} />
                <span className="text-xs text-gray-500">{current.category_label}</span>
              </div>
              <h3 className="mt-1 text-lg font-bold text-gray-900">{current.subject}</h3>
              {current.status === 'resolved' && (
                <p className="mt-1 text-sm text-emerald-700">Cette demande est résolue. Répondez-y si le problème persiste : elle sera rouverte.</p>
              )}
            </div>
            <TicketThread ticket={current} viewer="author" onReply={reply} />
          </section>
        )}
      </div>
    </div>
  );
}

// Page d'aide : tous les comptes connectés. Client et commerçant gardent leur menu ; livreur et admin ont un en-tête simple.
export default function Support() {
  const role = useRole();
  if (role === 'client') return <ClientLayout title="Aide et support"><SupportContent /></ClientLayout>;
  if (role === 'store_manager') return <StoreLayout title="Aide et support"><SupportContent /></StoreLayout>;
  return (
    <div className="min-h-screen bg-gray-100">
      <header className="flex items-center justify-between bg-slate-900 px-4 py-3 text-white">
        <h1 className="text-lg font-bold">Aide et support</h1>
        <Link to={ROLE_HOME[role] || '/dashboard'} className="text-sm font-semibold underline-offset-2 hover:underline">Mon espace</Link>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-4 pb-24 sm:py-8">
        <SupportContent />
      </main>
    </div>
  );
}
