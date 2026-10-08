export interface Insumo {
  id: string;
  name: string;
  category?: string | null;
  base_unit: { id: string; symbol: string };
  average_cost: string;
  minimum_stock: string;
  stock_total: string;
}

export interface Producto {
  id: string;
  name: string;
  description?: string | null;
  price: string;
  active: boolean;
  preparation_time_minutes: number;
}

export interface RecipeItemOut {
  ingredient_id: string;
  name: string;
  unit_symbol: string;
  quantity: string;
  cost: string;
}

export interface RecipeOut {
  product_id: string;
  status: string;
  version: number;
  items: RecipeItemOut[];
  total_cost: string;
}

export interface Margem {
  product_id: string;
  name: string;
  price: string;
  cost: string;
  margin_value: string;
  margin_percent: string | null;
}

export interface PedidoItem {
  product_id: string;
  product_name: string;
  quantity: number;
  unit_price: string;
  total_price: string;
}

export interface Pedido {
  id: string;
  code: string;
  status: string;
  customer_name?: string | null;
  customer_phone?: string | null;
  subtotal: string;
  total: string;
  notes?: string | null;
  created_at: string;
  order_items: PedidoItem[];
}

export interface Evento {
  event_type: string;
  from_status?: string | null;
  to_status?: string | null;
  created_at: string;
  outbox_status?: string | null;
}

export const STATUS_LABEL: Record<string, string> = {
  received: "Recebido",
  confirmed: "Confirmado",
  confirmed_pending_stock: "Confirmado c/ pendência",
  preparing: "Em preparo",
  ready: "Pronto",
  out_for_delivery: "Em entrega",
  delivered: "Entregue",
  completed: "Concluído",
  cancelled: "Cancelado",
  refunded: "Reembolsado",
};
