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

const pedido = {
  id: "o1",
  code: "SC-A1",
  status: "confirmed",
  customer_name: "Ana",
  customer_phone: "1199",
  channel: "pos",
  fulfillment_type: "table",
  expected_time: null,
  subtotal: "20.00",
  delivery_fee: "0.00",
  discount_total: "0.00",
  tax_total: "0.00",
  total: "20.00",
  notes: null,
  created_at: "2026-10-10T12:00:00Z",
  order_items: [
    {
      product_id: "p1",
      product_name: "X-Burger",
      quantity: 1,
      unit_price: "20.00",
      total_price: "20.00",
      notes: null,
      modifiers: [],
    },
  ],
};

function renderPage() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={["/pedidos/o1"]}>
        <Routes>
          <Route path="/pedidos/:id" element={<PedidoDetalhePage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("PedidoDetalhePage transicoes", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("inicia preparo de um pedido confirmado", async () => {
    const calls: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
        const u = String(url);
        calls.push(`${init?.method ?? "GET"} ${u}`);
        if (u === "/api/v1/pedidos/o1") return jsonResponse(pedido);
        if (u === "/api/v1/pedidos/o1/eventos")
          return jsonResponse({ order_id: "o1", status: pedido.status, events: [] });
        if (u === "/api/v1/pedidos/o1/status" && init?.method === "PATCH")
          return jsonResponse({ ...pedido, status: "preparing" });
        throw new Error(`fetch inesperado: ${u}`);
      }),
    );
    renderPage();
    await screen.findByText("SC-A1");
    await userEvent.click(screen.getByRole("button", { name: /iniciar preparo/i }));
    await waitFor(() => expect(calls).toContain("PATCH /api/v1/pedidos/o1/status"));
  });

  it("cancela pedido com motivo", async () => {
    const bodies: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
        const u = String(url);
        if (u === "/api/v1/pedidos/o1") return jsonResponse(pedido);
        if (u === "/api/v1/pedidos/o1/eventos")
          return jsonResponse({ order_id: "o1", status: pedido.status, events: [] });
        if (u === "/api/v1/pedidos/o1/cancelar" && init?.method === "POST") {
          bodies.push(String(init.body));
          return jsonResponse({ ...pedido, status: "cancelled" });
        }
        throw new Error(`fetch inesperado: ${u}`);
      }),
    );
    renderPage();
    await screen.findByText("SC-A1");
    await userEvent.click(screen.getByRole("button", { name: /cancelar pedido/i }));
    await userEvent.type(screen.getByLabelText(/motivo/i), "cliente desistiu");
    await userEvent.click(screen.getByRole("button", { name: /confirmar cancelamento/i }));
    await waitFor(() => expect(bodies.some((b) => b.includes("cliente desistiu"))).toBe(true));
  });
});
