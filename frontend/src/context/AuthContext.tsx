import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

import { ApiError, setApiBaseUrl, setAuthToken, setUnauthorizedHandler } from '../services/api/client';
import { authApi } from '../services/api/endpoints';
import { secureStorage } from '../services/storage/secureStorage';
import type { User } from '../types/api';

interface AuthState {
  user: User | null;
  ready: boolean; // stored token has been checked
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  setUser: (user: User) => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  const logout = useCallback(async () => {
    setAuthToken(null);
    setUser(null);
    await secureStorage.clearToken();
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(() => void logout());
    (async () => {
      const serverUrl = await secureStorage.getServerUrl();
      if (serverUrl) setApiBaseUrl(serverUrl);
      const token = await secureStorage.getToken();
      if (token) {
        setAuthToken(token);
        try {
          setUser(await authApi.me());
        } catch (err) {
          // Keep the token when the server is merely unreachable; drop it when it was rejected.
          if (err instanceof ApiError && !err.isNetworkError) await logout();
        }
      }
      setReady(true);
    })();
    return () => setUnauthorizedHandler(null);
  }, [logout]);

  const persist = useCallback(async (token: string, u: User) => {
    setAuthToken(token);
    await secureStorage.setToken(token);
    setUser(u);
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const res = await authApi.login(email.trim(), password);
      await persist(res.access_token, res.user);
    },
    [persist],
  );

  const register = useCallback(
    async (name: string, email: string, password: string) => {
      const res = await authApi.register(name.trim(), email.trim(), password);
      await persist(res.access_token, res.user);
    },
    [persist],
  );

  const value = useMemo(() => ({ user, ready, login, register, logout, setUser }), [user, ready, login, register, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}
