import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import { COUNT_STATUS_LABEL, type Insumo, type InventoryCount } from "../api/types";

export default function InventarioPage() {
  const qc = useQueryClient();
  const {
    data: contagens = [],
    isPending,
    isError,
  } = useQuery<InventoryCount[]>({
    queryKey: ["inventarios"],
    queryFn: () => api<InventoryCount[]>("/inventarios"),
  });
  const { data: insumos = [] } = useQuery<Insumo[]>({
    queryKey: ["insumos"],
    queryFn: () => api<Insumo[]>("/insumos"),
  });
  const insumoById = new Map(insumos.map((i) => [i.id, i]));

  const [counted, setCounted] = useState<Record<string, Record<string, string>>>({});

  const open = useMutation({
    mutationFn: () => api<InventoryCount>("/inventarios", { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["inventarios"] }),
  });

  const saveItems = useMutation({
    mutationFn: (countId: string) => {
      const items = Object.entries(counted[countId] ?? {})
        .filter(([, value]) => value.trim() !== "")
        .map(([ingredient_id, counted_quantity]) => ({ ingredient_id, counted_quantity }));
      return api<InventoryCount>(`/inventarios/${countId}/itens`, {
        method: "POST",
        body: JSON.stringify({ items }),
      });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["inventarios"] }),
  });

  const close = useMutation({
    mutationFn: (countId: string) =>
      api<InventoryCount>(`/inventarios/${countId}/fechar`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["inventarios"] }),
  });

  const erro = open.isError || saveItems.isError || close.isError;

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-8">
      <h1 className="text-2xl font-semibold">Inventário</h1>

      <button
        type="button"
        disabled={open.isPending}
        onClick={() => open.mutate()}
        className="rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
      >
        {open.isPending ? "Abrindo…" : "Abrir contagem"}
      </button>

      {erro && (
        <p role="alert" className="text-sm text-red-600">
          <span aria-hidden="true" className="mr-1">
            ⚠
          </span>
          {open.error instanceof Error
            ? open.error.message
            : saveItems.error instanceof Error
              ? saveItems.error.message
              : close.error instanceof Error
                ? close.error.message
                : "Erro ao processar contagem."}
        </p>
      )}

      {isError ? (
        <p role="alert" className="text-sm text-red-600">
          <span aria-hidden="true" className="mr-1">
            ⚠
          </span>
          Erro ao carregar contagens.
        </p>
      ) : isPending ? (
        <p className="text-sm text-gray-600">Carregando…</p>
      ) : contagens.length === 0 ? (
        <p className="text-sm text-gray-600">Nenhuma contagem registrada.</p>
      ) : (
        contagens.map((c) => (
          <section key={c.id} className="space-y-2 rounded border p-4">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold">
                Contagem {c.started_at.slice(0, 10)} · {COUNT_STATUS_LABEL[c.status] ?? c.status}
              </h2>
              {c.status === "open" && (
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={saveItems.isPending}
                    onClick={() => saveItems.mutate(c.id)}
                    className="rounded border px-3 py-1 text-sm disabled:opacity-50"
                  >
                    {saveItems.isPending ? "Salvando…" : "Salvar contagens"}
                  </button>
                  <button
                    type="button"
                    disabled={close.isPending}
                    onClick={() => close.mutate(c.id)}
                    className="rounded bg-green-700 px-3 py-1 text-sm text-white disabled:opacity-50"
                  >
                    {close.isPending ? "Fechando…" : "Fechar"}
                  </button>
                </div>
              )}
            </div>
            <ul className="text-sm">
              {c.items.map((i) => {
                const insumo = insumoById.get(i.ingredient_id);
                const name = insumo?.name ?? i.ingredient_id;
                const symbol = insumo?.base_unit.symbol ?? "";
                const value = counted[c.id]?.[i.ingredient_id] ?? i.counted_quantity ?? "";
                return (
                  <li
                    key={i.ingredient_id}
                    className="flex items-center justify-between gap-4 py-1"
                  >
                    <span>
                      {name} <span className="text-gray-500">({symbol})</span>
                    </span>
                    <span className="flex items-center gap-2 tabular-nums">
                      <span className="text-gray-600">sistema {i.system_quantity}</span>
                      {c.status === "open" ? (
                        <input
                          type="number"
                          min="0"
                          step="0.001"
                          aria-label={`Contagem de ${name}`}
                          value={value}
                          onChange={(e) =>
                            setCounted((prev) => ({
                              ...prev,
                              [c.id]: { ...prev[c.id], [i.ingredient_id]: e.target.value },
                            }))
                          }
                          className="w-24 rounded border px-2 py-1 text-right"
                        />
                      ) : (
                        <span>contado {i.counted_quantity ?? "—"}</span>
                      )}
                    </span>
                  </li>
                );
              })}
            </ul>
          </section>
        ))
      )}
    </main>
  );
}
