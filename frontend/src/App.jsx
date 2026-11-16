import { useAuth } from './auth.jsx';
import Login from './Login.jsx';
import Dashboard from './Dashboard.jsx';

export default function App() {
  const { user, ready } = useAuth();
  if (!ready) return <div className="boot" role="status">Loading…</div>;
  return user ? <Dashboard /> : <Login />;
}
