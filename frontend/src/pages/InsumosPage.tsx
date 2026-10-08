import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { api } from "../api/client";
import type { Insumo } from "../api/types";

export default function InsumosPage() {
  const qc = useQueryClient();
  const { data: insumos = [] } = useQuery<Insumo[]>({
    queryKey: ["insumos"],
    queryFn: () => api<Insumo[]>("/insumos"),
  });

  const [name, setName] = useState("");
  const [symbol, setSymbol] = useState("kg");
  const [cost, setCost] = useState("");
  const [stock, setStock] = useState("");

  const create = useMutation({
    mutationFn: () =>
      api<Insumo>("/insumos", {
        method: "POST",
        body: JSON.stringify({
          name,
          base_unit_symbol: symbol,
          average_cost: cost,
          initial_stock: stock || "0",
        }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["insumos"] });
      setName("");
      setCost("");
      setStock("");
    },
  });

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-8">
      <h1 className="text-2xl font-semibold">Insumos</h1>

      <form
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          create.mutate();
        }}
        className="flex flex-wrap items-end gap-3 rounded border p-4"
      >
        <label className="space-y-1">
          <span className="text-sm">Nome</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="rounded border px-3 py-2"
          />
        </label>
        <label className="space-y-1">
          <span className="text-sm">Unidade</span>
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="rounded border px-3 py-2"
          >
            {["kg", "g", "un", "ml", "l"].map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1">
          <span className="text-sm">Custo (R$/un)</span>
          <input
            value={cost}
            onChange={(e) => setCost(e.target.value)}
            required
            className="rounded border px-3 py-2"
          />
        </label>
        <label className="space-y-1">
          <span className="text-sm">Saldo inicial</span>
          <input
            value={stock}
            onChange={(e) => setStock(e.target.value)}
            className="rounded border px-3 py-2"
          />
        </label>
        <button
          type="submit"
          disabled={create.isPending}
          className="rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
        >
          Criar insumo
        </button>
      </form>

      <table className="w-full text-sm">
        <thead>
          <tr className="text-left">
            <th>Nome</th>
            <th>Un.</th>
            <th>Custo</th>
            <th>Estoque</th>
          </tr>
        </thead>
        <tbody>
          {insumos.map((i) => (
            <tr key={i.id} className="border-t">
              <td className="py-2">{i.name}</td>
              <td>{i.base_unit.symbol}</td>
              <td>R$ {Number(i.average_cost).toFixed(2)}</td>
              <td>{Number(i.stock_total).toFixed(i.base_unit.symbol === "un" ? 0 : 3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
