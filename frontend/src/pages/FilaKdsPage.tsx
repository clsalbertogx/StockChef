import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import { type KdsOrder, STATUS_LABEL } from "../api/types";

export default function FilaKdsPage() {
  const qc = useQueryClient();
  const {
    data: fila = [],
    isLoading,
    isError,
  } = useQuery<KdsOrder[]>({
    queryKey: ["cozinha-fila"],
    queryFn: () => api<KdsOrder[]>("/cozinha/fila"),
    refetchInterval: 5000,
  });
  const [erro, setErro] = useState("");

  const mudar = useMutation({
    mutationFn: ({ id, to }: { id: string; to: string }) =>
      api(`/pedidos/${id}/status`, { method: "PATCH", body: JSON.stringify({ status: to }) }),
    onSuccess: () => {
      setErro("");
      qc.invalidateQueries({ queryKey: ["cozinha-fila"] });
    },
    onError: () => setErro("Não foi possível atualizar o pedido."),
  });

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-8">
      <h1 className="text-2xl font-semibold">Fila da cozinha</h1>
      {erro && (
        <p role="alert" className="text-sm text-red-600">
          {erro}
        </p>
      )}
      {isError && (
        <p role="alert" className="text-sm text-red-600">
          Erro ao carregar a fila.
        </p>
      )}
      {isLoading && <p className="text-gray-600">Carregando…</p>}
      {!isLoading && !isError && fila.length === 0 && (
        <p role="status" className="text-gray-600">
          Nenhum pedido na fila.
        </p>
      )}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {fila.map((o) => (
          <article key={o.order_id} className="space-y-3 rounded border p-4">
            <header className="flex items-center justify-between">
              <strong>{o.code}</strong>
              <span className="text-xs text-gray-500">
                {STATUS_LABEL[o.status] ?? o.status} · {o.elapsed_minutes} min
              </span>
            </header>
            <ul className="text-sm">
              {o.items.map((it) => (
                <li key={it.order_item_id} className="tabular-nums">
                  {it.quantity}× {it.product_name}
                  {it.notes ? <em className="block text-gray-500">obs: {it.notes}</em> : null}
                </li>
              ))}
            </ul>
            {o.notes && <p className="text-xs text-gray-500">obs do pedido: {o.notes}</p>}
            <div className="flex flex-wrap gap-2">
              {o.status !== "preparing" && (
                <button
                  type="button"
                  className="rounded bg-amber-600 px-3 py-2 text-sm text-white disabled:opacity-50"
                  disabled={mudar.isPending}
                  onClick={() => mudar.mutate({ id: o.order_id, to: "preparing" })}
                >
                  Iniciar preparo
                </button>
              )}
              {o.status === "preparing" && (
                <button
                  type="button"
                  className="rounded bg-green-600 px-3 py-2 text-sm text-white disabled:opacity-50"
                  disabled={mudar.isPending}
                  onClick={() => mudar.mutate({ id: o.order_id, to: "ready" })}
                >
                  Marcar pronto
                </button>
              )}
            </div>
          </article>
        ))}
      </div>
    </main>
  );
}
