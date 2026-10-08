import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { type Pedido, STATUS_LABEL } from "../api/types";

export default function PedidosPage() {
  const { data: pedidos = [] } = useQuery<Pedido[]>({
    queryKey: ["pedidos"],
    queryFn: () => api<Pedido[]>("/pedidos"),
  });
  return (
    <main className="mx-auto max-w-5xl space-y-6 p-8">
      <h1 className="text-2xl font-semibold">Pedidos</h1>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left">
            <th>Código</th>
            <th>Cliente</th>
            <th>Itens</th>
            <th>Total</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {pedidos.map((p) => (
            <tr key={p.id} className="border-t">
              <td className="py-2">
                <Link to={`/pedidos/${p.id}`} className="text-blue-600">
                  {p.code}
                </Link>
              </td>
              <td>{p.customer_name ?? "—"}</td>
              <td>{p.order_items.reduce((acc, it) => acc + it.quantity, 0)}</td>
              <td>R$ {Number(p.total).toFixed(2)}</td>
              <td>{STATUS_LABEL[p.status] ?? p.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
