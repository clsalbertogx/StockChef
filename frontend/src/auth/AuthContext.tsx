import { createContext, type ReactNode, useCallback, useContext, useEffect, useState } from "react";
import { ApiError, api, clearToken, getToken } from "../api/client";

export interface SessionUser {
  id: string;
  email: string;
  name: string;
  role: string;
}

interface AuthContextValue {
  user: SessionUser | null;
  login: (tenantSlug: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null);

  useEffect(() => {
    if (!getToken()) return;
    api<SessionUser>("/auth/me")
      .then(setUser)
      .catch((e) => {
        if (e instanceof ApiError && e.status === 401) clearToken();
      });
  }, []);

  const login = useCallback(async (tenantSlug: string, email: string, password: string) => {
    const res = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ tenant_slug: tenantSlug, email, password }),
    });
    if (!res.ok) throw new ApiError("Credenciais inválidas.", res.status);
    const body = await res.json();
    localStorage.setItem("sc_token", body.access_token);
    setUser(body.user);
  }, []);

  const logout = useCallback(async () => {
    try {
      await api("/auth/logout", { method: "POST" });
    } finally {
      clearToken();
      setUser(null);
    }
  }, []);

  return <AuthContext.Provider value={{ user, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth deve ser usado dentro de AuthProvider");
  return ctx;
}
