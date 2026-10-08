const TOKEN_KEY = "sc_token";

export class ApiError extends Error {
  status: number;
  code?: string;
  constructor(message: string, status: number, code?: string) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

async function refreshSession(): Promise<boolean> {
  const res = await fetch("/api/v1/auth/refresh", { method: "POST", credentials: "include" });
  if (!res.ok) return false;
  const body = await res.json();
  setToken(body.access_token);
  return true;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body) headers.set("Content-Type", "application/json");

  let res = await fetch(`/api/v1${path}`, { ...init, headers, credentials: "include" });

  if (res.status === 401) {
    const ok = await refreshSession();
    if (ok) {
      const retryHeaders = new Headers(headers);
      const fresh = getToken();
      if (fresh) retryHeaders.set("Authorization", `Bearer ${fresh}`);
      res = await fetch(`/api/v1${path}`, {
        ...init,
        headers: retryHeaders,
        credentials: "include",
      });
    }
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(body.detail ?? "Erro inesperado.", res.status, body.code);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const login = (body: { tenant_slug: string; email: string; password: string }) =>
  api<{ access_token: string; user: { id: string; email: string; name: string; role: string } }>(
    "/auth/login",
    { method: "POST", body: JSON.stringify(body) },
  );
