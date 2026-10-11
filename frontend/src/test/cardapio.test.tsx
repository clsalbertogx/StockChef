import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CartProvider } from "../cart/CartContext";
import CardapioPage from "../pages/public/CardapioPage";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const menu = {
  tenant: { name: "Pizzaria", slug: "menu1" },
  store: { id: "s1", name: "Loja", delivery_enabled: true, pickup_enabled: true },
  categories: [{ id: "c1", name: "Lanches", sort_order: 0 }],
  products: [
    {
      id: "p1",
      name: "X-Burger",
      description: null,
      price: "25.00",
      image_url: null,
      category_id: "c1",
      preparation_time_minutes: 10,
      modifiers: [
        {
          id: "m1",
          group_name: "Ponto",
          modifier_name: "Ao ponto",
          price_delta: "0.00",
          required: true,
          min_selection: 1,
          max_selection: 1,
        },
      ],
    },
    {
      id: "p2",
      name: "Refrigerante",
      description: null,
      price: "6.00",
      image_url: null,
      category_id: null,
      preparation_time_minutes: 0,
      modifiers: [],
    },
  ],
};

function renderPage() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={["/cardapio/menu1"]}>
        <CartProvider>
          <Routes>
            <Route path="/cardapio/:slug" element={<CardapioPage />} />
          </Routes>
        </CartProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("CardapioPage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse(menu)),
    );
  });

  it("lista produtos e filtra por busca", async () => {
    renderPage();
    await screen.findByText("X-Burger");
    await userEvent.type(screen.getByLabelText(/buscar/i), "refri");
    expect(screen.queryByText("X-Burger")).not.toBeInTheDocument();
    expect(screen.getByText("Refrigerante")).toBeInTheDocument();
  });

  it("adiciona produto sem adicionais direto ao carrinho", async () => {
    renderPage();
    await screen.findByText("Refrigerante");
    await userEvent.click(screen.getByRole("button", { name: /adicionar refrigerante/i }));
    expect(await screen.findByText(/1 item/i)).toBeInTheDocument();
  });
});
