import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import FilaKdsPage from "../pages/FilaKdsPage";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const fila = [
  {
    order_id: "o1",
    code: "SC-A1",
    status: "confirmed",
    channel: "pos",
    fulfillment_type: "table",
    notes: "sem cebola",
    created_at: "2026-10-10T12:00:00Z",
    elapsed_minutes: 4,
    items: [
      { order_item_id: "i1", product_name: "X-Burger", quantity: 2, notes: null, modifiers: [] },
    ],
  },
];

describe("FilaKdsPage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("lista a fila e inicia preparo", async () => {
    const calls: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
        const u = String(url);
        calls.push(`${init?.method ?? "GET"} ${u}`);
        if (u === "/api/v1/cozinha/fila") return jsonResponse(fila);
        if (u === "/api/v1/pedidos/o1/status" && init?.method === "PATCH") {
          return jsonResponse({ ...fila[0], status: "preparing" });
        }
        throw new Error(`fetch inesperado: ${u}`);
      }),
    );

    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter>
          <FilaKdsPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await screen.findByText("SC-A1");
    expect(screen.getByText(/2× X-Burger/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /iniciar preparo/i }));
    await waitFor(() => expect(calls).toContain("PATCH /api/v1/pedidos/o1/status"));
  });

  it("mostra estado vazio", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse([])),
    );
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter>
          <FilaKdsPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    await screen.findByText(/nenhum pedido/i);
  });
});
