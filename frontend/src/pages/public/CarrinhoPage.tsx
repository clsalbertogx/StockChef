import { Link, useParams } from "react-router-dom";
import { useCart } from "../../cart/CartContext";

export default function CarrinhoPage() {
  const { slug = "" } = useParams();
  const { lines, setQuantity, remove, subtotal } = useCart();

  return (
    <main className="mx-auto max-w-2xl space-y-4 p-4">
      <header className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Carrinho</h1>
        <Link to={`/cardapio/${slug}`} className="text-sm text-blue-600">
          Continuar comprando
        </Link>
      </header>

      {lines.length === 0 ? (
        <p role="status" className="text-gray-600">
          Seu carrinho está vazio.
        </p>
      ) : (
        <>
          <ul className="space-y-3">
            {lines.map((l) => (
              <li
                key={l.key}
                className="flex items-center justify-between gap-4 rounded border p-3"
              >
                <div>
                  <p className="font-medium">{l.name}</p>
                  {l.modifiers.length > 0 && (
                    <p className="text-xs text-gray-500">
                      {l.modifiers.map((m) => m.modifier_name).join(", ")}
                    </p>
                  )}
                  <p className="tabular-nums text-sm">R$ {Number(l.unitPrice).toFixed(2)}</p>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="number"
                    min={1}
                    value={l.quantity}
                    aria-label={`Quantidade de ${l.name}`}
                    onChange={(e) => setQuantity(l.key, Math.max(1, Number(e.target.value)))}
                    className="w-16 rounded border px-2 py-1"
                  />
                  <button
                    type="button"
                    onClick={() => remove(l.key)}
                    className="text-sm text-red-600"
                  >
                    Remover
                  </button>
                </div>
              </li>
            ))}
          </ul>
          <div className="flex items-center justify-between border-t pt-4">
            <span className="font-medium">Subtotal</span>
            <span className="tabular-nums font-semibold">R$ {subtotal.toFixed(2)}</span>
          </div>
          <Link
            to={`/cardapio/${slug}/checkout`}
            className="block rounded bg-blue-600 px-4 py-2 text-center text-white"
          >
            Finalizar pedido
          </Link>
        </>
      )}
    </main>
  );
}
