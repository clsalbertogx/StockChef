import { beforeEach, describe, expect, it, vi } from "vitest";
import { publicApi } from "../api/public";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("publicApi", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("não envia Authorization e monta a URL", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ tenant: { slug: "x" } }));
    vi.stubGlobal("fetch", fetchMock);
    const body = await publicApi<{ tenant: { slug: string } }>("/public/x/cardapio");
    expect(body.tenant.slug).toBe("x");
    const call = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    const init = call[1];
    const headers = new Headers(init.headers);
    expect(headers.get("Authorization")).toBeNull();
  });

  it("converte erro em ApiError com code", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({ detail: "CEP não encontrado.", code: "cep_not_found" }, 404),
      ),
    );
    await expect(publicApi("/public/x/cep/9")).rejects.toMatchObject({
      status: 404,
      code: "cep_not_found",
    });
  });
});
