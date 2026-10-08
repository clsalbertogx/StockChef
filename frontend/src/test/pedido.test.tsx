import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PedidoDetalhePage from "../pages/PedidoDetalhePage";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const pedidoBase = {
  id: "o1",
  code: "SC-ABC1",
  status: "received",
  subtotal: "40.00",
  total: "40.00",
  order_items: [
    {
      product_id: "p1",
      product_name: "X-Burger",
      quantity: 2,
      unit_price: "20.00",
      total_price: "40.00",
    },
  ],
};

describe("PedidoDetalhePage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("confirma um pedido recebido", async () => {
    let pedidoState = { ...pedidoBase };
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
        const u = String(url);
        if (u === "/api/v1/pedidos/o1") {
          return jsonResponse(pedidoState);
        }
        if (u === "/api/v1/pedidos/o1/eventos") {
          return jsonResponse({ order_id: "o1", status: pedidoState.status, events: [] });
        }
        if (u === "/api/v1/pedidos/o1/confirmar" && init?.method === "POST") {
          pedidoState = { ...pedidoState, status: "confirmed" };
          return jsonResponse(pedidoState);
        }
        throw new Error(`fetch inesperado: ${u}`);
      }),
    );

    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={["/pedidos/o1"]}>
          <Routes>
            <Route path="/pedidos/:id" element={<PedidoDetalhePage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await screen.findByText("Recebido");
    await userEvent.click(screen.getByRole("button", { name: /confirmar pedido/i }));
    await waitFor(() => expect(screen.queryByText("Confirmado")).toBeInTheDocument());
  });
});
