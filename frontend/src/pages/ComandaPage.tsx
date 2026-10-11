import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { type Pedido, STATUS_LABEL } from "../api/types";

export default function ComandaPage() {
  const { id = "" } = useParams();
  const { data: pedido } = useQuery<Pedido>({
    queryKey: ["pedido", id],
    queryFn: () => api<Pedido>(`/pedidos/${id}`),
  });

  return (
    <main className="mx-auto max-w-md space-y-4 p-8">
      <div className="flex justify-end print:hidden">
        <button
          type="button"
          onClick={() => window.print()}
          className="rounded bg-blue-600 px-4 py-2 text-white"
        >
          Imprimir
        </button>
      </div>
      <article className="space-y-3 font-mono text-sm">
        <h1 className="text-lg font-bold">{pedido?.code ?? "Pedido"}</h1>
        <p>
          {pedido?.customer_name ?? "Cliente"} ·{" "}
          {pedido ? new Date(pedido.created_at).toLocaleString("pt-BR") : "—"}
        </p>
        <p>
          {pedido?.fulfillment_type} ·{" "}
          {pedido ? (STATUS_LABEL[pedido.status] ?? pedido.status) : "—"}
        </p>
        <ul className="border-y py-2">
          {pedido?.order_items.map((it) => (
            <li key={it.product_id} className="flex justify-between tabular-nums">
              <span>
                {it.quantity}× {it.product_name}
                {it.notes ? <em className="block">obs: {it.notes}</em> : null}
              </span>
              <span>R$ {Number(it.total_price).toFixed(2)}</span>
            </li>
          ))}
        </ul>
        <p className="flex justify-between font-bold tabular-nums">
          <span>Total</span>
          <span>R$ {pedido ? Number(pedido.total).toFixed(2) : "—"}</span>
        </p>
      </article>
    </main>
  );
}
