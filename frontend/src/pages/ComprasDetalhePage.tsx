import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { type Insumo, PO_STATUS_LABEL, type PurchaseOrder } from "../api/types";

export default function ComprasDetalhePage() {
  const { id = "" } = useParams();
  const qc = useQueryClient();
  const {
    data: po,
    isPending,
    isError,
  } = useQuery<PurchaseOrder>({
    queryKey: ["compra", id],
    queryFn: () => api<PurchaseOrder>(`/compras/${id}`),
    enabled: !!id,
  });
  const { data: insumos = [] } = useQuery<Insumo[]>({
    queryKey: ["insumos"],
    queryFn: () => api<Insumo[]>("/insumos"),
  });
  const insumoById = new Map(insumos.map((i) => [i.id, i]));

  const [invoice, setInvoice] = useState("");

  const invalidate = () => qc.invalidateQueries({ queryKey: ["compra", id] });

  const aprovar = useMutation({
    mutationFn: () => api<PurchaseOrder>(`/compras/${id}/aprovar`, { method: "POST" }),
    onSuccess: invalidate,
  });

  const cancelar = useMutation({
    mutationFn: () => api<PurchaseOrder>(`/compras/${id}/cancelar`, { method: "POST" }),
    onSuccess: invalidate,
  });

  const pendentes = (po?.items ?? []).filter(
    (it) => Number(it.quantity) - Number(it.received_quantity) > 0,
  );

  const receberTudo = useMutation({
    mutationFn: () =>
      api<PurchaseOrder>(`/compras/${id}/recebimento`, {
        method: "POST",
        body: JSON.stringify({
          invoice_number: invoice,
          items: pendentes.map((it) => ({
            purchase_order_item_id: it.id,
            received_quantity: String(Number(it.quantity) - Number(it.received_quantity)),
            unit_cost: it.unit_cost,
          })),
        }),
      }),
    onSuccess: () => {
      setInvoice("");
      invalidate();
    },
  });

  const erro = aprovar.isError || cancelar.isError || receberTudo.isError;

  if (isError)
    return (
      <main className="mx-auto max-w-3xl p-8">
        <p role="alert" className="text-sm text-red-600">
          <span aria-hidden="true" className="mr-1">
            ⚠
          </span>
          Erro ao carregar pedido de compra.
        </p>
      </main>
    );
  if (isPending || !po) return <main className="mx-auto max-w-3xl p-8">Carregando…</main>;

  const podeAprovar = po.status === "draft";
  const podeCancelar = po.status === "draft" || po.status === "sent";
  const podeReceber =
    (po.status === "sent" || po.status === "partially_received") && pendentes.length > 0;

  const mensagemErro =
    aprovar.error instanceof Error
      ? aprovar.error.message
      : cancelar.error instanceof Error
        ? cancelar.error.message
        : receberTudo.error instanceof Error
          ? receberTudo.error.message
          : "Erro ao processar pedido.";

  return (
    <main className="mx-auto max-w-3xl space-y-6 p-8">
      <h1 className="text-2xl font-semibold">Pedido de compra</h1>
      <p>
        Status: <strong>{PO_STATUS_LABEL[po.status] ?? po.status}</strong> · Total: R${" "}
        {Number(po.total_amount).toFixed(2)}
      </p>

      {erro && (
        <p role="alert" className="text-sm text-red-600">
          <span aria-hidden="true" className="mr-1">
            ⚠
          </span>
          {mensagemErro}
        </p>
      )}

      <div className="flex flex-wrap items-end gap-3">
        {podeAprovar && (
          <button
            type="button"
            disabled={aprovar.isPending}
            onClick={() => aprovar.mutate()}
            className="rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
          >
            {aprovar.isPending ? "Aprovando…" : "Aprovar pedido"}
          </button>
        )}
        {podeCancelar && (
          <button
            type="button"
            disabled={cancelar.isPending}
            onClick={() => cancelar.mutate()}
            className="rounded border px-4 py-2 text-sm disabled:opacity-50"
          >
            {cancelar.isPending ? "Cancelando…" : "Cancelar pedido"}
          </button>
        )}
        {podeReceber && (
          <>
            <label className="space-y-1">
              <span className="text-sm">Nota fiscal</span>
              <input
                value={invoice}
                onChange={(e) => setInvoice(e.target.value)}
                required
                className="rounded border px-3 py-2"
              />
            </label>
            <button
              type="button"
              disabled={receberTudo.isPending || invoice.trim() === ""}
              onClick={() => receberTudo.mutate()}
              className="rounded bg-green-700 px-4 py-2 text-white disabled:opacity-50"
            >
              {receberTudo.isPending ? "Recebendo…" : "Receber (todos os itens)"}
            </button>
          </>
        )}
      </div>

      <table className="w-full text-sm">
        <thead>
          <tr className="text-left">
            <th scope="col" className="py-2">
              Item
            </th>
            <th scope="col">Qtd</th>
            <th scope="col">Custo unit.</th>
            <th scope="col">Recebido</th>
            <th scope="col">Pendente</th>
          </tr>
        </thead>
        <tbody>
          {po.items.map((it) => (
            <tr key={it.id} className="border-t">
              <td className="py-2">{insumoById.get(it.ingredient_id)?.name ?? it.ingredient_id}</td>
              <td className="tabular-nums">{it.quantity}</td>
              <td className="tabular-nums">R$ {Number(it.unit_cost).toFixed(2)}</td>
              <td className="tabular-nums">{it.received_quantity}</td>
              <td className="tabular-nums">{Number(it.quantity) - Number(it.received_quantity)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
