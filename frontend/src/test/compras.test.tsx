import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ComprasDetalhePage from "../pages/ComprasDetalhePage";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const poBase = {
  id: "p1",
  supplier_id: "s1",
  status: "sent",
  total_amount: "40.00",
  created_at: "2026-10-08T10:00:00Z",
  items: [
    { id: "it1", ingredient_id: "i1", quantity: "10", unit_cost: "4.00", received_quantity: "0" },
  ],
};

describe("ComprasDetalhePage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });
  afterEach(() => vi.unstubAllGlobals());

  it("recebe todos os itens com nota fiscal e muda para received", async () => {
    let state = poBase;
    const fetchMock = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      const u = String(url);
      if (u === "/api/v1/compras/p1") return jsonResponse(state);
      if (u === "/api/v1/insumos") return jsonResponse([]);
      if (u === "/api/v1/compras/p1/recebimento" && init?.method === "POST") {
        const body = JSON.parse(String(init.body));
        expect(body.invoice_number).toBe("NF-1");
        expect(body.items).toEqual([
          { purchase_order_item_id: "it1", received_quantity: "10", unit_cost: "4.00" },
        ]);
        state = {
          ...state,
          status: "received",
          items: [{ ...state.items[0], received_quantity: "10" }],
        };
        return jsonResponse(state);
      }
      throw new Error(`fetch inesperado: ${u}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={["/compras/p1"]}>
          <Routes>
            <Route path="/compras/:id" element={<ComprasDetalhePage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await screen.findByText(/Enviado/);
    await userEvent.type(screen.getByLabelText(/Nota fiscal/i), "NF-1");
    await userEvent.click(screen.getByRole("button", { name: /receber/i }));
    await waitFor(() =>
      expect(screen.getByText("Recebido", { selector: "strong" })).toBeInTheDocument(),
    );
  });
});
