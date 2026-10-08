# Design: Fatia 2 — Estoque operacional + Compras (núcleo mínimo)

**Data:** 2026-10-08
**Status:** Aprovado (design em chat) — aguardando revisão do usuário
**Escopo:** próximo ciclo de implementação sobre o `main` (fatia 1 entregue). Substitui Fase 4 parcial do plano (`docs/plan-delivery-project.md:1024-1060`) com o corte de escopo acordado (núcleo mínimo).

## 1. Objetivo

Fechar o ciclo analítico do estoque sobre o que já existe (RLS + auth + catalog + pedidos + outbox + admin web):

> entrada de compra → custo médio ponderado móvel → perda → inventário/ajuste → alerta de mínimo → sugestão de compra por regra → pedido de compra com aprovação → recebimento parcial

Sem FEFO/lote, sem contagem mobile, sem histórico de preço por fornecedor, sem ML. Focado em tornar o estoque **confiável** e a sugestão de compra **explicável** (PRD §8.6).

## 2. Decisões aprovadas (em chat)

| Decisão | Escolha |
|---|---|
| Estrutura | Módulos novos `inventory` + `purchasing` (monólito modular, abordagem A) — espelha `identity/catalog/orders` |
| Migration nova | **Nenhuma** — todas as tabelas necessárias já existem no `0001` (original do backlog DDL) |
| Custo médio | Ponderado móvel, cálculos com `Decimal`, arredondamento `ROUND_HALF_UP`, escala `Numeric(14,4)` |
| Sugestão de compra | Regra determinística (consumo médio 14d + lead time + mínimo + segurança), com `motivo` explicável — sem ML |
| Aprovação de PO | Role `owner`/`manager` obrigatória; sem limiar configurável (sem tabela nova) |
| Frontend | Admin web (padrões existentes: TanStack Query, `api()`, shadcn/Tailwind, a11y) — sem PWA mobile |
| Erros | `DomainError {detail, code}` (handler global já existente) + validação pydantic (`Literal`, `ge=0`) |

## 3. Modelos (mapeiam o DDL do `0001` — sem alterar banco)

Acompanhe no `backlog-delivery-project.md:300-1013` (mesma fonte do `0001_initial.py`). Novos models ORM (não novas tabelas):

**`inventory/models.py`:**
- `Loss` → `losses` (tenant_id, store_id, ingredient_id, quantity>0, cost, reason `check (expiration|cooking_error|damage|theft|return|spoilage|other)`, occurred_at, registered_by)
- `InventoryCount` → `inventory_counts` (status `open|closed|canceled`, started_by, started_at, closed_at, notes)
- `InventoryCountItem` → `inventory_count_items` (system_quantity, counted_quantity, difference, adjusted, note)

**`purchasing/models.py`:**
- `PurchaseOrder` → `purchase_orders` (status `draft|sent|partially_received|received|canceled`, expected_date, total_amount, created_by, approved_by)
- `PurchaseOrderItem` → `purchase_order_items` (quantity>0, unit_id, unit_cost, received_quantity)
- `GoodsReceipt` → `goods_receipts` (purchase_order_id nullable, supplier_id not null, received_at, received_by, invoice_number, notes)
- `GoodsReceiptItem` → `goods_receipt_items` (purchase_order_item_id nullable, ingredient_id, quantity>0, unit_cost, lot_code/expires_at **não usados no núcleo** — mapeados como mapeáveis, deixados NULL)
- `Supplier` — já existe em `catalog/models.py`; reutilizar.

`stock_movements` já existente (com `idempotency_key` unique e `check type`). `stock_levels` (store_id, ingredient_id) unique — já existente.

## 4. Regras de negócio

### 4.1 Custo médio ponderado móvel (entrada de compra)
Ao receber quantidade `Q` por custo unitário `C` do insumo com estado atual `(qty_atual, avg_atual)`:

```
novo_avg = (qty_atual * avg_atual + Q * C) / (qty_atual + Q)
```

- Arredondar para 4 casas (`ROUND_HALF_UP`), gravar em `stock_levels.average_cost`.
- Aplicado **somente** em movimentos `type=purchase`. Vendas usam o custo vigente (já é o comportamento atual do `sale`); perdas usam custo vigente; ajustes de inventário **não** alteram `average_cost`.
- `Q = 0` ou estado vazio → `novo_avg = C`.
- Cálculo feito no `inventory/service.weighted_average_cost` (função pura, testável unit).

### 4.2 Movimento de estoque idempotente
`apply_movement(db, *, tenant_id, store_id, ingredient_id, type, quantity, unit_cost, reference_type, reference_id, reason=None, idempotency_key=None)`:
- Insere `stock_movements`; `quantity` negativo para saídas (loss/adjustment negativo), positivo para entradas (purchase).
- Atualiza `stock_levels.quantity` com `UPDATE ... SET quantity = stock_levels.quantity + :q WHERE store_id=:s AND ingredient_id=:i`.
- Se `idempotency_key` já existe → no-op (retorna movimento existente), nunca duplica.
- Para `type=purchase`: também recalcula `average_cost` (4.1).
- Para `adjustment`: mantém `average_cost`.
- Rejeitar com `DomainError("invalid_stock_operation", 409)` se a saída levaria `quantity < 0` (saldo nunca negativo, `check quantity>=0` no DDL).

### 4.3 Perda (`POST /perdas`)
- Body `{store_id?, ingredient_id, quantity>0, reason, occurred_at?}`; `store_id` default = `default_store`.
- Valida motivo contra o `check` do DDL (Literal).
- Grava `losses` (cost = custo vigente no `stock_levels.average_cost`), chama `apply_movement(type=loss, quantity=-qtd, reference_type="loss", reference_id=loss.id)`.
- Permissão: `require_roles("owner","manager","buyer")`.

### 4.4 Inventário (`/inventarios`)
- `POST /inventarios` → abre contagem: cria `InventoryCount(store_id, status=open)` + popula `InventoryCountItem` para todos insumos ativos da loja com `system_quantity = stock_total` (snapshot).
- `POST /inventarios/{id}/itens` (PUT-like) → grava `counted_quantity` para os itens enviados (valida pertencer à contagem e `status=open`).
- `POST /inventarios/{id}/fechar` → só em `open`; calcula `difference = counted - system` (default 0 quando não contado), gera `apply_movement(type=adjustment, quantity=difference)` por item com `|difference|>0`, marca `adjusted=true`, `status=closed`, `closed_at=now`. Permissão `owner`/`manager`.
- `GET /inventarios` e `GET /inventarios/{id}` para leitura.

### 4.5 Alerta de mínimo (`GET /estoque/critico`)
- Retorna insumos ativos com `stock_total (agregado) < minimum_stock`, cada um com `{ingredient_id, nome, unit_symbol, stock_total, minimum_stock}` ordenado por maior déficit.

### 4.6 Sugestão de compra (`GET /compras/sugestao`)
Por insumo ativo da loja:
```
consumo_diario = Σ sales(últimos 14 dias) / 14
estoque_seguranca = minimum_stock * 0.2
sugerido = máximo(0, minimum_stock + lead_time_fornecedor * consumo_diario + estoque_seguranca − stock_total)
sugerido = mínimo(sugerido, maximum_stock − stock_total) se maximum_stock definido
```
- `lead_time_fornecedor` = `ingredient.default_supplier_id → suppliers.lead_time_days` (default 1 se sem fornecedor).
- Cada linha: `{ingredient_id, nome, unit_symbol, stock_total, minimum_stock, consumo_diario, lead_time_days, suggested_quantity, reason}` — *reason* em pt-BR explicável (ex.: "Consumo 0,42 kg/dia + lead time 1d + mínimo 5 kg: sugere 3,2 kg").
- Filtra `suggested_quantity > 0`. Sem consumo → 0 (não sugere).
- `GET /compras/sugestao?dias=14` (default 14).

### 4.7 Pedido de compra — lifecycle
- `POST /fornecedores` + `GET /fornecedores` + `GET /fornecedores/{id}` — CRUD mínimo p/ suportar PO (US009 núcleo).
- `POST /compras` → cria `PurchaseOrder(status=draft, expected_date?, total_amount = Σ qtd×custo)` + itens `{ingredient_id, quantity, unit_cost}` (valida insumo ativo + `quantity>0`).
- `POST /compras/{id}/aprovar` → `draft→sent`; grava `approved_by`; só `owner`/`manager` (dependência `require_roles`). Status inválido → `DomainError("invalid_state", 409)`.
- `POST /compras/{id}/cancelar` → `draft|sent→canceled`; idempotente (já cancelado → no-op).
- `POST /compras/{id}/recebimento` → body `{items:[{purchase_order_item_id, received_quantity>0, unit_cost}], invoice_number?, notes?}`; só em `sent|partially_received`; valida `received_quantity ≤ quantity − received_quantity` (não ultrapassar); cria `GoodsReceipt` + `GoodsReceiptItem` (referenciando `purchase_order_item_id`); para cada item chama `apply_movement(type=purchase, quantity=received, unit_cost=item.unit_cost, reference_type="goods_receipt", reference_id=receipt.id, idempotency_key="receipt:{receipt_id}:{po_item_id}")` → atualiza `received_quantity` e custo médio; se todos `received_quantity ≥ quantity` → status `received`, senão `partially_received`. Permissão `owner`/`manager`/`buyer`.
- Idempotência de recebimento: `idempotency_key` unique por `receipt`+item impede duplicar dentro de um recebimento; recebimentos concorrentes do mesmo PO são serializados por `with_for_update` no PO + checagem de saldo de `received_quantity`.

**Contratos de erro:** status inválido → 409 `invalid_state`; perda/ajuste gerando saldo negativo → 409 `invalid_stock_operation`; item não existe/não pertence → 404 `not_found`; role insuficiente → 403 `forbidden`; validação pydantic → 422 `validation_error`.

## 5. RBAC (dependência nova)
`app/core/deps.require_roles(*roles)` → usa `Actor.role` (já no JWT) — se `actor.role not in roles` → `DomainError("forbidden", ..., 403)`. Não altera o fluxo atual das rotas existentes.

## 6. Rotas / contrato (prefixo `/api/v1`)

`inventory`:
- `GET /estoque/critico`
- `GET /estoque/movimentos?ingredient_id&tipo&limit=50`
- `POST /perdas`
- `POST /inventarios`
- `POST /inventarios/{id}/itens`
- `POST /inventarios/{id}/fechar`
- `GET /inventarios` · `GET /inventarios/{id}`

`purchasing`:
- `GET|POST /fornecedores` · `GET /fornecedores/{id}`
- `GET /compras/sugestao`
- `POST /compras` · `GET /compras` · `GET /compras/{id}`
- `POST /compras/{id}/aprovar` · `POST /compras/{id}/cancelar` · `POST /compras/{id}/recebimento`

Todos `get_tenant_db` (RLS). Nova rota de `GET /fornecedores` reusa o model `Supplier` (já no metadata).

## 7. Frontend (admin web)

- `api/types.ts`: `LossIn`, `InventoryCount{Item}`, `CriticalStock`, `PurchaseSuggestion`, `PurchaseOrder{Item}`, `GoodsReceiptIn`, `Supplier` (já parte do shape de insumos).
- Páginas novas (`App.tsx` + `DashboardPage` nav: Insumos/Produtos/Pedidos **+ Estoque/Inventário/Compras/Fornecedores**):
  - `EstoquePage` (`/estoque`): lista insumos com badge de crítico (abaixo mínimo), registrar perda (dialog), lista de últimos movimentos.
  - `InventarioPage` (`/inventario`): abrir contagem, editar contagens, fechar (com confirmação).
  - `ComprasPage` (`/compras`): abas `Sugestão` (gerar e mostrar com motivo + "criar PO") e `Pedidos de compra` (lista, criar, status).
  - `ComprasDetalhePage` (`/compras/:id`): itens, aprovar, receber parcial/total.
  - `FornecedoresPage` (`/fornecedores`): listar + criar.
- Padrões: TanStack Query (`queryKey` por rota), `api()`, `role="alert"` em erros, tabelas com `th scope`, labels programáticos, `Number()`/`toFixed`, botão de destaque `bg-green-700`+disabled durante pending.
- Sem novas deps de runtime.

## 8. Testes

**Backend (integração, testcontainers — padrão dos módulos atuais):**
1. Custo médio: entrada 10u a 10 → 10u a 12 → `average_cost=11,00`; venda não altera custo.
2. Perda: cria `losses` + movimento `loss` negativo; motivo inválido → 422; saldo insuficiente → 409.
3. Inventário: abre (snapshot), conta menor → fechar gera `adjustment` negativo + `quantity` atualizado + `difference` correto.
4. Sugestão: venda 14d → consumo diário; lead time + mínimo + segurança → `suggested_quantity` correto e `reason` não-vazio; `maximum_stock` respeitado; sem vendas → 0.
5. PO: criar `draft`; aprovar sem role owner → 403; aprovar → `sent`; receber parcial → `partially_received` + movimento `purchase` + custo médio; receber resto → `received`; recebimento em excesso → 409; 2º recebimento do mesmo receipt idempotente.
6. Crítico: abaixo do mínimo aparece; acima não.
7. Fornecedores: criar/listar/get; name obrigatório.

**Frontend (Vitest):** 1 teste por fluxo novo — `InventarioPage` abre+fecha; `ComprasDetalhePage` recebe parcial e reflete status (estilo `pedido.test.tsx`).

## 9. Critérios de saída

- [ ] `make lint` (ruff+mypy+biome) verde; `make test` verde (43+ testes existentes + novos).
- [ ] Custo médio ponderado correto após 2 entradas (unit + integração).
- [ ] Sugestão de compra explicável (unit + integração) respeitando mínimo/lead time/máximo.
- [ ] PO com aprovação por role e recebimento parcial idempotente.
- [ ] Perda e inventário auditados (movimentos + tabelas).
- [ ] Frontend: 4 páginas novas navegáveis com o mesmo padrão a11y; testes Vitest verdes.
- [ ] Nenhuma migration nova; schema inalterado (validator de drift do `env.py` mantido).

## 10. Fora de escopo (explícito — p/ próximas fatias)

- FEFO / lote / validade (`goods_receipt_items.lot_code|expires_at` ignorados), alerta de vencimento (US045 parcial)
- Contagem mobile/offline (US043)
- Histórico de preço por fornecedor (US051)
- Aprovação por limiar configurável (US049) — role fixa por enquanto
- Delivery, pagamentos, analytics avançado, agentes de IA
```