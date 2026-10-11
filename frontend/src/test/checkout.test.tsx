import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CartProvider } from "../cart/CartContext";
import CheckoutPage from "../pages/public/CheckoutPage";
import PedidoPublicoPage from "../pages/public/PedidoPublicoPage";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const order = {
  code: "SC-1",
  status: "received",
  fulfillment_type: "delivery",
  subtotal: "25.00",
  delivery_fee: "6.00",
  total: "31.00",
  eta_minutes: 35,
  created_at: "2026-10-10T12:00:00Z",
  items: [
    {
      product_name: "X-Burger",
      quantity: 1,
      unit_price: "25.00",
      total_price: "25.00",
      modifiers: [],
    },
  ],
};

describe("CheckoutPage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
    localStorage.setItem(
      "sc_cart:menu1",
      JSON.stringify([
        {
          key: "p1||",
          productId: "p1",
          name: "X-Burger",
          unitPrice: "25.00",
          quantity: 1,
          modifiers: [],
        },
      ]),
    );
  });

  it("finaliza o pedido e mostra a confirmação", async () => {
    const calls: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
        const u = String(url);
        calls.push(`${init?.method ?? "GET"} ${u}`);
        if (u.includes("/entrega")) {
          return jsonResponse({
            covered: true,
            zone_name: "Centro",
            delivery_fee: "6.00",
            min_order_value: "0.00",
            eta_minutes: 35,
          });
        }
        if (u.endsWith("/pedidos") && init?.method === "POST") return jsonResponse(order, 201);
        if (u.includes("/pedidos/SC-1")) return jsonResponse(order);
        throw new Error(`fetch inesperado: ${u}`);
      }),
    );

    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={["/cardapio/menu1/checkout"]}>
          <CartProvider>
            <Routes>
              <Route path="/cardapio/:slug/checkout" element={<CheckoutPage />} />
              <Route path="/cardapio/:slug/pedido/:code" element={<PedidoPublicoPage />} />
            </Routes>
          </CartProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await userEvent.type(screen.getByLabelText(/nome/i), "Ana");
    await userEvent.type(screen.getByLabelText(/telefone/i), "11999999999");
    await userEvent.type(screen.getByLabelText(/cep/i), "01001000");
    await userEvent.tab();
    await waitFor(() => expect(calls.some((c) => c.includes("/entrega"))).toBe(true));
    await userEvent.click(screen.getByRole("button", { name: /finalizar pedido/i }));
    await waitFor(() => expect(calls).toContain("POST /api/v1/public/menu1/pedidos"));
    expect(await screen.findByText("SC-1")).toBeInTheDocument();
  });
});
