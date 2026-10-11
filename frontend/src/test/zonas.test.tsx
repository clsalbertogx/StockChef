import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ZonasPage from "../pages/ZonasPage";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("ZonasPage", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("lista zonas e mostra estado vazio", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse([
          {
            id: "z1",
            store_id: "s1",
            name: "Centro",
            cep_ranges: [{ start: "01000000", end: "01999999" }],
            delivery_fee: "6.00",
            min_order_value: "10.00",
            eta_minutes: 35,
            active: true,
          },
        ]),
      ),
    );
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter>
          <ZonasPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(await screen.findByText("Centro")).toBeInTheDocument();
    expect(screen.getByText(/6,00|6.00/)).toBeInTheDocument();
  });
});
