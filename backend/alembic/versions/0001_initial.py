# ruff: noqa: E501
"""Alembic migration 0001 - schema completo do backlog + RLS + role.

DDL base: docs/backlog-delivery-project.md:300-971 aplicado literalmente, com os
deltas obrigatorios da task:
  1. orders.status check inclui 'confirmed_pending_stock';
  2. tabela refresh_tokens (excluida do RLS);
  3. tabela outbox_events (RLS via tenant_id);
  4. role stockchef_app + RLS/policy + grants ao final.

No downgrade, alem do DROP das 39 tabelas e do DROP ROLE, os grants sao
revogados antes do DROP ROLE: o "grant ... on all tables" do upgrade tambem
atingiu a alembic_version (criada antes do upgrade), que persiste ate aqui e
blocaria o DROP ROLE (DependentObjectsStillExist).
"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
create table plans (
  id uuid primary key default gen_random_uuid(),
  code text not null unique,
  name text not null,
  price_monthly numeric(14,2) not null default 0,
  included_orders integer not null default 0,
  overage_fee numeric(14,2) not null default 0,
  ai_enabled boolean not null default false,
  max_users integer,
  max_stores integer,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table tenants (
  id uuid primary key default gen_random_uuid(),
  plan_id uuid references plans(id),
  name text not null,
  slug text not null unique,
  status text not null default 'active'
    check (status in ('active','trial','suspended','canceled')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table subscriptions (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  plan_id uuid not null references plans(id),
  status text not null default 'active'
    check (status in ('trial','active','past_due','canceled','paused')),
  start_date date not null default current_date,
  end_date date,
  trial_ends_at timestamptz,
  external_subscription_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- =========================================================
-- Users and access
-- =========================================================

create table users (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid references tenants(id) on delete cascade,
  email text not null,
  password_hash text not null,
  name text not null,
  phone text,
  role text not null default 'manager'
    check (role in ('owner','manager','cashier','kitchen','buyer','driver','support','admin_saas')),
  status text not null default 'active'
    check (status in ('pending','active','invited','disabled')),
  mfa_enabled boolean not null default false,
  last_login_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, email)
);

create index idx_users_tenant_status on users(tenant_id, status);

-- =========================================================
-- Stores and customers
-- =========================================================

create table stores (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  name text not null,
  address jsonb not null default '{}'::jsonb,
  phone text,
  email text,
  opening_hours jsonb not null default '{}'::jsonb,
  delivery_enabled boolean not null default true,
  pickup_enabled boolean not null default true,
  status text not null default 'active'
    check (status in ('active','inactive','archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_stores_tenant on stores(tenant_id, status);

create table customers (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  name text,
  phone text,
  email text,
  address jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_customers_tenant_phone on customers(tenant_id, phone);
create index idx_customers_tenant_email on customers(tenant_id, email);

-- =========================================================
-- Suppliers, units, ingredients
-- =========================================================

create table suppliers (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  name text not null,
  document text,
  contact_name text,
  email text,
  phone text,
  lead_time_days integer not null default 1,
  minimum_order_value numeric(14,2) not null default 0,
  status text not null default 'active'
    check (status in ('active','inactive','archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_suppliers_tenant on suppliers(tenant_id, status);

create table units (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  name text not null,
  symbol text not null,
  type text not null default 'count'
    check (type in ('mass','volume','count','length','time','other')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, symbol)
);

create table unit_conversions (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  from_unit_id uuid not null references units(id),
  to_unit_id uuid not null references units(id),
  factor numeric(18,8) not null check (factor > 0),
  comment text,
  created_at timestamptz not null default now(),
  unique (tenant_id, from_unit_id, to_unit_id)
);

create table ingredients (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  name text not null,
  category text,
  base_unit_id uuid not null references units(id),
  default_supplier_id uuid references suppliers(id),
  average_cost numeric(14,4) not null default 0 check (average_cost >= 0),
  minimum_stock numeric(14,4) not null default 0 check (minimum_stock >= 0),
  maximum_stock numeric(14,4) check (maximum_stock is null or maximum_stock >= 0),
  shelf_life_days integer check (shelf_life_days is null or shelf_life_days >= 0),
  waste_factor numeric(6,4) not null default 0 check (waste_factor >= 0 and waste_factor <= 1),
  status text not null default 'active'
    check (status in ('active','inactive','archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, name)
);

create index idx_ingredients_tenant_status on ingredients(tenant_id, status);
create index idx_ingredients_supplier on ingredients(default_supplier_id);

-- =========================================================
-- Stock
-- =========================================================

create table stock_levels (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  store_id uuid not null references stores(id) on delete cascade,
  ingredient_id uuid not null references ingredients(id) on delete cascade,
  quantity numeric(14,4) not null default 0 check (quantity >= 0),
  average_cost numeric(14,4) not null default 0 check (average_cost >= 0),
  last_counted_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (store_id, ingredient_id)
);

create index idx_stock_levels_tenant_store on stock_levels(tenant_id, store_id);
create index idx_stock_levels_low_stock on stock_levels(tenant_id, store_id, quantity);

create table stock_movements (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  store_id uuid not null references stores(id) on delete cascade,
  ingredient_id uuid not null references ingredients(id) on delete cascade,
  type text not null
    check (type in ('purchase','sale','loss','adjustment','transfer','return','reservation','release','reversal')),
  quantity numeric(14,4) not null,
  unit_cost numeric(14,4) not null default 0 check (unit_cost >= 0),
  reference_type text,
  reference_id uuid,
  reason text,
  idempotency_key text unique,
  user_id uuid references users(id),
  created_at timestamptz not null default now()
);

create index idx_stock_movements_lookup
  on stock_movements(tenant_id, store_id, ingredient_id, created_at desc);
create index idx_stock_movements_reference
  on stock_movements(reference_type, reference_id);

-- =========================================================
-- Catalog, products, recipes
-- =========================================================

create table categories (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  store_id uuid references stores(id) on delete cascade,
  name text not null,
  sort_order integer not null default 0,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_categories_tenant_store on categories(tenant_id, store_id, active);

create table products (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  store_id uuid not null references stores(id) on delete cascade,
  category_id uuid references categories(id) on delete set null,
  name text not null,
  description text,
  price numeric(14,2) not null check (price >= 0),
  image_url text,
  active boolean not null default true,
  stock_control_enabled boolean not null default true,
  preparation_time_minutes integer not null default 10,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (store_id, name)
);

create index idx_products_tenant_store_active on products(tenant_id, store_id, active);

create table product_modifiers (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  product_id uuid not null references products(id) on delete cascade,
  group_name text not null,
  modifier_name text not null,
  price_delta numeric(14,2) not null default 0,
  required boolean not null default false,
  min_selection integer not null default 0,
  max_selection integer,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_product_modifiers_product on product_modifiers(product_id, active);

create table recipes (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  product_id uuid not null references products(id) on delete cascade,
  version integer not null default 1,
  status text not null default 'draft'
    check (status in ('draft','active','archived')),
  effective_from timestamptz not null default now(),
  created_by uuid references users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (product_id, version)
);

create index idx_recipes_product_status on recipes(product_id, status);

create table recipe_items (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  recipe_id uuid not null references recipes(id) on delete cascade,
  ingredient_id uuid not null references ingredients(id) on delete restrict,
  quantity numeric(14,4) not null check (quantity > 0),
  unit_id uuid not null references units(id),
  waste_factor numeric(6,4) not null default 0 check (waste_factor >= 0 and waste_factor <= 1),
  optional boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_recipe_items_recipe on recipe_items(recipe_id);
create index idx_recipe_items_ingredient on recipe_items(ingredient_id);

-- =========================================================
-- Delivery zones and drivers
-- =========================================================

create table zones (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  store_id uuid not null references stores(id) on delete cascade,
  name text not null,
  geometry jsonb not null default '{}'::jsonb,
  cep_ranges jsonb not null default '[]'::jsonb,
  delivery_fee numeric(14,2) not null default 0 check (delivery_fee >= 0),
  min_order_value numeric(14,2) not null default 0 check (min_order_value >= 0),
  eta_minutes integer not null default 30,
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_zones_store_active on zones(store_id, active);

create table drivers (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  name text not null,
  phone text not null,
  document text,
  vehicle_type text not null default 'motorcycle'
    check (vehicle_type in ('motorcycle','bicycle','car','van','other')),
  plate text,
  payment_model text not null default 'per_delivery'
    check (payment_model in ('per_delivery','hourly','monthly','fixed_route')),
  status text not null default 'active'
    check (status in ('active','inactive','suspended')),
  rating_average numeric(4,2) not null default 5 check (rating_average >= 0 and rating_average <= 5),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_drivers_tenant_status on drivers(tenant_id, status);

-- =========================================================
-- Orders
-- =========================================================

create table orders (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  store_id uuid not null references stores(id) on delete cascade,
  customer_id uuid references customers(id) on delete set null,
  code text not null,
  status text not null default 'received'
    check (status in ('received','confirmed','confirmed_pending_stock','preparing','ready','out_for_delivery','delivered','completed','cancelled','refunded')),
  channel text not null default 'own_pwa'
    check (channel in ('own_pwa','whatsapp','phone','pos','marketplace_future')),
  fulfillment_type text not null default 'delivery'
    check (fulfillment_type in ('delivery','pickup','table')),
  subtotal numeric(14,2) not null default 0 check (subtotal >= 0),
  delivery_fee numeric(14,2) not null default 0 check (delivery_fee >= 0),
  discount_total numeric(14,2) not null default 0 check (discount_total >= 0),
  tax_total numeric(14,2) not null default 0 check (tax_total >= 0),
  total numeric(14,2) not null default 0 check (total >= 0),
  expected_time timestamptz,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (tenant_id, store_id, code)
);

create index idx_orders_tenant_store_created on orders(tenant_id, store_id, created_at desc);
create index idx_orders_status on orders(tenant_id, status, created_at desc);

create table order_items (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  order_id uuid not null references orders(id) on delete cascade,
  product_id uuid not null references products(id) on delete restrict,
  quantity integer not null check (quantity > 0),
  unit_price numeric(14,2) not null check (unit_price >= 0),
  total_price numeric(14,2) not null check (total_price >= 0),
  modifiers jsonb not null default '[]'::jsonb,
  notes text,
  recipe_snapshot jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index idx_order_items_order on order_items(order_id);
create index idx_order_items_product on order_items(product_id);

create table order_events (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  order_id uuid not null references orders(id) on delete cascade,
  event_type text not null,
  from_status text,
  to_status text,
  user_id uuid references users(id),
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index idx_order_events_order on order_events(order_id, created_at);

-- =========================================================
-- Payments
-- =========================================================

create table payments (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  order_id uuid not null references orders(id) on delete cascade,
  provider text not null,
  provider_payment_id text unique,
  method text not null
    check (method in ('pix','credit_card','debit_card','cash','voucher')),
  amount numeric(14,2) not null check (amount >= 0),
  status text not null default 'pending'
    check (status in ('pending','authorized','captured','failed','refunded','partially_refunded')),
  idempotency_key text unique,
  raw_response jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_payments_order on payments(order_id, status);
create index idx_payments_tenant_provider on payments(tenant_id, provider, created_at desc);

-- =========================================================
-- Deliveries
-- =========================================================

create table deliveries (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  order_id uuid not null unique references orders(id) on delete cascade,
  driver_id uuid references drivers(id) on delete set null,
  status text not null default 'pending'
    check (status in ('pending','assigned','picked_up','in_transit','delivered','failed','canceled')),
  assigned_at timestamptz,
  picked_up_at timestamptz,
  delivered_at timestamptz,
  eta_minutes integer,
  route_hint jsonb not null default '{}'::jsonb,
  occurrence text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_deliveries_tenant_status on deliveries(tenant_id, status, created_at desc);
create index idx_deliveries_driver on deliveries(driver_id, status);

create table proof_of_deliveries (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  delivery_id uuid not null references deliveries(id) on delete cascade,
  type text not null
    check (type in ('photo','signature','pin','customer_confirmation')),
  file_url text,
  received_by text,
  created_at timestamptz not null default now()
);

create index idx_proof_delivery on proof_of_deliveries(delivery_id);

-- =========================================================
-- Purchasing
-- =========================================================

create table purchase_orders (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  store_id uuid not null references stores(id) on delete cascade,
  supplier_id uuid not null references suppliers(id) on delete restrict,
  status text not null default 'draft'
    check (status in ('draft','sent','partially_received','received','canceled')),
  expected_date date,
  total_amount numeric(14,2) not null default 0 check (total_amount >= 0),
  created_by uuid references users(id),
  approved_by uuid references users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_purchase_orders_tenant_status on purchase_orders(tenant_id, status, created_at desc);
create index idx_purchase_orders_supplier on purchase_orders(supplier_id, status);

create table purchase_order_items (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  purchase_order_id uuid not null references purchase_orders(id) on delete cascade,
  ingredient_id uuid not null references ingredients(id) on delete restrict,
  quantity numeric(14,4) not null check (quantity > 0),
  unit_id uuid not null references units(id),
  unit_cost numeric(14,4) not null check (unit_cost >= 0),
  received_quantity numeric(14,4) not null default 0 check (received_quantity >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_po_items_po on purchase_order_items(purchase_order_id);
create index idx_po_items_ingredient on purchase_order_items(ingredient_id);

create table goods_receipts (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  purchase_order_id uuid references purchase_orders(id) on delete set null,
  supplier_id uuid not null references suppliers(id) on delete restrict,
  received_at timestamptz not null default now(),
  received_by uuid references users(id),
  invoice_number text,
  notes text,
  created_at timestamptz not null default now()
);

create index idx_goods_receipts_supplier on goods_receipts(supplier_id, received_at desc);
create index idx_goods_receipts_po on goods_receipts(purchase_order_id);

create table goods_receipt_items (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  goods_receipt_id uuid not null references goods_receipts(id) on delete cascade,
  purchase_order_item_id uuid references purchase_order_items(id) on delete set null,
  ingredient_id uuid not null references ingredients(id) on delete restrict,
  quantity numeric(14,4) not null check (quantity > 0),
  unit_cost numeric(14,4) not null check (unit_cost >= 0),
  lot_code text,
  expires_at date,
  created_at timestamptz not null default now()
);

create index idx_gri_receipt on goods_receipt_items(goods_receipt_id);
create index idx_gri_ingredient on goods_receipt_items(ingredient_id);

-- =========================================================
-- Losses and inventory counts
-- =========================================================

create table losses (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  store_id uuid not null references stores(id) on delete cascade,
  ingredient_id uuid not null references ingredients(id) on delete restrict,
  quantity numeric(14,4) not null check (quantity > 0),
  cost numeric(14,2) not null default 0 check (cost >= 0),
  reason text not null default 'other'
    check (reason in ('expiration','cooking_error','damage','theft','return','spoilage','other')),
  occurred_at timestamptz not null default now(),
  registered_by uuid references users(id),
  created_at timestamptz not null default now()
);

create index idx_losses_tenant_store on losses(tenant_id, store_id, occurred_at desc);
create index idx_losses_ingredient on losses(ingredient_id, occurred_at desc);

create table inventory_counts (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  store_id uuid not null references stores(id) on delete cascade,
  status text not null default 'open'
    check (status in ('open','closed','canceled')),
  started_by uuid references users(id),
  started_at timestamptz not null default now(),
  closed_at timestamptz,
  notes text
);

create index idx_inventory_counts_store on inventory_counts(store_id, status, started_at desc);

create table inventory_count_items (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  inventory_count_id uuid not null references inventory_counts(id) on delete cascade,
  ingredient_id uuid not null references ingredients(id) on delete restrict,
  system_quantity numeric(14,4) not null default 0,
  counted_quantity numeric(14,4),
  difference numeric(14,4),
  adjusted boolean not null default false,
  note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_ici_count on inventory_count_items(inventory_count_id);
create index idx_ici_ingredient on inventory_count_items(ingredient_id);

-- =========================================================
-- Forecasts, recommendations, agents
-- =========================================================

create table forecasts (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  store_id uuid not null references stores(id) on delete cascade,
  entity_type text not null check (entity_type in ('product','ingredient')),
  entity_id uuid not null,
  horizon_date date not null,
  predicted_quantity numeric(14,4) not null check (predicted_quantity >= 0),
  confidence_interval_low numeric(14,4),
  confidence_interval_high numeric(14,4),
  model_version text not null,
  created_at timestamptz not null default now(),
  unique (tenant_id, store_id, entity_type, entity_id, horizon_date, model_version)
);

create index idx_forecasts_lookup on forecasts(tenant_id, store_id, entity_type, entity_id, horizon_date);

create table agent_runs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  agent_type text not null
    check (agent_type in ('stock','pricing','delivery','support','finance','onboarding','data_quality')),
  trigger text not null
    check (trigger in ('schedule','user_prompt','event')),
  input_summary text,
  tools_used jsonb not null default '[]'::jsonb,
  output_summary text,
  status text not null default 'running'
    check (status in ('running','succeeded','failed','blocked')),
  started_at timestamptz not null default now(),
  finished_at timestamptz
);

create index idx_agent_runs_tenant on agent_runs(tenant_id, agent_type, started_at desc);

create table recommendations (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  store_id uuid references stores(id) on delete cascade,
  type text not null
    check (type in ('purchase','pricing','waste','delivery','menu','cashflow')),
  entity_id uuid,
  title text not null,
  message text not null,
  explanation jsonb not null default '{}'::jsonb,
  suggested_action jsonb not null default '{}'::jsonb,
  status text not null default 'pending'
    check (status in ('pending','accepted','rejected','expired','executed')),
  confidence numeric(5,4) check (confidence is null or (confidence >= 0 and confidence <= 1)),
  created_by_agent_run_id uuid references agent_runs(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_recommendations_tenant_status on recommendations(tenant_id, status, created_at desc);
create index idx_recommendations_type on recommendations(tenant_id, type, status);

-- =========================================================
-- Audit and usage
-- =========================================================

create table audit_logs (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid references tenants(id) on delete set null,
  user_id uuid references users(id) on delete set null,
  agent_run_id uuid references agent_runs(id) on delete set null,
  action text not null,
  entity_type text not null,
  entity_id uuid,
  before jsonb,
  after jsonb,
  ip inet,
  created_at timestamptz not null default now()
);

create index idx_audit_logs_tenant on audit_logs(tenant_id, created_at desc);
create index idx_audit_logs_entity on audit_logs(entity_type, entity_id);

create table usage_metrics (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  metric text not null,
  period_start date not null,
  period_end date not null,
  value numeric(18,4) not null default 0,
  created_at timestamptz not null default now(),
  unique (tenant_id, metric, period_start, period_end)
);

create index idx_usage_metrics_tenant on usage_metrics(tenant_id, metric, period_start desc);

-- =========================================================
-- Delta task 3: refresh_tokens (sem RLS)
-- =========================================================

create table refresh_tokens (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid references tenants(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  token_hash text not null unique,
  expires_at timestamptz not null,
  revoked_at timestamptz,
  created_at timestamptz not null default now()
);

-- =========================================================
-- Delta task 3: outbox_events (com RLS via tenant_id)
-- =========================================================

create table outbox_events (
  id uuid primary key default gen_random_uuid(),
  tenant_id uuid not null references tenants(id) on delete cascade,
  event_type text not null,
  payload jsonb not null default '{}'::jsonb,
  idempotency_key text not null unique,
  status text not null default 'pending'
    check (status in ('pending','processing','processed','failed')),
  attempts integer not null default 0,
  last_error text,
  created_at timestamptz not null default now(),
  processed_at timestamptz
);
create index idx_outbox_events_pending on outbox_events(status, created_at);

    """)
    op.execute("""
do $$
begin
  if not exists (select 1 from pg_roles where rolname = 'stockchef_app') then
    create role stockchef_app login password 'stockchef_app';
  end if;
end$$;

-- Habilita RLS + policy única em toda tabela com tenant_id (exceto tabelas de identidade)
do $$
declare
  t record;
begin
  for t in
    select c.table_name
    from information_schema.columns c
    where c.table_schema = 'public'
      and c.column_name = 'tenant_id'
      and c.table_name not in ('plans', 'tenants', 'users', 'refresh_tokens')
  loop
    execute format('alter table %I enable row level security;', t.table_name);
    execute format(
      'create policy tenant_isolation on %I using (
         tenant_id = current_setting(''app.tenant_id'', true)::uuid
       ) with check (
         tenant_id = current_setting(''app.tenant_id'', true)::uuid
       );',
      t.table_name
    );
  end loop;
end$$;

grant select, insert, update, delete on all tables in schema public to stockchef_app;
grant usage, select on all sequences in schema public to stockchef_app;

    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS usage_metrics, audit_logs, recommendations, agent_runs, forecasts, inventory_count_items, inventory_counts, losses, goods_receipt_items, goods_receipts, purchase_order_items, purchase_orders, proof_of_deliveries, deliveries, payments, order_events, outbox_events, order_items, orders, drivers, zones, recipe_items, recipes, product_modifiers, products, categories, stock_movements, stock_levels, ingredients, unit_conversions, units, suppliers, customers, stores, refresh_tokens, users, subscriptions, tenants, plans CASCADE;")
    op.execute(
        "revoke select, insert, update, delete on all tables in schema public from stockchef_app;"
    )
    op.execute("revoke usage, select on all sequences in schema public from stockchef_app;")
    op.execute("DROP ROLE IF EXISTS stockchef_app;")
