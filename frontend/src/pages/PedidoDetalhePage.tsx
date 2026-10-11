import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { type Evento, type Pedido, STATUS_LABEL } from "../api/types";

function usePedido(id: string) {
  return useQuery<Pedido>({
    queryKey: ["pedido", id],
    queryFn: () => api<Pedido>(`/pedidos/${id}`),
  });
}

const NEXT_ACTIONS: Record<string, { to: string; label: string }[]> = {
  received: [],
  confirmed: [{ to: "preparing", label: "Iniciar preparo" }],
  confirmed_pending_stock: [{ to: "preparing", label: "Iniciar preparo" }],
  preparing: [{ to: "ready", label: "Marcar pronto" }],
  ready: [
    { to: "delivered", label: "Marcar entregue" },
    { to: "completed", label: "Concluir" },
  ],
  delivered: [{ to: "completed", label: "Concluir" }],
};

const CANCELAVEIS = ["received", "confirmed", "confirmed_pending_stock", "preparing", "ready"];

export default function PedidoDetalhePage() {
  const { id = "" } = useParams();
  const qc = useQueryClient();
  const { data: pedido } = usePedido(id);
  const { data: eventos } = useQuery<{ order_id: string; status: string; events: Evento[] }>({
    queryKey: ["pedido-eventos", id],
    queryFn: () =>
      api<{ order_id: string; status: string; events: Evento[] }>(`/pedidos/${id}/eventos`),
    enabled: !!id,
  });

  const [aviso, setAviso] = useState("");
  const [motivo, setMotivo] = useState("");
  const [cancelOpen, setCancelOpen] = useState(false);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["pedido", id] });
    qc.invalidateQueries({ queryKey: ["pedido-eventos", id] });
  };

  const confirmar = useMutation({
    mutationFn: () => api<Pedido>(`/pedidos/${id}/confirmar`, { method: "POST" }),
    onSuccess: (ped) => {
      invalidate();
      if (ped.status === "confirmed_pending_stock")
        setAviso("Pedido confirmado com pendência de estoque.");
    },
    onError: () => setAviso("Não foi possível confirmar."),
  });

  const mudar = useMutation({
    mutationFn: (to: string) =>
      api<Pedido>(`/pedidos/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: to }),
      }),
    onSuccess: () => {
      setAviso("");
      invalidate();
    },
    onError: () => setAviso("Transição não permitida."),
  });

  const cancelar = useMutation({
    mutationFn: () =>
      api<Pedido>(`/pedidos/${id}/cancelar`, {
        method: "POST",
        body: JSON.stringify({ motivo }),
      }),
    onSuccess: () => {
      setCancelOpen(false);
      setMotivo("");
      invalidate();
    },
    onError: () => setAviso("Não foi possível cancelar."),
  });

  const podeConfirmar = pedido?.status === "received";
  const podeCancelar = pedido ? CANCELAVEIS.includes(pedido.status) : false;

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
      {pedido && (
        <Link to={`/pedidos/${pedido.id}/comanda`} className="text-sm text-blue-600">
          Ver comanda
        </Link>
      )}

      <ul className="rounded border p-4">
        {pedido?.order_items.map((it) => (
          <li key={it.product_id} className="flex justify-between py-1">
            <span>
              {it.quantity}× {it.product_name}
            </span>
            <span className="tabular-nums">R$ {Number(it.total_price).toFixed(2)}</span>
          </li>
        ))}
      </ul>
      <p className="tabular-nums">
        Total: <strong>R$ {pedido ? Number(pedido.total).toFixed(2) : "—"}</strong>
      </p>

      <div className="flex flex-wrap gap-2">
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
        {pedido &&
          NEXT_ACTIONS[pedido.status]?.map((a) => (
            <button
              key={a.to}
              type="button"
              onClick={() => mudar.mutate(a.to)}
              disabled={mudar.isPending}
              className="rounded border px-4 py-2 disabled:opacity-50"
            >
              {a.label}
            </button>
          ))}
        {podeCancelar && (
          <button
            type="button"
            onClick={() => setCancelOpen(true)}
            className="rounded bg-red-600 px-4 py-2 text-white"
          >
            Cancelar pedido
          </button>
        )}
      </div>

      {cancelOpen && (
        <div className="space-y-2 rounded border p-4">
          <label htmlFor="motivo" className="block text-sm font-medium">
            Motivo
          </label>
          <input
            id="motivo"
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            className="w-full rounded border px-2 py-1"
          />
          <button
            type="button"
            onClick={() => cancelar.mutate()}
            disabled={cancelar.isPending || motivo.trim() === ""}
            className="rounded bg-red-600 px-4 py-2 text-white disabled:opacity-50"
          >
            Confirmar cancelamento
          </button>
        </div>
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
