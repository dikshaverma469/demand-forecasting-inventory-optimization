import { useEffect, useMemo, useRef, useState } from 'react';
import {
  ResponsiveContainer, ComposedChart, CartesianGrid, XAxis, YAxis,
  Area, Line, ReferenceLine, Tooltip,
} from 'recharts';
import api, { errorMessage } from './api';
import { useAuth } from './auth.jsx';

const INK = '#10222F';
const HARBOR = '#2E6F8E';
const SIGNAL = '#F4C21B';
const MUTED = '#5E7080';

const nf = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 1 });
const fmt = (n) => (n == null ? '–' : nf.format(n));
const nf0 = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 });
const fmt0 = (n) => (n == null ? '–' : nf0.format(n));
const parseDate = (iso) => new Date(`${iso}T00:00:00`);
const longDate = (iso) => parseDate(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
const shortDate = (iso) => parseDate(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
const nextDay = (iso) => {
  const d = parseDate(iso);
  d.setDate(d.getDate() + 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
};

/* ---------- pieces ---------- */

function DemandChart({ points, forecast, average }) {
  const data = useMemo(() => {
    if (!points?.length) return [];
    const rows = points.map((p, i) => {
      const window = points.slice(Math.max(0, i - 6), i + 1);
      const avg7 = window.reduce((s, x) => s + x.quantity, 0) / window.length;
      return { date: p.date, quantity: p.quantity, avg7: Math.round(avg7 * 10) / 10 };
    });
    if (forecast != null) {
      const last = rows[rows.length - 1];
      last.forecast = last.quantity; // join the dashed line to the last real day
      rows.push({ date: nextDay(last.date), forecast });
    }
    return rows;
  }, [points, forecast]);

  if (!data.length) return <p className="empty">No demand history to show for this category.</p>;

  const renderForecastDot = (p) =>
    p.index === data.length - 1
      ? <circle key="f" cx={p.cx} cy={p.cy} r={6} fill={SIGNAL} stroke={INK} strokeWidth={2.5} />
      : <g key={p.index} />;

  return (
    <ResponsiveContainer width="100%" height={300}>
      <ComposedChart data={data} margin={{ top: 8, right: 22, bottom: 0, left: -8 }}>
        <CartesianGrid vertical={false} stroke="#E1E6EA" />
        <XAxis dataKey="date" tickFormatter={shortDate} tick={{ fill: MUTED, fontSize: 12 }}
          tickLine={false} axisLine={{ stroke: '#C9D1D7' }} minTickGap={36} />
        <YAxis tick={{ fill: MUTED, fontSize: 12 }} tickLine={false} axisLine={false} width={44} />
        <Tooltip content={<ChartTip />} cursor={{ stroke: '#9AA8B3', strokeDasharray: '3 3' }} />
        <ReferenceLine y={average} stroke={HARBOR} strokeDasharray="4 6" strokeOpacity={0.8} />
        <Area dataKey="quantity" stroke="none" fill={HARBOR} fillOpacity={0.14} isAnimationActive={false} />
        <Line dataKey="quantity" stroke={HARBOR} strokeWidth={1.5} strokeOpacity={0.6} dot={false}
          isAnimationActive={false} />
        <Line dataKey="avg7" stroke={INK} strokeWidth={2.5} dot={false} isAnimationActive={false} />
        <Line dataKey="forecast" stroke={SIGNAL} strokeWidth={3} strokeDasharray="2 6" strokeLinecap="round"
          dot={renderForecastDot} activeDot={false} isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

function ChartTip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const row = payload[0].payload;
  return (
    <div className="tip">
      <strong>{longDate(label)}</strong>
      {row.quantity != null && <span>Orders: {fmt(row.quantity)}</span>}
      {row.avg7 != null && <span>7-day average: {fmt(row.avg7)}</span>}
      {row.forecast != null && row.quantity == null && <span>Forecast: {fmt(row.forecast)}</span>}
    </div>
  );
}

function StockBar({ plan }) {
  const total = plan.reorder_point || 1;
  const safety = Math.min(plan.safety_stock, total);
  const leadDemand = Math.max(plan.reorder_point - plan.safety_stock, 0);
  const pct = (safety / total) * 100;
  return (
    <section className="panel">
      <h3>What the reorder point is made of</h3>
      <p className="hint">
        When stock falls to {fmt0(plan.reorder_point)} units, order {fmt0(plan.economic_order_quantity)} more.
        About {fmt0(leadDemand)} units sell while the order is on its way ({plan.lead_time_days} days).
        The safety stock covers days busier than average.
      </p>
      <div className="stack" role="img"
        aria-label={`Safety stock ${fmt0(plan.safety_stock)} units plus demand during lead time ${fmt0(leadDemand)} units`}>
        <div className="stack-safety" style={{ width: `${pct}%` }} />
        <div className="stack-lead" />
      </div>
      <dl className="stack-key">
        <div><dt><i className="sw sw-safety" />Safety stock</dt><dd>{fmt0(plan.safety_stock)} units</dd></div>
        <div><dt><i className="sw sw-lead" />Demand during lead time</dt><dd>{fmt0(leadDemand)} units</dd></div>
        <div><dt>Reorder point</dt><dd>{fmt0(plan.reorder_point)} units</dd></div>
      </dl>
    </section>
  );
}

function Overview({ rows, onPick }) {
  const max = Math.max(...rows.map((r) => r.reorder_point), 1);
  return (
    <section className="panel">
      <h3>Top {rows.length} categories by order volume</h3>
      <p className="hint">Based on a 7-day lead time and a 95% service level. Select a category to see its forecast.</p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col">Category</th>
              <th scope="col" className="num">Avg daily demand</th>
              <th scope="col" className="num">Safety stock</th>
              <th scope="col">Reorder point</th>
              <th scope="col" className="num">Order quantity</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.category}>
                <th scope="row"><button className="link" onClick={() => onPick(r.category)}>{r.category}</button></th>
                <td className="num">{fmt(r.avg_daily_demand)}</td>
                <td className="num">{fmt0(r.safety_stock)}</td>
                <td>
                  <div className="bar-cell">
                    <span className="bar"><i style={{ width: `${(r.reorder_point / max) * 100}%` }} /></span>
                    <span className="num">{fmt0(r.reorder_point)}</span>
                  </div>
                </td>
                <td className="num">{fmt0(r.economic_order_quantity)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

/* ---------- page ---------- */

export default function Dashboard() {
  const { user, logout } = useAuth();
  const [categories, setCategories] = useState([]);
  const [summary, setSummary] = useState([]);
  const [boot, setBoot] = useState({ loading: true, error: '' });
  const [selected, setSelected] = useState('');
  const [view, setView] = useState('category'); // 'category' | 'overview'
  const [search, setSearch] = useState('');
  const [lead, setLead] = useState(7);
  const [service, setService] = useState(0.95);
  const [detail, setDetail] = useState({ loading: false, forecast: null, plan: null, history: null, errors: {} });
  const requestId = useRef(0);

  const loadBase = () => {
    setBoot({ loading: true, error: '' });
    Promise.all([api.get('/categories'), api.get('/dashboard-summary')])
      .then(([c, s]) => {
        const list = c.data.categories.slice().sort((a, b) => a.localeCompare(b));
        setCategories(list);
        setSummary(s.data.summary);
        setSelected((cur) => cur || s.data.summary[0]?.category || list[0] || '');
        setBoot({ loading: false, error: '' });
      })
      .catch((err) => setBoot({ loading: false, error: errorMessage(err) }));
  };
  useEffect(loadBase, []);

  useEffect(() => {
    if (!selected) return undefined;
    const id = ++requestId.current;
    setDetail((d) => ({ ...d, loading: true }));
    const timer = setTimeout(async () => {
      const name = encodeURIComponent(selected);
      const [f, p, h] = await Promise.allSettled([
        api.get(`/forecast/${name}`),
        api.get(`/inventory/${name}`, { params: { lead_time_days: lead, service_level: service } }),
        api.get(`/history/${name}`, { params: { days: 90 } }),
      ]);
      if (id !== requestId.current) return; // a newer request replaced this one
      setDetail({
        loading: false,
        forecast: f.status === 'fulfilled' ? f.value.data : null,
        plan: p.status === 'fulfilled' ? p.value.data : null,
        history: h.status === 'fulfilled' ? h.value.data.points : null,
        errors: {
          forecast: f.status === 'rejected' ? errorMessage(f.reason) : '',
          plan: p.status === 'rejected' ? errorMessage(p.reason) : '',
        },
      });
    }, 200);
    return () => clearTimeout(timer);
  }, [selected, lead, service]);

  const visible = categories.filter((c) => c.toLowerCase().includes(search.trim().toLowerCase()));
  const { forecast, plan, history } = detail;
  const lastDate = history?.length ? history[history.length - 1].date : forecast?.last_date;
  const pickFromOverview = (name) => { setSelected(name); setView('category'); };

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <svg width="26" height="26" viewBox="0 0 32 32" aria-hidden="true">
            <rect width="32" height="32" rx="7" fill="#1B3547" />
            <path d="M5 22 L12 15 L17 19 L27 8" fill="none" stroke={SIGNAL} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span>Demand Forecasting &amp; Inventory Optimization</span>
        </div>
        <div className="who">
          <span className="who-name">{user.full_name || user.username}</span>
          <button className="ghost" onClick={logout}>Sign out</button>
        </div>
      </header>

      <div className="workspace">
        <aside className="side" aria-label="Categories">
          <label className="visually-hidden" htmlFor="cat-search">Search categories</label>
          <input id="cat-search" className="search" type="search" placeholder="Search categories"
            value={search} onChange={(e) => setSearch(e.target.value)} />
          <ul className="cat-list">
            {visible.map((c) => (
              <li key={c}>
                <button className={c === selected && view === 'category' ? 'cat is-active' : 'cat'}
                  aria-current={c === selected && view === 'category' ? 'true' : undefined}
                  onClick={() => pickFromOverview(c)}>{c}</button>
              </li>
            ))}
            {!visible.length && <li className="empty">No category matches “{search}”.</li>}
          </ul>
        </aside>

        <main className="main" aria-busy={detail.loading || boot.loading}>
          {boot.loading && <p className="empty" role="status">Loading categories…</p>}
          {boot.error && (
            <div className="notice" role="alert">
              <p>{boot.error}</p>
              <button className="ghost dark" onClick={loadBase}>Try again</button>
            </div>
          )}

          {!boot.loading && !boot.error && (
            <>
              <div className="main-head">
                <div>
                  <h1>{view === 'overview' ? 'All categories' : selected}</h1>
                  {view === 'category' && lastDate && (
                    <p className="sub">History up to {longDate(lastDate)}</p>
                  )}
                </div>
                <div className="tabs" role="group" aria-label="View">
                  <button aria-pressed={view === 'category'} onClick={() => setView('category')}>Category</button>
                  <button aria-pressed={view === 'overview'} onClick={() => setView('overview')}>All categories</button>
                </div>
              </div>

              <label className="visually-hidden" htmlFor="cat-select">Category</label>
              <select id="cat-select" className="cat-select" value={selected}
                onChange={(e) => pickFromOverview(e.target.value)}>
                {categories.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>

              {view === 'overview' ? (
                <Overview rows={summary} onPick={pickFromOverview} />
              ) : (
                <div className={detail.loading ? 'is-loading' : ''}>
                  <section className="kpis" aria-label="Key numbers">
                    <div className="kpi kpi-lead">
                      <span className="kpi-label">
                        Forecast demand{lastDate ? `, ${longDate(nextDay(lastDate))}` : ''}
                      </span>
                      <strong>{forecast ? `${fmt0(forecast.predicted_next_day_demand)} units` : '–'}</strong>
                      <span className="kpi-note">
                        {forecast ? `Last recorded day: ${fmt0(forecast.last_actual_demand)} units` : detail.errors.forecast || ' '}
                      </span>
                    </div>
                    <div className="kpi">
                      <span className="kpi-label">Reorder point</span>
                      <strong>{plan ? `${fmt0(plan.reorder_point)} units` : '–'}</strong>
                      <span className="kpi-note">Order when stock reaches this level</span>
                    </div>
                    <div className="kpi">
                      <span className="kpi-label">Safety stock</span>
                      <strong>{plan ? `${fmt0(plan.safety_stock)} units` : '–'}</strong>
                      <span className="kpi-note">Buffer for busier-than-average days</span>
                    </div>
                    <div className="kpi">
                      <span className="kpi-label">Order quantity</span>
                      <strong>{plan ? `${fmt0(plan.economic_order_quantity)} units` : '–'}</strong>
                      <span className="kpi-note">Most economical amount per order</span>
                    </div>
                  </section>

                  <section className="panel">
                    <div className="panel-head">
                      <h3>Daily demand, last 90 days</h3>
                      <ul className="legend">
                        <li><i className="sw sw-orders" />Orders</li>
                        <li><i className="sw sw-avg" />7-day average</li>
                        <li><i className="sw sw-mean" />Overall average</li>
                        <li><i className="sw sw-forecast" />Forecast</li>
                      </ul>
                    </div>
                    <DemandChart points={history} forecast={forecast?.predicted_next_day_demand}
                      average={plan?.avg_daily_demand} />
                  </section>

                  <section className="panel controls">
                    <div className="field inline">
                      <label htmlFor="lead">Supplier lead time</label>
                      <select id="lead" value={lead} onChange={(e) => setLead(Number(e.target.value))}>
                        {[3, 5, 7, 10, 14, 21, 30].map((d) => <option key={d} value={d}>{d} days</option>)}
                      </select>
                    </div>
                    <div className="field inline">
                      <label htmlFor="service">Service level</label>
                      <select id="service" value={service} onChange={(e) => setService(Number(e.target.value))}>
                        {[0.9, 0.95, 0.97, 0.99].map((s) => <option key={s} value={s}>{Math.round(s * 100)}%</option>)}
                      </select>
                    </div>
                    <p className="hint">
                      Service level is the chance of not running out of stock while waiting for an order.
                      The numbers above update when you change these.
                    </p>
                  </section>

                  {plan
                    ? <StockBar plan={plan} />
                    : detail.errors.plan && <div className="notice" role="alert"><p>{detail.errors.plan}</p></div>}
                </div>
              )}
            </>
          )}
        </main>
      </div>

      <footer className="foot">Built by Diksha,Komal & Anshika, final-year B.Tech ECE, IGDTUW</footer>
    </div>
  );
}
