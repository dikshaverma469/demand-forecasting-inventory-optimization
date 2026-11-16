import { useState } from 'react';
import { useAuth } from './auth.jsx';
import { errorMessage } from './api';

// Decorative demand curve for the sign-in screen: a drawn history line,
// a dashed projection, and a reorder-point level. Deterministic, no data needed.
function buildCurve() {
  let seed = 11;
  const rand = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const W = 800, H = 340, total = 66, historyEnd = 53;
  const pts = [];
  for (let i = 0; i < total; i++) {
    const base = 215 + i * 1.1 + Math.sin(i / 3.1) * 16 + Math.sin(i / 8) * 20;
    const noise = i <= historyEnd ? (rand() - 0.5) * 22 : 0;
    pts.push([(i / (total - 1)) * (W - 90), H - (base + noise)]);
  }
  const toPath = (arr) => arr.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`).join(' ');
  return {
    W, H,
    history: toPath(pts.slice(0, historyEnd + 1)),
    projection: toPath(pts.slice(historyEnd)),
    end: pts[total - 1],
    reorderY: H - 150,
  };
}
const curve = buildCurve();

function ForecastArt() {
  const { W, H, history, projection, end, reorderY } = curve;
  return (
    <svg className="art" viewBox={`0 -60 ${W} ${H + 60}`} preserveAspectRatio="xMidYMax meet" aria-hidden="true">
      {[60, 140, 220, 300].map((y) => (
        <line key={y} x1="0" x2={W} y1={y} y2={y} stroke="#FFFFFF" strokeOpacity="0.07" />
      ))}
      <line x1="0" x2={W} y1={reorderY} y2={reorderY} stroke="#7FB4CC" strokeOpacity="0.55" strokeDasharray="3 7" />
      <text x="28" y={reorderY - 10} fill="#9CC4D8" fontSize="14">Reorder point</text>
      <path className="draw" pathLength="1" d={history} fill="none" stroke="#EAF0F3" strokeWidth="2.5" strokeLinejoin="round" />
      <g className="proj">
        <path d={projection} fill="none" stroke="#F4C21B" strokeWidth="3" strokeDasharray="2 8" strokeLinecap="round" />
        <circle cx={end[0]} cy={end[1]} r="7" fill="#F4C21B" stroke="#10222F" strokeWidth="3" />
        <text x={end[0] + 4} y={end[1] - 20} fill="#F4C21B" fontSize="15" textAnchor="end">Next day forecast</text>
      </g>
    </svg>
  );
}

export default function Login() {
  const { authenticate } = useAuth();
  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [form, setForm] = useState({ full_name: '', username: '', password: '' });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const signup = mode === 'register';

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  function switchMode(next) {
    setMode(next);
    setError('');
  }

  async function submit(e) {
    e.preventDefault();
    setError('');
    if (!form.username.trim() || !form.password) {
      setError('Enter your username and password.');
      return;
    }
    setBusy(true);
    try {
      const payload = signup
        ? form
        : { username: form.username, password: form.password };
      await authenticate(mode, payload);
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <main className="auth">
      <section className="stage">
        <p className="stage-title">Demand Forecasting &amp; Inventory Optimization</p>
        <h1>Stock what will sell, before it sells out.</h1>
        <p className="stage-sub">
          Daily demand forecasts, safety stock and reorder points for every product category, in one place.
        </p>
        <ForecastArt />
        <p className="stage-credit">Built by Diksha,Komal & Anshika</p>
      </section>

      <section className="auth-side">
        <div className="auth-card">
          <div className="seg-toggle" role="group" aria-label="Choose how to continue">
            <button type="button" aria-pressed={!signup} onClick={() => switchMode('login')}>Sign in</button>
            <button type="button" aria-pressed={signup} onClick={() => switchMode('register')}>Create account</button>
          </div>

          <h2>{signup ? 'Create your account' : 'Welcome back'}</h2>
          <p className="auth-lede">
            {signup
              ? 'Choose a username and a password of at least 8 characters.'
              : 'Sign in to open the dashboard.'}
          </p>

          <form onSubmit={submit} noValidate>
            {signup && (
              <div className="field">
                <label htmlFor="full_name">Full name</label>
                <input id="full_name" value={form.full_name} onChange={update('full_name')}
                  autoComplete="name" maxLength={60} placeholder="Diksha Verma" />
              </div>
            )}
            <div className="field">
              <label htmlFor="username">Username</label>
              <input id="username" value={form.username} onChange={update('username')}
                autoComplete="username" autoCapitalize="none" spellCheck="false" autoFocus />
            </div>
            <div className="field">
              <label htmlFor="password">Password</label>
              <div className="pw">
                <input id="password" type={showPassword ? 'text' : 'password'} value={form.password}
                  onChange={update('password')} autoComplete={signup ? 'new-password' : 'current-password'} />
                <button type="button" className="pw-toggle" onClick={() => setShowPassword((s) => !s)}
                  aria-pressed={showPassword}>
                  {showPassword ? 'Hide' : 'Show'}
                </button>
              </div>
            </div>

            <p className="form-error" role="alert">{error}</p>

            <button className="primary" type="submit" disabled={busy}>
              {busy ? (signup ? 'Creating account…' : 'Signing in…') : signup ? 'Create account' : 'Sign in'}
            </button>
          </form>

          <p className="switch">
            {signup ? 'Already have an account?' : 'New here?'}{' '}
            <button type="button" className="link" onClick={() => switchMode(signup ? 'login' : 'register')}>
              {signup ? 'Sign in' : 'Create an account'}
            </button>
          </p>
        </div>
      </section>
    </main>
  );
}
