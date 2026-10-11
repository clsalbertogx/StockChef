import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ComandaPage from "../pages/ComandaPage";

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
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
      quantity: 2,
      unit_price: "10.00",
      total_price: "20.00",
      notes: "sem cebola",
      modifiers: [],
    },
  ],
};

describe("ComandaPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renderiza itens e imprime", async () => {
    const print = vi.fn();
    vi.stubGlobal("print", print);
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse(pedido)),
    );

    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={["/pedidos/o1/comanda"]}>
          <Routes>
            <Route path="/pedidos/:id/comanda" element={<ComandaPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await screen.findByText(/X-Burger/);
    expect(screen.getByText(/sem cebola/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /imprimir/i }));
    expect(print).toHaveBeenCalled();
  });
});
