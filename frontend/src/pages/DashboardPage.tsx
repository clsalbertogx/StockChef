import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function DashboardPage() {
  const { user, logout } = useAuth();
  return (
    <main className="mx-auto max-w-5xl space-y-6 p-8">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">{user?.name}</span>
          <button type="button" onClick={() => void logout()} className="text-sm text-red-600">
            Sair
          </button>
        </div>
      </header>
      <nav className="flex gap-3">
        <Link to="/insumos" className="rounded border px-4 py-2">
          Insumos
        </Link>
        <Link to="/produtos" className="rounded border px-4 py-2">
          Produtos
        </Link>
        <Link to="/pedidos" className="rounded border px-4 py-2">
          Pedidos
        </Link>
      </nav>
      <p className="mb-64 text-gray-600">
        Vertical slice: insumo → produto → pedido → baixa → margem.
      </p>
    </main>
  );
}
