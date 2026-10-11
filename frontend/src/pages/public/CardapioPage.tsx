import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { publicApi } from "../../api/public";
import type { PublicMenu, PublicProduct } from "../../api/types";
import { useCart } from "../../cart/CartContext";
import ModifierDialog from "../../components/ModifierDialog";

export default function CardapioPage() {
  const { slug = "" } = useParams();
  const { add, count } = useCart();
  const [busca, setBusca] = useState("");
  const [categoria, setCategoria] = useState<string>("");
  const [aberto, setAberto] = useState<PublicProduct | null>(null);

  const { data, isLoading, isError } = useQuery<PublicMenu>({
    queryKey: ["cardapio", slug],
    queryFn: () => publicApi<PublicMenu>(`/public/${slug}/cardapio`),
    enabled: slug.length > 0,
  });

  const produtos = useMemo(() => {
    const list = data?.products ?? [];
    return list.filter(
      (p) =>
        (!categoria || p.category_id === categoria) &&
        p.name.toLowerCase().includes(busca.toLowerCase()),
    );
  }, [data, busca, categoria]);

  function adicionar(p: PublicProduct) {
    if (p.modifiers.length > 0) {
      setAberto(p);
      return;
    }
    add({ productId: p.id, name: p.name, unitPrice: p.price, quantity: 1, modifiers: [] });
  }

  if (isLoading) return <main className="p-8">Carregando…</main>;
  if (isError || !data)
    return (
      <main className="p-8" role="alert">
        Erro ao carregar o cardápio.
      </main>
    );

  return (
    <main className="mx-auto max-w-2xl space-y-4 p-4 text-gray-900">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">{data.tenant.name}</h1>
          <p className="text-sm text-gray-500">{data.store.name}</p>
        </div>
        <Link
          to={`/cardapio/${slug}/carrinho`}
          className="rounded bg-blue-600 px-4 py-2 text-white"
        >
          Carrinho ({count} {count === 1 ? "item" : "itens"})
        </Link>
      </header>

      <label className="block space-y-1">
        <span className="sr-only">Buscar</span>
        <input
          aria-label="Buscar"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          placeholder="Buscar no cardápio"
          className="w-full rounded border px-3 py-2"
        />
      </label>

      {data.categories.length > 0 && (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setCategoria("")}
            className={`rounded border px-3 py-1 text-sm ${!categoria ? "bg-gray-900 text-white" : ""}`}
          >
            Todos
          </button>
          {data.categories.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => setCategoria(c.id)}
              className={`rounded border px-3 py-1 text-sm ${categoria === c.id ? "bg-gray-900 text-white" : ""}`}
            >
              {c.name}
            </button>
          ))}
        </div>
      )}

      <ul className="space-y-3">
        {produtos.map((p) => (
          <li key={p.id} className="flex items-center justify-between gap-4 rounded border p-4">
            <div>
              <p className="font-medium">{p.name}</p>
              {p.description && <p className="text-sm text-gray-500">{p.description}</p>}
              <p className="tabular-nums text-sm">R$ {Number(p.price).toFixed(2)}</p>
            </div>
            <button
              type="button"
              onClick={() => adicionar(p)}
              className="rounded bg-blue-600 px-3 py-2 text-sm text-white"
            >
              Adicionar {p.name}
            </button>
          </li>
        ))}
        {produtos.length === 0 && (
          <li className="text-sm text-gray-500">Nenhum produto encontrado.</li>
        )}
      </ul>

      {aberto && (
        <ModifierDialog
          product={aberto}
          onCancel={() => setAberto(null)}
          onConfirm={(line) => {
            add(line);
            setAberto(null);
          }}
        />
      )}
    </main>
  );
}
