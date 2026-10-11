import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { publicApi } from "../../api/public";
import { type PublicOrder, STATUS_LABEL } from "../../api/types";

export default function PedidoPublicoPage() {
  const { slug = "", code = "" } = useParams();
  const { data, isLoading, isError } = useQuery<PublicOrder>({
    queryKey: ["pedido-publico", slug, code],
    queryFn: () => publicApi<PublicOrder>(`/public/${slug}/pedidos/${code}`),
    refetchInterval: 10000,
    enabled: slug.length > 0 && code.length > 0,
  });

  if (isLoading) return <main className="p-8">Carregando…</main>;
  if (isError || !data)
    return (
      <main className="p-8" role="alert">
        Pedido não encontrado.
      </main>
    );

  return (
    <main className="mx-auto max-w-2xl space-y-4 p-4">
      <h1 className="text-xl font-semibold">
        Pedido <span>{data.code}</span>
      </h1>
      <p className="text-sm">
        Status: <strong>{STATUS_LABEL[data.status] ?? data.status}</strong>
        {data.eta_minutes ? ` · ~${data.eta_minutes} min` : ""}
      </p>
      <ul className="space-y-2">
        {data.items.map((it) => (
          <li
            key={`${it.product_name}|${it.unit_price}|${it.quantity}|${it.modifiers
              .map((m) => m.id)
              .join(",")}`}
            className="rounded border p-3"
          >
            <div className="flex justify-between">
              <span>
                {it.quantity}× {it.product_name}
              </span>
              <span className="tabular-nums">R$ {Number(it.total_price).toFixed(2)}</span>
            </div>
            {it.modifiers.length > 0 && (
              <p className="text-xs text-gray-500">
                {it.modifiers.map((m) => m.modifier_name).join(", ")}
              </p>
            )}
          </li>
        ))}
      </ul>
      <div className="space-y-1 border-t pt-4 text-sm">
        <div className="flex justify-between">
          <span>Subtotal</span>
          <span className="tabular-nums">R$ {Number(data.subtotal).toFixed(2)}</span>
        </div>
        <div className="flex justify-between">
          <span>Taxa de entrega</span>
          <span className="tabular-nums">R$ {Number(data.delivery_fee).toFixed(2)}</span>
        </div>
        <div className="flex justify-between font-semibold">
          <span>Total</span>
          <span className="tabular-nums">R$ {Number(data.total).toFixed(2)}</span>
        </div>
      </div>
      <Link to={`/cardapio/${slug}`} className="block text-center text-sm text-blue-600">
        Voltar ao cardápio
      </Link>
    </main>
  );
}
