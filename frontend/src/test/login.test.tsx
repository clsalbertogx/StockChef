import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import LoginPage from "../pages/LoginPage";

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

describe("LoginPage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("faz login e guarda o token", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL) => {
        if (String(url) === "/api/v1/auth/login") {
          return jsonResponse({
            access_token: "abc",
            user: { id: "1", email: "a@b.com", name: "A", role: "owner" },
          });
        }
        throw new Error(`fetch inesperado: ${url}`);
      }),
    );

    render(
      <MemoryRouter>
        <AuthProvider>
          <LoginPage />
        </AuthProvider>
      </MemoryRouter>,
    );

    await userEvent.type(screen.getByLabelText(/tenant/i), "demo");
    await userEvent.type(screen.getByLabelText(/e-mail/i), "a@b.com");
    await userEvent.type(screen.getByLabelText(/senha/i), "demo1234");
    await userEvent.click(screen.getByRole("button", { name: /entrar/i }));

    await waitFor(() => expect(localStorage.getItem("sc_token")).toBe("abc"));
  });
});
