"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { api, tokenStore } from "@/lib/api";
import type { Profile, TokenPair } from "@/lib/types";

interface AuthContextValue {
  profile: Profile | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (input: {
    username: string;
    email: string;
    password: string;
    password2: string;
  }) => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);

  const loadProfile = useCallback(async () => {
    if (!tokenStore.access) {
      setProfile(null);
      setLoading(false);
      return;
    }
    try {
      const me = await api.get<Profile>("/auth/me/");
      setProfile(me);
    } catch {
      setProfile(null);
    } finally {
      setLoading(false);
    }
  }, []);

  // Bootstrap the session on mount by syncing with external systems (the token
  // store + the API). setState here is intentional, not derived render state.
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadProfile();
  }, [loadProfile]);

  const login = useCallback(
    async (username: string, password: string) => {
      const tokens = await api.post<TokenPair>(
        "/auth/token/",
        { username, password },
        false,
      );
      tokenStore.set(tokens);
      await loadProfile();
    },
    [loadProfile],
  );

  const register = useCallback(
    async (input: {
      username: string;
      email: string;
      password: string;
      password2: string;
    }) => {
      await api.post("/auth/register/", input, false);
      await login(input.username, input.password);
    },
    [login],
  );

  const logout = useCallback(() => {
    tokenStore.clear();
    setProfile(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ profile, loading, login, register, logout, refresh: loadProfile }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
