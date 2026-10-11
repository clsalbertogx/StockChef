import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import type { CriticalStockItem, Insumo, LossIn, MovementOut } from "../api/types";

const REASONS = [
  ["expiration", "Vencimento"],
  ["cooking_error", "Erro de preparo"],
  ["damage", "Dano"],
  ["theft", "Furto"],
  ["return", "Devolução"],
  ["spoilage", "Deteriorado"],
  ["other", "Outro"],
] as const;

const MOVEMENT_TYPE: Record<string, string> = {
  loss: "Perda",
  adjustment: "Ajuste",
  purchase: "Compra",
};

export default function EstoquePage() {
  const qc = useQueryClient();
  const { data: insumos = [], isError: insumosError } = useQuery<Insumo[]>({
    queryKey: ["insumos"],
    queryFn: () => api<Insumo[]>("/insumos"),
  });
  const {
    data: criticos = [],
    isPending: criticosLoading,
    isError: criticosError,
  } = useQuery<CriticalStockItem[]>({
    queryKey: ["estoque-critico"],
    queryFn: () => api<CriticalStockItem[]>("/estoque/critico"),
  });
  const {
    data: movimentos = [],
    isPending: movimentosLoading,
    isError: movimentosError,
  } = useQuery<MovementOut[]>({
    queryKey: ["movimentos"],
    queryFn: () => api<MovementOut[]>("/estoque/movimentos"),
  });

  const [perdaIng, setPerdaIng] = useState("");
  const [perdaQty, setPerdaQty] = useState("");
  const [perdaReason, setPerdaReason] = useState<string>("damage");
  const [aviso, setAviso] = useState<string | null>(null);

  const perda = useMutation({
    mutationFn: () =>
      api<LossIn>("/perdas", {
        method: "POST",
        body: JSON.stringify({
          ingredient_id: perdaIng,
          quantity: perdaQty,
          reason: perdaReason,
        }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["insumos"] });
      qc.invalidateQueries({ queryKey: ["estoque-critico"] });
      qc.invalidateQueries({ queryKey: ["movimentos"] });
      setAviso("Perda registrada.");
      setPerdaIng("");
      setPerdaQty("");
    },
    onError: (e) => setAviso(e instanceof Error ? e.message : "Erro ao registrar perda."),
  });

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-8">
      <h1 className="text-2xl font-semibold">Estoque</h1>
      {aviso && (
        <p
          role={perda.isError ? "alert" : "status"}
          className={`text-sm ${perda.isError ? "text-red-600" : "text-green-700"}`}
        >
          {perda.isError && (
            <span aria-hidden="true" className="mr-1">
              ⚠
            </span>
          )}
          {aviso}
        </p>
      )}

      <section className="space-y-2 rounded border p-4">
        <h2 className="font-semibold">Críticos (abaixo do mínimo)</h2>
        {criticosError ? (
          <p role="alert" className="text-sm text-red-600">
            <span aria-hidden="true" className="mr-1">
              ⚠
            </span>
            Erro ao carregar críticos.
          </p>
        ) : criticosLoading ? (
          <p className="text-sm text-gray-600">Carregando…</p>
        ) : criticos.length === 0 ? (
          <p className="text-sm text-gray-600">Nenhum insumo abaixo do mínimo.</p>
        ) : (
          <ul className="text-sm">
            {criticos.map((c) => (
              <li key={c.ingredient_id} className="flex justify-between">
                <span>{c.name}</span>
                <span className="tabular-nums">
                  {c.stock_total} {c.unit_symbol} / mínimo {c.minimum_stock}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="space-y-4 rounded border p-4">
        <h2 className="font-semibold">Registrar perda</h2>
        {insumosError && (
          <p role="alert" className="text-sm text-red-600">
            <span aria-hidden="true" className="mr-1">
              ⚠
            </span>
            Erro ao carregar insumos.
          </p>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            perda.mutate();
          }}
          className="flex flex-wrap items-end gap-3"
        >
          <label className="space-y-1">
            <span className="text-sm">Insumo</span>
            <select
              aria-label="Insumo"
              value={perdaIng}
              onChange={(e) => setPerdaIng(e.target.value)}
              className="rounded border px-3 py-2"
            >
              <option value="">Selecione…</option>
              {insumos.map((i) => (
                <option key={i.id} value={i.id}>
                  {i.name}
                </option>
              ))}
            </select>
          </label>
          <label className="space-y-1">
            <span className="text-sm">Quantidade</span>
            <input
              type="number"
              min="0"
              step="0.001"
              value={perdaQty}
              onChange={(e) => setPerdaQty(e.target.value)}
              required
              className="w-24 rounded border px-3 py-2"
            />
          </label>
          <label className="space-y-1">
            <span className="text-sm">Motivo</span>
            <select
              value={perdaReason}
              onChange={(e) => setPerdaReason(e.target.value)}
              className="rounded border px-3 py-2"
            >
              {REASONS.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <button
            type="submit"
            disabled={perda.isPending || !perdaIng}
            className="rounded bg-red-600 px-4 py-2 text-white disabled:opacity-50"
          >
            {perda.isPending ? "Registrando…" : "Registrar perda"}
          </button>
        </form>
      </section>

      <section className="space-y-2">
        <h2 className="font-semibold">Últimos movimentos</h2>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left">
              <th scope="col" className="py-2">
                Tipo
              </th>
              <th scope="col">Quantidade</th>
              <th scope="col">Custo unit.</th>
              <th scope="col">Motivo</th>
            </tr>
          </thead>
          <tbody>
            {movimentosError ? (
              <tr>
                <td colSpan={4} className="py-2">
                  <span role="alert" className="text-red-600">
                    <span aria-hidden="true" className="mr-1">
                      ⚠
                    </span>
                    Erro ao carregar movimentos.
                  </span>
                </td>
              </tr>
            ) : movimentosLoading ? (
              <tr>
                <td colSpan={4} className="py-2 text-gray-600">
                  Carregando…
                </td>
              </tr>
            ) : movimentos.length === 0 ? (
              <tr>
                <td colSpan={4} className="py-2">
                  Sem movimentos.
                </td>
              </tr>
            ) : (
              movimentos.slice(0, 20).map((m) => (
                <tr key={m.id} className="border-t">
                  <td className="py-2">{MOVEMENT_TYPE[m.type] ?? m.type}</td>
                  <td className="tabular-nums">{m.quantity}</td>
                  <td className="tabular-nums">R$ {Number(m.unit_cost).toFixed(2)}</td>
                  <td>{m.reason ?? "—"}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>
    </main>
  );
}
