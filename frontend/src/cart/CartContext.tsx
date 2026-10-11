import { createContext, type ReactNode, useContext, useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";

export interface CartModifier {
  id: string;
  group_name: string;
  modifier_name: string;
  price_delta: string;
}

export interface CartLine {
  key: string;
  productId: string;
  name: string;
  unitPrice: string;
  quantity: number;
  notes?: string;
  modifiers: CartModifier[];
}

interface CartValue {
  lines: CartLine[];
  add: (line: Omit<CartLine, "key">) => void;
  setQuantity: (key: string, quantity: number) => void;
  remove: (key: string) => void;
  clear: () => void;
  subtotal: number;
  count: number;
}

const CartContext = createContext<CartValue | null>(null);

function lineKey(line: Omit<CartLine, "key">): string {
  const mods = line.modifiers
    .map((m) => m.id)
    .sort()
    .join(",");
  return `${line.productId}|${mods}|${line.notes ?? ""}`;
}

export function CartProvider({ children }: { children: ReactNode }) {
  const location = useLocation();
  const slug = useMemo(() => {
    const match = location.pathname.match(/^\/cardapio\/([^/]+)/);
    return match ? match[1] : null;
  }, [location.pathname]);
  const [lines, setLines] = useState<CartLine[]>([]);

  useEffect(() => {
    if (!slug) {
      setLines([]);
      return;
    }
    const raw = localStorage.getItem(`sc_cart:${slug}`);
    setLines(raw ? (JSON.parse(raw) as CartLine[]) : []);
  }, [slug]);

  useEffect(() => {
    if (slug) localStorage.setItem(`sc_cart:${slug}`, JSON.stringify(lines));
  }, [slug, lines]);

  const value: CartValue = {
    lines,
    add: (line) =>
      setLines((ls) => {
        const key = lineKey(line);
        const existing = ls.find((l) => l.key === key);
        if (existing) {
          return ls.map((l) =>
            l.key === key ? { ...l, quantity: l.quantity + line.quantity } : l,
          );
        }
        return [...ls, { ...line, key }];
      }),
    setQuantity: (key, quantity) =>
      setLines((ls) => ls.map((l) => (l.key === key ? { ...l, quantity } : l))),
    remove: (key) => setLines((ls) => ls.filter((l) => l.key !== key)),
    clear: () => setLines([]),
    subtotal: lines.reduce((sum, l) => sum + Number(l.unitPrice) * l.quantity, 0),
    count: lines.reduce((sum, l) => sum + l.quantity, 0),
  };

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart(): CartValue {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart precisa de CartProvider");
  return ctx;
}
