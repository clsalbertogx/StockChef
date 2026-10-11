# Pedidos + Cozinha (Fatia 3) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fechar o loop operacional do restaurante sobre o que já existe — transições de status do pedido, cancelamento com baixa reversa idempotente, fila de cozinha (KDS) com polling e comanda imprimível.

**Architecture:** Tudo no módulo `orders` existente (sem módulo novo, sem migration, sem dependência nova). A fila KDS é uma leitura filtrada sobre `orders`. A reversão de estoque reusa `apply_movement`/`ensure_stock_level` de `inventory` (idempotência por `StockMovement.idempotency_key`). Frontend: nova página `FilaKdsPage`, `ComandaPage`, e enriquecimento das páginas de pedidos; polling via react-query.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + Postgres (RLS) no backend; React + TypeScript + Tailwind + TanStack Query + shadcn/ui no frontend; pytest + testcontainers e vitest + testing-library.

**Spec:** `docs/superpowers/specs/2026-10-10-pedidos-cozinha-design.md` (leia junto; o plano argumenta a partir dela).

## Global Constraints

- **Sem migration nova**; sem tabela nova; mapear fielmente o DDL `0001_initial.py`/`0002`.
- **Sem dependência nova** (backend nem frontend).
- RLS `app.tenant_id` em toda operação; `get_tenant_db` obrigatório nas rotas; `require_roles` / checagem de papel nas rotas sensíveis.
- `DomainError(code, detail, http_status)` → `{detail, code}`. 404 `not_found`; 409 `invalid_state`; 403 `forbidden`; 422 de validação é do pydantic.
- Decimal sempre `ROUND_HALF_UP`; `stock_levels` só muda via `apply_movement` (fora o update guardado do outbox).
- `SELECT ... FOR UPDATE` nas mutações concorrentes de pedido.
- Lint: `cd backend && ../.venv/bin/ruff check .` (line-length 100, E,F,I,UP,B) e `../.venv/bin/mypy .` limpos. Testes backend: `../.venv/bin/pytest -q`.
- Frontend: `cd frontend && npm run typecheck && npm run lint && npm test && npm run build` verdes.
- Frontend segue `DESIGN.md`: estados loading/error/empty, `role="alert"` (erro) / `role="status"` (sucesso), `tabular-nums` em números, enums traduzidos pt-BR.
- Testes de backend: testcontainers Postgres, `clean_db` por teste (TRUNCATE), helpers locais; role do usuário é alterada via SQL e o token re-emitido por `/api/v1/auth/login`.

---

### Task 1: Enriquecer `OrderOut` / `OrderItemOut`

Os schemas atuais omitem campos que o DDL tem (gap mapeado). Toda a feature seguinte (KDS, comanda, detalhe) depende deles.

**Files:**
- Modify: `backend/app/modules/orders/schemas.py`
- Modify: `backend/app/modules/orders/routes.py` (`_to_out`, linhas 68-98)
- Test: `backend/app/tests/integration/test_order_out_enriquecido.py`

**Interfaces:**
- Consumes: `orders/models.py` (`Order`, `OrderItem`), rota `POST/GET /pedidos` existente.
- Produces: `OrderOut` com `fulfillment_type`, `channel`, `expected_time`, `delivery_fee`, `discount_total`, `tax_total`; `OrderItemOut` com `notes`, `modifiers`. Consumido por Tasks 2, 3, 4 (respostas) e Task 6 (frontend).

- [ ] **Step 1: Escrever o teste que falha**

```python
# backend/app/tests/integration/test_order_out_enriquecido.py
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _setup(slug: str) -> dict[str, str]:
    r = client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": f"{slug}@x.com",
        "password": "senha-segura", "name": "Dono",
    })
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_order_out_expoe_campos_do_ddl() -> None:
    h = _setup("enriq")
    ing = client.post("/api/v1/insumos", headers=h, json={
        "name": "Pao", "base_unit_symbol": "kg", "average_cost": "5.00", "initial_stock": "10.00",
    }).json()["id"]
    prod = client.post(
        "/api/v1/produtos", headers=h, json={"name": "X-Tudo", "price": "18.00"}
    ).json()["id"]
    client.post(f"/api/v1/produtos/{prod}/ficha-tecnica", headers=h, json={
        "items": [{"ingredient_id": ing, "quantity": "0.050"}],
    })
    order = client.post(
        "/api/v1/pedidos", headers=h,
        json={"items": [{"product_id": prod, "quantity": 1}],
              "fulfillment_type": "table", "channel": "pos", "notes": "sem cebola"},
    ).json()
    got = client.get(f"/api/v1/pedidos/{order['id']}", headers=h).json()

    assert got["fulfillment_type"] == "table"
    assert got["channel"] == "pos"
    assert got["delivery_fee"] == "0.00"
    assert got["discount_total"] == "0.00"
    assert got["tax_total"] == "0.00"
    assert got["expected_time"] is None
    # item traz notes/modifiers (jsonb), mesmo que default
    assert got["order_items"][0]["notes"] is None
    assert got["order_items"][0]["modifiers"] == []
```

- [ ] **Step 2: Rodar o teste e ver falhar**

Run: `cd backend && ../.venv/bin/pytest -q app/tests/integration/test_order_out_enriquecido.py`
Expected: FAIL com `KeyError: 'fulfillment_type'` (campo ausente no JSON).

- [ ] **Step 3: Implementar**

Em `backend/app/modules/orders/schemas.py`, substituir `OrderItemOut` e `OrderOut`:

```python
class OrderItemOut(BaseModel):
    product_id: UUID
    product_name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    notes: str | None = None
    modifiers: list = []


class OrderOut(BaseModel):
    id: UUID
    code: str
    status: str
    customer_name: str | None
    customer_phone: str | None
    channel: str
    fulfillment_type: str
    expected_time: datetime | None
    subtotal: Decimal
    delivery_fee: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total: Decimal
    notes: str | None
    created_at: datetime
    order_items: list[OrderItemOut]
```

Em `backend/app/modules/orders/routes.py`, no `_to_out`, preencher os novos campos do item e do pedido:

```python
        out_items.append(
            OrderItemOut(
                product_id=it.product_id,
                product_name=product.name,
                quantity=it.quantity,
                unit_price=it.unit_price,
                total_price=it.total_price,
                notes=it.notes,
                modifiers=it.modifiers or [],
            )
        )
    cust = db.get(Customer, order.customer_id) if order.customer_id else None
    return OrderOut(
        id=order.id,
        code=order.code,
        status=order.status,
        customer_name=cust.name if cust else None,
        customer_phone=cust.phone if cust else None,
        channel=order.channel,
        fulfillment_type=order.fulfillment_type,
        expected_time=order.expected_time,
        subtotal=order.subtotal,
        delivery_fee=order.delivery_fee,
        discount_total=order.discount_total,
        tax_total=order.tax_total,
        total=order.total,
        notes=order.notes,
        created_at=order.created_at,
        order_items=out_items,
    )
```

- [ ] **Step 4: Rodar o teste e garantir verde**

Run: `cd backend && ../.venv/bin/pytest -q app/tests/integration/test_order_out_enriquecido.py app/tests/integration/test_pedidos.py app/tests/integration/test_confirmacao.py`
Expected: PASS (regressão de pedidos intacta).

- [ ] **Step 5: Lint/types**

Run: `cd backend && ../.venv/bin/ruff check . && ../.venv/bin/mypy .`
Expected: limpos.

- [ ] **Step 6: Commit**

```bash
git add backend/app/modules/orders/schemas.py backend/app/modules/orders/routes.py backend/app/tests/integration/test_order_out_enriquecido.py
git commit -m "feat(orders): enriquece OrderOut com campos do DDL"
```

---

### Task 2: Transições de status — `PATCH /pedidos/{order_id}/status`

**Files:**
- Modify: `backend/app/modules/orders/schemas.py` (adicionar `OrderStatusUpdate`)
- Modify: `backend/app/modules/orders/routes.py` (mapa `TRANSITIONS` + rota)
- Test: `backend/app/tests/integration/test_status.py`

**Interfaces:**
- Consumes: `_to_out`/`OrderOut` (Task 1); `current_actor` (`app.core.deps`), `Actor` (`app.core.tenant`).
- Produces: `PATCH /api/v1/pedidos/{order_id}/status`, body `OrderStatusUpdate{status, notes?}` → `OrderOut`; grava `OrderEvent(event_type="status.changed", from_status, to_status, user_id, payload)`. Consumido pelas Tasks 4 (KDS UI) e 6 (frontend).

Mapa legal (dado no código):

```python
TRANSITIONS: dict[tuple[str, str], frozenset[str]] = {
    ("confirmed", "preparing"): frozenset({"kitchen", "manager", "owner"}),
    ("confirmed_pending_stock", "preparing"): frozenset({"kitchen", "manager", "owner"}),
    ("preparing", "ready"): frozenset({"kitchen", "manager", "owner"}),
    ("ready", "delivered"): frozenset({"cashier", "manager", "owner"}),
    ("ready", "completed"): frozenset({"cashier", "manager", "owner"}),
    ("delivered", "completed"): frozenset({"owner", "manager"}),
}
```

Regras: alvo igual ao atual → no-op (retorna `OrderOut`, sem evento). Transição fora do mapa → 409 `invalid_state`. Papel fora do conjunto → 403 `forbidden`. Não toca estoque.

- [ ] **Step 1: Escrever o teste que falha**

```python
# backend/app/tests/integration/test_status.py
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _register(slug: str) -> str:
    r = client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": f"{slug}@x.com",
        "password": "senha-segura", "name": "Dono",
    })
    assert r.status_code == 201, r.text
    return slug


def _login(slug: str, role: str) -> dict[str, str]:
    from sqlalchemy import text

    from app.core.db import SessionLocal

    db = SessionLocal()
    try:
        db.execute(
            text("UPDATE users SET role = :r WHERE email = :e"),
            {"r": role, "e": f"{slug}@x.com"},
        )
        db.commit()
    finally:
        db.close()
    r = client.post("/api/v1/auth/login", json={
        "tenant_slug": slug, "email": f"{slug}@x.com", "password": "senha-segura",
    })
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _order(slug: str, h_owner: dict[str, str]) -> str:
    ing = client.post("/api/v1/insumos", headers=h_owner, json={
        "name": "Pao", "base_unit_symbol": "kg", "average_cost": "5.00", "initial_stock": "10.00",
    }).json()["id"]
    prod = client.post(
        "/api/v1/produtos", headers=h_owner, json={"name": "X", "price": "10.00"}
    ).json()["id"]
    client.post(f"/api/v1/produtos/{prod}/ficha-tecnica", headers=h_owner, json={
        "items": [{"ingredient_id": ing, "quantity": "0.050"}],
    })
    return client.post(
        "/api/v1/pedidos", headers=h_owner, json={"items": [{"product_id": prod, "quantity": 1}]}
    ).json()["id"]


def _patch(h: dict[str, str], oid: str, to: str):
    return client.patch(f"/api/v1/pedidos/{oid}/status", headers=h, json={"status": to})


def test_received_nao_vai_para_preparing_409() -> None:
    slug = _register("st-recv")
    owner = _login(slug, "owner")
    oid = _order(slug, owner)
    r = _patch(owner, oid, "preparing")
    assert r.status_code == 409
    assert r.json()["code"] == "invalid_state"


def test_fluxo_completo_confirma_prepara_pronto_entrega_conclui() -> None:
    slug = _register("st-fluxo")
    owner = _login(slug, "owner")
    oid = _order(slug, owner)
    assert client.post(f"/api/v1/pedidos/{oid}/confirmar", headers=owner).status_code == 200

    kitchen = _login(slug, "kitchen")
    assert _patch(kitchen, oid, "preparing").json()["status"] == "preparing"
    assert _patch(kitchen, oid, "ready").json()["status"] == "ready"

    cashier = _login(slug, "cashier")
    assert _patch(cashier, oid, "delivered").json()["status"] == "delivered"
    assert _patch(owner, oid, "completed").json()["status"] == "completed"

    events = client.get(f"/api/v1/pedidos/{oid}/eventos", headers=owner).json()["events"]
    changed = [e for e in events if e["event_type"] == "status.changed"]
    assert [e["to_status"] for e in changed] == [
        "confirmed", "preparing", "ready", "delivered", "completed",
    ]


def test_confirmed_pending_stock_pode_preparar() -> None:
    from sqlalchemy import text

    from app.core.db import SessionLocal

    slug = _register("st-pend")
    owner = _login(slug, "owner")
    oid = _order(slug, owner)
    db = SessionLocal()
    try:
        db.execute(
            text("UPDATE orders SET status = 'confirmed_pending_stock' WHERE id = :i"),
            {"i": oid},
        )
        db.commit()
    finally:
        db.close()
    kitchen = _login(slug, "kitchen")
    assert _patch(kitchen, oid, "preparing").status_code == 200


def test_ready_nao_volta_para_confirmed_409() -> None:
    slug = _register("st-ready")
    owner = _login(slug, "owner")
    oid = _order(slug, owner)
    client.post(f"/api/v1/pedidos/{oid}/confirmar", headers=owner)
    kitchen = _login(slug, "kitchen")
    _patch(kitchen, oid, "preparing")
    _patch(kitchen, oid, "ready")
    r = _patch(kitchen, oid, "confirmed")
    assert r.status_code == 409


def test_noop_mesmo_status_nao_grava_evento() -> None:
    slug = _register("st-noop")
    owner = _login(slug, "owner")
    oid = _order(slug, owner)
    client.post(f"/api/v1/pedidos/{oid}/confirmar", headers=owner)
    before = len(client.get(f"/api/v1/pedidos/{oid}/eventos", headers=owner).json()["events"])
    r = _patch(owner, oid, "confirmed")
    assert r.status_code == 200 and r.json()["status"] == "confirmed"
    after = len(client.get(f"/api/v1/pedidos/{oid}/eventos", headers=owner).json()["events"])
    assert after == before


def test_rbac_transicoes() -> None:
    slug = _register("st-rbac")
    owner = _login(slug, "owner")
    oid = _order(slug, owner)
    client.post(f"/api/v1/pedidos/{oid}/confirmar", headers=owner)

    cashier = _login(slug, "cashier")
    assert _patch(cashier, oid, "preparing").status_code == 403  # cashier não prepara

    kitchen = _login(slug, "kitchen")
    assert _patch(kitchen, oid, "preparing").status_code == 200
    _patch(kitchen, oid, "ready")
    assert _patch(kitchen, oid, "delivered").status_code == 403  # kitchen não entrega
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && ../.venv/bin/pytest -q app/tests/integration/test_status.py`
Expected: FAIL — 405 (rota inexistente) / asserções de status.

- [ ] **Step 3: Implementar**

Em `schemas.py` (`orders`), adicionar:

```python
OrderStatus = Literal[
    "received", "confirmed", "confirmed_pending_stock", "preparing", "ready",
    "out_for_delivery", "delivered", "completed", "cancelled", "refunded",
]


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    notes: str | None = None
```

Em `routes.py`, ajustar imports e adicionar o mapa + rota:

```python
from datetime import UTC, datetime

from app.core.deps import current_actor, get_tenant_db
from app.core.tenant import Actor
from app.modules.orders.schemas import (
    OrderCreate, OrderItemOut, OrderOut, OrderStatusUpdate,
)
```

```python
TRANSITIONS: dict[tuple[str, str], frozenset[str]] = {
    ("confirmed", "preparing"): frozenset({"kitchen", "manager", "owner"}),
    ("confirmed_pending_stock", "preparing"): frozenset({"kitchen", "manager", "owner"}),
    ("preparing", "ready"): frozenset({"kitchen", "manager", "owner"}),
    ("ready", "delivered"): frozenset({"cashier", "manager", "owner"}),
    ("ready", "completed"): frozenset({"cashier", "manager", "owner"}),
    ("delivered", "completed"): frozenset({"owner", "manager"}),
}


@router.patch("/pedidos/{order_id}/status")
def update_order_status(
    order_id: UUID,
    payload: OrderStatusUpdate,
    actor: Actor = Depends(current_actor),  # noqa: B008
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> OrderOut:
    tid = _tenant_id(db)
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise DomainError("not_found", "Pedido não encontrado.", status.HTTP_404_NOT_FOUND)
    if payload.status == order.status:
        return _to_out(db, order)  # no-op idempotente
    roles = TRANSITIONS.get((order.status, payload.status))
    if roles is None:
        raise DomainError(
            "invalid_state", "Transição de status inválida.", status.HTTP_409_CONFLICT
        )
    if actor.role not in roles:
        raise DomainError("forbidden", "Permissão insuficiente.", status.HTTP_403_FORBIDDEN)
    old = order.status
    order.status = payload.status
    order.updated_at = datetime.now(UTC)
    db.add(
        OrderEvent(
            tenant_id=tid,
            order_id=order.id,
            event_type="status.changed",
            from_status=old,
            to_status=payload.status,
            user_id=actor.id,
            payload={"notes": payload.notes} if payload.notes else {},
        )
    )
    db.commit()
    return _to_out(db, order)
```

- [ ] **Step 4: Rodar e garantir verde**

Run: `cd backend && ../.venv/bin/pytest -q app/tests/integration/test_status.py`
Expected: PASS.

- [ ] **Step 5: Lint/types**

Run: `cd backend && ../.venv/bin/ruff check . && ../.venv/bin/mypy .`
Expected: limpos.

- [ ] **Step 6: Commit**

```bash
git add backend/app/modules/orders/schemas.py backend/app/modules/orders/routes.py backend/app/tests/integration/test_status.py
git commit -m "feat(orders): transicoes de status com RBAC e auditoria"
```

---

### Task 3: Cancelamento com baixa reversa

**Files:**
- Modify: `backend/app/modules/orders/schemas.py` (`OrderCancel`)
- Modify: `backend/app/modules/orders/routes.py` (rota `POST /pedidos/{order_id}/cancelar`)
- Test: `backend/app/tests/integration/test_cancelamento.py`

**Interfaces:**
- Consumes: `apply_movement`, `ensure_stock_level` (`app.modules.inventory.service`); `StockMovement` (`app.modules.catalog.models`); `OrderOut`/`_to_out` (Task 1).
- Produces: `POST /api/v1/pedidos/{order_id}/cancelar`, body `OrderCancel{motivo}` → `OrderOut`; grava `StockMovement(type="reversal", idempotency_key=f"order.reversed:{order.id}:{ingredient_id}")` e `OrderEvent(order.cancelled)`.

Regras: estados permitidos `received|confirmed|confirmed_pending_stock|preparing|ready`; já `cancelled` → no-op; `delivered|completed|refunded` → 409. Papel `owner|manager|cashier`. Reverte **só** `StockMovement(type="sale", reference_type="order", reference_id=order.id)` existentes (logo `confirmed_pending_stock` sem baixa não cria reversão espúria).

- [ ] **Step 1: Escrever o teste que falha**

```python
# backend/app/tests/integration/test_cancelamento.py
from decimal import ROUND_HALF_UP, Decimal

from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.core.db import SessionLocal, set_tenant
from app.main import app
from app.modules.catalog.models import StockLevel
from app.modules.identity.models import Tenant

client = TestClient(app)


def _setup(slug: str) -> tuple[dict[str, str], str]:
    r = client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": f"{slug}@x.com",
        "password": "senha-segura", "name": "Dono",
    })
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}, slug


def _tid(slug: str) -> str:
    db = SessionLocal()
    try:
        return str(db.scalar(select(Tenant.id).where(Tenant.slug == slug)))
    finally:
        db.close()


def _ing(h, name, avg, stock) -> str:
    return client.post("/api/v1/insumos", headers=h, json={
        "name": name, "base_unit_symbol": "kg", "average_cost": avg, "initial_stock": stock,
    }).json()["id"]


def _prod(h, ing) -> str:
    p = client.post(
        "/api/v1/produtos", headers=h, json={"name": "X", "price": "10.00"}
    ).json()["id"]
    client.post(f"/api/v1/produtos/{p}/ficha-tecnica", headers=h, json={
        "items": [{"ingredient_id": ing, "quantity": "0.030"}],
    })
    return p


def _stock(ing: str, slug: str) -> str:
    db = SessionLocal()
    try:
        set_tenant(db, _tid(slug))
        q = db.scalar(select(StockLevel.quantity).where(StockLevel.ingredient_id == ing))
        assert q is not None
        return str(Decimal(q).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    finally:
        db.close()


def _cost(ing: str, slug: str) -> str:
    db = SessionLocal()
    try:
        set_tenant(db, _tid(slug))
        c = db.scalar(select(StockLevel.average_cost).where(StockLevel.ingredient_id == ing))
        assert c is not None
        return str(Decimal(c).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    finally:
        db.close()


def _types(ing: str, slug: str) -> list[str]:
    db = SessionLocal()
    try:
        set_tenant(db, _tid(slug))
        return [r[0] for r in db.execute(text(
            "SELECT type FROM stock_movements WHERE ingredient_id = :i ORDER BY created_at"
        ), {"i": ing}).all()]
    finally:
        db.close()


def test_cancelar_reverte_estoque_e_preserva_custo_medio() -> None:
    h, slug = _setup("cancela")
    ing = _ing(h, "Queijo", "45.00", "3.00")
    pid = _prod(h, ing)
    o = client.post("/api/v1/pedidos", headers=h, json={
        "items": [{"product_id": pid, "quantity": 2}]}).json()
    client.post(f"/api/v1/pedidos/{o['id']}/confirmar", headers=h)
    assert _stock(ing, slug) == "2.94"
    assert _cost(ing, slug) == "45.00"

    r = client.post(f"/api/v1/pedidos/{o['id']}/cancelar", headers=h, json={"motivo": "cliente desistiu"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "cancelled"
    assert _stock(ing, slug) == "3.00"               # revertido
    assert _cost(ing, slug) == "45.00"               # custo médio intacto
    assert _types(ing, slug) == ["sale", "reversal"]

    events = client.get(f"/api/v1/pedidos/{o['id']}/eventos", headers=h).json()["events"]
    cancel = next(e for e in events if e["event_type"] == "order.cancelled")
    assert cancel["to_status"] == "cancelled"


def test_cancelar_duas_vezes_e_idempotente() -> None:
    h, slug = _setup("canc-idem")
    ing = _ing(h, "Queijo", "45.00", "3.00")
    pid = _prod(h, ing)
    o = client.post("/api/v1/pedidos", headers=h, json={
        "items": [{"product_id": pid, "quantity": 1}]}).json()
    client.post(f"/api/v1/pedidos/{o['id']}/confirmar", headers=h)
    client.post(f"/api/v1/pedidos/{o['id']}/cancelar", headers=h, json={"motivo": "x"})
    first = _stock(ing, slug)
    r = client.post(f"/api/v1/pedidos/{o['id']}/cancelar", headers=h, json={"motivo": "x"})
    assert r.status_code == 200
    assert _stock(ing, slug) == first
    assert _types(ing, slug) == ["sale", "reversal"]  # não duplica reversão


def test_cancelar_pending_stock_nao_cria_reversao() -> None:
    h, slug = _setup("canc-pend")
    ing = _ing(h, "Queijo", "45.00", "0.05")
    pid = _prod(h, ing)
    o = client.post("/api/v1/pedidos", headers=h, json={
        "items": [{"product_id": pid, "quantity": 1}]}).json()
    db = SessionLocal()
    try:
        set_tenant(db, _tid(slug))
        db.execute(text("UPDATE stock_levels SET quantity = 0.02 WHERE ingredient_id = :i"), {"i": ing})
        db.commit()
    finally:
        db.close()
    client.post(f"/api/v1/pedidos/{o['id']}/confirmar", headers=h)   # vira pending
    r = client.post(f"/api/v1/pedidos/{o['id']}/cancelar", headers=h, json={"motivo": "sem estoque"})
    assert r.status_code == 200
    assert _types(ing, slug) == []                    # nada foi baixado → nada revertido
    assert _stock(ing, slug) == "0.02"


def test_cancelar_delivered_409_e_motivo_obrigatorio() -> None:
    h, slug = _setup("canc-term")
    ing = _ing(h, "Queijo", "45.00", "3.00")
    pid = _prod(h, ing)
    o = client.post("/api/v1/pedidos", headers=h, json={
        "items": [{"product_id": pid, "quantity": 1}]}).json()
    db = SessionLocal()
    try:
        set_tenant(db, _tid(slug))
        db.execute(text("UPDATE orders SET status='delivered' WHERE id=:i"), {"i": o["id"]})
        db.commit()
    finally:
        db.close()
    assert client.post(f"/api/v1/pedidos/{o['id']}/cancelar", headers=h,
                       json={"motivo": "x"}).status_code == 409
    # motivo vazio → 422 (validação)
    o2 = client.post("/api/v1/pedidos", headers=h, json={
        "items": [{"product_id": pid, "quantity": 1}]}).json()
    assert client.post(f"/api/v1/pedidos/{o2['id']}/cancelar", headers=h,
                       json={"motivo": ""}).status_code == 422
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && ../.venv/bin/pytest -q app/tests/integration/test_cancelamento.py`
Expected: FAIL — 404/405 (rota inexistente).

- [ ] **Step 3: Implementar**

Em `schemas.py`:

```python
class OrderCancel(BaseModel):
    motivo: str = Field(min_length=1)
```

Em `routes.py`, imports e rota:

```python
from app.modules.catalog.models import Product, StockMovement, Store
from app.modules.inventory.service import apply_movement, ensure_stock_level
from app.modules.orders.schemas import (
    OrderCancel, OrderCreate, OrderItemOut, OrderOut, OrderStatusUpdate,
)

CANCELLABLE = ("received", "confirmed", "confirmed_pending_stock", "preparing", "ready")
CANCEL_BLOCKED = ("delivered", "completed", "refunded")


@router.post("/pedidos/{order_id}/cancelar")
def cancel_order(
    order_id: UUID,
    payload: OrderCancel,
    actor: Actor = Depends(current_actor),  # noqa: B008
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> OrderOut:
    tid = _tenant_id(db)
    order = db.scalar(select(Order).where(Order.id == order_id).with_for_update())
    if order is None:
        raise DomainError("not_found", "Pedido não encontrado.", status.HTTP_404_NOT_FOUND)
    if order.status == "cancelled":
        return _to_out(db, order)  # idempotente
    if order.status in CANCEL_BLOCKED or order.status not in CANCELLABLE:
        raise DomainError(
            "invalid_state", "Pedido não pode ser cancelado nesse estado.",
            status.HTTP_409_CONFLICT,
        )
    if actor.role not in ("owner", "manager", "cashier"):
        raise DomainError("forbidden", "Permissão insuficiente.", status.HTTP_403_FORBIDDEN)

    sales = db.scalars(
        select(StockMovement).where(
            StockMovement.reference_type == "order",
            StockMovement.reference_id == order.id,
            StockMovement.type == "sale",
        )
    ).all()
    for mov in sales:
        ensure_stock_level(
            db, tenant_id=tid, store_id=order.store_id, ingredient_id=mov.ingredient_id
        )
        apply_movement(
            db,
            tenant_id=tid,
            store_id=order.store_id,
            ingredient_id=mov.ingredient_id,
            type_="reversal",
            quantity=abs(mov.quantity),
            unit_cost=mov.unit_cost,
            reference_type="order",
            reference_id=order.id,
            reason="Cancelamento de pedido",
            idempotency_key=f"order.reversed:{order.id}:{mov.ingredient_id}",
            user_id=actor.id,
        )

    old = order.status
    order.status = "cancelled"
    order.updated_at = datetime.now(UTC)
    db.add(OrderEvent(tenant_id=tid, order_id=order.id, event_type="status.changed",
                      from_status=old, to_status="cancelled", user_id=actor.id))
    db.add(OrderEvent(tenant_id=tid, order_id=order.id, event_type="order.cancelled",
                      from_status=old, to_status="cancelled", user_id=actor.id,
                      payload={"motivo": payload.motivo}))
    db.commit()
    return _to_out(db, order)
```

- [ ] **Step 4: Rodar e garantir verde**

Run: `cd backend && ../.venv/bin/pytest -q app/tests/integration/test_cancelamento.py`
Expected: PASS.

- [ ] **Step 5: Lint/types**

Run: `cd backend && ../.venv/bin/ruff check . && ../.venv/bin/mypy .`
Expected: limpos.

- [ ] **Step 6: Commit**

```bash
git add backend/app/modules/orders/schemas.py backend/app/modules/orders/routes.py backend/app/tests/integration/test_cancelamento.py
git commit -m "feat(orders): cancelamento com baixa reversa idempotente"
```

---

### Task 4: Fila de cozinha — `GET /cozinha/fila`

**Files:**
- Modify: `backend/app/modules/orders/schemas.py` (`KitchenItemOut`, `KitchenOrderOut`)
- Modify: `backend/app/modules/orders/routes.py` (rota)
- Test: `backend/app/tests/integration/test_fila_kds.py`

**Interfaces:**
- Consumes: `require_roles` (`app.core.deps`); `Order`, `OrderItem`; `Product`.
- Produces: `GET /api/v1/cozinha/fila` → `list[KitchenOrderOut]` (`order_id, code, status, channel, fulfillment_type, notes, created_at, elapsed_minutes, items[{order_item_id, product_name, quantity, notes, modifiers}]`). Consumido pela Task 5.

- [ ] **Step 1: Escrever o teste que falha**

```python
# backend/app/tests/integration/test_fila_kds.py
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.db import SessionLocal
from app.main import app

client = TestClient(app)


def _register(slug: str) -> str:
    r = client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": f"{slug}@x.com",
        "password": "senha-segura", "name": "Dono",
    })
    assert r.status_code == 201, r.text
    return slug


def _login(slug: str, role: str) -> dict[str, str]:
    db = SessionLocal()
    try:
        db.execute(text("UPDATE users SET role = :r WHERE email = :e"),
                   {"r": role, "e": f"{slug}@x.com"})
        db.commit()
    finally:
        db.close()
    r = client.post("/api/v1/auth/login", json={
        "tenant_slug": slug, "email": f"{slug}@x.com", "password": "senha-segura"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _order(slug, h, name) -> str:
    ing = client.post("/api/v1/insumos", headers=h, json={
        "name": f"ing-{name}", "base_unit_symbol": "kg", "average_cost": "5.00", "initial_stock": "10.00",
    }).json()["id"]
    prod = client.post("/api/v1/produtos", headers=h, json={
        "name": name, "price": "10.00"}).json()["id"]
    client.post(f"/api/v1/produtos/{prod}/ficha-tecnica", headers=h, json={
        "items": [{"ingredient_id": ing, "quantity": "0.050"}]})
    return client.post("/api/v1/pedidos", headers=h, json={
        "items": [{"product_id": prod, "quantity": 3}]}).json()["id"]


def test_fila_lista_apenas_em_producao_e_traz_itens() -> None:
    slug = _register("kds-a")
    h = _login(slug, "owner")
    o_conf = _order(slug, h, "Hamburguer")
    client.post(f"/api/v1/pedidos/{o_conf}/confirmar", headers=h)
    o_recv = _order(slug, h, "Pizza")  # fica em received — não entra na fila

    kitchen = _login(slug, "kitchen")
    resp = client.get("/api/v1/cozinha/fila", headers=kitchen)
    assert resp.status_code == 200, resp.text
    codes = [o["order_id"] for o in resp.json()]
    assert o_conf in codes and o_recv not in codes
    row = next(o for o in resp.json() if o["order_id"] == o_conf)
    assert row["items"][0]["product_name"] == "Hamburguer"
    assert row["items"][0]["quantity"] == 3
    assert row["elapsed_minutes"] >= 0


def test_fila_fifo() -> None:
    slug = _register("kds-fifo")
    h = _login(slug, "owner")
    first = _order(slug, h, "A")
    second = _order(slug, h, "B")
    for oid in (first, second):
        client.post(f"/api/v1/pedidos/{oid}/confirmar", headers=h)
    kitchen = _login(slug, "kitchen")
    ids = [o["order_id"] for o in client.get("/api/v1/cozinha/fila", headers=kitchen).json()]
    assert ids.index(first) < ids.index(second)


def test_fila_isola_tenant() -> None:
    slug_a = _register("kds-ta")
    ha = _login(slug_a, "owner")
    oa = _order(slug_a, ha, "Hamburguer")
    client.post(f"/api/v1/pedidos/{oa}/confirmar", headers=ha)

    slug_b = _register("kds-tb")
    hb = _login(slug_b, "kitchen")
    codes = [o["order_id"] for o in client.get("/api/v1/cozinha/fila", headers=hb).json()]
    assert oa not in codes


def test_fila_rbac_buyer_403() -> None:
    slug = _register("kds-rbac")
    buyer = _login(slug, "buyer")
    assert client.get("/api/v1/cozinha/fila", headers=buyer).status_code == 403
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && ../.venv/bin/pytest -q app/tests/integration/test_fila_kds.py`
Expected: FAIL — 404/405.

- [ ] **Step 3: Implementar**

Em `schemas.py`:

```python
class KitchenItemOut(BaseModel):
    order_item_id: UUID
    product_name: str
    quantity: int
    notes: str | None = None
    modifiers: list = []


class KitchenOrderOut(BaseModel):
    order_id: UUID
    code: str
    status: str
    channel: str
    fulfillment_type: str
    notes: str | None
    created_at: datetime
    elapsed_minutes: int
    items: list[KitchenItemOut]
```

Em `routes.py`, imports + rota:

```python
from app.core.deps import current_actor, get_tenant_db, require_roles
from app.modules.orders.schemas import (
    KitchenItemOut, KitchenOrderOut, OrderCancel, OrderCreate,
    OrderItemOut, OrderOut, OrderStatusUpdate,
)

KDS_STATUSES = ("confirmed", "confirmed_pending_stock", "preparing")


@router.get("/cozinha/fila")
def kitchen_queue(
    actor: Actor = Depends(require_roles("kitchen", "manager", "owner")),  # noqa: B008
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> list[KitchenOrderOut]:
    tid = _tenant_id(db)
    orders = db.scalars(
        select(Order)
        .where(Order.tenant_id == tid, Order.status.in_(KDS_STATUSES))
        .order_by(Order.created_at.asc())
    ).all()
    if not orders:
        return []
    order_ids = [o.id for o in orders]
    rows = db.execute(
        select(OrderItem, Product.name)
        .join(Product, Product.id == OrderItem.product_id)
        .where(OrderItem.order_id.in_(order_ids))
    ).all()
    by_order: dict[UUID, list[KitchenItemOut]] = {}
    for item, product_name in rows:
        by_order.setdefault(item.order_id, []).append(
            KitchenItemOut(
                order_item_id=item.id,
                product_name=product_name,
                quantity=item.quantity,
                notes=item.notes,
                modifiers=item.modifiers or [],
            )
        )
    now = datetime.now(UTC)
    return [
        KitchenOrderOut(
            order_id=o.id,
            code=o.code,
            status=o.status,
            channel=o.channel,
            fulfillment_type=o.fulfillment_type,
            notes=o.notes,
            created_at=o.created_at,
            elapsed_minutes=max(0, int((now - o.created_at).total_seconds() // 60)),
            items=by_order.get(o.id, []),
        )
        for o in orders
    ]
```

- [ ] **Step 4: Rodar e garantir verde**

Run: `cd backend && ../.venv/bin/pytest -q app/tests/integration/test_fila_kds.py`
Expected: PASS.

- [ ] **Step 5: Suíte completa + lint/types**

Run: `cd backend && ../.venv/bin/pytest -q && ../.venv/bin/ruff check . && ../.venv/bin/mypy .`
Expected: tudo verde.

- [ ] **Step 6: Commit**

```bash
git add backend/app/modules/orders/schemas.py backend/app/modules/orders/routes.py backend/app/tests/integration/test_fila_kds.py
git commit -m "feat(orders): fila de cozinha (KDS) por status"
```

---

### Task 5: Frontend — tipos + `FilaKdsPage` + rota/nav

**Files:**
- Modify: `frontend/src/api/types.ts` (tipos `KdsItem`, `KdsOrder`)
- Create: `frontend/src/pages/FilaKdsPage.tsx`
- Modify: `frontend/src/App.tsx` (rota `/cozinha`)
- Modify: `frontend/src/pages/DashboardPage.tsx` (nav "Cozinha")
- Test: `frontend/src/test/fila-kds.test.tsx`

**Interfaces:**
- Consumes: `GET /api/v1/cozinha/fila` (Task 4), `PATCH /api/v1/pedidos/{id}/status` (Task 2), `POST /api/v1/pedidos/{id}/cancelar` (Task 3); `api` de `../api/client`.
- Produces: `KdsOrder`/`KdsItem` em `types.ts`; página de fila.

> Nota de simplicidade: a UI **não** gateia botões por papel — o backend enforça (403). Esconder por papel é upgrade futuro (a página é usada pela cozinha).

- [ ] **Step 1: Escrever o teste que falha**

```tsx
// frontend/src/test/fila-kds.test.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import FilaKdsPage from "../pages/FilaKdsPage";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const fila = [
  {
    order_id: "o1",
    code: "SC-A1",
    status: "confirmed",
    channel: "pos",
    fulfillment_type: "table",
    notes: "sem cebola",
    created_at: "2026-10-10T12:00:00Z",
    elapsed_minutes: 4,
    items: [
      { order_item_id: "i1", product_name: "X-Burger", quantity: 2, notes: null, modifiers: [] },
    ],
  },
];

describe("FilaKdsPage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("lista a fila e inicia preparo", async () => {
    const calls: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
        const u = String(url);
        calls.push(`${init?.method ?? "GET"} ${u}`);
        if (u === "/api/v1/cozinha/fila") return jsonResponse(fila);
        if (u === "/api/v1/pedidos/o1/status" && init?.method === "PATCH") {
          return jsonResponse({ ...fila[0], status: "preparing" });
        }
        throw new Error(`fetch inesperado: ${u}`);
      }),
    );

    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter>
          <FilaKdsPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await screen.findByText("SC-A1");
    expect(screen.getByText("X-Burger")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /iniciar preparo/i }));
    await waitFor(() =>
      expect(calls).toContain("PATCH /api/v1/pedidos/o1/status"),
    );
  });

  it("mostra estado vazio", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse([])),
    );
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter>
          <FilaKdsPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    await screen.findByText(/nenhum pedido/i);
  });
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd frontend && npm test -- --run src/test/fila-kds.test.tsx`
Expected: FAIL — módulo `FilaKdsPage` não existe.

- [ ] **Step 3: Implementar**

Em `frontend/src/api/types.ts`, adicionar:

```ts
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
```

Criar `frontend/src/pages/FilaKdsPage.tsx`:

```tsx
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import { type KdsOrder, STATUS_LABEL } from "../api/types";

export default function FilaKdsPage() {
  const qc = useQueryClient();
  const { data: fila = [], isLoading, isError } = useQuery<KdsOrder[]>({
    queryKey: ["cozinha-fila"],
    queryFn: () => api<KdsOrder[]>("/cozinha/fila"),
    refetchInterval: 5000,
  });
  const [erro, setErro] = useState("");

  const mudar = useMutation({
    mutationFn: ({ id, to }: { id: string; to: string }) =>
      api(`/pedidos/${id}/status`, { method: "PATCH", body: JSON.stringify({ status: to }) }),
    onSuccess: () => {
      setErro("");
      qc.invalidateQueries({ queryKey: ["cozinha-fila"] });
    },
    onError: () => setErro("Não foi possível atualizar o pedido."),
  });

  return (
    <main className="mx-auto max-w-5xl space-y-6 p-8">
      <h1 className="text-2xl font-semibold">Fila da cozinha</h1>
      {erro && (
        <p role="alert" className="text-sm text-red-600">
          {erro}
        </p>
      )}
      {isError && (
        <p role="alert" className="text-sm text-red-600">
          Erro ao carregar a fila.
        </p>
      )}
      {isLoading && <p className="text-gray-600">Carregando…</p>}
      {!isLoading && !isError && fila.length === 0 && (
        <p role="status" className="text-gray-600">
          Nenhum pedido na fila.
        </p>
      )}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {fila.map((o) => (
          <article key={o.order_id} className="space-y-3 rounded border p-4">
            <header className="flex items-center justify-between">
              <strong>{o.code}</strong>
              <span className="text-xs text-gray-500">
                {STATUS_LABEL[o.status] ?? o.status} · {o.elapsed_minutes} min
              </span>
            </header>
            <ul className="text-sm">
              {o.items.map((it) => (
                <li key={it.order_item_id} className="tabular-nums">
                  {it.quantity}× {it.product_name}
                  {it.notes ? <em className="block text-gray-500">obs: {it.notes}</em> : null}
                </li>
              ))}
            </ul>
            {o.notes && <p className="text-xs text-gray-500">obs do pedido: {o.notes}</p>}
            <div className="flex flex-wrap gap-2">
              {o.status !== "preparing" && (
                <button
                  type="button"
                  className="rounded bg-amber-600 px-3 py-2 text-sm text-white disabled:opacity-50"
                  disabled={mudar.isPending}
                  onClick={() => mudar.mutate({ id: o.order_id, to: "preparing" })}
                >
                  Iniciar preparo
                </button>
              )}
              {o.status === "preparing" && (
                <button
                  type="button"
                  className="rounded bg-green-600 px-3 py-2 text-sm text-white disabled:opacity-50"
                  disabled={mudar.isPending}
                  onClick={() => mudar.mutate({ id: o.order_id, to: "ready" })}
                >
                  Marcar pronto
                </button>
              )}
            </div>
          </article>
        ))}
      </div>
    </main>
  );
}
```

Em `frontend/src/App.tsx`: importar `FilaKdsPage` e adicionar a rota (após `/pedidos/:id`):

```tsx
          <Route
            path="/cozinha"
            element={
              <Protected>
                <FilaKdsPage />
              </Protected>
            }
          />
```

Em `frontend/src/pages/DashboardPage.tsx`, adicionar ao `<nav>`:

```tsx
        <Link to="/cozinha" className="rounded border px-4 py-2">
          Cozinha
        </Link>
```

- [ ] **Step 4: Rodar e garantir verde**

Run: `cd frontend && npm test -- --run src/test/fila-kds.test.tsx`
Expected: PASS.

- [ ] **Step 5: Suíte + lint/build**

Run: `cd frontend && npm run typecheck && npm run lint && npm test -- --run && npm run build`
Expected: verde.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/pages/FilaKdsPage.tsx frontend/src/pages/DashboardPage.tsx frontend/src/App.tsx frontend/src/test/fila-kds.test.tsx
git commit -m "feat(web): fila de cozinha (KDS)"
```

---

### Task 6: Frontend — transições no detalhe, comanda e polling

**Files:**
- Modify: `frontend/src/api/types.ts` (enriquecer `Pedido`/`PedidoItem`)
- Create: `frontend/src/pages/ComandaPage.tsx`
- Modify: `frontend/src/pages/PedidoDetalhePage.tsx` (ações de transição + cancelar + link comanda)
- Modify: `frontend/src/pages/PedidosPage.tsx` (polling + link comanda)
- Modify: `frontend/src/App.tsx` (rota `/pedidos/:id/comanda`)
- Test: `frontend/src/test/pedido-status.test.tsx`, `frontend/src/test/comanda.test.tsx`

**Interfaces:**
- Consumes: `PATCH /pedidos/{id}/status` (Task 2), `POST /pedidos/{id}/cancelar` (Task 3), `GET /pedidos/{id}` enriquecido (Task 1).

- [ ] **Step 1: Escrever os testes que falham**

```tsx
// frontend/src/test/pedido-status.test.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PedidoDetalhePage from "../pages/PedidoDetalhePage";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const pedido = {
  id: "o1",
  code: "SC-A1",
  status: "confirmed",
  customer_name: "Ana",
  customer_phone: "1199",
  channel: "pos",
  fulfillment_type: "table",
  expected_time: null,
  subtotal: "20.00",
  delivery_fee: "0.00",
  discount_total: "0.00",
  tax_total: "0.00",
  total: "20.00",
  notes: null,
  created_at: "2026-10-10T12:00:00Z",
  order_items: [
    {
      product_id: "p1",
      product_name: "X-Burger",
      quantity: 1,
      unit_price: "20.00",
      total_price: "20.00",
      notes: null,
      modifiers: [],
    },
  ],
};

function renderPage() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <MemoryRouter initialEntries={["/pedidos/o1"]}>
        <Routes>
          <Route path="/pedidos/:id" element={<PedidoDetalhePage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("PedidoDetalhePage transicoes", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
  });

  it("inicia preparo de um pedido confirmado", async () => {
    const calls: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
        const u = String(url);
        calls.push(`${init?.method ?? "GET"} ${u}`);
        if (u === "/api/v1/pedidos/o1") return jsonResponse(pedido);
        if (u === "/api/v1/pedidos/o1/eventos")
          return jsonResponse({ order_id: "o1", status: pedido.status, events: [] });
        if (u === "/api/v1/pedidos/o1/status" && init?.method === "PATCH")
          return jsonResponse({ ...pedido, status: "preparing" });
        throw new Error(`fetch inesperado: ${u}`);
      }),
    );
    renderPage();
    await screen.findByText("SC-A1");
    await userEvent.click(screen.getByRole("button", { name: /iniciar preparo/i }));
    await waitFor(() => expect(calls).toContain("PATCH /api/v1/pedidos/o1/status"));
  });

  it("cancela pedido com motivo", async () => {
    const bodies: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
        const u = String(url);
        if (u === "/api/v1/pedidos/o1") return jsonResponse(pedido);
        if (u === "/api/v1/pedidos/o1/eventos")
          return jsonResponse({ order_id: "o1", status: pedido.status, events: [] });
        if (u === "/api/v1/pedidos/o1/cancelar" && init?.method === "POST") {
          bodies.push(String(init.body));
          return jsonResponse({ ...pedido, status: "cancelled" });
        }
        throw new Error(`fetch inesperado: ${u}`);
      }),
    );
    renderPage();
    await screen.findByText("SC-A1");
    await userEvent.click(screen.getByRole("button", { name: /cancelar pedido/i }));
    await userEvent.type(screen.getByLabelText(/motivo/i), "cliente desistiu");
    await userEvent.click(screen.getByRole("button", { name: /confirmar cancelamento/i }));
    await waitFor(() => expect(bodies.some((b) => b.includes("cliente desistiu"))).toBe(true));
  });
});
```

```tsx
// frontend/src/test/comanda.test.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ComandaPage from "../pages/ComandaPage";

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

const pedido = {
  id: "o1", code: "SC-A1", status: "confirmed", customer_name: "Ana",
  customer_phone: "1199", channel: "pos", fulfillment_type: "table",
  expected_time: null, subtotal: "20.00", delivery_fee: "0.00",
  discount_total: "0.00", tax_total: "0.00", total: "20.00", notes: null,
  created_at: "2026-10-10T12:00:00Z",
  order_items: [
    { product_id: "p1", product_name: "X-Burger", quantity: 2, unit_price: "10.00",
      total_price: "20.00", notes: "sem cebola", modifiers: [] },
  ],
};

describe("ComandaPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renderiza itens e imprime", async () => {
    const print = vi.fn();
    vi.stubGlobal("print", print);
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(pedido)));

    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={["/pedidos/o1/comanda"]}>
          <Routes>
            <Route path="/pedidos/:id/comanda" element={<ComandaPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await screen.findByText("X-Burger");
    expect(screen.getByText("sem cebola")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /imprimir/i }));
    expect(print).toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd frontend && npm test -- --run src/test/pedido-status.test.tsx src/test/comanda.test.tsx`
Expected: FAIL — `ComandaPage` inexistente; botões de transição ausentes.

- [ ] **Step 3: Implementar**

Enriquecer `Pedido`/`PedidoItem` em `types.ts`:

```ts
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
```

Criar `frontend/src/pages/ComandaPage.tsx`:

```tsx
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { api } from "../api/client";
import { type Pedido, STATUS_LABEL } from "../api/types";

export default function ComandaPage() {
  const { id = "" } = useParams();
  const { data: pedido } = useQuery<Pedido>({
    queryKey: ["pedido", id],
    queryFn: () => api<Pedido>(`/pedidos/${id}`),
  });

  return (
    <main className="mx-auto max-w-md space-y-4 p-8">
      <div className="flex justify-end print:hidden">
        <button
          type="button"
          onClick={() => window.print()}
          className="rounded bg-blue-600 px-4 py-2 text-white"
        >
          Imprimir
        </button>
      </div>
      <article className="space-y-3 font-mono text-sm">
        <h1 className="text-lg font-bold">{pedido?.code ?? "Pedido"}</h1>
        <p>
          {pedido?.customer_name ?? "Cliente"} ·{" "}
          {pedido ? new Date(pedido.created_at).toLocaleString("pt-BR") : "—"}
        </p>
        <p>
          {pedido?.fulfillment_type} · {pedido ? (STATUS_LABEL[pedido.status] ?? pedido.status) : "—"}
        </p>
        <ul className="border-y py-2">
          {pedido?.order_items.map((it) => (
            <li key={it.product_id} className="flex justify-between tabular-nums">
              <span>
                {it.quantity}× {it.product_name}
                {it.notes ? <em className="block">obs: {it.notes}</em> : null}
              </span>
              <span>R$ {Number(it.total_price).toFixed(2)}</span>
            </li>
          ))}
        </ul>
        <p className="flex justify-between font-bold tabular-nums">
          <span>Total</span>
          <span>R$ {pedido ? Number(pedido.total).toFixed(2) : "—"}</span>
        </p>
      </article>
    </main>
  );
}
```

Reescrever `frontend/src/pages/PedidoDetalhePage.tsx` adicionando as ações. Substituir o corpo por (mantendo `usePedido`, eventos e `confirmar` existentes):

```tsx
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { type Evento, type Pedido, STATUS_LABEL } from "../api/types";

function usePedido(id: string) {
  return useQuery<Pedido>({
    queryKey: ["pedido", id],
    queryFn: () => api<Pedido>(`/pedidos/${id}`),
  });
}

const NEXT_ACTIONS: Record<string, { to: string; label: string }[]> = {
  received: [],
  confirmed: [{ to: "preparing", label: "Iniciar preparo" }],
  confirmed_pending_stock: [{ to: "preparing", label: "Iniciar preparo" }],
  preparing: [{ to: "ready", label: "Marcar pronto" }],
  ready: [
    { to: "delivered", label: "Marcar entregue" },
    { to: "completed", label: "Concluir" },
  ],
  delivered: [{ to: "completed", label: "Concluir" }],
};

const CANCELAVEIS = ["received", "confirmed", "confirmed_pending_stock", "preparing", "ready"];

export default function PedidoDetalhePage() {
  const { id = "" } = useParams();
  const qc = useQueryClient();
  const { data: pedido } = usePedido(id);
  const { data: eventos } = useQuery<{ order_id: string; status: string; events: Evento[] }>({
    queryKey: ["pedido-eventos", id],
    queryFn: () =>
      api<{ order_id: string; status: string; events: Evento[] }>(`/pedidos/${id}/eventos`),
    enabled: !!id,
  });

  const [aviso, setAviso] = useState("");
  const [motivo, setMotivo] = useState("");
  const [cancelOpen, setCancelOpen] = useState(false);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ["pedido", id] });
    qc.invalidateQueries({ queryKey: ["pedido-eventos", id] });
  };

  const confirmar = useMutation({
    mutationFn: () => api<Pedido>(`/pedidos/${id}/confirmar`, { method: "POST" }),
    onSuccess: (ped) => {
      invalidate();
      if (ped.status === "confirmed_pending_stock")
        setAviso("Pedido confirmado com pendência de estoque.");
    },
    onError: () => setAviso("Não foi possível confirmar."),
  });

  const mudar = useMutation({
    mutationFn: (to: string) =>
      api<Pedido>(`/pedidos/${id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: to }),
      }),
    onSuccess: () => {
      setAviso("");
      invalidate();
    },
    onError: () => setAviso("Transição não permitida."),
  });

  const cancelar = useMutation({
    mutationFn: () =>
      api<Pedido>(`/pedidos/${id}/cancelar`, {
        method: "POST",
        body: JSON.stringify({ motivo }),
      }),
    onSuccess: () => {
      setCancelOpen(false);
      setMotivo("");
      invalidate();
    },
    onError: () => setAviso("Não foi possível cancelar."),
  });

  const podeConfirmar = pedido?.status === "received";
  const podeCancelar = pedido ? CANCELAVEIS.includes(pedido.status) : false;

  return (
    <main className="mx-auto max-w-3xl space-y-6 p-8">
      <h1 className="text-2xl font-semibold">{pedido?.code ?? "Pedido"}</h1>
      {pedido && (
        <p>
          Status: <strong>{STATUS_LABEL[pedido.status] ?? pedido.status}</strong>
        </p>
      )}
      {aviso && (
        <p role="alert" className="text-sm text-amber-700">
          {aviso}
        </p>
      )}
      {pedido && (
        <Link to={`/pedidos/${pedido.id}/comanda`} className="text-sm text-blue-600">
          Ver comanda
        </Link>
      )}

      <ul className="rounded border p-4">
        {pedido?.order_items.map((it) => (
          <li key={it.product_id} className="flex justify-between py-1">
            <span>
              {it.quantity}× {it.product_name}
            </span>
            <span className="tabular-nums">R$ {Number(it.total_price).toFixed(2)}</span>
          </li>
        ))}
      </ul>
      <p className="tabular-nums">
        Total: <strong>R$ {pedido ? Number(pedido.total).toFixed(2) : "—"}</strong>
      </p>

      <div className="flex flex-wrap gap-2">
        {podeConfirmar && (
          <button
            type="button"
            onClick={() => confirmar.mutate()}
            disabled={confirmar.isPending}
            className="rounded bg-green-600 px-4 py-2 text-white disabled:opacity-50"
          >
            {confirmar.isPending ? "Confirmando…" : "Confirmar pedido"}
          </button>
        )}
        {pedido &&
          NEXT_ACTIONS[pedido.status]?.map((a) => (
            <button
              key={a.to}
              type="button"
              onClick={() => mudar.mutate(a.to)}
              disabled={mudar.isPending}
              className="rounded border px-4 py-2 disabled:opacity-50"
            >
              {a.label}
            </button>
          ))}
        {podeCancelar && (
          <button
            type="button"
            onClick={() => setCancelOpen(true)}
            className="rounded bg-red-600 px-4 py-2 text-white"
          >
            Cancelar pedido
          </button>
        )}
      </div>

      {cancelOpen && (
        <div className="space-y-2 rounded border p-4">
          <label htmlFor="motivo" className="block text-sm font-medium">
            Motivo
          </label>
          <input
            id="motivo"
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            className="w-full rounded border px-2 py-1"
          />
          <button
            type="button"
            onClick={() => cancelar.mutate()}
            disabled={cancelar.isPending || motivo.trim() === ""}
            className="rounded bg-red-600 px-4 py-2 text-white disabled:opacity-50"
          >
            Confirmar cancelamento
          </button>
        </div>
      )}

      <section>
        <h2 className="font-semibold">Eventos</h2>
        <ul className="text-sm">
          {eventos?.events.map((e) => (
            <li key={`${e.event_type}-${e.created_at}`} className="flex justify-between py-1">
              <span>{e.event_type}</span>
              <span className="text-gray-500">{e.outbox_status ?? e.created_at}</span>
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
```

Em `frontend/src/pages/PedidosPage.tsx`: adicionar `refetchInterval: 5000` ao `useQuery` e uma coluna com link "Comanda" (import `Link` já existe):

```tsx
  const { data: pedidos = [] } = useQuery<Pedido[]>({
    queryKey: ["pedidos"],
    queryFn: () => api<Pedido[]>("/pedidos"),
    refetchInterval: 5000,
  });
```

e na linha da tabela, após a célula de status:

```tsx
              <td>
                <Link to={`/pedidos/${p.id}/comanda`} className="text-blue-600">
                  Comanda
                </Link>
              </td>
```

(adicionar `<th>Comanda</th>` no cabeçalho também).

Em `App.tsx`: importar `ComandaPage` e adicionar rota (antes de `/pedidos/:id`, para casar o caminho mais específico):

```tsx
          <Route
            path="/pedidos/:id/comanda"
            element={
              <Protected>
                <ComandaPage />
              </Protected>
            }
          />
```

- [ ] **Step 4: Rodar e garantir verde**

Run: `cd frontend && npm test -- --run src/test/pedido-status.test.tsx src/test/comanda.test.tsx src/test/pedido.test.tsx`
Expected: PASS (incluindo a regressão de pedido existente).

- [ ] **Step 5: Suíte + lint/build**

Run: `cd frontend && npm run typecheck && npm run lint && npm test -- --run && npm run build`
Expected: verde.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/pages/ComandaPage.tsx frontend/src/pages/PedidoDetalhePage.tsx frontend/src/pages/PedidosPage.tsx frontend/src/App.tsx frontend/src/test/pedido-status.test.tsx frontend/src/test/comanda.test.tsx
git commit -m "feat(web): transicoes de pedido, comanda e polling"
```

---

### Task 7: Verificação final

**Files:** nenhum (rodada de verificação; corrige se necessário).

- [ ] **Step 1: Backend completo**

Run: `cd backend && ../.venv/bin/ruff check . && ../.venv/bin/mypy . && ../.venv/bin/pytest -q`
Expected: lint/types limpos; suíte inteira verde.

- [ ] **Step 2: Frontend completo**

Run: `cd frontend && npm run typecheck && npm run lint && npm test -- --run && npm run build`
Expected: tudo verde.

- [ ] **Step 3: Corrigir + commit se houver falha**

Se algo falhar, corrigir e commitar: `git commit -m "fix: ..."`. Se nada falhar, **nenhum commit**.

- [ ] **Step 4: Relatório de verificação**

Registrar a matriz (suítes + contagens de teste) no relatório da task.

---

## Self-Review (do plano)

- **Cobertura da spec:** §2 transições → Task 2; §3 cancelamento/reversão → Task 3; §4 KDS → Task 4; §5 comanda → Task 6; §6 `OrderOut` → Task 1; §7 frontend → Tasks 5/6; §8 testes → embutidos por task; §9 constraints → Global Constraints; §10 decisões → refletidas. Sem lacuna.
- **Sem placeholders:** todo passo traz código/teste/command reais.
- **Consistência de tipos:** `OrderStatusUpdate{status,notes}`, `OrderCancel{motivo}`; `KitchenOrderOut`/`KitchenItemOut`; `KdsOrder`/`KdsItem`; `TRANSITIONS` (inclui `ready→completed`, consistente com a spec ajustada); `_to_out` enriquecido consumido por Tasks 2/3/4. Nomes estáveis entre tasks.
- **Ajuste de spec:** adicionada a transição `ready→completed` em `docs/superpowers/specs/2026-10-10-pedidos-cozinha-design.md` §2 (consistente com o design aprovado; necessária para retirada/mesa).