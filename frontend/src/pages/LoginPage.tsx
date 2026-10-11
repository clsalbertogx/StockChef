import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { publicApi } from "../api/public";
import type { TenantInfo } from "../api/types";
import { useAuth } from "../auth/AuthContext";

type Step = "email" | "tenant" | "password";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [step, setStep] = useState<Step>("email");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [selectedTenant, setSelectedTenant] = useState<TenantInfo | null>(null);
  const [tenants, setTenants] = useState<TenantInfo[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onEmailSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await publicApi<{ tenants: TenantInfo[] }>(
        `/auth/tenants-by-email?email=${encodeURIComponent(email)}`,
      );
      if (res.tenants.length === 0) {
        setError("Email não cadastrado.");
        return;
      }
      if (res.tenants.length === 1) {
        setSelectedTenant(res.tenants[0]);
        setStep("password");
      } else {
        setTenants(res.tenants);
        setStep("tenant");
      }
    } catch {
      setError("Erro ao buscar contas. Tente novamente.");
    } finally {
      setLoading(false);
    }
  }

  function onTenantSelect(tenant: TenantInfo) {
    setSelectedTenant(tenant);
    setStep("password");
  }

  async function onPasswordSubmit(e: FormEvent) {
    e.preventDefault();
    if (!selectedTenant) return;
    setError(null);
    setLoading(true);
    try {
      await login(selectedTenant.slug, email, password);
      navigate("/");
    } catch {
      setError("Senha incorreta.");
    } finally {
      setLoading(false);
    }
  }

  function goBack() {
    if (step === "tenant") setStep("email");
    else if (step === "password") setStep(tenants.length > 1 ? "tenant" : "email");
  }

  return (
    <main className="mx-auto grid min-h-dvh max-w-md place-items-center p-8">
      <form
        onSubmit={step === "email" ? onEmailSubmit : onPasswordSubmit}
        className="w-full space-y-4"
      >
        <h1 className="text-2xl font-semibold">Acessar StockChef</h1>

        {step === "email" && (
          <>
            <label className="block space-y-1">
              <span className="text-sm">E-mail</span>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={loading}
                className="w-full rounded border px-3 py-2"
                placeholder="seu@email.com"
                autoComplete="email"
              />
            </label>
            {error && (
              <p role="alert" className="text-sm text-red-600">
                {error}
              </p>
            )}
            <button
              type="submit"
              disabled={loading || !email}
              className="w-full rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
            >
              {loading ? "Buscando…" : "Continuar"}
            </button>
          </>
        )}

        {step === "tenant" && (
          <>
            <p className="text-sm text-gray-600">
              Encontramos {tenants.length} restaurantes para <strong>{email}</strong>. Escolha um
              para continuar:
            </p>
            <div className="space-y-2">
              {tenants.map((t) => (
                <button
                  key={t.slug}
                  type="button"
                  onClick={() => onTenantSelect(t)}
                  disabled={loading}
                  className="w-full text-left rounded border px-3 py-2 hover:bg-gray-50 disabled:opacity-50"
                >
                  <span className="font-medium">{t.name}</span>
                  <span className="text-xs text-gray-500"> ({t.slug})</span>
                </button>
              ))}
            </div>
            <button
              type="button"
              onClick={goBack}
              disabled={loading}
              className="w-full rounded border px-4 py-2 text-sm"
            >
              Voltar
            </button>
          </>
        )}

        {step === "password" && (
          <>
            <p className="text-sm text-gray-600">
              Entrando em <strong>{selectedTenant?.name}</strong> ({selectedTenant?.slug})
            </p>
            <label className="block space-y-1">
              <span className="text-sm">Senha</span>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={loading}
                className="w-full rounded border px-3 py-2"
                autoComplete="current-password"
              />
            </label>
            {error && (
              <p role="alert" className="text-sm text-red-600">
                {error}
              </p>
            )}
            <button
              type="submit"
              disabled={loading || !password}
              className="w-full rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
            >
              {loading ? "Entrando…" : "Entrar"}
            </button>
            <button
              type="button"
              onClick={goBack}
              disabled={loading}
              className="w-full rounded border px-4 py-2 text-sm"
            >
              Trocar restaurante
            </button>
          </>
        )}

        <p className="text-center text-sm text-gray-600">
          Não tem conta?{" "}
          <a href="/register" className="text-blue-600 hover:underline">
            Criar conta
          </a>
        </p>
      </form>
    </main>
  );
}
