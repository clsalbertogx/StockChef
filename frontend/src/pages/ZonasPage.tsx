import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { type FormEvent, useState } from "react";
import { api } from "../api/client";
import type { Zone } from "../api/types";

export default function ZonasPage() {
  const qc = useQueryClient();
  const { data: zonas = [], isLoading } = useQuery<Zone[]>({
    queryKey: ["zonas"],
    queryFn: () => api<Zone[]>("/zonas"),
  });
  const [name, setName] = useState("");
  const [cepStart, setCepStart] = useState("");
  const [cepEnd, setCepEnd] = useState("");
  const [fee, setFee] = useState("0.00");
  const [minOrder, setMinOrder] = useState("0.00");
  const [eta, setEta] = useState("30");

  const create = useMutation({
    mutationFn: () =>
      api<Zone>("/zonas", {
        method: "POST",
        body: JSON.stringify({
          name,
          cep_ranges: [{ start: cepStart, end: cepEnd }],
          delivery_fee: fee,
          min_order_value: minOrder,
          eta_minutes: Number(eta),
        }),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["zonas"] });
      setName("");
      setCepStart("");
      setCepEnd("");
    },
  });

  const toggle = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) =>
      api<Zone>(`/zonas/${id}`, { method: "PATCH", body: JSON.stringify({ active }) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["zonas"] }),
  });

  return (
    <main className="mx-auto max-w-4xl space-y-6 p-8">
      <h1 className="text-2xl font-semibold">Entregas</h1>

      <form
        onSubmit={(e: FormEvent) => {
          e.preventDefault();
          create.mutate();
        }}
        className="grid gap-3 rounded border p-4 sm:grid-cols-3"
      >
        <label className="space-y-1">
          <span className="text-sm">Nome da zona</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="w-full rounded border px-3 py-2"
          />
        </label>
        <label className="space-y-1">
          <span className="text-sm">CEP inicial</span>
          <input
            value={cepStart}
            onChange={(e) => setCepStart(e.target.value)}
            required
            className="w-full rounded border px-3 py-2"
          />
        </label>
        <label className="space-y-1">
          <span className="text-sm">CEP final</span>
          <input
            value={cepEnd}
            onChange={(e) => setCepEnd(e.target.value)}
            required
            className="w-full rounded border px-3 py-2"
          />
        </label>
        <label className="space-y-1">
          <span className="text-sm">Taxa (R$)</span>
          <input
            value={fee}
            onChange={(e) => setFee(e.target.value)}
            className="w-full rounded border px-3 py-2"
          />
        </label>
        <label className="space-y-1">
          <span className="text-sm">Mínimo (R$)</span>
          <input
            value={minOrder}
            onChange={(e) => setMinOrder(e.target.value)}
            className="w-full rounded border px-3 py-2"
          />
        </label>
        <label className="space-y-1">
          <span className="text-sm">ETA (min)</span>
          <input
            value={eta}
            onChange={(e) => setEta(e.target.value)}
            className="w-full rounded border px-3 py-2"
          />
        </label>
        <button type="submit" className="rounded bg-blue-600 px-4 py-2 text-white sm:col-span-3">
          Criar zona
        </button>
      </form>

      {isLoading && <p className="text-gray-600">Carregando…</p>}
      {!isLoading && zonas.length === 0 && (
        <p role="status" className="text-gray-600">
          Nenhuma zona de entrega cadastrada.
        </p>
      )}
      <ul className="space-y-2">
        {zonas.map((z) => (
          <li key={z.id} className="flex items-center justify-between rounded border p-3">
            <div>
              <p className="font-medium">{z.name}</p>
              <p className="text-sm text-gray-600 tabular-nums">
                {z.cep_ranges[0]?.start}–{z.cep_ranges[0]?.end} · R${" "}
                {Number(z.delivery_fee).toFixed(2)}
                {" · "}~{z.eta_minutes} min
              </p>
            </div>
            <button
              type="button"
              onClick={() => toggle.mutate({ id: z.id, active: !z.active })}
              className="rounded border px-3 py-2 text-sm"
            >
              {z.active ? "Desativar" : "Ativar"}
            </button>
          </li>
        ))}
      </ul>
    </main>
  );
}
