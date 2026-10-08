import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import InsumosPage from "../pages/InsumosPage";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const insumoBase = {
  id: "i1",
  name: "Farinha",
  category: null,
  base_unit: { id: "u1", symbol: "kg" },
  average_cost: "5.00",
  minimum_stock: "0.00",
  stock_total: "10.000",
};

describe("InsumosPage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("edita custo de insumo via PATCH", async () => {
    let insumoState = { ...insumoBase };
    const fetchMock = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      const u = String(url);
      if (u === "/api/v1/insumos") {
        return jsonResponse([insumoState]);
      }
      if (u.startsWith("/api/v1/insumos/") && init?.method === "PATCH") {
        const body = init.body ? JSON.parse(String(init.body)) : {};
        insumoState = { ...insumoState, average_cost: body.average_cost };
        return jsonResponse(insumoState);
      }
      throw new Error(`fetch inesperado: ${u}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter>
          <InsumosPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await screen.findByText("Farinha");
    await userEvent.click(screen.getByRole("button", { name: /editar custo/i }));
    const input = screen.getByLabelText("Novo custo");
    await userEvent.clear(input);
    await userEvent.type(input, "6.50");
    await userEvent.click(screen.getByRole("button", { name: /salvar/i }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/insumos/i1"),
        expect.objectContaining({ method: "PATCH" }),
      ),
    );
    await waitFor(() => expect(screen.getByText(/R\$ 6\.50/)).toBeInTheDocument());
  });
});
