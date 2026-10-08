import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { type Evento, type Pedido, STATUS_LABEL } from "../api/types";

function usePedido(id: string) {
  return useQuery<Pedido>({
    queryKey: ["pedido", id],
    queryFn: () => api<Pedido>(`/pedidos/${id}`),
  });
}

export default function PedidoDetalhePage() {
  const { id = "" } = useParams();
  const qc = useQueryClient();
  const { data: pedido } = usePedido(id);
  const { data: eventos } = useQuery<{
    order_id: string;
    status: string;
    events: Evento[];
  }>({
    queryKey: ["pedido-eventos", id],
    queryFn: () =>
      api<{ order_id: string; status: string; events: Evento[] }>(`/pedidos/${id}/eventos`),
    enabled: !!id,
  });

  const [aviso, setAviso] = useState("");
  const confirmar = useMutation({
    mutationFn: () => api<Pedido>(`/pedidos/${id}/confirmar`, { method: "POST" }),
    onSuccess: (ped) => {
      qc.invalidateQueries({ queryKey: ["pedido", id] });
      qc.invalidateQueries({ queryKey: ["pedido-eventos", id] });
      if (ped.status === "confirmed_pending_stock") {
        setAviso("Pedido confirmado com pendência de estoque.");
      }
    },
  });

  const podeConfirmar = pedido && ["received"].includes(pedido.status);

  return (
    <main className="mx-auto max-w-3xl space-y-6 p-8">
      <h1 className="text-2xl font-semibold">{pedido?.code ?? "Pedido"}</h1>
      {pedido && (
        <p>
          Status: <strong>{STATUS_LABEL[pedido.status] ?? pedido.status}</strong>
        </p>
      )}
      {aviso && (
        <p role="alert" className="text-sm text-amber-700">
          {aviso}
        </p>
      )}

      <ul className="rounded border p-4">
        {pedido?.order_items.map((it) => (
          <li key={it.product_id} className="flex justify-between py-1">
            <span>
              {it.quantity}× {it.product_name}
            </span>
            <span>R$ {Number(it.total_price).toFixed(2)}</span>
          </li>
        ))}
      </ul>
      <p>
        Total: <strong>R$ {pedido ? Number(pedido.total).toFixed(2) : "—"}</strong>
      </p>

      {podeConfirmar && (
        <button
          type="button"
          onClick={() => confirmar.mutate()}
          disabled={confirmar.isPending}
          className="rounded bg-green-600 px-4 py-2 text-white disabled:opacity-50"
        >
          {confirmar.isPending ? "Confirmando…" : "Confirmar pedido"}
        </button>
      )}

      <section>
        <h2 className="font-semibold">Eventos</h2>
        <ul className="text-sm">
          {eventos?.events.map((e) => (
            <li key={`${e.event_type}-${e.created_at}`} className="flex justify-between py-1">
              <span>{e.event_type}</span>
              <span className="text-gray-500">{e.outbox_status ?? e.created_at}</span>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
