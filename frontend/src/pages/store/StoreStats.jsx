import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Cell } from 'recharts';

import StoreLayout from '../../components/StoreLayout';
import api from '../../services/api';
import { describeError } from '../../utils/feedback';

// Statistiques du commerçant (GET /store/stats/). Le forfait Gratuit voit le résumé de la période ;
// le reste (jour par jour, produits, clients, heures) fait partie du forfait Pro.

const PERIODS = [7, 30, 90];
const PRO_TOOLS = [
  'Ventes jour par jour',
  'Meilleurs produits',
  'Clients fidèles',
  'Meilleures heures et meilleurs jours',
  'Produits qui ne se vendent pas',
  "Taux d'annulation",
];

const BAR = '#6366f1';
const BAR_MUTED = '#c7d2fe';
const BAR_BEST = '#4338ca';

const formatMoney = (value) => `${Math.round(Number(value) || 0).toLocaleString('fr-FR')} F`;
const formatCount = (value) => (Number(value) || 0).toLocaleString('fr-FR');

// Axe des ventes : entiers lisibles (750, 15 k, 1,2 M).
const compactFcfa = new Intl.NumberFormat('fr-FR', { notation: 'compact', maximumFractionDigits: 1 });
const formatFcfaAxis = (value) => {
  const n = Math.round(Number(value) || 0);
  return Math.abs(n) < 1000 ? n.toLocaleString('fr-FR') : compactFcfa.format(n);
};

// 'YYYY-MM-DD' lu comme une date locale (pas de décalage d'un jour dû au fuseau).
const parseDay = (iso) => {
  const [y, m, d] = String(iso || '').split('-').map(Number);
  return y && m && d ? new Date(y, m - 1, d) : null;
};
const shortDay = (iso) => {
  const date = parseDay(iso);
  return date ? date.toLocaleDateString('fr-FR', { day: '2-digit', month: '2-digit' }) : iso;
};
const longDay = (iso) => {
  const date = parseDay(iso);
  return date ? date.toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' }) : iso;
};

const plural = (n, word) => `${formatCount(n)} ${word}${Number(n) > 1 ? 's' : ''}`;

const capitalize = (text) => (text ? text.charAt(0).toUpperCase() + text.slice(1) : '');

const changeOf = (now, before) => {
  if (!before) return null;
  return Math.round(((Number(now) || 0) - before) * 100 / before);
};

// Évolution par rapport à la période précédente de même durée.
const Change = ({ percent, days }) => {
  if (percent === null || percent === undefined) {
    return <p className="mt-1 text-xs text-gray-500">Rien à comparer sur les {days} jours d'avant</p>;
  }
  const up = percent > 0;
  const down = percent < 0;
  const tone = up ? 'bg-emerald-50 text-emerald-700' : down ? 'bg-red-50 text-red-700' : 'bg-gray-100 text-gray-600';
  const sign = up ? '▲ +' : down ? '▼ ' : '= ';
  return (
    <p className="mt-1 flex flex-wrap items-center gap-1 text-xs text-gray-500">
      <span className={`rounded-full px-2 py-0.5 font-semibold ${tone}`}>{sign}{percent} %</span>
      <span>par rapport aux {days} jours d'avant</span>
    </p>
  );
};

const SummaryTile = ({ label, value, hint, percent, days }) => (
  <div className="min-w-0 rounded-2xl border border-gray-100 bg-white p-4 shadow-sm">
    <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">{label}</p>
    <p className="mt-1 break-words text-2xl font-bold text-gray-900">{value}</p>
    {hint && <p className="text-xs text-gray-400">{hint}</p>}
    <Change percent={percent} days={days} />
  </div>
);

const Section = ({ title, aside, children, className = '' }) => (
  <section className={`min-w-0 rounded-2xl border border-gray-100 bg-white p-4 shadow-sm sm:p-6 ${className}`}>
    <div className="mb-4 flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
      <h3 className="text-lg font-bold text-gray-900">{title}</h3>
      {aside && <p className="text-sm font-semibold text-indigo-700">{aside}</p>}
    </div>
    {children}
  </section>
);

const Empty = ({ children = 'Pas encore de vente sur cette période' }) => (
  <p className="rounded-xl bg-gray-50 px-4 py-6 text-center text-sm text-gray-500">{children}</p>
);

const DailyTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="rounded-xl bg-white px-3 py-2 text-sm shadow-lg">
      <p className="font-semibold text-gray-900">{capitalize(longDay(row.date))}</p>
      <p className="text-gray-700">{formatMoney(row.revenue)}</p>
      <p className="text-gray-500">{plural(row.orders, 'commande')}</p>
    </div>
  );
};

const HourTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="rounded-xl bg-white px-3 py-2 text-sm shadow-lg">
      <p className="font-semibold text-gray-900">De {row.hour} h à {(row.hour + 1) % 24} h</p>
      <p className="text-gray-700">{plural(row.orders, 'commande')}</p>
    </div>
  );
};

// Liste classée avec une barre proportionnelle (produits, catégories, jours).
const RankedList = ({ rows }) => {
  const max = Math.max(1, ...rows.map((r) => r.value));
  return (
    <ol className="space-y-3">
      {rows.map((row, index) => (
        <li key={row.key} className="min-w-0">
          <div className="flex items-start justify-between gap-3 text-sm">
            <p className="min-w-0 break-words text-gray-900">
              {row.rank !== false && <span className="mr-1 font-semibold text-gray-400">{index + 1}.</span>}
              <span className={row.best ? 'font-bold' : 'font-medium'}>{row.label}</span>
              {row.detail && <span className="block text-xs text-gray-500">{row.detail}</span>}
            </p>
            <p className="shrink-0 font-semibold text-gray-900">{row.display}</p>
          </div>
          <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-gray-100">
            <div
              className="h-full rounded-full"
              style={{ width: `${Math.max(2, (row.value / max) * 100)}%`, backgroundColor: row.best ? BAR_BEST : BAR }}
            />
          </div>
        </li>
      ))}
    </ol>
  );
};

const LockedTeaser = ({ message, planName }) => (
  <section className="rounded-2xl border border-indigo-200 bg-indigo-50 p-4 sm:p-6">
    <div className="flex items-start gap-3">
      <svg className="mt-0.5 h-7 w-7 shrink-0 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
      </svg>
      <div className="min-w-0 flex-1">
        <h3 className="text-lg font-bold text-indigo-900">Statistiques avancées : forfait Pro</h3>
        <p className="mt-1 break-words text-sm text-indigo-800">
          {message || `Les statistiques détaillées font partie du forfait Pro.${planName ? ` Votre forfait actuel : ${planName}.` : ''}`}
        </p>
        <p className="mt-3 text-sm font-semibold text-indigo-900">Avec le forfait Pro, vous voyez aussi :</p>
        <ul className="mt-2 grid grid-cols-1 gap-1.5 text-sm text-indigo-900 sm:grid-cols-2">
          {PRO_TOOLS.map((tool) => (
            <li key={tool} className="flex items-start gap-2">
              <span className="mt-0.5 text-indigo-600" aria-hidden="true">✓</span>
              <span>{tool}</span>
            </li>
          ))}
        </ul>
        <Link
          to="/store/subscription"
          className="mt-4 inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-md transition-colors hover:bg-indigo-700"
        >
          Passer au forfait Pro
        </Link>
      </div>
    </div>
  </section>
);

const StoreStats = () => {
  const [days, setDays] = useState(30);
  const [attempt, setAttempt] = useState(0);
  // Dernière réponse reçue, avec la demande qu'elle concerne : { key, data, error }.
  const [result, setResult] = useState(null);
  const requestKey = `${days}-${attempt}`;

  useEffect(() => {
    let active = true;
    const key = `${days}-${attempt}`;
    api.get('/store/stats/', { params: { days } })
      .then((res) => {
        if (!active) return;
        if (res.data?.success && res.data.data) {
          setResult({ key, data: res.data.data, error: null });
        } else {
          setResult((prev) => ({ key, data: prev?.data || null, error: describeError(res.data || {}, "Les statistiques n'ont pas pu être chargées.") }));
        }
      })
      .catch((err) => {
        if (!active) return;
        setResult((prev) => ({ key, data: prev?.data || null, error: describeError(err, "Les statistiques n'ont pas pu être chargées.") }));
      });
    return () => { active = false; };
  }, [days, attempt]);

  const loading = !result || result.key !== requestKey;
  const data = result?.data || null;
  const error = !loading ? result?.error : null;
  const retry = () => setAttempt((n) => n + 1);

  const periodSelector = (
    <div className="mb-4 flex flex-wrap items-center gap-2" role="group" aria-label="Période">
      {PERIODS.map((value) => (
        <button
          key={value}
          type="button"
          onClick={() => setDays(value)}
          aria-pressed={days === value}
          className={`rounded-full px-4 py-2 text-sm font-semibold transition-colors ${
            days === value ? 'bg-indigo-600 text-white shadow' : 'border border-gray-300 bg-white text-gray-700 hover:bg-gray-50'
          }`}
        >
          {value} jours
        </button>
      ))}
      {loading && data && <span className="text-sm text-gray-500">Mise à jour…</span>}
    </div>
  );

  if (loading && !data) {
    return (
      <StoreLayout title="Statistiques">
        {periodSelector}
        <div className="flex min-h-[40vh] items-center justify-center" role="status" aria-label="Chargement des statistiques">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent" />
        </div>
      </StoreLayout>
    );
  }

  if (error && !data) {
    return (
      <StoreLayout title="Statistiques">
        {periodSelector}
        <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-red-800 sm:p-6">
          <p className="font-bold">{error.message}</p>
          {error.reason && <p className="mt-1 break-words text-sm">{error.reason}</p>}
          {error.nextStep && <p className="mt-1 break-words text-sm">{error.nextStep}</p>}
          <button
            type="button"
            onClick={retry}
            className="mt-4 rounded-lg bg-red-600 px-5 py-2 text-sm font-semibold text-white hover:bg-red-700"
          >
            Réessayer
          </button>
        </div>
      </StoreLayout>
    );
  }

  const period = data.days || days;
  const summary = data.summary || {};
  const previousBasket = summary.previous_orders ? Math.round((summary.previous_revenue || 0) / summary.previous_orders) : 0;

  const daily = Array.isArray(data.daily) ? data.daily : [];
  const hasDailySales = daily.some((d) => d.orders > 0 || d.revenue > 0);
  const bestDay = daily.reduce((best, d) => (d.revenue > (best?.revenue || 0) ? d : best), null);

  const topProducts = Array.isArray(data.top_products) ? data.top_products : [];
  const categories = Array.isArray(data.categories) ? data.categories : [];
  const customers = data.customers || {};
  const hours = Array.isArray(data.hours) ? data.hours.map((orders, hour) => ({ hour, orders: Number(orders) || 0 })) : [];
  const hasHours = hours.some((h) => h.orders > 0);
  const weekdays = Array.isArray(data.weekdays) ? data.weekdays : [];
  const hasWeekdays = weekdays.some((w) => w.orders > 0);
  const slowProducts = Array.isArray(data.slow_products) ? data.slow_products : [];
  const cancellationRate = Number(data.cancellation_rate) || 0;

  return (
    <StoreLayout title="Statistiques">
      {periodSelector}

      {error && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
          <p className="min-w-0 break-words">
            <span className="font-semibold">{error.message}</span>
            {error.nextStep ? ` ${error.nextStep}` : ''} Les chiffres affichés restent ceux de la période de {period} jours.
          </p>
          <button type="button" onClick={retry} className="rounded-lg bg-red-600 px-4 py-1.5 font-semibold text-white hover:bg-red-700">
            Réessayer
          </button>
        </div>
      )}

      <div className={`space-y-4 sm:space-y-6 ${loading ? 'opacity-60' : ''}`}>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 sm:gap-4">
          <SummaryTile
            label="Ventes"
            value={formatMoney(summary.revenue)}
            hint="Produits vendus, hors livraison"
            percent={summary.revenue_change_percent}
            days={period}
          />
          <SummaryTile
            label="Commandes"
            value={formatCount(summary.orders)}
            percent={summary.orders_change_percent}
            days={period}
          />
          <SummaryTile
            label="Panier moyen"
            value={formatMoney(summary.average_basket)}
            hint="Montant moyen d'une commande"
            percent={changeOf(summary.average_basket, previousBasket)}
            days={period}
          />
        </div>

        {data.locked ? (
          <LockedTeaser message={data.message} planName={data.plan_name} />
        ) : (
          <>
            <Section
              title="Ventes jour par jour"
              aside={hasDailySales && bestDay ? `Meilleure journée : ${shortDay(bestDay.date)}` : null}
            >
              {hasDailySales ? (
                <div className="h-64 w-full min-w-0">
                  <ResponsiveContainer width="100%" height={256}>
                    <BarChart data={daily} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                      <XAxis
                        dataKey="date"
                        tickFormatter={shortDay}
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: '#6b7280', fontSize: 12 }}
                        minTickGap={16}
                        dy={8}
                      />
                      <YAxis
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: '#6b7280', fontSize: 12 }}
                        tickFormatter={formatFcfaAxis}
                        width={48}
                        allowDecimals={false}
                      />
                      <Tooltip content={<DailyTooltip />} cursor={{ fill: '#f3f4f6' }} />
                      <Bar dataKey="revenue" fill={BAR} radius={[4, 4, 0, 0]} maxBarSize={32} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <Empty />
              )}
            </Section>

            <div className="grid grid-cols-1 gap-4 sm:gap-6 lg:grid-cols-2">
              <Section title="Meilleurs produits">
                {topProducts.length ? (
                  <RankedList
                    rows={topProducts.map((p) => ({
                      key: p.product_id ?? p.name,
                      label: p.name || 'Produit supprimé',
                      detail: plural(p.quantity, 'vendu'),
                      value: Number(p.revenue) || 0,
                      display: formatMoney(p.revenue),
                    }))}
                  />
                ) : (
                  <Empty />
                )}
              </Section>

              <Section title="Ventes par catégorie">
                {categories.length ? (
                  <RankedList
                    rows={categories.map((c) => ({
                      key: c.name,
                      label: c.name,
                      detail: plural(c.quantity, 'article'),
                      value: Number(c.revenue) || 0,
                      display: formatMoney(c.revenue),
                    }))}
                  />
                ) : (
                  <Empty />
                )}
              </Section>
            </div>

            <Section title="Vos clients">
              {customers.unique ? (
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                  <div className="rounded-xl bg-gray-50 p-4">
                    <p className="text-2xl font-bold text-gray-900">{formatCount(customers.unique)}</p>
                    <p className="text-sm font-semibold text-gray-700">Clients différents</p>
                    <p className="text-xs text-gray-500">Ont commandé sur la période</p>
                  </div>
                  <div className="rounded-xl bg-gray-50 p-4">
                    <p className="text-2xl font-bold text-gray-900">{formatCount(customers.returning)}</p>
                    <p className="text-sm font-semibold text-gray-700">Clients fidèles</p>
                    <p className="text-xs text-gray-500">2 commandes ou plus sur la période</p>
                  </div>
                  <div className="rounded-xl bg-gray-50 p-4">
                    <p className="text-2xl font-bold text-gray-900">{formatCount(customers.new)}</p>
                    <p className="text-sm font-semibold text-gray-700">Nouveaux clients</p>
                    <p className="text-xs text-gray-500">Première commande chez vous</p>
                  </div>
                </div>
              ) : (
                <Empty />
              )}
            </Section>

            <div className="grid grid-cols-1 gap-4 sm:gap-6 lg:grid-cols-2">
              <Section
                title="Heures des commandes"
                aside={data.best_hour !== null && data.best_hour !== undefined ? `Meilleure heure : ${data.best_hour} h` : null}
              >
                {hasHours ? (
                  <>
                    <div className="h-48 w-full min-w-0">
                      <ResponsiveContainer width="100%" height={192}>
                        <BarChart data={hours} margin={{ top: 4, right: 4, left: 0, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e5e7eb" />
                          <XAxis
                            dataKey="hour"
                            ticks={[0, 6, 12, 18, 23]}
                            tickFormatter={(h) => `${h} h`}
                            axisLine={false}
                            tickLine={false}
                            tick={{ fill: '#6b7280', fontSize: 12 }}
                            interval={0}
                          />
                          <YAxis
                            axisLine={false}
                            tickLine={false}
                            tick={{ fill: '#6b7280', fontSize: 12 }}
                            width={28}
                            allowDecimals={false}
                          />
                          <Tooltip content={<HourTooltip />} cursor={{ fill: '#f3f4f6' }} />
                          <Bar dataKey="orders" radius={[4, 4, 0, 0]}>
                            {hours.map((h) => (
                              <Cell key={h.hour} fill={h.hour === data.best_hour ? BAR_BEST : BAR_MUTED} />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                    <p className="mt-2 text-xs text-gray-500">Heure de Libreville. La barre foncée est l'heure où vous recevez le plus de commandes.</p>
                  </>
                ) : (
                  <Empty />
                )}
              </Section>

              <Section
                title="Jours de la semaine"
                aside={data.best_weekday ? `Meilleur jour : ${data.best_weekday}` : null}
              >
                {hasWeekdays ? (
                  <RankedList
                    rows={weekdays.map((w) => ({
                      key: w.day,
                      label: capitalize(w.day),
                      value: Number(w.orders) || 0,
                      display: plural(w.orders, 'commande'),
                      best: w.day === data.best_weekday,
                      rank: false,
                    }))}
                  />
                ) : (
                  <Empty />
                )}
              </Section>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:gap-6 lg:grid-cols-2">
              <Section title="Produits qui ne se vendent pas">
                {slowProducts.length ? (
                  <>
                    <p className="mb-3 text-sm text-gray-600">
                      En stock, mais aucune vente sur les {period} derniers jours.
                      {data.can_promote ? ' Pensez à une promotion ou à revoir le prix.' : ' Pensez à revoir le prix ou la description.'}
                    </p>
                    <ul className="divide-y divide-gray-100">
                      {slowProducts.map((p) => (
                        <li key={p.product_id ?? p.name} className="flex items-start justify-between gap-3 py-2 text-sm">
                          <span className="min-w-0 break-words font-medium text-gray-900">{p.name}</span>
                          <span className="shrink-0 text-gray-600">Stock : {formatCount(p.stock)}</span>
                        </li>
                      ))}
                    </ul>
                    <Link to="/store/products" className="mt-3 inline-block text-sm font-semibold text-indigo-700 hover:underline">
                      Gérer mes produits
                    </Link>
                  </>
                ) : (
                  <Empty>Tous vos produits en stock se sont vendus au moins une fois sur la période.</Empty>
                )}
              </Section>

              <Section title="Taux d'annulation">
                {cancellationRate === 0 && !summary.orders ? (
                  <Empty>Pas encore de commande sur cette période</Empty>
                ) : (
                  <>
                    <p className={`text-4xl font-bold ${cancellationRate > 10 ? 'text-red-700' : 'text-gray-900'}`}>{cancellationRate} %</p>
                    <p className="mt-1 text-sm text-gray-600">Part des commandes confirmées puis annulées ou remboursées sur les {period} derniers jours.</p>
                    {cancellationRate > 10 ? (
                      <p className="mt-3 rounded-xl bg-red-50 px-3 py-2 text-sm text-red-800">
                        ⚠️ Plus d'une commande sur dix est annulée. Gardez vos stocks à jour et confirmez vite les commandes.
                      </p>
                    ) : (
                      <p className="mt-3 rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
                        ✓ Taux bas : vos clients reçoivent ce qu'ils commandent.
                      </p>
                    )}
                  </>
                )}
              </Section>
            </div>
          </>
        )}
      </div>
    </StoreLayout>
  );
};

export default StoreStats;
