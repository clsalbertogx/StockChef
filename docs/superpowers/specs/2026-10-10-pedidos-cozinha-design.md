# Spec — Fatia 3: Pedidos + Cozinha (núcleo mínimo)

- **Data:** 2026-10-10
- **Branch:** `feat/pedidos-cozinha`
- **Epic:** E05 — Pedidos e Cozinha (US025, US026, US027, US028, US029, US030)
- **Objetivo:** fechar o loop operacional do restaurante: status do pedido fluindo até concluir, fila de cozinha (KDS) com polling, cancelamento com baixa reversa de estoque, e comanda imprimível — sobre o que já existe (auth/RLS/outbox/catálogo/estoque/compras).

## Autoridade

- Backlog: `docs/backlog-delivery-project.md` (US025–US030).
- DDL (binding): `backend/alembic/versions/0001_initial.py` — tabelas `orders`, `order_items`, `order_events` já criadas e suficientes. **Nenhuma migration nova.**
- Constraints globais persistentes (das fatias 1–2): RLS `app.tenant_id`; `set_tenant(None)` = zero-uuid; `BackgroundTasks` para outbox; `DomainError(code, detail, http_status)` → `{detail, code}`; Decimal sempre com `ROUND_HALF_UP`; ruff line-length 100 (E,F,I,UP,B) + mypy; `require_roles` nas rotas sensíveis; `FOR UPDATE` nas mutações concorrentes; `apply_movement` é o único portal de mutação de `stock_levels` (fora o update guardado do outbox).

## Escopo

Núcleo mínimo. Inclui:

1. **Transições de status** — `PATCH /pedidos/{order_id}/status` (genérico, validado por mapa de transições + roles). `received→confirmed` permanece na rota existente `/confirmar` (idempotente + outbox).
2. **Cancelamento com baixa reversa** — `POST /pedidos/{order_id}/cancelar` com `motivo` obrigatório; reverte estoque de forma idempotente por `StockMovement.idempotency_key`.
3. **Fila de cozinha (KDS)** — `GET /cozinha/fila` (leitura filtrada sobre `orders`); frontend com polling 5s.
4. **Comanda** — página frontend imprimível (`/pedidos/:id/comanda`) com CSS `@media print`.
5. **Registro de eventos** — toda transição grava `OrderEvent` (já existe mecanismo; estende-se).
6. **`OrderOut` enriquecido** — expõe campos que o DDL tem mas o schema atual omite (gap mapeado nas fatias 1–2).

Fora de escopo (defer): WebSocket realtime; "pronto por item" na KDS (status é por pedido — fiel ao DDL); pagamento/refund (`payments`); fluxo de entrega completo (`out_for_delivery`, `deliveries`/`drivers`/`drivers`); impressão server-side; histórico/versões de receita.

## Decisões do usuário (planejamento aprovado)

- US025/US026 tempo real → **polling 5s** + eventos (react-query `refetchInterval`), não WebSocket.
- US030 comanda → **view de impressão no frontend** (`@media print` + `window.print`), não endpoint server-side.
- US029 cancelamento → **cancelar + reverter estoque**, sem tocar em pagamentos.

---

## 1. Modelo de dados

Nenhuma tabela nova, nenhuma migration. Uso fiel ao DDL:

- `orders.status` (check): `received, confirmed, confirmed_pending_stock, preparing, ready, out_for_delivery, delivered, completed, cancelled, refunded`.
- `order_items`: `product_id, quantity, unit_price, total_price, modifiers jsonb, notes, recipe_snapshot`.
- `order_events`: `event_type, from_status, to_status, user_id, payload jsonb`.

## 2. Transições de status

### Mapa de transições legais

| De | Para | Roles |
|---|---|---|
| `received` | `confirmed` | rota `/confirmar` existente (cashier/manager/owner na view) |
| `confirmed` | `confirmed_pending_stock` | (backstage do outbox; inalterado) |
| `confirmed` | `preparing` | kitchen, manager, owner |
| `confirmed_pending_stock` | `preparing` | kitchen, manager, owner |
| `preparing` | `ready` | kitchen, manager, owner |
| `ready` | `delivered` | cashier, manager, owner |
| `ready` | `completed` | cashier, manager, owner |
| `delivered` | `completed` | owner, manager |
| `ready` | `cancelled` | rota `/cancelar` (§3) |
| qualquer-aberto (*) | `cancelled` | rota `/cancelar` (§3) |

(*) aberto = `received, confirmed, confirmed_pending_stock, preparing, ready`.

Transições não listadas → `409 invalid_state`. Nebulosa: `confirmed_pending_stock → preparing` direto (estoque ainda pode estar pendente; a cozinha produz mesmo assim — o flag `confirmed_pending_stock` é de aviso, não de bloqueio). `received → preparing` NÃO é permitida: confirmação (e, logo, disponibilidade) é pré-requisito para entrar na fila.

### Endpoint

**`PATCH /api/v1/pedidos/{order_id}/status`** — `OrderStatusUpdate{status, notes?}`

```
Rule: status in legal map + role in matrix → apply.
If order is None → 404 not_found.
If transition ilegal → 409 invalid_state.
If role sem permissão → 403 forbidden.
```

- Lock `SELECT ... FOR UPDATE` no pedido (concorrência com cancelamento/outbox).
- Grava `OrderEvent(event_type="status.changed", from_status=old, to_status=new, user_id=actor.id, payload={notes?})`.
- **Não toca estoque** (única baixa é confirm → outbox; única reversão é o cancelamento, §3).
- Retorna `OrderOut` (enriquecido, §6).
- Idempotência natural: enviar o mesmo `status` em que o pedido já está → se a transição `X→X` estiver no mapa (ex.: `preparing→preparing`)? Regra: alvo igual ao atual → retorna `OrderOut` atual (no-op), exceto nos estados terminais. Simples: se `payload.status == order.status`, retornar no-op.

### Roles

`require_roles("kitchen", "manager", "owner")` para `confirmed→preparing` etc.; `require_roles("cashier", "manager", "owner")` para `ready→delivered`; `require_roles("owner", "manager")` para `delivered→completed`. A matriz está **no código como dado** (dict `TRANSITIONS: dict[from][to] -> set[roles]`), e o `require_roles` dinâmico por transição.

## 3. Cancelamento com baixa reversa

**`POST /api/v1/pedidos/{order_id}/cancelar`** — `OrderCancel{motivo: str(min_length=1)}`

```
Rule:
1. Lock order FOR UPDATE.
2. order None → 404.
3. order.status in ("delivered","completed","refunded") → 409 invalid_state.
4. order.status == "cancelled" → no-op (retorna OrderOut atual).  # idempotente
5. Reverter estoque (abaixo).
6. order.status = "cancelled"; gravar OrderEvent status.changed (from→cancelled) 
   + OrderEvent event_type="order.cancelled" payload={motivo}.
7. commit; retorna OrderOut.
```

### Reversão de estoque (idempotente)

Para cada `StockMovement` com `reference_type="order"` e `reference_id=order.id` (as linhas `sale` do outbox; inexistentes para `confirmed_pending_stock` sem baixa):

```
apply_movement(db,
    tenant_id=tid, store_id=order.store_id,
    ingredient_id=mov.ingredient_id,
    type_="reversal", quantity=+abs(mov.quantity),
    unit_cost=mov.unit_cost,
    reference_type="order", reference_id=order.id,   # mesma ref da baixa
    reason="Cancelamento de pedido",
    idempotency_key=f"order.reversed:{order.id}:{mov.ingredient_id}",
    user_id=actor.id)
```

- `idempotency_key` única por `(order, ingredient)` → retry do `POST` não duplica reversão (mesma mecânica do recebimento de PO §4 da fatia 2).
- `type_="reversal"` **não recalcula** `average_cost` (só `purchase` o faz — regra da fatia 2 preservada: custo médio ponderado móvel só muda em entrada de compra).
- `quantity` sempre positivo (o movimento de reversão é materialmente um aumento de estoque).
- Bloqueio: o lock do `order` (§3 step 1) serializa concorrentes; `apply_movement` ainda trava `StockLevel` `FOR UPDATE` por linha — mesmo padrão testado da fatia 2.

**Sem outbox**: a reversão é inline e idempotente por chave; não há consumo assíncrono envolvido. Manter simples.

## 4. Fila de cozinha (KDS)

**`GET /api/v1/cozinha/fila`** — reads, `require_roles("kitchen","manager","owner")`.

```
select orders where tenant=... and status in ('confirmed','confirmed_pending_stock','preparing')
order by created_at asc    # FIFO
```

Retorna `list[KitchenOrderOut]`:
- `order_id`, `code`, `status`, `created_at`, `elapsed_minutes` (now - created_at, min 0), `channel`, `fulfillment_type`, `notes`
- `items`: `[{order_item_id, product_name, quantity, notes, modifiers}]`

- `idx_orders_status` cobre a query (tenant, status, created_at). Sem N+1: uma query de items (`.in_(order_ids)`) + join/select de nomes de produto.
- Tenant-scoped via `get_tenant_db` + filtro explícito `tenant_id == tid`.

## 5. Comanda (frontend)

- Rota `/pedidos/:id/comanda` → `ComandaPage`.
- Dados: `GET /pedidos/{order_id}` (`OrderOut` enriquecido).
- Impressão: bloco `@media print` que esconde nav/buttons; botão "Imprimir" chama `window.print()` (print dialog do browser → impressora térmica em papel A4/térmico).
- Conteúdo: código, data/hora, cliente, canal/entrega, itens (nome × qtd × preço), observações, totais, status.
- Sem backend novo, sem lib nova.

## 6. Schema `OrderOut` enriquecido

Campos a adicionar (hoje omitidos em `orders/schemas.py` `_to_out`):

```
fulfillment_type: Literal["delivery","pickup","table"]
channel:          Literal["own_pwa","whatsapp","phone","pos","marketplace_future"]
expected_time:    datetime | None
subtotal, delivery_fee, discount_total, tax_total, total: Decimal(piso 2 casas)
notes:            str | None
```

`OrderItemOut` passa a incluir `notes: str | None` e `modifiers: list` (jsonb, hoje omitidos).

- `OrderOut` já usado pelas rotas existentes (create/get/list/confirm/cancel) — enriquecer o helper `_to_out` beneficia todas sem quebrar contrato (campos novos são aditivos).
- Frontend: tipos em `frontend/src/api/types.ts` atualizados (Decimal → string).

## 7. Frontend

### `FilaKdsPage` (`/cozinha`)

- `useQuery(["cozinha-fila"], fetch, { refetchInterval: 5000 })`.
- Cards por pedido: código, status, tempo decorrido, itens (nome × qtd × obs), canal/entrega.
- Ações (por role): "Iniciar preparo" (`PATCH status=preparing`), "Marcar pronto" (`status=ready`), "Cancelar" (dialog `motivo` → `POST /cancelar`). Invalidate `cozinha-fila` + `pedido` após cada.
- Estados error/empty/loading; `role=alert` em erro; tabular-nums nos valores.

### `ComandaPage` (`/pedidos/:id/comanda`)

- `useQuery(["pedido", id], ...)`; render imprimível; `@media print` oculta UI; botão "Imprimir" (`window.print`).

### `PedidoDetalhePage`

- Já consulta `["pedido"]` e `["pedido-eventos"]`. Adicionar: ações de transição (por role; badge de status alerta para `confirmed_pending_stock`), botão Cancelar (dialog motivo), link "Comanda".
- Chamadas de transição via `PATCH /pedidos/{id}/status`; invalidate queries.

### `PedidosPage`

- Lista com badge de status (já existe `STATUS_LABEL`); polling leve (`refetchInterval 5000`) para acompanhar em tempo real na caixa; link "Comanda".

### Dashboard

- Link para `/cozinha` (Fila) e atalho para pedidos. Padrão existente.

## 8. Testes

### Backend (integration, testcontainers, padrão existente `clean_db`)

1. `test_transicoes.py`
   - `received → preparing` → 409 `invalid_state`.
   - `confirmed → preparing → ready → delivered → completed` flui.
   - `confirmed_pending_stock → preparing` ok.
   - `ready → confirmed` → 409.
   - RBAC: `kitchen` não pode `ready→delivered` (403); `cashier` não pode `confirmed→preparing` (403); `owner` pode tudo no mapa.
   - No-op: `PATCH status=delivered` quando já `delivered` retorna `OrderOut`, não grava evento duplicado.
   - Eventos: toda transição grava `status.changed` com `from/to/user_id`.

2. `test_cancelamento.py`
   - Cancelar `confirmed` reverter: `StockLevel.quantity` volta (soma o movido), `average_cost` **inalterado** — a regra da fatia 2 é que custo médio só muda em `purchase`, e `reversal` não o recalcula.
   - Duplo `POST /cancelar`: segundo é no-op (early-return `status == cancelled` antes de chegar à reversão; a `idempotency_key` protege o caso concorrente de dois handlers simultâneos).
   - Cancelar `confirmed_pending_stock` (sem baixa aplicada): não cria movimento `reversal` espúrio, estoque não muda.
   - `delivered → cancelar` → 409.
   - `motivo` obrigatório (422 sem, 422 vazio).
   - Evento `order.cancelled` gravado com payload `{motivo}`.

3. `test_fila_kds.py`
   - Retorna só `confirmed/confirmed_pending_stock/preparing`, FIFO.
   - Itens com nome/qtd/notes.
   - Cross-tenant: pedido de outro tenant não aparece (404/`[]`).
   - RBAC: role `buyer` → 403.

4. Regressão: suíte completa backend + ruff + mypy limpos.

### Frontend (vitest + fetch stub, padrão existente)

- `fila-kds.test.tsx`: render da fila (fetch stub 2 pedidos), "Iniciar preparo" e "Marcar pronto" chamam `PATCH /pedidos/{id}/status` com body certo; cancelar abre dialog e chama `POST /cancelar` com motivo; estado vazio/erro.
- `pedido.cozinha.test.tsx`: ComandaPage render + `window.print` stubado (botão aciona `print`); Detalhe mostra badge `confirmed_pending_stock` e link comanda.
- Regressão: suíte frontend + typecheck + lint + build.

## 9. Constraints e qualidade

- RLS viola ever: nenhuma query sem filtro de tenant.
- File de eventos: `order_events` é o único trilho de auditoria (não criar tabela nova).
- Sem migration nova; sem nova dependência (backend nem frontend).
- Frontend segue DESIGN.md (estados, a11y, escala 8px, tabular-nums).
- Rodapé do merge: `make lint`/test backend+frontend verdes.

## 10. Riscos / decisões já tomadas

| Decisão | Custo se errada |
|---|---|
| KDS por pedido, não por item (DDL tem status só em `orders`) | "marcar pronto item a item" exige migration `order_items.status` — upgrade path documentado |
| `PATCH /pedidos/{order_id}/status` genérico em vez de endpoints dedicados | menos explícito na API; mapa no código mantém invariantes |
| Cancelamento só com reversão do que foi baixado | cliente(restaurante) espera restock mesmo em `confirmed_pending_stock`? — reversão só existe para o que rolou; correto para a semântica de estoque |
| Polling 5s em vez de WebSocket | latência ~5s vs real; aceito pelo usuário no planejamento |
| `apply_movement` idempotente por `idempotency_key` reutilizado para reversão | mesma mecânica testada do recebimento; sem custo |