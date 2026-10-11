import { type FormEvent, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ApiError } from "../../api/client";
import { publicApi } from "../../api/public";
import type { DeliveryEstimate, PublicOrder } from "../../api/types";
import { useCart } from "../../cart/CartContext";

interface Address {
  street: string;
  number: string;
  district: string;
  city: string;
  state: string;
}

export default function CheckoutPage() {
  const { slug = "" } = useParams();
  const navigate = useNavigate();
  const { lines, subtotal, clear } = useCart();
  const idempotency = useRef(crypto.randomUUID());

  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [fulfillment, setFulfillment] = useState<"delivery" | "pickup">("delivery");
  const [cep, setCep] = useState("");
  const [address, setAddress] = useState<Address>({
    street: "",
    number: "",
    district: "",
    city: "",
    state: "",
  });
  const [notes, setNotes] = useState("");
  const [estimate, setEstimate] = useState<DeliveryEstimate | null>(null);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);

  useEffect(() => {
    if (fulfillment !== "delivery" || cep.replace(/\D/g, "").length !== 8) {
      setEstimate(null);
      return;
    }
    let alive = true;
    publicApi<DeliveryEstimate>(`/public/${slug}/entrega?cep=${encodeURIComponent(cep)}`)
      .then((e) => alive && setEstimate(e))
      .catch(() => alive && setEstimate(null));
    return () => {
      alive = false;
    };
  }, [cep, fulfillment, slug]);

  async function onCepBlur() {
    if (cep.replace(/\D/g, "").length !== 8) return;
    try {
      const found = await publicApi<{
        street: string;
        district: string;
        city: string;
        state: string;
      }>(`/public/${slug}/cep/${encodeURIComponent(cep)}`);
      setAddress((a) => ({
        ...a,
        street: found.street,
        district: found.district,
        city: found.city,
        state: found.state,
      }));
    } catch {
      setError("Não foi possível consultar o CEP.");
    }
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSending(true);
    try {
      const order = await publicApi<PublicOrder>(`/public/${slug}/pedidos`, {
        method: "POST",
        body: JSON.stringify({
          customer_name: name,
          customer_phone: phone,
          fulfillment_type: fulfillment,
          cep: fulfillment === "delivery" ? cep : null,
          address: fulfillment === "delivery" ? address : null,
          notes: notes || null,
          idempotency_key: idempotency.current,
          items: lines.map((l) => ({
            product_id: l.productId,
            quantity: l.quantity,
            notes: l.notes ?? null,
            modifier_ids: l.modifiers.map((m) => m.id),
          })),
        }),
      });
      clear();
      navigate(`/cardapio/${slug}/pedido/${order.code}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Não foi possível enviar o pedido.");
    } finally {
      setSending(false);
    }
  }

  const fee = fulfillment === "delivery" ? Number(estimate?.delivery_fee ?? 0) : 0;
  const total = subtotal + fee;
  const minOrder = Number(estimate?.min_order_value ?? 0);
  const abaixoMinimo = fulfillment === "delivery" && subtotal < minOrder;
  const uncovered = fulfillment === "delivery" && estimate !== null && !estimate.covered;

  return (
    <main className="mx-auto max-w-2xl space-y-4 p-4">
      <h1 className="text-xl font-semibold">Finalizar pedido</h1>
      {error && (
        <p role="alert" className="text-sm text-red-600">
          {error}
        </p>
      )}
      <form onSubmit={submit} className="space-y-4">
        <label className="block space-y-1">
          <span className="text-sm">Nome</span>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="w-full rounded border px-3 py-2"
          />
        </label>
        <label className="block space-y-1">
          <span className="text-sm">Telefone</span>
          <input
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            required
            className="w-full rounded border px-3 py-2"
          />
        </label>
        <label className="block space-y-1">
          <span className="text-sm">Tipo de entrega</span>
          <select
            value={fulfillment}
            onChange={(e) => setFulfillment(e.target.value as "delivery" | "pickup")}
            className="w-full rounded border px-3 py-2"
          >
            <option value="delivery">Entrega</option>
            <option value="pickup">Retirada</option>
          </select>
        </label>

        {fulfillment === "delivery" && (
          <>
            <label className="block space-y-1">
              <span className="text-sm">CEP</span>
              <input
                value={cep}
                onChange={(e) => setCep(e.target.value)}
                onBlur={onCepBlur}
                inputMode="numeric"
                required
                className="w-full rounded border px-3 py-2"
              />
            </label>
            {estimate && !estimate.covered && (
              <p role="alert" className="text-sm text-red-600">
                Não entregamos nesse CEP.
              </p>
            )}
            {estimate?.covered && (
              <p className="text-sm text-gray-600">
                {estimate.zone_name} · taxa R$ {fee.toFixed(2)} · entrega em ~{estimate.eta_minutes}{" "}
                min
              </p>
            )}
            <label className="block space-y-1">
              <span className="text-sm">Rua</span>
              <input
                value={address.street}
                onChange={(e) => setAddress({ ...address, street: e.target.value })}
                className="w-full rounded border px-3 py-2"
              />
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="block space-y-1">
                <span className="text-sm">Número</span>
                <input
                  value={address.number}
                  onChange={(e) => setAddress({ ...address, number: e.target.value })}
                  className="w-full rounded border px-3 py-2"
                />
              </label>
              <label className="block space-y-1">
                <span className="text-sm">Bairro</span>
                <input
                  value={address.district}
                  onChange={(e) => setAddress({ ...address, district: e.target.value })}
                  className="w-full rounded border px-3 py-2"
                />
              </label>
            </div>
          </>
        )}

        <label className="block space-y-1">
          <span className="text-sm">Observações</span>
          <input
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full rounded border px-3 py-2"
          />
        </label>

        <div className="space-y-1 border-t pt-4 text-sm">
          <div className="flex justify-between">
            <span>Subtotal</span>
            <span className="tabular-nums">R$ {subtotal.toFixed(2)}</span>
          </div>
          <div className="flex justify-between">
            <span>Taxa de entrega</span>
            <span className="tabular-nums">R$ {fee.toFixed(2)}</span>
          </div>
          <div className="flex justify-between font-semibold">
            <span>Total</span>
            <span className="tabular-nums">R$ {total.toFixed(2)}</span>
          </div>
        </div>

        {abaixoMinimo && (
          <p role="alert" className="text-sm text-red-600">
            Pedido mínimo de R$ {minOrder.toFixed(2)}.
          </p>
        )}

        <button
          type="submit"
          disabled={sending || lines.length === 0 || abaixoMinimo || uncovered}
          className="w-full rounded bg-blue-600 px-4 py-3 text-white disabled:opacity-50"
        >
          {sending ? "Enviando…" : "Finalizar pedido"}
        </button>
      </form>
    </main>
  );
}
