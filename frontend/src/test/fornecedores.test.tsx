import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import FornecedoresPage from "../pages/FornecedoresPage";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function renderPage() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <FornecedoresPage />
    </QueryClientProvider>,
  );
}

describe("FornecedoresPage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("mostra empty state com ação primária quando não há fornecedores", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse([])),
    );

    renderPage();

    expect(await screen.findByText("Nenhum fornecedor cadastrado.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /adicionar fornecedor/i })).toBeInTheDocument();
  });

  it("mostra erro visível quando o POST falha", async () => {
    const fetchMock = vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      const u = String(url);
      if (u === "/api/v1/fornecedores" && init?.method === "POST") {
        return jsonResponse({ detail: "Nome duplicado." }, 400);
      }
      return jsonResponse([]);
    });
    vi.stubGlobal("fetch", fetchMock);

    renderPage();

    await userEvent.type(await screen.findByLabelText(/Nome/), "Atacado X");
    await userEvent.click(screen.getByRole("button", { name: /criar fornecedor/i }));

    await waitFor(() => expect(screen.getByText("Nome duplicado.")).toBeInTheDocument());
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
