import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";

interface DashboardMetrics {
  pedidos: { hoje: number; ontem: number; variacao_pct: number };
  faturamento: { hoje: string; mes: string; ticket_medio_hoje: string };
  pedidos_por_status: Record<string, number>;
  alertas: {
    estoque_critico: Array<{ nome: string; quantidade: string; minimo: string; unidade: string }>;
    pedidos_aguardando: number;
    pedidos_preparando: number;
    pedidos_prontos: number;
    pos_pendentes: number;
  };
  clientes_ativos_30d: number;
  top_produtos: Array<{ nome: string; quantidade: number }>;
}

interface RecentOrder {
  codigo: string;
  status: string;
  total: string;
  criado_em: string;
  cliente: string;
}

const STATUS_LABELS: Record<string, string> = {
  received: "Recebido",
  confirmed: "Confirmado",
  preparing: "Preparando",
  ready: "Pronto",
  out_for_delivery: "Em entrega",
  delivered: "Entregue",
  completed: "Concluído",
  cancelled: "Cancelado",
  refunded: "Reembolsado",
};

const STATUS_COLORS: Record<string, string> = {
  received: "bg-gray-100 text-gray-800",
  confirmed: "bg-blue-100 text-blue-800",
  preparing: "bg-yellow-100 text-yellow-800",
  ready: "bg-green-100 text-green-800",
  out_for_delivery: "bg-purple-100 text-purple-800",
  delivered: "bg-indigo-100 text-indigo-800",
  completed: "bg-gray-100 text-gray-800",
  cancelled: "bg-red-100 text-red-800",
  refunded: "bg-orange-100 text-orange-800",
};

export default function DashboardPage() {
  const { user, logout } = useAuth();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [recentOrders, setRecentOrders] = useState<RecentOrder[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadDashboard() {
      try {
        setLoading(true);
        const [resumoRes, recentesRes] = await Promise.all([
          api<DashboardMetrics>("/dashboard/resumo"),
          api<RecentOrder[]>("/dashboard/pedidos-recentes?limit=8"),
        ]);
        setMetrics(resumoRes);
        setRecentOrders(recentesRes);
      } catch (err) {
        setError("Erro ao carregar dashboard. Verifique sua conexão.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadDashboard();
  }, []);

  if (loading) {
    return (
      <main className="mx-auto max-w-5xl space-y-6 p-8">
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-10 w-10 border-3 border-blue-600 border-t-transparent"></div>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main className="mx-auto max-w-5xl space-y-6 p-8">
        <div className="rounded border border-red-300 bg-red-50 p-4 text-red-700">{error}</div>
      </main>
    );
  }

  const m = metrics ?? {
    pedidos: { hoje: 0, ontem: 0, variacao_pct: 0 },
    faturamento: { hoje: "0", mes: "0", ticket_medio_hoje: "0" },
    pedidos_por_status: {},
    alertas: {
      estoque_critico: [],
      pedidos_aguardando: 0,
      pedidos_preparando: 0,
      pedidos_prontos: 0,
      pos_pendentes: 0,
    },
    clientes_ativos_30d: 0,
    top_produtos: [],
  };

  const statusCards = [
    { label: "Pedidos hoje", value: m.pedidos.hoje, icon: "📦", color: "bg-blue-500" },
    {
      label: "Faturamento hoje",
      value: `R$ ${Number(m.faturamento.hoje).toFixed(2)}`,
      icon: "💰",
      color: "bg-green-500",
    },
    {
      label: "Ticket médio",
      value: `R$ ${Number(m.faturamento.ticket_medio_hoje).toFixed(2)}`,
      icon: "🎯",
      color: "bg-purple-500",
    },
    { label: "Clientes (30d)", value: m.clientes_ativos_30d, icon: "👥", color: "bg-orange-500" },
  ];

  const alertCards = [
    {
      label: "Aguardando",
      count: m.alertas.pedidos_aguardando,
      color: "bg-blue-100 text-blue-800",
    },
    {
      label: "Preparando",
      count: m.alertas.pedidos_preparando,
      color: "bg-yellow-100 text-yellow-800",
    },
    { label: "Pronto", count: m.alertas.pedidos_prontos, color: "bg-green-100 text-green-800" },
    {
      label: "POs pendentes",
      count: m.alertas.pos_pendentes,
      color: "bg-orange-100 text-orange-800",
    },
  ];

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-8">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="text-sm text-gray-600 mt-1">Visão geral do seu restaurante</p>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">{user?.name}</span>
          <button
            type="button"
            onClick={() => void logout()}
            className="text-sm text-red-600 hover:underline"
          >
            Sair
          </button>
        </div>
      </header>

      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {statusCards.map((card) => (
          <div key={card.label} className="rounded-lg border bg-white p-5 shadow-sm">
            <div className="flex items-center gap-3">
              <div className={`rounded-full p-3 ${card.color}`}>{card.icon}</div>
              <div>
                <p className="text-sm text-gray-600">{card.label}</p>
                <p className="text-2xl font-bold text-gray-900">{card.value}</p>
              </div>
            </div>
          </div>
        ))}
      </section>

      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {alertCards.map((card) => (
          <Link
            key={card.label}
            to={card.label === "POs pendentes" ? "/compras" : "/pedidos"}
            className="rounded-lg border bg-white p-4 shadow-sm hover:shadow-md transition-shadow"
          >
            <p className="text-sm text-gray-600">{card.label}</p>
            <p className="text-2xl font-bold mt-1">{card.count}</p>
            <span
              className={`inline-block mt-2 px-2 py-0.5 rounded text-xs font-medium ${card.color}`}
            >
              Ver detalhes
            </span>
          </Link>
        ))}
      </section>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <h2 className="text-lg font-semibold mb-4">Pedidos recentes</h2>
          {recentOrders.length === 0 ? (
            <div className="rounded border bg-gray-50 p-8 text-center text-gray-500">
              Nenhum pedido recente
            </div>
          ) : (
            <div className="rounded border overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Código
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Cliente
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Total
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Data
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {recentOrders.map((order) => (
                    <tr key={order.codigo} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-mono text-gray-900">{order.codigo}</td>
                      <td className="px-4 py-3 text-sm text-gray-700">{order.cliente}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex px-2 py-1 rounded-full text-xs font-medium ${STATUS_COLORS[order.status] || "bg-gray-100 text-gray-800"}`}
                        >
                          {STATUS_LABELS[order.status] || order.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900 text-right font-mono">
                        R$ {Number(order.total).toFixed(2)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {new Date(order.criado_em).toLocaleString("pt-BR", {
                          day: "2-digit",
                          month: "2-digit",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div>
            <h2 className="text-lg font-semibold mb-4">Top 5 produtos (mês)</h2>
            {m.top_produtos.length === 0 ? (
              <div className="rounded border bg-gray-50 p-8 text-center text-gray-500">
                Sem dados de vendas no mês
              </div>
            ) : (
              <ul className="space-y-3">
                {m.top_produtos.map((p, i) => (
                  <li
                    key={p.nome}
                    className="flex items-center justify-between rounded border bg-white p-4"
                  >
                    <div className="flex items-center gap-3">
                      <span className="rounded-full bg-gray-100 px-3 py-1 text-sm font-medium text-gray-700">
                        {i + 1}
                      </span>
                      <span className="font-medium">{p.nome}</span>
                    </div>
                    <span className="text-lg font-bold text-gray-900">{p.quantidade} un</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div>
            <h2 className="text-lg font-semibold mb-4">Estoque crítico</h2>
            {m.alertas.estoque_critico.length === 0 ? (
              <div className="rounded border bg-green-50 p-8 text-center text-green-700">
                ✓ Todos os insumos acima do mínimo
              </div>
            ) : (
              <ul className="space-y-2">
                {m.alertas.estoque_critico.map((item) => (
                  <li
                    key={item.nome}
                    className="rounded border bg-white p-3 flex items-center justify-between"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium text-red-600">⚠</span>
                      <span className="font-medium">{item.nome}</span>
                    </div>
                    <div className="text-sm text-gray-600">
                      {item.quantidade} {item.unidade} (mín: {item.minimo})
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>

      <nav className="flex flex-wrap gap-3 pt-4 border-t">
        <Link to="/insumos" className="rounded border px-4 py-2 text-sm">
          Insumos
        </Link>
        <Link to="/produtos" className="rounded border px-4 py-2 text-sm">
          Produtos
        </Link>
        <Link to="/pedidos" className="rounded border px-4 py-2 text-sm">
          Pedidos
        </Link>
        <Link to="/estoque" className="rounded border px-4 py-2 text-sm">
          Estoque
        </Link>
        <Link to="/fornecedores" className="rounded border px-4 py-2 text-sm">
          Fornecedores
        </Link>
        <Link to="/inventario" className="rounded border px-4 py-2 text-sm">
          Inventário
        </Link>
        <Link to="/compras" className="rounded border px-4 py-2 text-sm">
          Compras
        </Link>
        <Link to="/cozinha" className="rounded border px-4 py-2 text-sm">
          Cozinha
        </Link>
        <Link to="/zonas" className="rounded border px-4 py-2 text-sm">
          Entregas
        </Link>
      </nav>
    </main>
  );
}
