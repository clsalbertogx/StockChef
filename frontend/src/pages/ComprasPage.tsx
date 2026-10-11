import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import {
  PO_STATUS_LABEL,
  type PurchaseOrder,
  type PurchaseSuggestion,
  type Supplier,
} from "../api/types";

export default function ComprasPage() {
  const qc = useQueryClient();
  const tabs = ["sugestao", "pos"] as const;
  const [tab, setTab] = useState<(typeof tabs)[number]>("sugestao");

  const {
    data: sugestoes = [],
    isPending: sugestoesLoading,
    isError: sugestoesError,
  } = useQuery<PurchaseSuggestion[]>({
    queryKey: ["sugestao"],
    queryFn: () => api<PurchaseSuggestion[]>("/compras/sugestao"),
    enabled: tab === "sugestao",
  });
  const {
    data: pos = [],
    isPending: posLoading,
    isError: posError,
  } = useQuery<PurchaseOrder[]>({
    queryKey: ["compras"],
    queryFn: () => api<PurchaseOrder[]>("/compras"),
    enabled: tab === "pos",
  });
  const { data: fornecedores = [] } = useQuery<Supplier[]>({
    queryKey: ["fornecedores"],
    queryFn: () => api<Supplier[]>("/fornecedores"),
  });
  const [supplierId, setSupplierId] = useState("");

  const createPo = useMutation({
    mutationFn: (items: PurchaseSuggestion[]) =>
      api<PurchaseOrder>("/compras", {
        method: "POST",
        body: JSON.stringify({
          supplier_id: supplierId,
          items: items.map((s) => ({
            ingredient_id: s.ingredient_id,
            quantity: s.suggested_quantity,
            unit_cost: "0",
          })),
        }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["compras"] });
      qc.invalidateQueries({ queryKey: ["sugestao"] });
      setTab("pos");
    },
  });

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-8">
      <h1 className="text-2xl font-semibold">Compras</h1>
      <div className="flex gap-3">
        {tabs.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`rounded border px-4 py-2 ${tab === t ? "border-blue-500" : ""}`}
          >
            {t === "sugestao" ? "Sugestão" : "Pedidos de compra"}
          </button>
        ))}
      </div>

      {createPo.isError && (
        <p role="alert" className="text-sm text-red-600">
          <span aria-hidden="true" className="mr-1">
            ⚠
          </span>
          {createPo.error instanceof Error
            ? createPo.error.message
            : "Erro ao criar pedido de compra."}
        </p>
      )}

      {tab === "sugestao" && (
        <section className="space-y-3">
          <p className="text-sm text-gray-600">
            Baseada no consumo médio dos últimos 14 dias, lead time do fornecedor e estoque mínimo.
          </p>
          {sugestoesError ? (
            <p role="alert" className="text-sm text-red-600">
              <span aria-hidden="true" className="mr-1">
                ⚠
              </span>
              Erro ao carregar sugestões.
            </p>
          ) : sugestoesLoading ? (
            <p className="text-sm text-gray-600">Carregando…</p>
          ) : (
            <>
              <ul className="space-y-2">
                {sugestoes.map((s) => (
                  <li key={s.ingredient_id} className="rounded border p-3 text-sm">
                    <div className="font-medium">{s.name}</div>
                    <div className="text-gray-600">{s.reason}</div>
                    <div className="tabular-nums">
                      Sugerido:{" "}
                      <strong>
                        {s.suggested_quantity} {s.unit_symbol}
                      </strong>
                    </div>
                  </li>
                ))}
                {sugestoes.length === 0 && (
                  <li className="text-sm text-gray-600">Nenhuma sugestão no momento.</li>
                )}
              </ul>
              {sugestoes.length > 0 && (
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    createPo.mutate(sugestoes);
                  }}
                  className="flex flex-wrap items-end gap-3"
                >
                  <label className="space-y-1">
                    <span className="text-sm">Fornecedor</span>
                    <select
                      value={supplierId}
                      onChange={(e) => setSupplierId(e.target.value)}
                      required
                      className="rounded border px-3 py-2"
                    >
                      <option value="">Selecione…</option>
                      {fornecedores.map((f) => (
                        <option key={f.id} value={f.id}>
                          {f.name}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    type="submit"
                    disabled={createPo.isPending || !supplierId}
                    className="rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
                  >
                    {createPo.isPending ? "Criando…" : "Criar pedido de compra"}
                  </button>
                </form>
              )}
            </>
          )}
        </section>
      )}

      {tab === "pos" && (
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left">
              <th scope="col" className="py-2">
                Status
              </th>
              <th scope="col">Total</th>
              <th scope="col">Criado em</th>
            </tr>
          </thead>
          <tbody>
            {posError ? (
              <tr>
                <td colSpan={3} className="py-2">
                  <span role="alert" className="text-red-600">
                    <span aria-hidden="true" className="mr-1">
                      ⚠
                    </span>
                    Erro ao carregar pedidos.
                  </span>
                </td>
              </tr>
            ) : posLoading ? (
              <tr>
                <td colSpan={3} className="py-2 text-gray-600">
                  Carregando…
                </td>
              </tr>
            ) : pos.length === 0 ? (
              <tr>
                <td colSpan={3} className="py-2 text-gray-600">
                  Nenhum pedido de compra.
                </td>
              </tr>
            ) : (
              pos.map((p) => (
                <tr key={p.id} className="border-t">
                  <td className="py-2">
                    <Link to={`/compras/${p.id}`} className="text-blue-600">
                      {PO_STATUS_LABEL[p.status] ?? p.status}
                    </Link>
                  </td>
                  <td className="tabular-nums">R$ {Number(p.total_amount).toFixed(2)}</td>
                  <td className="tabular-nums">{p.created_at.slice(0, 10)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      )}
    </main>
  );
}
