import { formatCurrency } from '../../utils/helpers';
import { describeOptions } from '../../utils/productOptions';

const money = (value) => formatCurrency(Number(value) || 0);

function Row({ label, value, strong = false, tone = 'text-gray-700' }) {
  return (
    <div className={`flex items-start justify-between gap-3 ${tone}`}>
      <span className="min-w-0">{label}</span>
      <span className={`shrink-0 text-right ${strong ? 'font-semibold' : ''}`}>{value}</span>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div className="space-y-1 border-t border-gray-200 pt-2">
      <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-500">{title}</p>
      {children}
    </div>
  );
}

/** Devis complet du serveur (orders/quote.py) : articles, livraison, frais, total, qui payer et quand,
 *  et ce qui bloquerait la commande. `items` : lignes du panier (pour afficher taille et couleur). */
export default function QuoteDetails({ quote = {}, items = [], itemsTotal = 0, deliveryRequested = true }) {
  const lines = quote.lines || [];
  const problems = Object.fromEntries(lines.filter((l) => l.problem).map((l) => [l.product_id, l.problem]));
  const delivery = quote.delivery || {};
  const payment = quote.payment;
  const loading = !quote.lines && !quote.message;
  const total = quote.total != null ? money(quote.total) : (quote.message ? '—' : 'Calcul…');

  return (
    <div className="mt-4 space-y-2 rounded-md border border-gray-200 bg-gray-50 p-3 text-xs">
      <div className="flex items-start justify-between gap-2">
        <p className="font-semibold uppercase text-gray-700">Devis</p>
        {quote.store && (
          <span className={`shrink-0 rounded-full px-2 py-0.5 text-[11px] font-semibold ${quote.store.is_open ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-700'}`}>
            {quote.store.is_open ? 'Ouvert' : 'Fermé'}{quote.store.hours ? ` · ${quote.store.hours}` : ''}
          </span>
        )}
      </div>
      {quote.store && (
        <p className="text-gray-600">
          {quote.store.name}{quote.store.category ? ` · ${quote.store.category}` : ''}{quote.store.phone ? ` · ${quote.store.phone}` : ''}
        </p>
      )}

      <Section title="Articles">
        {items.map((it) => (
          <div key={`${it.id}-${describeOptions(it.options)}`}>
            <Row
              label={`${it.name}${describeOptions(it.options) ? ` (${describeOptions(it.options)})` : ''} × ${it.quantity || 1}`}
              value={money((Number(it.price) || 0) * (it.quantity || 1))}
            />
            {problems[it.id] && <p className="text-red-600">⚠ {problems[it.id]}</p>}
          </div>
        ))}
        <Row label="Sous-total articles" value={money(quote.items_total ?? itemsTotal)} strong />
      </Section>

      <Section title={deliveryRequested ? 'Livraison' : 'Retrait'}>
        {delivery.address && <p className="break-words text-gray-700">📍 {delivery.address}</p>}
        {deliveryRequested && (
          <>
            {delivery.delivered_by && (
              <p className="text-gray-600">
                {delivery.delivered_by}{delivery.vehicle_label ? ` · ${delivery.vehicle_label}` : ''}
                {delivery.price_zone && delivery.price_zone_rate ? ` · tarif zone ${delivery.price_zone}` : ''}
                {delivery.intercity ? ' · hors de la ville du commerce' : ''}
              </p>
            )}
            {quote.message && <p className="font-semibold text-amber-700">{quote.message}</p>}
            <Row
              label="🚚 Frais de livraison"
              value={quote.delivery_fee != null ? money(quote.delivery_fee) : (loading ? 'Calcul…' : '—')}
              strong
              tone="text-amber-700"
            />
          </>
        )}
      </Section>

      {(quote.fee_details || []).length > 0 ? (
        <Section title="Frais, commissions et réductions">
          {quote.fee_details.map((fee) => {
            const amount = Number(fee.amount) || 0;
            const tone = amount < 0 ? 'text-green-700' : fee.status === 'charged' ? 'text-gray-900' : 'text-gray-500';
            const shown = fee.status === 'charged' ? money(fee.amount) : (fee.status === 'free' ? 'Offert' : '—');
            return (
              <div key={fee.label}>
                <Row label={fee.label} value={shown} strong={fee.status === 'charged'} tone={tone} />
                {fee.note && <p className="text-[11px] text-gray-500">{fee.note}</p>}
              </div>
            );
          })}
        </Section>
      ) : (quote.fees || []).length > 0 && (
        <Section title="Frais et réductions">
          {quote.fees.map((fee) => (
            <Row key={fee.label} label={fee.label} value={money(fee.amount)} tone={Number(fee.amount) < 0 ? 'text-green-700' : 'text-gray-700'} />
          ))}
        </Section>
      )}

      <div className="flex items-center justify-between gap-3 border-t border-gray-300 pt-2 text-sm font-bold text-gray-900">
        <span>TOTAL À PAYER</span>
        <span className="text-base text-indigo-600">{total}</span>
      </div>

      {payment && payment.split?.length > 0 && (
        <Section title="Qui payer, comment et quand">
          <p className="text-gray-600">{payment.flow_label} · {payment.method_label}</p>
          {payment.split.map((line) => (
            <div key={`${line.payee}-${line.amount}`} className="rounded border border-gray-200 bg-white p-2">
              <Row label={line.payee} value={money(line.amount)} strong tone="text-gray-900" />
              <p className="text-gray-600">{line.how}</p>
              <p className="text-gray-500">{line.when}</p>
              {line.then && <p className="mt-1 text-gray-500">{line.then}</p>}
            </div>
          ))}
          {payment.simulated && (
            <p className="font-semibold text-amber-700">Site de test : paiement simulé, rien n’est débité.</p>
          )}
        </Section>
      )}

      {(quote.blocking || []).length > 0 && (
        <div className="rounded border border-red-200 bg-red-50 p-2 text-red-700">
          <p className="font-semibold">Commande impossible pour l’instant :</p>
          <ul className="ml-4 list-disc">
            {quote.blocking.map((reason) => <li key={reason}>{reason}</li>)}
          </ul>
        </div>
      )}

      {(quote.notes || []).length > 0 && (
        <Section title="Bon à savoir">
          <ul className="ml-4 list-disc space-y-0.5 text-gray-600">
            {quote.notes.map((note) => <li key={note}>{note}</li>)}
          </ul>
        </Section>
      )}

      <p className="pt-1 italic text-gray-500">Montants calculés par Gaboshop comme à la commande : aucune surcharge à la confirmation.</p>
    </div>
  );
}
