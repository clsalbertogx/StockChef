import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useRef, useState } from "react";
import { api } from "../api/client";
import type { Supplier } from "../api/types";

const SUPPLIER_STATUS_LABEL: Record<string, string> = {
  active: "Ativo",
  inactive: "Inativo",
  archived: "Arquivado",
};

export default function FornecedoresPage() {
  const qc = useQueryClient();
  const {
    data: fornecedores = [],
    isPending: loading,
    isError,
  } = useQuery<Supplier[]>({
    queryKey: ["fornecedores"],
    queryFn: () => api<Supplier[]>("/fornecedores"),
  });
  const [name, setName] = useState("");
  const [leadDays, setLeadDays] = useState("1");
  const nameRef = useRef<HTMLInputElement>(null);

  const create = useMutation({
    mutationFn: () =>
      api<Supplier>("/fornecedores", {
        method: "POST",
        body: JSON.stringify({ name, lead_time_days: Number(leadDays) }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["fornecedores"] });
      setName("");
      setLeadDays("1");
    },
  });

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-8">
      <h1 className="text-2xl font-semibold">Fornecedores</h1>
      <form
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          create.mutate();
        }}
        className="flex flex-wrap items-end gap-3 rounded border p-4"
      >
        <label className="space-y-1">
          <span className="text-sm">Nome</span>
          <input
            ref={nameRef}
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="rounded border px-3 py-2"
          />
        </label>
        <label className="space-y-1">
          <span className="text-sm">Lead time (dias)</span>
          <input
            type="number"
            min="1"
            value={leadDays}
            onChange={(e) => setLeadDays(e.target.value)}
            className="w-24 rounded border px-3 py-2"
          />
        </label>
        <button
          type="submit"
          disabled={create.isPending}
          className="rounded bg-blue-600 px-4 py-2 text-white disabled:opacity-50"
        >
          {create.isPending ? "Criando…" : "Criar fornecedor"}
        </button>
      </form>
      {create.isError && (
        <p role="alert" className="text-sm text-red-600">
          <span aria-hidden="true" className="mr-1">
            ⚠
          </span>
          {create.error instanceof Error ? create.error.message : "Erro ao criar fornecedor."}
        </p>
      )}
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left">
            <th scope="col" className="py-2">
              Nome
            </th>
            <th scope="col">Lead time</th>
            <th scope="col">Status</th>
          </tr>
        </thead>
        <tbody>
          {isError ? (
            <tr>
              <td colSpan={3} className="py-2">
                <span role="alert" className="text-red-600">
                  <span aria-hidden="true" className="mr-1">
                    ⚠
                  </span>
                  Erro ao carregar fornecedores.
                </span>
              </td>
            </tr>
          ) : loading ? (
            <tr>
              <td colSpan={3} className="py-2 text-gray-600">
                Carregando…
              </td>
            </tr>
          ) : fornecedores.length === 0 ? (
            <tr>
              <td colSpan={3} className="py-4 text-gray-600">
                Nenhum fornecedor cadastrado.
                <button
                  type="button"
                  onClick={() => nameRef.current?.focus()}
                  className="ml-2 rounded bg-blue-600 px-3 py-1 text-white"
                >
                  Adicionar fornecedor
                </button>
              </td>
            </tr>
          ) : (
            fornecedores.map((f) => (
              <tr key={f.id} className="border-t">
                <td className="py-2">{f.name}</td>
                <td className="tabular-nums">{f.lead_time_days} dias</td>
                <td>{SUPPLIER_STATUS_LABEL[f.status] ?? f.status}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </main>
  );
}
