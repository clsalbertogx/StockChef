import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import EstoquePage from "../pages/EstoquePage";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const insumo = {
  id: "i1",
  name: "Queijo",
  category: null,
  base_unit: { id: "u1", symbol: "kg" },
  average_cost: "45.00",
  minimum_stock: "0",
  status: "active",
  stock_total: "3.0000",
};

describe("EstoquePage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("registra perda e reflete no estoque", async () => {
    const fetchMock = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      const u = String(url);
      if (u === "/api/v1/insumos") return jsonResponse([insumo]);
      if (u === "/api/v1/estoque/critico") return jsonResponse([]);
      if (u === "/api/v1/estoque/movimentos") return jsonResponse([]);
      if (u === "/api/v1/perdas" && init?.method === "POST") {
        return jsonResponse({ id: "x", ingredient_id: "i1", quantity: "1.0000" }, 201);
      }
      throw new Error(`fetch inesperado: ${u}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <QueryClientProvider client={new QueryClient()}>
        <EstoquePage />
      </QueryClientProvider>,
    );

    await screen.findByText(/Críticos/);
    await screen.findByRole("option", { name: "Queijo" });
    await userEvent.selectOptions(screen.getByLabelText(/Insumo/), "i1");
    await userEvent.type(screen.getByLabelText(/Quantidade/), "1");
    await userEvent.click(screen.getByRole("button", { name: /registrar perda/i }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/perdas",
        expect.objectContaining({ method: "POST" }),
      ),
    );
    await waitFor(() => expect(screen.getByRole("status")).toBeInTheDocument());
  });

  it("mostra erro quando críticos falham em vez de empty state", async () => {
    const fetchMock = vi.fn(async (url: RequestInfo | URL) => {
      const u = String(url);
      if (u === "/api/v1/insumos") return jsonResponse([insumo]);
      if (u === "/api/v1/estoque/critico") return jsonResponse({ detail: "boom" }, 500);
      if (u === "/api/v1/estoque/movimentos") return jsonResponse({ detail: "boom" }, 500);
      throw new Error(`fetch inesperado: ${u}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <QueryClientProvider
        client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
      >
        <EstoquePage />
      </QueryClientProvider>,
    );

    expect(await screen.findByText("Erro ao carregar críticos.")).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByRole("alert")).toHaveLength(2));
    expect(screen.queryByText("Nenhum insumo abaixo do mínimo.")).not.toBeInTheDocument();
  });
});
