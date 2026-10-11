import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { api } from "../api/client";
import type { Supplier } from "../api/types";

export default function FornecedoresPage() {
  const qc = useQueryClient();
  const { data: fornecedores = [] } = useQuery<Supplier[]>({
    queryKey: ["fornecedores"],
    queryFn: () => api<Supplier[]>("/fornecedores"),
  });
  const [name, setName] = useState("");
  const [leadDays, setLeadDays] = useState("1");

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
          Criar fornecedor
        </button>
      </form>
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
          {fornecedores.map((f) => (
            <tr key={f.id} className="border-t">
              <td className="py-2">{f.name}</td>
              <td>{f.lead_time_days} dias</td>
              <td>{f.active ? "Ativo" : "Inativo"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
