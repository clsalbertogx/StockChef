# Spec — Fatia 4: Cardápio Digital e Checkout (E04)

- **Data:** 2026-10-10
- **Branch:** `feat/cardapio-checkout`
- **Epic:** E04 — Cardápio Digital e Checkout (US018, US019, US020, US021, US022, US024)
- **Objetivo:** abrir o funil do cliente final: cardápio público (sem login) acessível por link/QR, busca e filtro por categoria, adicionais/observações, carrinho no PWA, checkout com endereço (ViaCEP) e taxa de entrega por zona, e criação de pedido público que cai direto na operação (KDS/pedidos) já construída nas fatias 1–3.

## Autoridade

- Backlog: `docs/backlog-delivery-project.md` (US018–US022, US024; US023 pagamento fica deferido).
- DDL (binding): `backend/alembic/versions/0001_initial.py` — tabelas `tenants` (slug), `stores`, `categories`, `products`, `product_modifiers`, `zones`, `customers`, `orders`, `order_items`, `payments`, `order_events` **já existem e são suficientes.** **Nenhuma migration nova.**
- Constraints globais persistentes (fatias 1–3): RLS `app.tenant_id`; `set_tenant(None)` = zero-uuid; `DomainError(code, detail, http_status)` → `{detail, code}`; Decimal sempre `ROUND_HALF_UP`; ruff line-length 100 (E,F,I,UP,B) + mypy; `FOR UPDATE` nas mutações concorrentes; `apply_movement` é o único portal de mutação de `stock_levels`; `require_roles` nas rotas internas sensíveis.
- **Nova constraint desta fatia:** **sem dependência nova** (backend e frontend). ViaCEP é chamado via `urllib.request` da stdlib (sem `httpx`/`requests`), atrás de uma função injetável para testes offline.

## Escopo

Núcleo mínimo. Inclui:

1. **Cardápio público por slug** — `GET /public/{slug}/cardapio` (loja + categorias + produtos ativos + adicionais), sem login.
2. **Busca e filtro** — cliente-side (nome/descrição + categoria) no PWA; payload já traz tudo.
3. **Carrinho (PWA)** — quantidade, adicionais, observação, editar/remover; persistido em `localStorage` por slug.
4. **Adicionais e variações** — UI de grupos (obrigatório/opcional, mín/máx) + validação server-side contra `product_modifiers` (US013/US020).
5. **Checkout** — tipo de atendimento (`delivery`/`pickup`), endereço com **ViaCEP**, agendamento opcional, resumo com subtotal/taxa/total.
6. **Taxa de entrega** — cálculo por **zona** (`zones.cep_ranges` + `delivery_fee` + `min_order_value` + `eta_minutes`) (US022); zonas gerenciáveis por gestor.
7. **Criação do pedido público** — `POST /public/{slug}/pedidos` → `orders` (`received`, `channel="own_pwa"`) + `order_items` (modifiers/snapshot) + `payments` (`cash`, `pending`) + `OrderEvent`; idempotente.
8. **Acompanhamento público** — `GET /public/{slug}/pedidos/{code}` para a página de confirmação (US024, polling).

Fora de escopo (defer):
- **US023 — pagamento Pix/cartão** (PSP). Nesta fatia só `cash` (pagar na entrega/retirada), registrado em `payments` como `pending`.
- Notificação e-mail/WhatsApp/push (US024 além da tela de confirmação).
- Imagem/upload de produto (usa `image_url` já existente se preenchido).
- Disponibilidade em tempo real por estoque (payload é active-only; `availability` roda na criação do pedido).
- Cupons/descontos, fidelidade, avaliações, login de cliente.
- ETA dinâmico por rota/distância (usa `zones.eta_minutes` fixo).

## Decisões do usuário (planejamento aprovado)

- Pagamento → **cash apenas** nesta fatia; PSP em momento futuro (US023 deferido).
- Endereço → **integração ViaCEP** obrigatória no checkout.
- Cardápio → **busca + filtro de categoria** e demais funcionalidades do gênero (adicionais, carrinho, taxa de entrega, agendamento, confirmação).

---

## 1. Modelo de dados

Nenhuma tabela nova, nenhuma migration. Uso fiel ao DDL:

- `tenants.slug` (unique) — chave pública da loja na URL.
- `stores`: `delivery_enabled`, `pickup_enabled`, `address` (JSONB), `opening_hours` (JSONB), `status`.
- `categories`: `store_id`, `sort_order`, `active`.
- `products`: `store_id`, `category_id`, `price`, `image_url`, `active`, `preparation_time_minutes`.
- `product_modifiers`: `group_name`, `modifier_name`, `price_delta`, `required`, `min_selection`, `max_selection`, `active`.
- `zones`: `store_id`, `name`, `cep_ranges` (JSONB `[{"start","end"}]`), `delivery_fee`, `min_order_value`, `eta_minutes`, `active`.
- `customers`: `name`, `phone`, `address` (JSONB).
- `orders` / `order_items` / `order_events` / `payments` — como já existem.

Modelos ORM faltantes a criar (apenas mapeamento, sem DDL): `ProductModifier` (catalog), `Zone` (delivery), `Payment` (orders).

## 2. Acesso público e resolução de tenant

### Dependência `get_public_db`

Novo módulo `backend/app/modules/storefront/`:

```
def get_public_db(tenant_slug: str, db: Session = Depends(get_db)) -> Iterator[Session]:
    tenant = db.scalar(select(Tenant).where(Tenant.slug == tenant_slug))   # tenants fora do RLS
    if tenant is None or tenant.status != "active":
        raise DomainError("not_found", "Loja não encontrada.", 404)
    set_tenant(db, tenant.id)                                              # RLS a partir daqui
    yield db
```

- `tenants`/`users` **não** têm RLS (migration §744-754): resolver o slug antes de setar o tenant é seguro.
- Loja: `default_store(db, tid)` (primeira loja `active`); `?store_id=` opcional quando houver mais de uma — **deferido** (hoje 1 loja/tenant).
- Loja inativa (`status != "active"`) → `404 store_not_found`.

### Frontend
Public pages chamam um helper `publicApi()` que **não** envia `Authorization` (evita 401 de token expirado no middleware de tenant, `core/tenant.py`).

## 3. Catálogo público

**`GET /api/v1/public/{slug}/cardapio`** (sem auth):

```
{ 
  "store": {"id","name","phone","address","opening_hours","delivery_enabled","pickup_enabled"},
  "categories": [{"id","name","sort_order"}],          # active, ordenadas por sort_order,name
  "products": [{
      "id","category_id","name","description","price","image_url",
      "preparation_time_minutes",
      "modifiers": [{"id","group_name","name","price_delta","required","min_selection","max_selection"}]
  }]
}
```

- Só `products.active = true` e `categories.active = true` do tenant/loja.
- Sem N+1: 3 queries (categories, products, modifiers por `product_id.in_(...)`) + 1 store.
- Produto sem categoria aparece com `category_id: null` (frontend agrupa em "Outros").
- Sem cálculo de disponibilidade (active-only); a checagem de estoque ocorre no `POST` do pedido.

## 4. Adicionais e variações (modifiers)

Formato canônico gravado em `order_items.modifiers` (JSONB):

```
[{"product_modifier_id":"<uuid>","group_name":"Ponto","name":"Ao ponto",
  "price_delta":"0.00","quantity":1}]
```

Validação server-side (na criação do pedido):
- Cada `product_modifier_id` deve existir, estar `active` e pertencer ao produto do item.
- Agrupa por `group_name`; respeita `min_selection` (ou `required=true` → mínimo 1) e `max_selection` (quando não-nulo).
- Violação → `422 invalid_modifiers` com `extra={"groups":[...]}`.

Preço: `unit_price = product.price + Σ(price_delta × quantity_of_modifier)`; `total_price = unit_price × item.quantity` (deltas embutidos no preço unitário; a comanda imprime os adicionais separados a partir de `modifiers`).

Frontend: `ModifierDialog` — grupos obrigatórios destacados, contador de seleção, delta exibido; bloqueia avançar se `min_selection` não atingido.

## 5. CEP (ViaCEP)

**`GET /api/v1/public/{slug}/cep/{cep}`** (sem auth):

- Normaliza para 8 dígitos; se não tiver 8 dígitos → `422 cep_invalid`.
- Chama o serviço `storefront/viacep.py` — `lookup(cep)` via `urllib.request` (`https://viacep.com.br/ws/{cep}/json/`, `timeout=5`).
- Sucesso → `{"cep","logradouro","bairro","cidade","uf"}`.
- `{"erro": true}` / vazio → `404 cep_not_found`.
- Falha de rede/timeout → `503 cep_unavailable`.
- **Testes**: monkeypatch de `storefront.viacep.lookup` (nunca bate na rede).

## 6. Taxa de entrega (zonas)

### Modelo `Zone` (delivery)
`id, tenant_id, store_id, name, geometry(JSONB={}), cep_ranges(JSONB=[]), delivery_fee, min_order_value, eta_minutes, active`.

`cep_ranges` = `[{"start":"01000000","end":"01999999"}]` (strings numéricas, 8 dígitos, `start <= end`).

### Estimativa pública
**`GET /api/v1/public/{slug}/entrega?cep={cep}`** (sem auth):

```
{"covered": bool, "delivery_fee": Decimal, "min_order_value": Decimal,
 "eta_minutes": int, "zone_name": str|null}
```

- Loja sem zonas `active` → **fallback**: `covered=true, delivery_fee=0, min_order_value=0, eta_minutes=30, zone_name=null` (permite demo sem configuração).
- Com zonas → primeira zona cujo `[start,end]` contém o CEP (comparação lexicográfica numérica); sem match → `covered=false`.

### Administração (interna)
Novo módulo `backend/app/modules/delivery/`:

- `POST /api/v1/zonas` — `require_roles("manager","owner")`; valida cep_ranges.
- `GET /api/v1/zonas` — lista zonas do tenant.
- `PATCH /api/v1/zonas/{zone_id}` — atualiza (inclui `active`).
- (Sem delete; desativação via `active=false`.)

## 7. Criação do pedido público

**`POST /api/v1/public/{slug}/pedidos`**

```jsonc
{
  "items": [{"product_id":"uuid","quantity":2,"notes":"sem cebola",
             "modifiers":[{"product_modifier_id":"uuid","quantity":1}]}],
  "fulfillment_type": "delivery" | "pickup",
  "customer_name": "Ana",
  "customer_phone": "11999999999",
  "delivery_address": {"cep","logradouro","numero","complemento","bairro","cidade","uf"},
  "notes": "tocar a campainha",
  "payment_method": "cash",
  "scheduled_time": "2026-10-10T20:00:00Z" | null,
  "idempotency_key": "uuid" | null
}
```

Regras (ordem):
1. Tenant/loja `active`; `fulfillment_type` permitido por `store.delivery_enabled`/`pickup_enabled` → senão `422 fulfillment_unavailable`.
2. `items` não vazio (`min_length=1`, `quantity>=1`).
3. Cada produto existe, é do tenant/loja e está `active` → senão `404 product_not_found`.
4. Modificadores validados (§4) → senão `422 invalid_modifiers`.
5. Preços **calculados no servidor** (nunca confia no cliente): `subtotal = Σ total_price`.
6. Se `delivery`: `delivery_address` obrigatório (`422 address_required`); CEP coberto (§6) → senão `422 cep_not_covered`; `subtotal >= min_order_value` → senão `422 below_min_order`; `delivery_fee` da zona. Se `pickup`: `delivery_fee = 0`.
7. `total = subtotal + delivery_fee` (Decimal `ROUND_HALF_UP`).
8. `customer` upsert por `phone` (nome/address atualizados).
9. `Order`: `status="received"`, `channel="own_pwa"`, `store_id`, `customer_id`, `subtotal/delivery_fee/total`, `expected_time = scheduled_time or now + (prep_time_max + eta)` (delivery) / `now + prep_time_max` (pickup), `notes`.
10. `OrderItem` com `unit_price` (=base+deltas), `total_price`, `modifiers` canônicos, `notes`, `recipe_snapshot` (reuso `orders.service.recipe_snapshot`).
11. `Payment(provider="cash", method="cash", amount=total, status="pending", idempotency_key=f"order.public:{key}")` (ou gerada se ausente).
12. `OrderEvent(event_type="order.created", to_status="received")`.
13. `commit`.

**Idempotência:** se `idempotency_key` já existe em `payments.idempotency_key` → retorna o pedido existente (`PublicOrderOut`) sem criar nada (proteção contra duplo submit / retry).

Resposta `PublicOrderOut`:
```
{"code","status","fulfillment_type","subtotal","delivery_fee","total",
 "expected_time","created_at","items":[{"product_name","quantity","unit_price","total_price","modifiers"}]}
```

## 8. Acompanhamento público

**`GET /api/v1/public/{slug}/pedidos/{code}`** (sem auth):
- Busca `Order` por `(tenant_id, code)`; `404 not_found` se não existir.
- Retorna `PublicOrderOut` (+ `customer_name`). Sem ids internos sensíveis do tenant.
- Frontend faz polling 5s na tela de confirmação.

## 9. Frontend (PWA)

Rotas **públicas** (fora do `Protected`), em `frontend/src/pages/public/`:

| Rota | Página | Função |
|---|---|---|
| `/cardapio/:slug` | `CardapioPage` | loja, busca, filtro de categoria, lista de produtos, abrir `ModifierDialog`, adicionar ao carrinho |
| `/cardapio/:slug/carrinho` | `CarrinhoPage` | editar quantidade, observação por item, remover, subtotal |
| `/cardapio/:slug/checkout` | `CheckoutPage` | delivery/pickup, ViaCEP, agendamento, resumo (subtotal/taxa/total), confirmar |
| `/cardapio/:slug/pedido/:code` | `PedidoPublicoPage` | confirmação (código, resumo) + status com polling 5s |

- **Carrinho**: `frontend/src/cart/CartContext.tsx` (`useReducer`) + `localStorage["sc_cart:{slug}"]`; ações add/update/remove/clear; recálculo de subtotal com deltas.
- **API pública**: `frontend/src/api/public.ts` — `publicApi<T>(path, init)` sem `Authorization`; tipos `CardapioPublico`, `PublicOrderIn/Out` em `types.ts`.
- **Modifiers**: `frontend/src/components/ModifierDialog.tsx`.
- DESIGN.md: mobile-first, alvos ≥44px, estados loading/erro/vazio, `role="alert"`, `tabular-nums` nos preços, sem cor como único sinal.
- `App.tsx`: adicionar as 4 rotas públicas **antes** do `catch-all`; nada de `Protected`.
- `AuthContext` já tolera sessão ausente (não bloqueia rotas públicas).

Painel interno: link para `/{slug}/cardapio` (pré-visualização) no `DashboardPage`; página `/zonas` (gestor) para CRUD de zonas de entrega.

## 10. Testes

### Backend (integração, testcontainers, padrão `clean_db`)

1. `test_storefront_cardapio.py`
   - Retorna só produtos/categorias `active`; inclui modifiers ativos com `min/max`; slug inexistente/inativo → 404; isolamento cross-tenant.
2. `test_storefront_cep.py` (monkeypatch `viacep.lookup`)
   - CEP válido → endereço; formato inválido → 422; `erro` → 404; exceção → 503.
3. `test_storefront_entrega.py`
   - Sem zonas → covered true/fee 0; zona casando o CEP → fee/min/eta corretos; CEP fora → covered false.
4. `test_storefront_pedido.py`
   - Cria Order `received` + Payment `cash/pending` + OrderItem com modifiers canônicos e snapshot; total = subtotal + fee (ignora preço enviado pelo cliente).
   - Delivery abaixo do `min_order_value` → 422 `below_min_order`; CEP não coberto → 422 `cep_not_covered`; mods fora de mín/máx → 422 `invalid_modifiers`.
   - Idempotência: segundo POST com mesma `idempotency_key` → mesmo pedido, sem novas linhas.
   - Cross-tenant: produto de outro tenant → 404.
5. `test_zonas.py`
   - CRUD + RBAC (cashier/buyer → 403) + validação de `cep_ranges` (start>end → 422).
6. Regressão: suíte completa backend + ruff + mypy limpos.

### Frontend (vitest + fetch stub)

- `cardapio.test.tsx`: render de produtos; busca filtra; filtro de categoria; adicionar ao carrinho.
- `modifiers.test.tsx`: grupo obrigatório bloqueia até selecionar; delta soma no payload.
- `checkout.test.tsx`: ViaCEP preenche endereço; taxa exibida; submit chama `POST /public/{slug}/pedidos` com body correto.
- `pedido-publico.test.tsx`: confirmação renderiza código/total; polling.
- Regressão: suíte frontend + typecheck + lint + build.

## 11. Constraints e qualidade

- RLS viola ever: nenhuma query no `storefront` sem tenant setado (só a resolução do slug roda fora do RLS, em `tenants`).
- Sem migration; sem dependência nova (ViaCEP via stdlib).
- Decimal com `ROUND_HALF_UP`; dinheiro só no servidor.
- Sem vazar ids internos na API pública (usar `code`).
- Frontend segue DESIGN.md.

## 12. Riscos / decisões

| Decisão | Custo se errada |
|---|---|
| `cash` apenas (US023 deferido) | cliente espera Pix/cartão — upgrade path: `payments` + PSP, contrato já modelado |
| ViaCEP via stdlib `urllib` (sem lib) | parsing manual + sem pool; aceitável para volume baixo, função isolada é trocável |
| Fallback de entrega sem zonas (fee 0) | loja sem config cobra R$0; documentado, gestor configura zonas |
| Idempotência ancorada em `payments.idempotency_key` | acopla público a payments; reusa unique existente, sem migration |
| Availability active-only no cardápio | item esgotado ainda aparece; checagem real no POST (422 `insufficient_stock`) |
| Sem rate-limit/anti-bot no público | abuso de criação de pedidos — deferido; nota para fatia de hardening |
| `unit_price` inclui deltas de adicionais | muda semântica de "preço base"; deltas preservados em `modifiers` p/ comanda |
