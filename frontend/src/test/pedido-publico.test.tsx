import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PedidoPublicoPage from "../pages/public/PedidoPublicoPage";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("PedidoPublicoPage", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("mostra status e itens do pedido", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({
          code: "SC-9",
          status: "preparing",
          fulfillment_type: "pickup",
          subtotal: "25.00",
          delivery_fee: "0.00",
          total: "25.00",
          eta_minutes: 0,
          created_at: "2026-10-10T12:00:00Z",
          items: [
            {
              product_name: "X-Burger",
              quantity: 1,
              unit_price: "25.00",
              total_price: "25.00",
              modifiers: [
                { id: "m1", group_name: "Ponto", modifier_name: "Ao ponto", price_delta: "0.00" },
              ],
            },
          ],
        }),
      ),
    );

    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={["/cardapio/menu1/pedido/SC-9"]}>
          <Routes>
            <Route path="/cardapio/:slug/pedido/:code" element={<PedidoPublicoPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(await screen.findByText("SC-9")).toBeInTheDocument();
    expect(screen.getByText(/em preparo/i)).toBeInTheDocument();
    expect(screen.getByText(/ao ponto/i)).toBeInTheDocument();
  });
});
