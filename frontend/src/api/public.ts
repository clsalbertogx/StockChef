import { ApiError } from "./client";

export async function publicApi<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  const res = await fetch(`/api/v1${path}`, { ...init, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(body.detail ?? "Erro inesperado.", res.status, body.code);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
