import { type FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [restaurantName, setRestaurantName] = useState("");
  const [slug, setSlug] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [slugTouched, setSlugTouched] = useState(false);

  function generateSlug(input: string): string {
    return input
      .toLowerCase()
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "")
      .slice(0, 60);
  }

  function handleRestaurantNameChange(e: React.ChangeEvent<HTMLInputElement>) {
    const value = e.target.value;
    setRestaurantName(value);
    if (!slugTouched) {
      setSlug(generateSlug(value));
    }
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (password !== confirmPassword) {
      setError("As senhas não conferem.");
      return;
    }
    if (password.length < 8) {
      setError("A senha deve ter pelo menos 8 caracteres.");
      return;
    }
    setLoading(true);
    try {
      await register(email, password, {
        tenant_name: restaurantName,
        tenant_slug: slug,
        name,
      });
      navigate("/");
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Não foi possível criar a conta.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto grid min-h-dvh max-w-md place-items-center p-8">
      <form onSubmit={onSubmit} className="w-full space-y-4">
        <h1 className="text-2xl font-semibold">Criar conta no StockChef</h1>
        <p className="text-sm text-gray-600">
          Configure seu restaurante e comece a gerenciar pedidos e estoque.
        </p>

        <label className="block space-y-1">
          <span className="text-sm">Nome do restaurante</span>
          <input
            value={restaurantName}
            onChange={handleRestaurantNameChange}
            onBlur={() => setSlugTouched(true)}
            required
            className="w-full rounded border px-3 py-2"
            placeholder="Ex: Lanches do João"
          />
        </label>

        <label className="block space-y-1">
          <span className="text-sm">Seu nome</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="w-full rounded border px-3 py-2"
            placeholder="Ex: João Silva"
          />
        </label>

        <label className="block space-y-1">
          <span className="text-sm">E-mail</span>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full rounded border px-3 py-2"
            placeholder="exemplo@email.com"
          />
        </label>

        <label className="block space-y-1">
          <span className="text-sm">Senha</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            className="w-full rounded border px-3 py-2"
          />
        </label>

        <label className="block space-y-1">
          <span className="text-sm">Confirmar senha</span>
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
            className="w-full rounded border px-3 py-2"
          />
        </label>

        {error && (
          <p role="alert" className="text-sm text-red-600">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
        >
          {loading ? "Criando conta…" : "Criar conta"}
        </button>

        <p className="text-center text-sm text-gray-600">
          Já tem conta?{" "}
          <a href="/login" className="text-blue-600 hover:underline">
            Entrar
          </a>
        </p>
      </form>
    </main>
  );
}
