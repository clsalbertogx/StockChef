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
  notes?: string | null;
  modifiers?: unknown[];
}

export interface Pedido {
  id: string;
  code: string;
  status: string;
  customer_name?: string | null;
  customer_phone?: string | null;
  channel: string;
  fulfillment_type: string;
  expected_time?: string | null;
  subtotal: string;
  delivery_fee: string;
  discount_total: string;
  tax_total: string;
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

export interface Supplier {
  id: string;
  name: string;
  lead_time_days: number;
  status: "active" | "inactive" | "archived";
}

export interface LossIn {
  ingredient_id: string;
  quantity: string;
  reason: string;
}

export interface CriticalStockItem {
  ingredient_id: string;
  name: string;
  unit_symbol: string;
  stock_total: string;
  minimum_stock: string;
}

export interface MovementOut {
  id: string;
  ingredient_id: string;
  type: string;
  quantity: string;
  unit_cost: string;
  reason?: string | null;
  created_at: string;
}

export interface InventoryCountItemOut {
  ingredient_id: string;
  system_quantity: string;
  counted_quantity?: string | null;
  difference?: string | null;
  adjusted: boolean;
}

export interface InventoryCount {
  id: string;
  store_id: string;
  status: string;
  started_at: string;
  closed_at?: string | null;
  items: InventoryCountItemOut[];
}

export interface PurchaseSuggestion {
  ingredient_id: string;
  name: string;
  unit_symbol: string;
  stock_total: string;
  minimum_stock: string;
  consumption_daily: string;
  lead_time_days: number;
  suggested_quantity: string;
  reason: string;
}

export interface PurchaseOrderItem {
  id: string;
  ingredient_id: string;
  quantity: string;
  unit_cost: string;
  received_quantity: string;
}

export interface PurchaseOrder {
  id: string;
  supplier_id: string;
  status: string;
  expected_date?: string | null;
  total_amount: string;
  created_at: string;
  items: PurchaseOrderItem[];
}

export const PO_STATUS_LABEL: Record<string, string> = {
  draft: "Rascunho",
  sent: "Enviado",
  partially_received: "Recebido parcial",
  received: "Recebido",
  canceled: "Cancelado",
};

export const COUNT_STATUS_LABEL: Record<string, string> = {
  open: "Aberta",
  closed: "Fechada",
};

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

export interface KdsItem {
  order_item_id: string;
  product_name: string;
  quantity: number;
  notes?: string | null;
  modifiers: unknown[];
}

export interface KdsOrder {
  order_id: string;
  code: string;
  status: string;
  channel: string;
  fulfillment_type: string;
  notes?: string | null;
  created_at: string;
  elapsed_minutes: number;
  items: KdsItem[];
}

export interface PublicModifier {
  id: string;
  group_name: string;
  modifier_name: string;
  price_delta: string;
  required: boolean;
  min_selection: number;
  max_selection: number | null;
}

export interface PublicProduct {
  id: string;
  name: string;
  description?: string | null;
  price: string;
  image_url?: string | null;
  category_id?: string | null;
  preparation_time_minutes: number;
  modifiers: PublicModifier[];
}

export interface PublicCategory {
  id: string;
  name: string;
  sort_order: number;
}

export interface PublicStore {
  id: string;
  name: string;
  delivery_enabled: boolean;
  pickup_enabled: boolean;
}

export interface PublicTenant {
  name: string;
  slug: string;
}

export interface PublicMenu {
  tenant: PublicTenant;
  store: PublicStore;
  categories: PublicCategory[];
  products: PublicProduct[];
}

export interface DeliveryEstimate {
  covered: boolean;
  zone_name: string | null;
  delivery_fee: string;
  min_order_value: string;
  eta_minutes: number;
}

export interface PublicOrderItem {
  product_name: string;
  quantity: number;
  unit_price: string;
  total_price: string;
  modifiers: { id: string; group_name: string; modifier_name: string; price_delta: string }[];
}

export interface PublicOrder {
  code: string;
  status: string;
  fulfillment_type: string;
  subtotal: string;
  delivery_fee: string;
  total: string;
  eta_minutes: number | null;
  created_at: string;
  items: PublicOrderItem[];
}

export interface Zone {
  id: string;
  store_id: string;
  name: string;
  cep_ranges: { start: string; end: string }[];
  delivery_fee: string;
  min_order_value: string;
  eta_minutes: number;
  active: boolean;
}

export interface ZoneCreate {
  name: string;
  cep_start: string;
  cep_end: string;
  delivery_fee: string;
  min_order_value: string;
  eta_minutes: number;
}
