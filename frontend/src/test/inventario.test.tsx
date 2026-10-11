import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import InventarioPage from "../pages/InventarioPage";

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
  stock_total: "3.0000",
};

const contagem = {
  id: "c1",
  store_id: "st1",
  status: "open",
  started_at: "2026-10-08T10:00:00Z",
  closed_at: null,
  items: [
    {
      ingredient_id: "i1",
      system_quantity: "3.0000",
      counted_quantity: null,
      difference: null,
      adjusted: false,
    },
  ],
};

describe("InventarioPage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });
  afterEach(() => vi.unstubAllGlobals());

  it("abre uma contagem, registra e salva a contagem", async () => {
    let contagens: unknown[] = [];
    const fetchMock = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      const u = String(url);
      if (u === "/api/v1/insumos") return jsonResponse([insumo]);
      if (u === "/api/v1/inventarios" && init?.method === "POST") {
        contagens = [contagem];
        return jsonResponse(contagem, 201);
      }
      if (u === "/api/v1/inventarios") return jsonResponse(contagens);
      if (u === "/api/v1/inventarios/c1/itens" && init?.method === "POST") {
        const body = JSON.parse(String(init.body));
        expect(body.items).toEqual([{ ingredient_id: "i1", counted_quantity: "5" }]);
        return jsonResponse(contagem);
      }
      throw new Error(`fetch inesperado: ${u}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <QueryClientProvider client={new QueryClient()}>
        <InventarioPage />
      </QueryClientProvider>,
    );

    await screen.findByText(/Nenhuma contagem/i);
    await userEvent.click(screen.getByRole("button", { name: /abrir contagem/i }));

    await screen.findByText("Queijo");
    await userEvent.type(screen.getByLabelText(/Contagem de Queijo/i), "5");
    await userEvent.click(screen.getByRole("button", { name: /salvar contagens/i }));

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/inventarios/c1/itens",
        expect.objectContaining({ method: "POST" }),
      ),
    );
  });

  it("persiste as contagens digitadas ao clicar Fechar diretamente", async () => {
    let contagens: unknown[] = [];
    let itensBody: unknown = null;
    let fechou = false;
    const fetchMock = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      const u = String(url);
      if (u === "/api/v1/insumos") return jsonResponse([insumo]);
      if (u === "/api/v1/inventarios" && init?.method === "POST") {
        contagens = [contagem];
        return jsonResponse(contagem, 201);
      }
      if (u === "/api/v1/inventarios") return jsonResponse(contagens);
      if (u === "/api/v1/inventarios/c1/itens" && init?.method === "POST") {
        itensBody = JSON.parse(String(init.body));
        return jsonResponse({ ...contagem, status: "closed" });
      }
      if (u === "/api/v1/inventarios/c1/fechar" && init?.method === "POST") {
        fechou = true;
        return jsonResponse({ ...contagem, status: "closed" });
      }
      throw new Error(`fetch inesperado: ${u}`);
    });
    vi.stubGlobal("fetch", fetchMock);

    render(
      <QueryClientProvider client={new QueryClient()}>
        <InventarioPage />
      </QueryClientProvider>,
    );

    await screen.findByText(/Nenhuma contagem/i);
    await userEvent.click(screen.getByRole("button", { name: /abrir contagem/i }));
    await screen.findByText("Queijo");
    await userEvent.type(screen.getByLabelText(/Contagem de Queijo/i), "5");
    await userEvent.click(screen.getByRole("button", { name: /^fechar$/i }));

    await waitFor(() => expect(fechou).toBe(true));
    expect(itensBody).toEqual({ items: [{ ingredient_id: "i1", counted_quantity: "5" }] });
  });
});
