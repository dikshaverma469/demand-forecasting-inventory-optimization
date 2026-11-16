import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import api, { setUnauthorizedHandler, tokenStore } from './api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  // On first load, restore the session if a saved token is still valid.
  useEffect(() => {
    setUnauthorizedHandler(logout);
    if (!tokenStore.get()) {
      setReady(true);
      return;
    }
    api.get('/auth/me')
      .then((res) => setUser(res.data))
      .catch(() => tokenStore.clear())
      .finally(() => setReady(true));
  }, [logout]);

  // mode is 'login' or 'register'
  const authenticate = useCallback(async (mode, payload) => {
    const res = await api.post(`/auth/${mode}`, payload);
    tokenStore.set(res.data.access_token);
    setUser(res.data.user);
  }, []);

  const value = useMemo(() => ({ user, ready, authenticate, logout }), [user, ready, authenticate, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
