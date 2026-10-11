import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { PublicProduct } from "../api/types";
import ModifierDialog from "../components/ModifierDialog";

const product: PublicProduct = {
  id: "p1",
  name: "X-Burger",
  description: null,
  price: "25.00",
  image_url: null,
  category_id: null,
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
    {
      id: "m2",
      group_name: "Extras",
      modifier_name: "Bacon",
      price_delta: "3.00",
      required: false,
      min_selection: 0,
      max_selection: 2,
    },
  ],
};

describe("ModifierDialog", () => {
  it("bloqueia confirmação sem grupo obrigatório", async () => {
    const onConfirm = vi.fn();
    render(<ModifierDialog product={product} onConfirm={onConfirm} onCancel={() => {}} />);
    await userEvent.click(screen.getByRole("button", { name: /adicionar/i }));
    expect(onConfirm).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });

  it("confirma com adicional e soma o delta", async () => {
    const onConfirm = vi.fn();
    render(<ModifierDialog product={product} onConfirm={onConfirm} onCancel={() => {}} />);
    await userEvent.click(screen.getByLabelText(/ao ponto/i));
    await userEvent.click(screen.getByLabelText(/bacon/i));
    await userEvent.click(screen.getByRole("button", { name: /adicionar/i }));
    const arg = onConfirm.mock.calls[0][0];
    expect(arg.unitPrice).toBe("28.00");
    expect(arg.modifiers).toHaveLength(2);
  });
});
