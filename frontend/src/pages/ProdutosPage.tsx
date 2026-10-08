import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { api } from "../api/client";
import type { Insumo, Margem, Producto, RecipeOut } from "../api/types";

export default function ProdutosPage() {
  const qc = useQueryClient();
  const { data: produtos = [] } = useQuery<Producto[]>({
    queryKey: ["produtos"],
    queryFn: () => api<Producto[]>("/produtos"),
  });
  const { data: insumos = [] } = useQuery<Insumo[]>({
    queryKey: ["insumos"],
    queryFn: () => api<Insumo[]>("/insumos"),
  });

  const [name, setName] = useState("");
  const [price, setPrice] = useState("");
  const [selected, setSelected] = useState<string | null>(null);

  const create = useMutation({
    mutationFn: () =>
      api<Producto>("/produtos", {
        method: "POST",
        body: JSON.stringify({ name, price }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["produtos"] });
      setName("");
      setPrice("");
    },
  });

  const { data: ficha } = useQuery<RecipeOut>({
    queryKey: ["ficha", selected],
    queryFn: () => api<RecipeOut>(`/produtos/${selected}/ficha-tecnica`),
    enabled: !!selected,
  });
  const { data: margem } = useQuery<Margem>({
    queryKey: ["margem", selected],
    queryFn: () => api<Margem>(`/produtos/${selected}/margem`),
    enabled: !!selected,
  });

  const [linhas, setLinhas] = useState<{ id: number; ingredient_id: string; quantity: string }[]>([
    { id: Date.now(), ingredient_id: "", quantity: "" },
  ]);

  const saveFicha = useMutation({
    mutationFn: () =>
      api<RecipeOut>(`/produtos/${selected}/ficha-tecnica`, {
        method: "POST",
        body: JSON.stringify({ items: linhas }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["ficha", selected] });
      qc.invalidateQueries({ queryKey: ["margem", selected] });
    },
  });

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-8">
      <h1 className="text-2xl font-semibold">Produtos</h1>
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
          <span className="text-sm">Preço (R$)</span>
          <input
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            required
            className="rounded border px-3 py-2"
          />
        </label>
        <button type="submit" className="rounded bg-blue-600 px-4 py-2 text-white">
          Criar produto
        </button>
      </form>

      <div className="grid gap-6 md:grid-cols-2">
        <ul className="space-y-2">
          {produtos.map((p) => (
            <li key={p.id}>
              <button
                type="button"
                onClick={() => setSelected(p.id)}
                className={`w-full rounded border p-3 text-left ${selected === p.id ? "border-blue-500" : ""}`}
              >
                <div className="font-medium">{p.name}</div>
                <div className="text-sm text-gray-600">R$ {Number(p.price).toFixed(2)}</div>
              </button>
            </li>
          ))}
        </ul>

        <section className="space-y-4 rounded border p-4">
          <h2 className="font-semibold">Ficha técnica</h2>
          {linhas.map((linha, idx) => (
            <div key={linha.id} className="flex gap-2">
              <select
                value={linha.ingredient_id}
                aria-label="Insumo da ficha"
                onChange={(e) =>
                  setLinhas((ls) =>
                    ls.map((l, i) => (i === idx ? { ...l, ingredient_id: e.target.value } : l)),
                  )
                }
                className="flex-1 rounded border px-3 py-2"
              >
                <option value="">Insumo…</option>
                {insumos.map((i) => (
                  <option key={i.id} value={i.id}>
                    {i.name} ({i.base_unit.symbol})
                  </option>
                ))}
              </select>
              <input
                value={linha.quantity}
                placeholder="qtd"
                aria-label="Quantidade"
                onChange={(e) =>
                  setLinhas((ls) =>
                    ls.map((l, i) => (i === idx ? { ...l, quantity: e.target.value } : l)),
                  )
                }
                className="w-24 rounded border px-3 py-2"
              />
            </div>
          ))}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() =>
                setLinhas((ls) => [...ls, { id: Date.now(), ingredient_id: "", quantity: "" }])
              }
              className="rounded border px-3 py-2 text-sm"
            >
              + insumo
            </button>
            <button
              type="button"
              onClick={() => selected && saveFicha.mutate()}
              disabled={!selected}
              className="rounded bg-blue-600 px-4 py-2 text-white text-sm disabled:opacity-50"
            >
              Salvar ficha
            </button>
          </div>
          {ficha && (
            <ul className="text-sm">
              {ficha.items.map((it) => (
                <li key={it.ingredient_id} className="flex justify-between">
                  <span>
                    {it.name} · {it.quantity} {it.unit_symbol}
                  </span>
                  <span>R$ {Number(it.cost).toFixed(2)}</span>
                </li>
              ))}
              <li className="mt-2 flex justify-between font-medium">
                <span>Custo</span>
                <span>R$ {Number(ficha.total_cost).toFixed(2)}</span>
              </li>
            </ul>
          )}
          {margem && margem.margin_percent !== null && (
            <p className="text-sm">
              Margem: <strong>{margem.margin_percent}%</strong> · R$ {margem.margin_value}
            </p>
          )}
        </section>
      </div>
    </main>
  );
}
