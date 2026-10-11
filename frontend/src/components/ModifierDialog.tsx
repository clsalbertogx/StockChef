import { useState } from "react";
import type { PublicModifier, PublicProduct } from "../api/types";
import { type CartModifier, useCart } from "../cart/CartContext";

interface Props {
  product: PublicProduct;
  onConfirm: (line: {
    productId: string;
    name: string;
    unitPrice: string;
    quantity: number;
    notes?: string;
    modifiers: CartModifier[];
  }) => void;
  onCancel: () => void;
}

export default function ModifierDialog({ product, onConfirm, onCancel }: Props) {
  const [selected, setSelected] = useState<string[]>([]);
  const [qty, setQty] = useState(1);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");

  const groups = Array.from(new Set(product.modifiers.map((m) => m.group_name)));

  function toggle(mod: PublicModifier) {
    setSelected((sel) => {
      const groupMods = product.modifiers.filter((m) => m.group_name === mod.group_name);
      const maxes = groupMods.map((m) => m.max_selection).filter((v): v is number => v !== null);
      const groupMax = maxes.length ? Math.min(...maxes) : Number.POSITIVE_INFINITY;
      const inGroup = sel.filter((id) => groupMods.some((gm) => gm.id === id));
      if (sel.includes(mod.id)) return sel.filter((id) => id !== mod.id);
      if (inGroup.length >= groupMax) {
        return [...sel.filter((id) => !groupMods.some((gm) => gm.id === id)), mod.id];
      }
      return [...sel, mod.id];
    });
  }

  function confirm() {
    for (const group of groups) {
      const groupMods = product.modifiers.filter((m) => m.group_name === group);
      const chosen = selected.filter((id) => groupMods.some((m) => m.id === id));
      const required = groupMods.some((m) => m.required);
      const min = Math.max(...groupMods.map((m) => m.min_selection), required ? 1 : 0);
      if (chosen.length < min) {
        setError(`Escolha uma opção em "${group}".`);
        return;
      }
    }
    const chosenMods = product.modifiers.filter((m) => selected.includes(m.id));
    const delta = chosenMods.reduce((sum, m) => sum + Number(m.price_delta), 0);
    const unitPrice = (Number(product.price) + delta).toFixed(2);
    onConfirm({
      productId: product.id,
      name: product.name,
      unitPrice,
      quantity: qty,
      notes: notes || undefined,
      modifiers: chosenMods.map((m) => ({
        id: m.id,
        group_name: m.group_name,
        modifier_name: m.modifier_name,
        price_delta: m.price_delta,
      })),
    });
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={product.name}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
    >
      <div className="w-full max-w-md space-y-4 rounded bg-white p-4">
        <h2 className="text-lg font-semibold">{product.name}</h2>
        {error && (
          <p role="alert" className="text-sm text-red-600">
            {error}
          </p>
        )}
        {groups.map((group) => (
          <fieldset key={group} className="space-y-1">
            <legend className="text-sm font-medium">{group}</legend>
            {product.modifiers
              .filter((m) => m.group_name === group)
              .map((m) => (
                <label key={m.id} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={selected.includes(m.id)}
                    onChange={() => toggle(m)}
                  />
                  <span>
                    {m.modifier_name}
                    {Number(m.price_delta) > 0 ? ` (+R$ ${Number(m.price_delta).toFixed(2)})` : ""}
                  </span>
                </label>
              ))}
          </fieldset>
        ))}
        <label className="block space-y-1">
          <span className="text-sm">Observações</span>
          <input
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full rounded border px-3 py-2"
          />
        </label>
        <label className="block space-y-1">
          <span className="text-sm">Quantidade</span>
          <input
            type="number"
            min={1}
            value={qty}
            onChange={(e) => setQty(Math.max(1, Number(e.target.value)))}
            className="w-24 rounded border px-3 py-2"
          />
        </label>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onCancel} className="rounded border px-4 py-2">
            Cancelar
          </button>
          <button
            type="button"
            onClick={confirm}
            className="rounded bg-blue-600 px-4 py-2 text-white"
          >
            Adicionar
          </button>
        </div>
      </div>
    </div>
  );
}

export function useAddToCart() {
  const { add } = useCart();
  return add;
}
