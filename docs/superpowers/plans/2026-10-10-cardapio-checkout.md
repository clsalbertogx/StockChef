# Cardápio Digital e Checkout (E04) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Entregar o cardápio público sem login (busca, filtro de categoria, adicionais), carrinho no PWA, checkout com ViaCEP e taxa por zona, e criação do pedido público que entra na operação existente (KDS/pedidos/cancelamento/baixa de estoque).

**Architecture:** Novo módulo backend `storefront` expõe `/api/v1/public/{slug}/...`, resolve o tenant por `tenants.slug`, seta a RLS (`set_tenant`) e reusa o core de pedidos (`recipe_snapshot`, `availability`). Zonas de entrega ficam no novo módulo `delivery`. Modelos ORM faltantes (`ProductModifier`, `Zone`, `Payment`) mapeiam tabelas já existentes — **sem migration**. Frontend React adiciona páginas públicas `/cardapio/:slug/*` fora do `Protected`, com carrinho em `localStorage`.

**Tech Stack:** FastAPI + SQLAlchemy 2.0 + Pydantic v2 + pytest/testcontainers; React 19 + TypeScript + Vite + TanStack Query + React Router + Tailwind + vitest.

**Spec:** `docs/superpowers/specs/2026-10-10-cardapio-checkout-design.md`

## Global Constraints

- **Sem migration e sem tabela nova.** Todas as tabelas já existem no DDL.
- **Sem dependência nova** (backend e frontend). ViaCEP via `urllib.request` da stdlib, atrás de `storefront/viacep.py:lookup` (mockável).
- RLS `app.tenant_id` em toda query; único acesso fora do RLS é ler `tenants` por slug (tabela excluída da policy).
- `DomainError(code, detail, http_status)` → `{detail, code}`. 404 `not_found`/`store_not_found`/`cep_not_found`/`product_not_found`; 403 `forbidden`; 422 de negócio (`invalid_modifiers`, `cep_invalid`, `cep_not_covered`, `below_min_order`, `address_required`, `fulfillment_unavailable`); 503 `cep_unavailable`/`code_conflict`.
- Dinheiro Decimal com `ROUND_HALF_UP`; preços calculados **só** no servidor.
- `stock_levels` só via `apply_movement`/`ensure_stock_level` (não tocar nesta fatia).
- Backend: `cd backend && ../.venv/bin/ruff check . && ../.venv/bin/mypy . && ../.venv/bin/pytest -q` limpos (line-length 100, select E,F,I,UP,B).
- Frontend: `cd frontend && npm run typecheck && npm run lint && npm test && npm run build` limpos.
- Rotas internas sensíveis usam `require_roles`; rotas públicas **não** usam `current_actor`.
- DESIGN.md: mobile-first, alvos ≥44px, estados loading/erro/vazio, `role="alert"`, `tabular-nums` em preços, `STATUS_LABEL` pt-BR.

---

## File Structure

**Backend — criar:**
- `backend/app/modules/delivery/{__init__,models,schemas,service,routes}.py` — `Zone` + `/zonas`
- `backend/app/modules/storefront/{__init__,deps,viacep,schemas,service,routes}.py` — rotas públicas
- `backend/app/tests/integration/test_adicionais.py`
- `backend/app/tests/integration/test_zonas.py`
- `backend/app/tests/integration/test_storefront_cardapio.py`
- `backend/app/tests/integration/test_storefront_cep.py`
- `backend/app/tests/integration/test_storefront_entrega.py`
- `backend/app/tests/integration/test_storefront_pedido.py`

**Backend — modificar:**
- `backend/app/modules/catalog/models.py` — `ProductModifier`
- `backend/app/modules/catalog/schemas.py` — `Modifier*`
- `backend/app/modules/catalog/routes.py` — `/produtos/{id}/adicionais`
- `backend/app/modules/orders/models.py` — `Payment`
- `backend/app/main.py` — registrar `delivery_router`, `storefront_router`
- `backend/app/tests/integration/test_models_mapeiam_ddl.py`

**Frontend — criar:**
- `frontend/src/api/public.ts`
- `frontend/src/cart/CartContext.tsx`
- `frontend/src/components/ModifierDialog.tsx`
- `frontend/src/pages/public/{CardapioPage,CarrinhoPage,CheckoutPage,PedidoPublicoPage}.tsx`
- `frontend/src/pages/ZonasPage.tsx`
- `frontend/src/test/{cardapio,modifiers,checkout,pedido-publico}.test.tsx`

**Frontend — modificar:**
- `frontend/src/api/types.ts`, `frontend/src/App.tsx`, `frontend/src/pages/DashboardPage.tsx`

---

### Task 1: Modelos ORM faltantes (ProductModifier, Zone, Payment)

**Files:**
- Modify: `backend/app/modules/catalog/models.py` (append `ProductModifier`)
- Create: `backend/app/modules/delivery/__init__.py`, `backend/app/modules/delivery/models.py`
- Modify: `backend/app/modules/orders/models.py` (append `Payment`)
- Test: `backend/app/tests/integration/test_models_mapeiam_ddl.py`

**Interfaces:**
- Produces: `catalog.models.ProductModifier`, `delivery.models.Zone`, `orders.models.Payment` (colunas idênticas ao DDL).

- [ ] **Step 1: Escrever o teste que falha**

Em `test_models_mapeiam_ddl.py`, adicionar imports:

```python
from app.modules.catalog.models import Product, ProductModifier
from app.modules.delivery.models import Zone
from app.modules.orders.models import Order, Payment
```

Antes do `db.commit()` (após `db.add(poi)` / `db.flush()`), adicionar:

```python
        product = Product(tenant_id=tenant_id, store_id=store.id, name="Produto m",
                          price=Decimal("10.00"))
        db.add(product)
        db.flush()
        db.add(ProductModifier(tenant_id=tenant_id, product_id=product.id,
                               group_name="Ponto", modifier_name="Ao ponto",
                               price_delta=Decimal("0.00")))
        db.add(Zone(tenant_id=tenant_id, store_id=store.id, name="Centro",
                    cep_ranges=[{"start": "01000000", "end": "01999999"}]))
        order = Order(tenant_id=tenant_id, store_id=store.id, code="SC-M1")
        db.add(order)
        db.flush()
        db.add(Payment(tenant_id=tenant_id, order_id=order.id, provider="cash",
                       method="cash", amount=Decimal("10.00")))
```

E após o commit:

```python
        assert db.scalar(select(ProductModifier)) is not None
        assert db.scalar(select(Zone)) is not None
        assert db.scalar(select(Payment)) is not None
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && ../.venv/bin/pytest app/tests/integration/test_models_mapeiam_ddl.py -q`
Expected: FAIL (ImportError `ProductModifier`/`Zone`/`Payment`).

- [ ] **Step 3: Implementar os modelos**

Append em `catalog/models.py`:

```python
class ProductModifier(Base):
    __tablename__ = "product_modifiers"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    product_id: Mapped[UUID] = mapped_column(ForeignKey("products.id"), nullable=False)
    group_name: Mapped[str] = mapped_column(String)
    modifier_name: Mapped[str] = mapped_column(String)
    price_delta: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    required: Mapped[bool] = mapped_column(default=False)
    min_selection: Mapped[int] = mapped_column(default=0)
    max_selection: Mapped[int | None] = mapped_column(default=None)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
```

Criar `delivery/__init__.py` (vazio) e `delivery/models.py`:

```python
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _now() -> Any:
    return datetime.now(UTC)


class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    store_id: Mapped[UUID] = mapped_column(ForeignKey("stores.id"), nullable=False)
    name: Mapped[str] = mapped_column(String)
    geometry: Mapped[dict] = mapped_column(JSONB, default=dict)
    cep_ranges: Mapped[list] = mapped_column(JSONB, default=list)
    delivery_fee: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    min_order_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    eta_minutes: Mapped[int] = mapped_column(default=30)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
```

Append em `orders/models.py`:

```python
class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    order_id: Mapped[UUID] = mapped_column(ForeignKey("orders.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String)
    provider_payment_id: Mapped[str | None] = mapped_column(String, unique=True, default=None)
    method: Mapped[str] = mapped_column(String)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[str] = mapped_column(String, default="pending")
    idempotency_key: Mapped[str | None] = mapped_column(String, unique=True, default=None)
    raw_response: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd backend && ../.venv/bin/ruff check . && ../.venv/bin/mypy . && ../.venv/bin/pytest app/tests/integration/test_models_mapeiam_ddl.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/catalog/models.py backend/app/modules/delivery/__init__.py backend/app/modules/delivery/models.py backend/app/modules/orders/models.py backend/app/tests/integration/test_models_mapeiam_ddl.py
git commit -m "feat(models): mapeia product_modifiers, zones e payments"
```

---

### Task 2: Adicionais de produto (admin CRUD)

**Files:**
- Modify: `backend/app/modules/catalog/schemas.py`, `backend/app/modules/catalog/routes.py`
- Test: `backend/app/tests/integration/test_adicionais.py`

**Interfaces:**
- Consumes: `catalog.models.ProductModifier` (Task 1).
- Produces: `POST/GET /api/v1/produtos/{product_id}/adicionais`, `PATCH .../{modifier_id}`; schemas `ModifierCreate`, `ModifierPatch`, `ModifierOut`.

- [ ] **Step 1: Escrever o teste que falha**

Criar `backend/app/tests/integration/test_adicionais.py`:

```python
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


def _product(h: dict[str, str], name: str) -> str:
    r = client.post("/api/v1/produtos", headers=h, json={"name": name, "price": "20.00"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_cria_e_lista_adicionais() -> None:
    h = _setup("adic1")
    pid = _product(h, "X-Burger")
    r = client.post(f"/api/v1/produtos/{pid}/adicionais", headers=h, json={
        "group_name": "Ponto", "modifier_name": "Ao ponto", "price_delta": "0.00",
        "required": True, "min_selection": 1, "max_selection": 1,
    })
    assert r.status_code == 201, r.text
    assert r.json()["modifier_name"] == "Ao ponto"
    r2 = client.get(f"/api/v1/produtos/{pid}/adicionais", headers=h)
    assert r2.status_code == 200 and len(r2.json()) == 1


def test_patch_desativa_adicional() -> None:
    h = _setup("adic2")
    pid = _product(h, "X-Burger")
    mid = client.post(f"/api/v1/produtos/{pid}/adicionais", headers=h, json={
        "group_name": "Extras", "modifier_name": "Bacon", "price_delta": "3.00",
    }).json()["id"]
    r = client.patch(f"/api/v1/produtos/{pid}/adicionais/{mid}", headers=h,
                     json={"active": False})
    assert r.status_code == 200 and r.json()["active"] is False


def test_produto_inexistente_404() -> None:
    h = _setup("adic3")
    r = client.post("/api/v1/produtos/00000000-0000-0000-0000-000000000000/adicionais",
                    headers=h, json={"group_name": "X", "modifier_name": "Y"})
    assert r.status_code == 404, r.text
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && ../.venv/bin/pytest app/tests/integration/test_adicionais.py -q`
Expected: FAIL (404 nas rotas).

- [ ] **Step 3: Implementar schemas e rotas**

Append em `catalog/schemas.py`:

```python
class ModifierCreate(BaseModel):
    group_name: str = Field(min_length=1, max_length=80)
    modifier_name: str = Field(min_length=1, max_length=80)
    price_delta: Decimal = Decimal("0")
    required: bool = False
    min_selection: int = Field(default=0, ge=0)
    max_selection: int | None = Field(default=None, ge=0)


class ModifierPatch(BaseModel):
    group_name: str | None = None
    modifier_name: str | None = None
    price_delta: Decimal | None = None
    required: bool | None = None
    min_selection: int | None = Field(default=None, ge=0)
    max_selection: int | None = Field(default=None, ge=0)
    active: bool | None = None


class ModifierOut(BaseModel):
    id: UUID
    group_name: str
    modifier_name: str
    price_delta: Decimal
    required: bool
    min_selection: int
    max_selection: int | None
    active: bool
```

Em `catalog/routes.py`: adicionar `ProductModifier` aos imports de models e `ModifierCreate, ModifierOut, ModifierPatch` aos schemas; append:

```python
def _require_product(db: Session, product_id: UUID) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise DomainError("not_found", "Produto não encontrado.", status.HTTP_404_NOT_FOUND)
    return product


def _modifier_out(m: ProductModifier) -> ModifierOut:
    return ModifierOut(
        id=m.id, group_name=m.group_name, modifier_name=m.modifier_name,
        price_delta=m.price_delta, required=m.required,
        min_selection=m.min_selection, max_selection=m.max_selection, active=m.active,
    )


@router.post("/produtos/{product_id}/adicionais", status_code=status.HTTP_201_CREATED)
def create_modifier(
    product_id: UUID, payload: ModifierCreate, db: Session = Depends(get_tenant_db)  # noqa: B008
) -> ModifierOut:
    _require_product(db, product_id)
    m = ProductModifier(
        tenant_id=_tenant_id(db), product_id=product_id, group_name=payload.group_name,
        modifier_name=payload.modifier_name, price_delta=payload.price_delta,
        required=payload.required, min_selection=payload.min_selection,
        max_selection=payload.max_selection,
    )
    db.add(m)
    db.commit()
    return _modifier_out(m)


@router.get("/produtos/{product_id}/adicionais")
def list_modifiers(product_id: UUID, db: Session = Depends(get_tenant_db)) -> list[ModifierOut]:  # noqa: B008
    _require_product(db, product_id)
    rows = db.scalars(
        select(ProductModifier).where(ProductModifier.product_id == product_id)
    ).all()
    return [_modifier_out(m) for m in rows]


@router.patch("/produtos/{product_id}/adicionais/{modifier_id}")
def patch_modifier(
    product_id: UUID, modifier_id: UUID, payload: ModifierPatch,
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> ModifierOut:
    _require_product(db, product_id)
    m = db.get(ProductModifier, modifier_id)
    if m is None or m.product_id != product_id:
        raise DomainError("not_found", "Adicional não encontrado.", status.HTTP_404_NOT_FOUND)
    for field in ("group_name", "modifier_name", "price_delta", "required",
                  "min_selection", "max_selection", "active"):
        value = getattr(payload, field)
        if value is not None:
            setattr(m, field, value)
    db.commit()
    return _modifier_out(m)
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd backend && ../.venv/bin/ruff check . && ../.venv/bin/mypy . && ../.venv/bin/pytest app/tests/integration/test_adicionais.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/catalog/schemas.py backend/app/modules/catalog/routes.py backend/app/tests/integration/test_adicionais.py
git commit -m "feat(catalog): CRUD de adicionais de produto"
```

### Task 3: Zonas de entrega (admin CRUD + resolução por CEP)

**Files:**
- Create: `backend/app/modules/delivery/schemas.py`, `backend/app/modules/delivery/service.py`, `backend/app/modules/delivery/routes.py`
- Modify: `backend/app/main.py` (registrar `delivery_router`)
- Test: `backend/app/tests/integration/test_zonas.py`

**Interfaces:**
- Consumes: `delivery.models.Zone` (Task 1), `catalog.service.default_store`.
- Produces: `delivery.service.resolve_zone(db, store_id, cep) -> Zone | None`; `GET/POST /api/v1/zonas`, `PATCH /api/v1/zonas/{zone_id}` (RBAC `manager`/`owner`); schemas `ZoneCreate`, `ZonePatch`, `ZoneOut`.

- [ ] **Step 1: Escrever o teste que falha**

Criar `backend/app/tests/integration/test_zonas.py`:

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _owner(slug: str) -> dict[str, str]:
    r = client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": f"{slug}@x.com",
        "password": "senha-segura", "name": "Dono",
    })
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_cria_lista_e_patch_zona() -> None:
    h = _owner("zona1")
    r = client.post("/api/v1/zonas", headers=h, json={
        "name": "Centro", "cep_ranges": [{"start": "01000000", "end": "01999999"}],
        "delivery_fee": "7.50", "min_order_value": "20.00", "eta_minutes": 40,
    })
    assert r.status_code == 201, r.text
    zid = r.json()["id"]
    assert r.json()["delivery_fee"] == "7.50"
    lst = client.get("/api/v1/zonas", headers=h)
    assert lst.status_code == 200 and len(lst.json()) == 1
    p = client.patch(f"/api/v1/zonas/{zid}", headers=h, json={"active": False})
    assert p.status_code == 200 and p.json()["active"] is False


def test_cep_normalizado_com_mascara() -> None:
    h = _owner("zona2")
    client.post("/api/v1/zonas", headers=h, json={
        "name": "Zona A", "cep_ranges": [{"start": "20000000", "end": "20999999"}],
        "delivery_fee": "5.00",
    })
    from app.core.db import SessionLocal, set_tenant
    from app.modules.delivery.service import resolve_zone
    from app.modules.identity.models import Tenant
    from sqlalchemy import select

    db = SessionLocal()
    try:
        t = db.scalar(select(Tenant).where(Tenant.slug == "zona2"))
        set_tenant(db, t.id)
        from app.modules.catalog.service import default_store

        store = default_store(db, t.id)
        assert resolve_zone(db, store.id, "20000-100") is not None
        assert resolve_zone(db, store.id, "99999999") is None
    finally:
        db.close()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && ../.venv/bin/pytest app/tests/integration/test_zonas.py -q`
Expected: FAIL (404 nas rotas / ImportError `delivery.schemas`).

- [ ] **Step 3: Implementar schemas, service e rotas**

Criar `delivery/schemas.py`:

```python
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class CepRange(BaseModel):
    start: str = Field(min_length=8, max_length=9)
    end: str = Field(min_length=8, max_length=9)


class ZoneCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    store_id: UUID | None = None
    cep_ranges: list[CepRange] = []
    delivery_fee: Decimal = Field(default=Decimal("0"), ge=0)
    min_order_value: Decimal = Field(default=Decimal("0"), ge=0)
    eta_minutes: int = Field(default=30, ge=0)


class ZonePatch(BaseModel):
    name: str | None = None
    cep_ranges: list[CepRange] | None = None
    delivery_fee: Decimal | None = Field(default=None, ge=0)
    min_order_value: Decimal | None = Field(default=None, ge=0)
    eta_minutes: int | None = Field(default=None, ge=0)
    active: bool | None = None


class ZoneOut(BaseModel):
    id: UUID
    store_id: UUID
    name: str
    cep_ranges: list
    delivery_fee: Decimal
    min_order_value: Decimal
    eta_minutes: int
    active: bool
```

Criar `delivery/service.py`:

```python
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.delivery.models import Zone


def normalize_cep(cep: str) -> str:
    return "".join(ch for ch in cep if ch.isdigit())


def resolve_zone(db: Session, store_id: UUID, cep: str) -> Zone | None:
    normalized = normalize_cep(cep)
    if len(normalized) != 8:
        return None
    zones = db.scalars(
        select(Zone).where(Zone.store_id == store_id, Zone.active.is_(True))
    ).all()
    for zone in zones:
        for rng in zone.cep_ranges or []:
            start = normalize_cep(str(rng.get("start", "")))
            end = normalize_cep(str(rng.get("end", "")))
            if len(start) == 8 and len(end) == 8 and start <= normalized <= end:
                return zone
    return None
```

Criar `delivery/routes.py`:

```python
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_tenant_db, require_roles
from app.core.errors import DomainError
from app.core.tenant import Actor
from app.modules.catalog.service import default_store
from app.modules.delivery.models import Zone
from app.modules.delivery.schemas import CepRange, ZoneCreate, ZoneOut, ZonePatch

router = APIRouter(tags=["entregas"])


def _tenant_id(db: Session) -> UUID:
    return db.info["tenant_id"]


def _to_out(z: Zone) -> ZoneOut:
    return ZoneOut(
        id=z.id, store_id=z.store_id, name=z.name, cep_ranges=z.cep_ranges or [],
        delivery_fee=z.delivery_fee, min_order_value=z.min_order_value,
        eta_minutes=z.eta_minutes, active=z.active,
    )


def _ranges(payload_ranges: list[CepRange]) -> list[dict]:
    return [{"start": r.start, "end": r.end} for r in payload_ranges]


@router.post("/zonas", status_code=status.HTTP_201_CREATED)
def create_zone(
    payload: ZoneCreate,
    actor: Actor = Depends(require_roles("manager", "owner")),  # noqa: B008
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> ZoneOut:
    tid = _tenant_id(db)
    store_id = payload.store_id or default_store(db, tid).id
    zone = Zone(
        tenant_id=tid, store_id=store_id, name=payload.name,
        cep_ranges=_ranges(payload.cep_ranges), delivery_fee=payload.delivery_fee,
        min_order_value=payload.min_order_value, eta_minutes=payload.eta_minutes,
    )
    db.add(zone)
    db.commit()
    return _to_out(zone)


@router.get("/zonas")
def list_zones(db: Session = Depends(get_tenant_db)) -> list[ZoneOut]:  # noqa: B008
    rows = db.scalars(
        select(Zone).where(Zone.tenant_id == _tenant_id(db)).order_by(Zone.name)
    ).all()
    return [_to_out(z) for z in rows]


@router.patch("/zonas/{zone_id}")
def patch_zone(
    zone_id: UUID,
    payload: ZonePatch,
    actor: Actor = Depends(require_roles("manager", "owner")),  # noqa: B008
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> ZoneOut:
    zone = db.get(Zone, zone_id)
    if zone is None:
        raise DomainError("not_found", "Zona não encontrada.", status.HTTP_404_NOT_FOUND)
    if payload.name is not None:
        zone.name = payload.name
    if payload.cep_ranges is not None:
        zone.cep_ranges = _ranges(payload.cep_ranges)
    for field in ("delivery_fee", "min_order_value", "eta_minutes", "active"):
        value = getattr(payload, field)
        if value is not None:
            setattr(zone, field, value)
    db.commit()
    return _to_out(zone)
```

Em `main.py`: importar `from app.modules.delivery.routes import router as delivery_router` e adicionar `app.include_router(delivery_router, prefix="/api/v1")`.

- [ ] **Step 4: Rodar e ver passar**

Run: `cd backend && ../.venv/bin/ruff check . && ../.venv/bin/mypy . && ../.venv/bin/pytest app/tests/integration/test_zonas.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/delivery/schemas.py backend/app/modules/delivery/service.py backend/app/modules/delivery/routes.py backend/app/main.py backend/app/tests/integration/test_zonas.py
git commit -m "feat(delivery): zonas de entrega e resolucao por CEP"
```

---

### Task 4: Storefront — contexto público + cardápio

**Files:**
- Create: `backend/app/modules/storefront/{__init__,deps,service,schemas,routes}.py`
- Modify: `backend/app/main.py` (registrar `storefront_router`)
- Test: `backend/app/tests/integration/test_storefront_cardapio.py`

**Interfaces:**
- Consumes: `catalog.service.default_store`, `catalog.models.{Product,Category,ProductModifier}`, `identity.models.Tenant`.
- Produces: `GET /api/v1/public/{slug}/cardapio?q=&category_id=`; dep `storefront.deps.get_public_db`; schemas `PublicMenuOut`, `PublicProductOut`, `ModifierOut` (storefront-local), `PublicCategoryOut`.

- [ ] **Step 1: Escrever o teste que falha**

Criar `backend/app/tests/integration/test_storefront_cardapio.py`:

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _seed(slug: str) -> None:
    r = client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": f"{slug}@x.com",
        "password": "senha-segura", "name": "Dono",
    })
    assert r.status_code == 201, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    p = client.post("/api/v1/produtos", headers=h, json={"name": "X-Burger", "price": "25.00"})
    pid = p.json()["id"]
    client.post(f"/api/v1/produtos/{pid}/adicionais", headers=h, json={
        "group_name": "Ponto", "modifier_name": "Ao ponto", "required": True,
        "min_selection": 1, "max_selection": 1,
    })


def test_cardapio_publico_sem_auth() -> None:
    _seed("menu1")
    r = client.get("/api/v1/public/menu1/cardapio")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["tenant"]["slug"] == "menu1"
    assert len(body["products"]) == 1
    assert body["products"][0]["name"] == "X-Burger"
    assert body["products"][0]["modifiers"][0]["modifier_name"] == "Ao ponto"


def test_busca_e_filtro() -> None:
    _seed("menu2")
    r = client.get("/api/v1/public/menu2/cardapio", params={"q": "burger"})
    assert len(r.json()["products"]) == 1
    r2 = client.get("/api/v1/public/menu2/cardapio", params={"q": "inexistente"})
    assert r2.json()["products"] == []


def test_slug_inexistente_404() -> None:
    r = client.get("/api/v1/public/nao-existe/cardapio")
    assert r.status_code == 404, r.text
    assert r.json()["code"] == "store_not_found"


def test_isolamento_entre_tenants() -> None:
    _seed("menu3")
    _seed("menu4")
    assert client.get("/api/v1/public/menu3/cardapio").json()["tenant"]["slug"] == "menu3"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && ../.venv/bin/pytest app/tests/integration/test_storefront_cardapio.py -q`
Expected: FAIL (404).

- [ ] **Step 3: Implementar deps, schemas, service e rotas**

Criar `storefront/__init__.py` (vazio).

Criar `storefront/deps.py`:

```python
from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import set_tenant
from app.core.deps import get_db
from app.core.errors import DomainError
from app.modules.identity.models import Tenant


def get_public_db(slug: str, db: Session = Depends(get_db)) -> Iterator[Session]:  # noqa: B008
    """Resolve o tenant pelo slug (fora do RLS) e ativa o escopo da sessão."""
    tenant = db.scalar(select(Tenant).where(Tenant.slug == slug))
    if tenant is None or tenant.status != "active":
        raise DomainError(
            "store_not_found", "Loja não encontrada.", status.HTTP_404_NOT_FOUND
        )
    set_tenant(db, tenant.id)
    yield db
```

Criar `storefront/schemas.py`:

```python
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class ModifierOut(BaseModel):
    id: UUID
    group_name: str
    modifier_name: str
    price_delta: Decimal
    required: bool
    min_selection: int
    max_selection: int | None


class PublicProductOut(BaseModel):
    id: UUID
    name: str
    description: str | None
    price: Decimal
    image_url: str | None
    category_id: UUID | None
    preparation_time_minutes: int
    modifiers: list[ModifierOut]


class PublicCategoryOut(BaseModel):
    id: UUID
    name: str
    sort_order: int


class PublicStoreOut(BaseModel):
    id: UUID
    name: str
    delivery_enabled: bool
    pickup_enabled: bool


class PublicTenantOut(BaseModel):
    name: str
    slug: str


class PublicMenuOut(BaseModel):
    tenant: PublicTenantOut
    store: PublicStoreOut
    categories: list[PublicCategoryOut]
    products: list[PublicProductOut]
```

Criar `storefront/service.py`:

```python
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.catalog.models import Category, Product, ProductModifier, Store
from app.modules.catalog.service import default_store
from app.modules.identity.models import Tenant
from app.modules.storefront.schemas import (
    ModifierOut,
    PublicCategoryOut,
    PublicMenuOut,
    PublicProductOut,
    PublicStoreOut,
    PublicTenantOut,
)


def _modifiers(db: Session, product_id: UUID) -> list[ModifierOut]:
    rows = db.scalars(
        select(ProductModifier)
        .where(ProductModifier.product_id == product_id, ProductModifier.active.is_(True))
        .order_by(ProductModifier.group_name, ProductModifier.modifier_name)
    ).all()
    return [
        ModifierOut(
            id=m.id, group_name=m.group_name, modifier_name=m.modifier_name,
            price_delta=m.price_delta, required=m.required,
            min_selection=m.min_selection, max_selection=m.max_selection,
        )
        for m in rows
    ]


def public_menu(
    db: Session, tenant: Tenant, store: Store, q: str | None, category_id: UUID | None
) -> PublicMenuOut:
    query = select(Product).where(Product.store_id == store.id, Product.active.is_(True))
    if category_id is not None:
        query = query.where(Product.category_id == category_id)
    if q:
        query = query.where(Product.name.ilike(f"%{q}%"))
    products = db.scalars(query.order_by(Product.name)).all()

    categories = db.scalars(
        select(Category)
        .where(Category.tenant_id == tenant.id, Category.active.is_(True))
        .order_by(Category.sort_order)
    ).all()

    return PublicMenuOut(
        tenant=PublicTenantOut(name=tenant.name, slug=tenant.slug),
        store=PublicStoreOut(
            id=store.id, name=store.name, delivery_enabled=store.delivery_enabled,
            pickup_enabled=store.pickup_enabled,
        ),
        categories=[
            PublicCategoryOut(id=c.id, name=c.name, sort_order=c.sort_order) for c in categories
        ],
        products=[
            PublicProductOut(
                id=p.id, name=p.name, description=p.description, price=p.price,
                image_url=p.image_url, category_id=p.category_id,
                preparation_time_minutes=p.preparation_time_minutes,
                modifiers=_modifiers(db, p.id),
            )
            for p in products
        ],
    )


def current_store(db: Session, tenant_id: UUID) -> Store:
    return default_store(db, tenant_id)
```

> Nota: `q`/`category_id` entram como `Query`. O `_modifiers` por produto gera N+1 aceitável para cardápios (<100 itens); se o revisor apontar, agregue com um único `select(...).where(in_)`.

Criar `storefront/routes.py`:

```python
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.modules.identity.models import Tenant
from app.modules.storefront.deps import get_public_db
from app.modules.storefront.schemas import PublicMenuOut
from app.modules.storefront.service import current_store, public_menu

router = APIRouter(tags=["storefront"])


@router.get("/public/{slug}/cardapio")
def get_cardapio(
    slug: str,
    q: str | None = Query(default=None, max_length=80),
    category_id: UUID | None = None,
    db: Session = Depends(get_public_db),  # noqa: B008
) -> PublicMenuOut:
    tid = db.info["tenant_id"]
    tenant = db.get(Tenant, tid)
    assert tenant is not None  # resolvido em get_public_db
    store = current_store(db, tid)
    return public_menu(db, tenant, store, q, category_id)
```

Em `main.py`: importar `from app.modules.storefront.routes import router as storefront_router` e adicionar `app.include_router(storefront_router, prefix="/api/v1")`.

- [ ] **Step 4: Rodar e ver passar**

Run: `cd backend && ../.venv/bin/ruff check . && ../.venv/bin/mypy . && ../.venv/bin/pytest app/tests/integration/test_storefront_cardapio.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/storefront/ backend/app/main.py backend/app/tests/integration/test_storefront_cardapio.py
git commit -m "feat(storefront): cardapio publico por slug"
```

### Task 5: ViaCEP + estimativa de entrega

**Files:**
- Create: `backend/app/modules/storefront/viacep.py`
- Modify: `backend/app/modules/storefront/schemas.py`, `backend/app/modules/storefront/routes.py`
- Test: `backend/app/tests/integration/test_storefront_cep.py`, `backend/app/tests/integration/test_storefront_entrega.py`

**Interfaces:**
- Consumes: `delivery.service.resolve_zone`, `storefront.deps.get_public_db`.
- Produces: `storefront.viacep.lookup(cep) -> dict` + `ViaCepError`; `GET /api/v1/public/{slug}/cep/{cep}`; `GET /api/v1/public/{slug}/entrega?cep=`; schema `DeliveryEstimateOut`.

- [ ] **Step 1: Escrever os testes que falham**

Criar `backend/app/tests/integration/test_storefront_cep.py`:

```python
from fastapi.testclient import TestClient

from app.main import app
from app.modules.storefront import viacep

client = TestClient(app)


def _seed(slug: str) -> None:
    client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": f"{slug}@x.com",
        "password": "senha-segura", "name": "Dono",
    })


def test_cep_retorna_endereco(monkeypatch) -> None:
    _seed("cep1")
    monkeypatch.setattr(viacep, "lookup", lambda cep: {
        "cep": "01001000", "street": "Praça da Sé", "district": "Sé",
        "city": "São Paulo", "state": "SP",
    })
    r = client.get("/api/v1/public/cep1/cep/01001000")
    assert r.status_code == 200, r.text
    assert r.json()["city"] == "São Paulo"


def test_cep_invalido_422() -> None:
    _seed("cep2")
    r = client.get("/api/v1/public/cep2/cep/123")
    assert r.status_code == 422, r.text


def test_cep_nao_encontrado_404(monkeypatch) -> None:
    _seed("cep3")

    def _raise(cep: str) -> dict:
        raise viacep.ViaCepError("not_found")

    monkeypatch.setattr(viacep, "lookup", _raise)
    r = client.get("/api/v1/public/cep3/cep/99999999")
    assert r.status_code == 404 and r.json()["code"] == "cep_not_found"


def test_cep_indisponivel_503(monkeypatch) -> None:
    _seed("cep4")

    def _raise(cep: str) -> dict:
        raise viacep.ViaCepError("unavailable")

    monkeypatch.setattr(viacep, "lookup", _raise)
    r = client.get("/api/v1/public/cep4/cep/01001000")
    assert r.status_code == 503 and r.json()["code"] == "cep_unavailable"
```

Criar `backend/app/tests/integration/test_storefront_entrega.py`:

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _owner(slug: str) -> dict[str, str]:
    r = client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": f"{slug}@x.com",
        "password": "senha-segura", "name": "Dono",
    })
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_entrega_com_zona_coberta() -> None:
    h = _owner("ent1")
    client.post("/api/v1/zonas", headers=h, json={
        "name": "Centro", "cep_ranges": [{"start": "01000000", "end": "01999999"}],
        "delivery_fee": "8.00", "min_order_value": "15.00", "eta_minutes": 45,
    })
    r = client.get("/api/v1/public/ent1/entrega", params={"cep": "01001000"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["covered"] is True and body["delivery_fee"] == "8.00"
    assert body["eta_minutes"] == 45


def test_entrega_cep_fora_retorna_nao_coberto() -> None:
    h = _owner("ent2")
    client.post("/api/v1/zonas", headers=h, json={
        "name": "Centro", "cep_ranges": [{"start": "01000000", "end": "01999999"}],
    })
    r = client.get("/api/v1/public/ent2/entrega", params={"cep": "99999999"})
    assert r.json()["covered"] is False


def test_entrega_sem_zonas_fallback() -> None:
    _owner("ent3")
    r = client.get("/api/v1/public/ent3/entrega", params={"cep": "01001000"})
    body = r.json()
    assert body["covered"] is True and body["delivery_fee"] == "0.00"
    assert body["eta_minutes"] == 30
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && ../.venv/bin/pytest app/tests/integration/test_storefront_cep.py app/tests/integration/test_storefront_entrega.py -q`
Expected: FAIL.

- [ ] **Step 3: Implementar viacep, schemas e rotas**

Criar `storefront/viacep.py`:

```python
from __future__ import annotations

import json
import urllib.request

VIACEP_URL = "https://viacep.com.br/ws/{cep}/json/"
TIMEOUT_SECONDS = 5


class ViaCepError(Exception):
    def __init__(self, kind: str) -> None:
        super().__init__(kind)
        self.kind = kind  # "invalid" | "not_found" | "unavailable"


def lookup(cep: str) -> dict:
    digits = "".join(ch for ch in cep if ch.isdigit())
    if len(digits) != 8:
        raise ViaCepError("invalid")
    request = urllib.request.Request(
        VIACEP_URL.format(cep=digits), headers={"User-Agent": "StockChef/1.0"}
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ViaCepError("unavailable") from exc
    if data.get("erro"):
        raise ViaCepError("not_found")
    return {
        "cep": digits,
        "street": data.get("logradouro", ""),
        "district": data.get("bairro", ""),
        "city": data.get("localidade", ""),
        "state": data.get("uf", ""),
    }
```

Append em `storefront/schemas.py`:

```python
class DeliveryEstimateOut(BaseModel):
    covered: bool
    zone_name: str | None
    delivery_fee: Decimal
    min_order_value: Decimal
    eta_minutes: int
```

Append em `storefront/routes.py` (imports no topo: `from app.core.errors import DomainError`, `from app.modules.delivery.service import resolve_zone`, `from app.modules.storefront.service import current_store`, `from app.modules.storefront.viacep import ViaCepError, lookup`, `from fastapi import status`, `from decimal import Decimal`):

```python
@router.get("/public/{slug}/cep/{cep}")
def get_cep(slug: str, cep: str, db: Session = Depends(get_public_db)) -> dict:  # noqa: B008
    try:
        return lookup(cep)
    except ViaCepError as exc:
        if exc.kind == "invalid":
            raise DomainError(
                "cep_invalid", "CEP inválido.", status.HTTP_422_UNPROCESSABLE_ENTITY
            ) from exc
        if exc.kind == "not_found":
            raise DomainError(
                "cep_not_found", "CEP não encontrado.", status.HTTP_404_NOT_FOUND
            ) from exc
        raise DomainError(
            "cep_unavailable",
            "Consulta de CEP indisponível no momento.",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        ) from exc


@router.get("/public/{slug}/entrega")
def get_entrega(
    slug: str, cep: str, db: Session = Depends(get_public_db)  # noqa: B008
) -> DeliveryEstimateOut:
    tid = db.info["tenant_id"]
    store = current_store(db, tid)
    zone = resolve_zone(db, store.id, cep)
    if zone is not None:
        return DeliveryEstimateOut(
            covered=True, zone_name=zone.name, delivery_fee=zone.delivery_fee,
            min_order_value=zone.min_order_value, eta_minutes=zone.eta_minutes,
        )
    has_zones = bool(
        db.scalar(select(Zone.id).where(Zone.store_id == store.id, Zone.active.is_(True)))
    )
    return DeliveryEstimateOut(
        covered=not has_zones, zone_name=None, delivery_fee=Decimal("0"),
        min_order_value=Decimal("0"), eta_minutes=30 if not has_zones else 0,
    )
```

> Imports adicionais em `routes.py`: `from app.modules.delivery.models import Zone` e `from app.modules.storefront.schemas import DeliveryEstimateOut`.

- [ ] **Step 4: Rodar e ver passar**

Run: `cd backend && ../.venv/bin/ruff check . && ../.venv/bin/mypy . && ../.venv/bin/pytest app/tests/integration/test_storefront_cep.py app/tests/integration/test_storefront_entrega.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/modules/storefront/viacep.py backend/app/modules/storefront/schemas.py backend/app/modules/storefront/routes.py backend/app/tests/integration/test_storefront_cep.py backend/app/tests/integration/test_storefront_entrega.py
git commit -m "feat(storefront): consulta ViaCEP e estimativa de entrega"
```

---

### Task 6: Pedido público (checkout)

**Files:**
- Modify: `backend/app/modules/storefront/schemas.py`, `backend/app/modules/storefront/service.py`, `backend/app/modules/storefront/routes.py`
- Test: `backend/app/tests/integration/test_storefront_pedido.py`

**Interfaces:**
- Consumes: `orders.service.{availability, recipe_snapshot}`, `orders.models.{Order,OrderItem,OrderEvent,Customer,Payment}`, `catalog.models.Product`, `delivery.service.resolve_zone`, `storefront.deps.get_public_db`.
- Produces: `POST /api/v1/public/{slug}/pedidos`, `GET /api/v1/public/{slug}/pedidos/{code}`; schemas `PublicOrderCreate`, `PublicOrderItemIn`, `PublicOrderOut`, `PublicOrderItemOut`.

- [ ] **Step 1: Escrever o teste que falha**

Criar `backend/app/tests/integration/test_storefront_pedido.py`:

```python
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _seed(slug: str, *, with_zone: bool = True) -> tuple[dict[str, str], str]:
    r = client.post("/api/v1/auth/register", json={
        "tenant_name": slug, "tenant_slug": slug, "email": f"{slug}@x.com",
        "password": "senha-segura", "name": "Dono",
    })
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    if with_zone:
        client.post("/api/v1/zonas", headers=h, json={
            "name": "Centro", "cep_ranges": [{"start": "01000000", "end": "01999999"}],
            "delivery_fee": "6.00", "min_order_value": "10.00", "eta_minutes": 35,
        })
    p = client.post("/api/v1/produtos", headers=h, json={"name": "X-Burger", "price": "25.00"})
    return h, p.json()["id"]


def _body(pid: str, **over) -> dict:
    body = {
        "customer_name": "Ana", "customer_phone": "11999999999",
        "fulfillment_type": "delivery", "cep": "01001000",
        "address": {"street": "Sé", "number": "1", "district": "Sé", "city": "SP", "state": "SP"},
        "idempotency_key": "chave-publica-0001",
        "items": [{"product_id": pid, "quantity": 1, "modifier_ids": []}],
    }
    body.update(over)
    return body


def test_cria_pedido_publico_com_taxa() -> None:
    _h, pid = _seed("pub1")
    r = client.post("/api/v1/public/pub1/pedidos", json=_body(pid))
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["subtotal"] == "25.00" and body["delivery_fee"] == "6.00"
    assert body["total"] == "31.00" and body["status"] == "received"
    assert body["eta_minutes"] == 35
    code = body["code"]

    got = client.get(f"/api/v1/public/pub1/pedidos/{code}")
    assert got.status_code == 200 and got.json()["code"] == code


def test_idempotencia_nao_duplica() -> None:
    _h, pid = _seed("pub2")
    r1 = client.post("/api/v1/public/pub2/pedidos", json=_body(pid))
    r2 = client.post("/api/v1/public/pub2/pedidos", json=_body(pid))
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["code"] == r2.json()["code"]


def test_pickup_sem_taxa() -> None:
    _h, pid = _seed("pub3", with_zone=False)
    r = client.post("/api/v1/public/pub3/pedidos", json=_body(
        pid, fulfillment_type="pickup", cep=None, address=None,
        idempotency_key="chave-pickup-0001",
    ))
    assert r.status_code == 201, r.text
    assert r.json()["delivery_fee"] == "0.00" and r.json()["total"] == "25.00"


def test_cep_nao_coberto_422() -> None:
    _h, pid = _seed("pub4")
    r = client.post("/api/v1/public/pub4/pedidos", json=_body(
        pid, cep="99999999", idempotency_key="chave-fora-0001",
    ))
    assert r.status_code == 422 and r.json()["code"] == "cep_not_covered"


def test_abaixo_do_minimo_422() -> None:
    h, _pid = _seed("pub5")
    p = client.post("/api/v1/produtos", headers=h, json={"name": "Água", "price": "3.00"}).json()
    r = client.post("/api/v1/public/pub5/pedidos", json=_body(
        p["id"], idempotency_key="chave-min-0001",
    ))
    assert r.status_code == 422 and r.json()["code"] == "below_min_order"


def test_adicional_invalido_422() -> None:
    _h, pid = _seed("pub6")
    r = client.post("/api/v1/public/pub6/pedidos", json=_body(pid, items=[
        {"product_id": pid, "quantity": 1, "modifier_ids": ["00000000-0000-0000-0000-000000000000"]},
    ], idempotency_key="chave-mod-0001"))
    assert r.status_code == 422 and r.json()["code"] == "invalid_modifiers"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd backend && ../.venv/bin/pytest app/tests/integration/test_storefront_pedido.py -q`
Expected: FAIL (404).

- [ ] **Step 3: Implementar schemas, service e rotas**

Append em `storefront/schemas.py` (imports: `from datetime import datetime`, `from typing import Literal`):

```python
class PublicOrderItemIn(BaseModel):
    product_id: UUID
    quantity: int = Field(ge=1)
    notes: str | None = None
    modifier_ids: list[UUID] = []


class PublicOrderCreate(BaseModel):
    customer_name: str = Field(min_length=1, max_length=120)
    customer_phone: str = Field(min_length=8, max_length=20)
    fulfillment_type: Literal["delivery", "pickup"] = "delivery"
    cep: str | None = None
    address: dict | None = None
    notes: str | None = None
    idempotency_key: str = Field(min_length=8, max_length=64)
    items: list[PublicOrderItemIn] = Field(min_length=1)


class PublicOrderItemOut(BaseModel):
    product_name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    modifiers: list


class PublicOrderOut(BaseModel):
    code: str
    status: str
    fulfillment_type: str
    subtotal: Decimal
    delivery_fee: Decimal
    total: Decimal
    eta_minutes: int | None
    created_at: datetime
    items: list[PublicOrderItemOut]
```

Append em `storefront/service.py` (imports: `import secrets`, `from collections import defaultdict`, `from datetime import UTC, datetime, timedelta`, `from decimal import ROUND_HALF_UP, Decimal`, `from sqlalchemy import select`; models: `from app.modules.orders.models import Customer, Order, OrderEvent, OrderItem, Payment`; service: `from app.modules.orders.service import availability, recipe_snapshot`; delivery: `from app.modules.delivery.service import resolve_zone`; errors: `from app.core.errors import DomainError`; `from fastapi import status`):

```python
def _gen_code(db: Session, store_id: UUID) -> str:
    for _ in range(5):
        code = f"SC-{secrets.token_hex(6).upper()}"
        if not db.scalar(select(Order).where(Order.code == code)):
            return code
    raise DomainError(
        "code_conflict", "Não foi possível gerar um código.",
        status.HTTP_503_SERVICE_UNAVAILABLE,
    )


def _upsert_customer(db: Session, tid: UUID, name: str, phone: str, address: dict) -> Customer:
    cust = db.scalar(
        select(Customer).where(Customer.tenant_id == tid, Customer.phone == phone)
    )
    if cust is None:
        cust = Customer(tenant_id=tid, name=name, phone=phone, address=address)
        db.add(cust)
        db.flush()
    else:
        cust.name = name
        if address:
            cust.address = address
    return cust


def _resolve_modifiers(
    db: Session, product: Product, modifier_ids: list[UUID]
) -> tuple[list[ProductModifier], Decimal]:
    mods = db.scalars(
        select(ProductModifier).where(
            ProductModifier.product_id == product.id, ProductModifier.active.is_(True)
        )
    ).all()
    by_id = {m.id: m for m in mods}
    chosen = []
    for mid in modifier_ids:
        mod = by_id.get(mid)
        if mod is None:
            raise DomainError(
                "invalid_modifiers", "Adicional inválido para o produto.",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        chosen.append(mod)
    groups: defaultdict[str, list[ProductModifier]] = defaultdict(list)
    for mod in mods:
        groups[mod.group_name].append(mod)
    for group_name, group_mods in groups.items():
        selected = [m for m in chosen if m.group_name == group_name]
        required = any(m.required for m in group_mods)
        min_sel = max([m.min_selection for m in group_mods] or [0])
        maxes = [m.max_selection for m in group_mods if m.max_selection is not None]
        max_sel = min(maxes) if maxes else None
        if required and len(selected) < max(min_sel, 1):
            raise DomainError(
                "invalid_modifiers", f"Escolha obrigatória no grupo '{group_name}'.",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        if len(selected) < min_sel or (max_sel is not None and len(selected) > max_sel):
            raise DomainError(
                "invalid_modifiers", f"Seleção inválida no grupo '{group_name}'.",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
    delta = sum((m.price_delta for m in chosen), Decimal("0"))
    return chosen, delta


def create_public_order(
    db: Session, tenant: Tenant, store: Store, payload: PublicOrderCreate
) -> Order:
    existing = db.scalar(
        select(Payment).where(
            Payment.idempotency_key == f"order.public:{payload.idempotency_key}"
        )
    )
    if existing is not None:
        return db.get(Order, existing.order_id)  # type: ignore[return-value]

    tid = tenant.id
    if payload.fulfillment_type == "delivery":
        if not payload.cep or not payload.address:
            raise DomainError(
                "address_required", "Endereço é obrigatório para entrega.",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        zone = resolve_zone(db, store.id, payload.cep)
        has_zones = bool(
            db.scalar(select(Zone.id).where(Zone.store_id == store.id, Zone.active.is_(True)))
        )
        if zone is None and has_zones:
            raise DomainError(
                "cep_not_covered", "Não entregamos nesse CEP.",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        delivery_fee = zone.delivery_fee if zone else Decimal("0")
        min_order = zone.min_order_value if zone else Decimal("0")
        eta = zone.eta_minutes if zone else 30
    else:
        delivery_fee = Decimal("0")
        min_order = Decimal("0")
        eta = 0

    resolved = []
    subtotal = Decimal("0")
    for it in payload.items:
        product = db.get(Product, it.product_id)
        if product is None or product.store_id != store.id or not product.active:
            raise DomainError(
                "product_not_found", "Produto não encontrado.",
                status.HTTP_404_NOT_FOUND,
            )
        availability(db, store.id, [(product.id, it.quantity)])
        chosen, delta = _resolve_modifiers(db, product, it.modifier_ids)
        unit = (product.price + delta).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        line = (unit * it.quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        subtotal += line
        resolved.append((product, it, chosen, unit, line))

    if subtotal < min_order:
        raise DomainError(
            "below_min_order",
            f"Pedido mínimo de {min_order}.",
            status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    address = payload.address or {}
    customer = _upsert_customer(db, tid, payload.customer_name, payload.customer_phone, address)
    total = (subtotal + delivery_fee).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    order = Order(
        tenant_id=tid, store_id=store.id, customer_id=customer.id, code=_gen_code(db, store.id),
        status="received", channel="own_pwa", fulfillment_type=payload.fulfillment_type,
        subtotal=subtotal, delivery_fee=delivery_fee, total=total, notes=payload.notes,
        expected_time=datetime.now(UTC) + timedelta(minutes=eta) if eta else None,
    )
    db.add(order)
    db.flush()
    for product, it, chosen, unit, line in resolved:
        db.add(OrderItem(
            tenant_id=tid, order_id=order.id, product_id=product.id, quantity=it.quantity,
            unit_price=unit, total_price=line, notes=it.notes,
            modifiers=[
                {"id": str(m.id), "group_name": m.group_name,
                 "modifier_name": m.modifier_name, "price_delta": str(m.price_delta)}
                for m in chosen
            ],
            recipe_snapshot=recipe_snapshot(db, product.id),
        ))
    db.add(OrderEvent(
        tenant_id=tid, order_id=order.id, event_type="order.created",
        from_status=None, to_status="received",
    ))
    db.add(Payment(
        tenant_id=tid, order_id=order.id, provider="cash", method="cash", amount=total,
        status="pending", idempotency_key=f"order.public:{payload.idempotency_key}",
    ))
    db.commit()
    return order


def _eta_minutes(order: Order) -> int | None:
    if order.expected_time is None:
        return None
    delta = order.expected_time - datetime.now(UTC)
    return max(0, int(delta.total_seconds() // 60))


def public_order_out(db: Session, order: Order) -> PublicOrderOut:
    items = db.scalars(
        select(OrderItem).where(OrderItem.order_id == order.id)
    ).all()
    out_items = []
    for it in items:
        product = db.get(Product, it.product_id)
        out_items.append(PublicOrderItemOut(
            product_name=product.name if product else "",
            quantity=it.quantity, unit_price=it.unit_price, total_price=it.total_price,
            modifiers=it.modifiers or [],
        ))
    return PublicOrderOut(
        code=order.code, status=order.status, fulfillment_type=order.fulfillment_type,
        subtotal=order.subtotal, delivery_fee=order.delivery_fee, total=order.total,
        eta_minutes=_eta_minutes(order), created_at=order.created_at, items=out_items,
    )
```

> Nota: `PublicOrderCreate`/`PublicOrderOut` precisam entrar nos imports de `schemas` no `service.py`. `Zone` (delivery.models) também.

Append em `storefront/routes.py`:

```python
@router.post("/public/{slug}/pedidos", status_code=status.HTTP_201_CREATED)
def create_pedido(
    slug: str, payload: PublicOrderCreate, db: Session = Depends(get_public_db)  # noqa: B008
) -> PublicOrderOut:
    tid = db.info["tenant_id"]
    tenant = db.get(Tenant, tid)
    assert tenant is not None
    store = current_store(db, tid)
    order = create_public_order(db, tenant, store, payload)
    return public_order_out(db, order)


@router.get("/public/{slug}/pedidos/{code}")
def get_pedido(
    slug: str, code: str, db: Session = Depends(get_public_db)  # noqa: B008
) -> PublicOrderOut:
    order = db.scalar(select(Order).where(Order.code == code))
    if order is None:
        raise DomainError("not_found", "Pedido não encontrado.", status.HTTP_404_NOT_FOUND)
    return public_order_out(db, order)
```

> Imports extra em `routes.py`: `from app.modules.orders.models import Order`, `from app.modules.storefront.schemas import PublicOrderCreate, PublicOrderOut`, e `from app.modules.storefront.service import create_public_order, public_order_out`.

- [ ] **Step 4: Rodar e ver passar**

Run: `cd backend && ../.venv/bin/ruff check . && ../.venv/bin/mypy . && ../.venv/bin/pytest app/tests/integration/test_storefront_pedido.py -q`
Expected: PASS (todos os 6 testes).

- [ ] **Step 5: Rodar a suíte backend completa**

Run: `cd backend && ../.venv/bin/pytest -q`
Expected: PASS (sem regressões nas fatias anteriores).

- [ ] **Step 6: Commit**

```bash
git add backend/app/modules/storefront/schemas.py backend/app/modules/storefront/service.py backend/app/modules/storefront/routes.py backend/app/tests/integration/test_storefront_pedido.py
git commit -m "feat(storefront): checkout publico com pagamento em dinheiro"
```

### Task 7: publicApi + tipos públicos

**Files:**
- Create: `frontend/src/api/public.ts`
- Modify: `frontend/src/api/types.ts`

**Interfaces:**
- Consumes: `ApiError` de `api/client.ts`.
- Produces: `publicApi<T>(path, init)`; tipos `PublicMenu`, `PublicProduct`, `PublicModifier`, `PublicCategory`, `PublicStore`, `PublicTenant`, `DeliveryEstimate`, `PublicOrder`, `PublicOrderItem`, `Zone`, `ZoneCreate`.

- [ ] **Step 1: Escrever o teste que falha**

Criar `frontend/src/test/public-api.test.ts`:

```ts
import { beforeEach, describe, expect, it, vi } from "vitest";
import { publicApi } from "../api/public";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("publicApi", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("não envia Authorization e monta a URL", async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ tenant: { slug: "x" } }));
    vi.stubGlobal("fetch", fetchMock);
    const body = await publicApi<{ tenant: { slug: string } }>("/public/x/cardapio");
    expect(body.tenant.slug).toBe("x");
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = new Headers(init.headers);
    expect(headers.get("Authorization")).toBeNull();
  });

  it("converte erro em ApiError com code", async () => {
    vi.stubGlobal("fetch", vi.fn(async () =>
      jsonResponse({ detail: "CEP não encontrado.", code: "cep_not_found" }, 404),
    ));
    await expect(publicApi("/public/x/cep/9")).rejects.toMatchObject({
      status: 404,
      code: "cep_not_found",
    });
  });
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd frontend && npm test -- public-api`
Expected: FAIL (módulo `../api/public` não existe).

- [ ] **Step 3: Implementar publicApi e tipos**

Criar `frontend/src/api/public.ts`:

```ts
import { ApiError } from "./client";

export async function publicApi<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  const res = await fetch(`/api/v1${path}`, { ...init, headers });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(body.detail ?? "Erro inesperado.", res.status, body.code);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
```

Append em `frontend/src/api/types.ts`:

```ts
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
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd frontend && npm run typecheck && npm run lint && npm test -- public-api`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/api/public.ts frontend/src/api/types.ts frontend/src/test/public-api.test.ts
git commit -m "feat(web): publicApi e tipos do storefront"
```

---

### Task 8: CartContext + ModifierDialog

**Files:**
- Create: `frontend/src/cart/CartContext.tsx`, `frontend/src/components/ModifierDialog.tsx`
- Test: `frontend/src/test/modifiers.test.tsx`

**Interfaces:**
- Produces: `CartProvider`, `useCart()` com `{ lines, add, setQuantity, remove, clear, subtotal, count }`; `ModifierDialog` com props `{ product: PublicProduct; onConfirm: (c) => void; onCancel: () => void }`.

- [ ] **Step 1: Escrever os testes que falham**

Criar `frontend/src/test/modifiers.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import ModifierDialog from "../components/ModifierDialog";
import type { PublicProduct } from "../api/types";

const product: PublicProduct = {
  id: "p1", name: "X-Burger", description: null, price: "25.00", image_url: null,
  category_id: null, preparation_time_minutes: 10,
  modifiers: [
    { id: "m1", group_name: "Ponto", modifier_name: "Ao ponto", price_delta: "0.00",
      required: true, min_selection: 1, max_selection: 1 },
    { id: "m2", group_name: "Extras", modifier_name: "Bacon", price_delta: "3.00",
      required: false, min_selection: 0, max_selection: 2 },
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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd frontend && npm test -- modifiers`
Expected: FAIL (módulos ausentes).

- [ ] **Step 3: Implementar CartContext e ModifierDialog**

Criar `frontend/src/cart/CartContext.tsx`:

```tsx
import {
  createContext,
  type ReactNode,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useLocation } from "react-router-dom";

export interface CartModifier {
  id: string;
  group_name: string;
  modifier_name: string;
  price_delta: string;
}

export interface CartLine {
  key: string;
  productId: string;
  name: string;
  unitPrice: string;
  quantity: number;
  notes?: string;
  modifiers: CartModifier[];
}

interface CartValue {
  lines: CartLine[];
  add: (line: Omit<CartLine, "key">) => void;
  setQuantity: (key: string, quantity: number) => void;
  remove: (key: string) => void;
  clear: () => void;
  subtotal: number;
  count: number;
}

const CartContext = createContext<CartValue | null>(null);

function lineKey(line: Omit<CartLine, "key">): string {
  const mods = line.modifiers.map((m) => m.id).sort().join(",");
  return `${line.productId}|${mods}|${line.notes ?? ""}`;
}

export function CartProvider({ children }: { children: ReactNode }) {
  const location = useLocation();
  const slug = useMemo(() => {
    const match = location.pathname.match(/^\/cardapio\/([^/]+)/);
    return match ? match[1] : null;
  }, [location.pathname]);
  const [lines, setLines] = useState<CartLine[]>([]);

  useEffect(() => {
    if (!slug) {
      setLines([]);
      return;
    }
    const raw = localStorage.getItem(`sc_cart:${slug}`);
    setLines(raw ? (JSON.parse(raw) as CartLine[]) : []);
  }, [slug]);

  useEffect(() => {
    if (slug) localStorage.setItem(`sc_cart:${slug}`, JSON.stringify(lines));
  }, [slug, lines]);

  const value: CartValue = {
    lines,
    add: (line) =>
      setLines((ls) => {
        const key = lineKey(line);
        const existing = ls.find((l) => l.key === key);
        if (existing) {
          return ls.map((l) => (l.key === key ? { ...l, quantity: l.quantity + line.quantity } : l));
        }
        return [...ls, { ...line, key }];
      }),
    setQuantity: (key, quantity) =>
      setLines((ls) => ls.map((l) => (l.key === key ? { ...l, quantity } : l))),
    remove: (key) => setLines((ls) => ls.filter((l) => l.key !== key)),
    clear: () => setLines([]),
    subtotal: lines.reduce((sum, l) => sum + Number(l.unitPrice) * l.quantity, 0),
    count: lines.reduce((sum, l) => sum + l.quantity, 0),
  };

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart(): CartValue {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart precisa de CartProvider");
  return ctx;
}
```

Criar `frontend/src/components/ModifierDialog.tsx`:

```tsx
import { useState } from "react";
import type { PublicModifier, PublicProduct } from "../api/types";
import { type CartModifier, useCart } from "../cart/CartContext";

interface Props {
  product: PublicProduct;
  onConfirm: (line: {
    productId: string;
    name: string;
    unitPrice: string;
    quantity: number;
    notes?: string;
    modifiers: CartModifier[];
  }) => void;
  onCancel: () => void;
}

export default function ModifierDialog({ product, onConfirm, onCancel }: Props) {
  const [selected, setSelected] = useState<string[]>([]);
  const [qty, setQty] = useState(1);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");

  const groups = Array.from(new Set(product.modifiers.map((m) => m.group_name)));

  function toggle(mod: PublicModifier) {
    setSelected((sel) => {
      const groupMods = product.modifiers.filter((m) => m.group_name === mod.group_name);
      const maxes = groupMods.map((m) => m.max_selection).filter((v): v is number => v !== null);
      const groupMax = maxes.length ? Math.min(...maxes) : 1;
      const inGroup = sel.filter((id) =>
        groupMods.some((gm) => gm.id === id),
      );
      if (sel.includes(mod.id)) return sel.filter((id) => id !== mod.id);
      if (inGroup.length >= groupMax) {
        return [...sel.filter((id) => !groupMods.some((gm) => gm.id === id)), mod.id];
      }
      return [...sel, mod.id];
    });
  }

  function confirm() {
    for (const group of groups) {
      const groupMods = product.modifiers.filter((m) => m.group_name === group);
      const chosen = selected.filter((id) => groupMods.some((m) => m.id === id));
      const required = groupMods.some((m) => m.required);
      const min = Math.max(...groupMods.map((m) => m.min_selection), required ? 1 : 0);
      if (chosen.length < min) {
        setError(`Escolha uma opção em "${group}".`);
        return;
      }
    }
    const chosenMods = product.modifiers.filter((m) => selected.includes(m.id));
    const delta = chosenMods.reduce((sum, m) => sum + Number(m.price_delta), 0);
    const unitPrice = (Number(product.price) + delta).toFixed(2);
    onConfirm({
      productId: product.id,
      name: product.name,
      unitPrice,
      quantity: qty,
      notes: notes || undefined,
      modifiers: chosenMods.map((m) => ({
        id: m.id, group_name: m.group_name, modifier_name: m.modifier_name,
        price_delta: m.price_delta,
      })),
    });
  }

  return (
    <div role="dialog" aria-modal="true" aria-label={product.name}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="w-full max-w-md space-y-4 rounded bg-white p-4">
        <h2 className="text-lg font-semibold">{product.name}</h2>
        {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
        {groups.map((group) => (
          <fieldset key={group} className="space-y-1">
            <legend className="text-sm font-medium">{group}</legend>
            {product.modifiers
              .filter((m) => m.group_name === group)
              .map((m) => (
                <label key={m.id} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={selected.includes(m.id)}
                    onChange={() => toggle(m)}
                  />
                  <span>
                    {m.modifier_name}
                    {Number(m.price_delta) > 0 ? ` (+R$ ${Number(m.price_delta).toFixed(2)})` : ""}
                  </span>
                </label>
              ))}
          </fieldset>
        ))}
        <label className="block space-y-1">
          <span className="text-sm">Observações</span>
          <input value={notes} onChange={(e) => setNotes(e.target.value)}
            className="w-full rounded border px-3 py-2" />
        </label>
        <label className="block space-y-1">
          <span className="text-sm">Quantidade</span>
          <input type="number" min={1} value={qty}
            onChange={(e) => setQty(Math.max(1, Number(e.target.value)))}
            className="w-24 rounded border px-3 py-2" />
        </label>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onCancel} className="rounded border px-4 py-2">Cancelar</button>
          <button type="button" onClick={confirm}
            className="rounded bg-blue-600 px-4 py-2 text-white">Adicionar</button>
        </div>
      </div>
    </div>
  );
}

export function useAddToCart() {
  const { add } = useCart();
  return add;
}
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd frontend && npm run typecheck && npm run lint && npm test -- modifiers`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/cart/CartContext.tsx frontend/src/components/ModifierDialog.tsx frontend/src/test/modifiers.test.tsx
git commit -m "feat(web): carrinho e dialogo de adicionais"
```

---

### Task 9: CardapioPage + CarrinhoPage

**Files:**
- Create: `frontend/src/pages/public/CardapioPage.tsx`, `frontend/src/pages/public/CarrinhoPage.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/test/cardapio.test.tsx`

**Interfaces:**
- Consumes: `publicApi`, `useCart`, `ModifierDialog`, tipos `PublicMenu`.
- Produces: rotas `/cardapio/:slug` (CardapioPage) e `/cardapio/:slug/carrinho` (CarrinhoPage), fora do `Protected`, com `CartProvider` envolvendo ambas.

- [ ] **Step 1: Escrever o teste que falha**

Criar `frontend/src/test/cardapio.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CartProvider } from "../cart/CartContext";
import CardapioPage from "../pages/public/CardapioPage";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

const menu = {
  tenant: { name: "Pizzaria", slug: "menu1" },
  store: { id: "s1", name: "Loja", delivery_enabled: true, pickup_enabled: true },
  categories: [{ id: "c1", name: "Lanches", sort_order: 0 }],
  products: [
    { id: "p1", name: "X-Burger", description: null, price: "25.00", image_url: null,
      category_id: "c1", preparation_time_minutes: 10,
      modifiers: [{ id: "m1", group_name: "Ponto", modifier_name: "Ao ponto",
        price_delta: "0.00", required: true, min_selection: 1, max_selection: 1 }] },
    { id: "p2", name: "Refrigerante", description: null, price: "6.00", image_url: null,
      category_id: null, preparation_time_minutes: 0, modifiers: [] },
  ],
};

function renderPage() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <CartProvider>
        <MemoryRouter initialEntries={["/cardapio/menu1"]}>
          <Routes>
            <Route path="/cardapio/:slug" element={<CardapioPage />} />
          </Routes>
        </MemoryRouter>
      </CartProvider>
    </QueryClientProvider>,
  );
}

describe("CardapioPage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse(menu)));
  });

  it("lista produtos e filtra por busca", async () => {
    renderPage();
    await screen.findByText("X-Burger");
    await userEvent.type(screen.getByLabelText(/buscar/i), "refri");
    expect(screen.queryByText("X-Burger")).not.toBeInTheDocument();
    expect(screen.getByText("Refrigerante")).toBeInTheDocument();
  });

  it("adiciona produto sem adicionais direto ao carrinho", async () => {
    renderPage();
    await screen.findByText("Refrigerante");
    await userEvent.click(screen.getByRole("button", { name: /adicionar refrigerante/i }));
    expect(await screen.findByText(/1 item/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd frontend && npm test -- cardapio`
Expected: FAIL (páginas ausentes).

- [ ] **Step 3: Implementar as páginas e as rotas**

Criar `frontend/src/pages/public/CardapioPage.tsx`:

```tsx
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { publicApi } from "../../api/public";
import type { PublicMenu, PublicProduct } from "../../api/types";
import { useCart } from "../../cart/CartContext";
import ModifierDialog from "../../components/ModifierDialog";

export default function CardapioPage() {
  const { slug = "" } = useParams();
  const { add, count } = useCart();
  const [busca, setBusca] = useState("");
  const [categoria, setCategoria] = useState<string>("");
  const [aberto, setAberto] = useState<PublicProduct | null>(null);

  const { data, isLoading, isError } = useQuery<PublicMenu>({
    queryKey: ["cardapio", slug],
    queryFn: () => publicApi<PublicMenu>(`/public/${slug}/cardapio`),
    enabled: slug.length > 0,
  });

  const produtos = useMemo(() => {
    const list = data?.products ?? [];
    return list.filter(
      (p) =>
        (!categoria || p.category_id === categoria) &&
        p.name.toLowerCase().includes(busca.toLowerCase()),
    );
  }, [data, busca, categoria]);

  function adicionar(p: PublicProduct) {
    if (p.modifiers.length > 0) {
      setAberto(p);
      return;
    }
    add({ productId: p.id, name: p.name, unitPrice: p.price, quantity: 1, modifiers: [] });
  }

  if (isLoading) return <main className="p-8">Carregando…</main>;
  if (isError || !data) return <main className="p-8" role="alert">Erro ao carregar o cardápio.</main>;

  return (
    <main className="mx-auto max-w-2xl space-y-4 p-4 text-gray-900">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">{data.tenant.name}</h1>
          <p className="text-sm text-gray-500">{data.store.name}</p>
        </div>
        <Link to={`/cardapio/${slug}/carrinho`} className="rounded bg-blue-600 px-4 py-2 text-white">
          Carrinho ({count} {count === 1 ? "item" : "itens"})
        </Link>
      </header>

      <label className="block space-y-1">
        <span className="sr-only">Buscar</span>
        <input aria-label="Buscar" value={busca} onChange={(e) => setBusca(e.target.value)}
          placeholder="Buscar no cardápio" className="w-full rounded border px-3 py-2" />
      </label>

      {data.categories.length > 0 && (
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => setCategoria("")}
            className={`rounded border px-3 py-1 text-sm ${!categoria ? "bg-gray-900 text-white" : ""}`}>
            Todos
          </button>
          {data.categories.map((c) => (
            <button key={c.id} type="button" onClick={() => setCategoria(c.id)}
              className={`rounded border px-3 py-1 text-sm ${categoria === c.id ? "bg-gray-900 text-white" : ""}`}>
              {c.name}
            </button>
          ))}
        </div>
      )}

      <ul className="space-y-3">
        {produtos.map((p) => (
          <li key={p.id} className="flex items-center justify-between gap-4 rounded border p-4">
            <div>
              <p className="font-medium">{p.name}</p>
              {p.description && <p className="text-sm text-gray-500">{p.description}</p>}
              <p className="tabular-nums text-sm">R$ {Number(p.price).toFixed(2)}</p>
            </div>
            <button type="button" onClick={() => adicionar(p)}
              className="rounded bg-blue-600 px-3 py-2 text-sm text-white">
              Adicionar {p.name}
            </button>
          </li>
        ))}
        {produtos.length === 0 && <li className="text-sm text-gray-500">Nenhum produto encontrado.</li>}
      </ul>

      {aberto && (
        <ModifierDialog
          product={aberto}
          onCancel={() => setAberto(null)}
          onConfirm={(line) => {
            add(line);
            setAberto(null);
          }}
        />
      )}
    </main>
  );
}
```

Criar `frontend/src/pages/public/CarrinhoPage.tsx`:

```tsx
import { Link, useParams } from "react-router-dom";
import { useCart } from "../../cart/CartContext";

export default function CarrinhoPage() {
  const { slug = "" } = useParams();
  const { lines, setQuantity, remove, subtotal } = useCart();

  return (
    <main className="mx-auto max-w-2xl space-y-4 p-4">
      <header className="flex items-center justify-between">
        <h1 className="text-xl font-semibold">Carrinho</h1>
        <Link to={`/cardapio/${slug}`} className="text-sm text-blue-600">Continuar comprando</Link>
      </header>

      {lines.length === 0 ? (
        <p role="status" className="text-gray-600">Seu carrinho está vazio.</p>
      ) : (
        <>
          <ul className="space-y-3">
            {lines.map((l) => (
              <li key={l.key} className="flex items-center justify-between gap-4 rounded border p-3">
                <div>
                  <p className="font-medium">{l.name}</p>
                  {l.modifiers.length > 0 && (
                    <p className="text-xs text-gray-500">
                      {l.modifiers.map((m) => m.modifier_name).join(", ")}
                    </p>
                  )}
                  <p className="tabular-nums text-sm">R$ {Number(l.unitPrice).toFixed(2)}</p>
                </div>
                <div className="flex items-center gap-2">
                  <input type="number" min={1} value={l.quantity}
                    aria-label={`Quantidade de ${l.name}`}
                    onChange={(e) => setQuantity(l.key, Math.max(1, Number(e.target.value)))}
                    className="w-16 rounded border px-2 py-1" />
                  <button type="button" onClick={() => remove(l.key)}
                    className="text-sm text-red-600">Remover</button>
                </div>
              </li>
            ))}
          </ul>
          <div className="flex items-center justify-between border-t pt-4">
            <span className="font-medium">Subtotal</span>
            <span className="tabular-nums font-semibold">R$ {subtotal.toFixed(2)}</span>
          </div>
          <Link to={`/cardapio/${slug}/checkout`}
            className="block rounded bg-blue-600 px-4 py-2 text-center text-white">
            Finalizar pedido
          </Link>
        </>
      )}
    </main>
  );
}
```

Modificar `frontend/src/App.tsx`: importar as páginas e o `CartProvider`; adicionar antes do `{/* ... */}` das rotas protegidas:

```tsx
          <Route
            path="/cardapio/:slug"
            element={
              <CartProvider>
                <CardapioPage />
              </CartProvider>
            }
          />
          <Route
            path="/cardapio/:slug/carrinho"
            element={
              <CartProvider>
                <CarrinhoPage />
              </CartProvider>
            }
          />
```

> O `CartProvider` deriva o slug da URL, então cada rota pode envolver seu próprio provider; o estado persiste em `localStorage` por slug.

- [ ] **Step 4: Rodar e ver passar**

Run: `cd frontend && npm run typecheck && npm run lint && npm test -- cardapio`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/public/CardapioPage.tsx frontend/src/pages/public/CarrinhoPage.tsx frontend/src/App.tsx frontend/src/test/cardapio.test.tsx
git commit -m "feat(web): cardapio publico e carrinho"
```

### Task 10: CheckoutPage + PedidoPublicoPage

**Files:**
- Create: `frontend/src/pages/public/CheckoutPage.tsx`, `frontend/src/pages/public/PedidoPublicoPage.tsx`
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/test/checkout.test.tsx`, `frontend/src/test/pedido-publico.test.tsx`

**Interfaces:**
- Consumes: `publicApi`, `useCart`, tipos `PublicOrder`, `DeliveryEstimate`.
- Produces: rotas `/cardapio/:slug/checkout` e `/cardapio/:slug/pedido/:code` (fora do `Protected`).

- [ ] **Step 1: Escrever os testes que falham**

Criar `frontend/src/test/checkout.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CartProvider } from "../cart/CartContext";
import CheckoutPage from "../pages/public/CheckoutPage";
import PedidoPublicoPage from "../pages/public/PedidoPublicoPage";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

const order = {
  code: "SC-1", status: "received", fulfillment_type: "delivery",
  subtotal: "25.00", delivery_fee: "6.00", total: "31.00", eta_minutes: 35,
  created_at: "2026-10-10T12:00:00Z",
  items: [{ product_name: "X-Burger", quantity: 1, unit_price: "25.00", total_price: "25.00", modifiers: [] }],
};

describe("CheckoutPage", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.restoreAllMocks();
    localStorage.setItem("sc_cart:menu1", JSON.stringify([
      { key: "p1||", productId: "p1", name: "X-Burger", unitPrice: "25.00", quantity: 1, modifiers: [] },
    ]));
  });

  it("finaliza o pedido e mostra a confirmação", async () => {
    const calls: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
      const u = String(url);
      calls.push(`${init?.method ?? "GET"} ${u}`);
      if (u.includes("/entrega")) {
        return jsonResponse({ covered: true, zone_name: "Centro", delivery_fee: "6.00",
          min_order_value: "0.00", eta_minutes: 35 });
      }
      if (u.endsWith("/pedidos") && init?.method === "POST") return jsonResponse(order, 201);
      if (u.includes("/pedidos/SC-1")) return jsonResponse(order);
      throw new Error(`fetch inesperado: ${u}`);
    }));

    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={["/cardapio/menu1/checkout"]}>
          <CartProvider>
            <Routes>
              <Route path="/cardapio/:slug/checkout" element={<CheckoutPage />} />
              <Route path="/cardapio/:slug/pedido/:code" element={<PedidoPublicoPage />} />
            </Routes>
          </CartProvider>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await userEvent.type(screen.getByLabelText(/nome/i), "Ana");
    await userEvent.type(screen.getByLabelText(/telefone/i), "11999999999");
    await userEvent.type(screen.getByLabelText(/cep/i), "01001000");
    await userEvent.tab();
    await waitFor(() => expect(calls.some((c) => c.includes("/entrega"))).toBe(true));
    await userEvent.click(screen.getByRole("button", { name: /finalizar pedido/i }));
    await waitFor(() => expect(calls).toContain("POST /api/v1/public/menu1/pedidos"));
    expect(await screen.findByText("SC-1")).toBeInTheDocument();
  });
});
```

Criar `frontend/src/test/pedido-publico.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import PedidoPublicoPage from "../pages/public/PedidoPublicoPage";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

describe("PedidoPublicoPage", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("mostra status e itens do pedido", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({
      code: "SC-9", status: "preparing", fulfillment_type: "pickup",
      subtotal: "25.00", delivery_fee: "0.00", total: "25.00", eta_minutes: 0,
      created_at: "2026-10-10T12:00:00Z",
      items: [{ product_name: "X-Burger", quantity: 1, unit_price: "25.00", total_price: "25.00",
        modifiers: [{ id: "m1", group_name: "Ponto", modifier_name: "Ao ponto", price_delta: "0.00" }] }],
    })));

    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter initialEntries={["/cardapio/menu1/pedido/SC-9"]}>
          <Routes>
            <Route path="/cardapio/:slug/pedido/:code" element={<PedidoPublicoPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(await screen.findByText("SC-9")).toBeInTheDocument();
    expect(screen.getByText(/em preparo/i)).toBeInTheDocument();
    expect(screen.getByText(/ao ponto/i)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd frontend && npm test -- checkout pedido-publico`
Expected: FAIL (páginas ausentes).

- [ ] **Step 3: Implementar as páginas e as rotas**

Criar `frontend/src/pages/public/CheckoutPage.tsx`:

```tsx
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
    street: "", number: "", district: "", city: "", state: "",
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
      const found = await publicApi<{ street: string; district: string; city: string; state: string }>(
        `/public/${slug}/cep/${encodeURIComponent(cep)}`,
      );
      setAddress((a) => ({
        ...a, street: found.street, district: found.district,
        city: found.city, state: found.state,
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
            product_id: l.productId, quantity: l.quantity,
            notes: l.notes ?? null, modifier_ids: l.modifiers.map((m) => m.id),
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

  return (
    <main className="mx-auto max-w-2xl space-y-4 p-4">
      <h1 className="text-xl font-semibold">Finalizar pedido</h1>
      {error && <p role="alert" className="text-sm text-red-600">{error}</p>}
      <form onSubmit={submit} className="space-y-4">
        <label className="block space-y-1">
          <span className="text-sm">Nome</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required
            className="w-full rounded border px-3 py-2" />
        </label>
        <label className="block space-y-1">
          <span className="text-sm">Telefone</span>
          <input value={phone} onChange={(e) => setPhone(e.target.value)} required
            className="w-full rounded border px-3 py-2" />
        </label>
        <label className="block space-y-1">
          <span className="text-sm">Tipo de entrega</span>
          <select value={fulfillment} onChange={(e) => setFulfillment(e.target.value as "delivery" | "pickup")}
            className="w-full rounded border px-3 py-2">
            <option value="delivery">Entrega</option>
            <option value="pickup">Retirada</option>
          </select>
        </label>

        {fulfillment === "delivery" && (
          <>
            <label className="block space-y-1">
              <span className="text-sm">CEP</span>
              <input value={cep} onChange={(e) => setCep(e.target.value)} onBlur={onCepBlur}
                inputMode="numeric" required className="w-full rounded border px-3 py-2" />
            </label>
            {estimate && !estimate.covered && (
              <p role="alert" className="text-sm text-red-600">Não entregamos nesse CEP.</p>
            )}
            {estimate?.covered && (
              <p className="text-sm text-gray-600">
                {estimate.zone_name} · taxa R$ {fee.toFixed(2)} · entrega em ~{estimate.eta_minutes} min
              </p>
            )}
            <label className="block space-y-1">
              <span className="text-sm">Rua</span>
              <input value={address.street} onChange={(e) => setAddress({ ...address, street: e.target.value })}
                required className="w-full rounded border px-3 py-2" />
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="block space-y-1">
                <span className="text-sm">Número</span>
                <input value={address.number} onChange={(e) => setAddress({ ...address, number: e.target.value })}
                  required className="w-full rounded border px-3 py-2" />
              </label>
              <label className="block space-y-1">
                <span className="text-sm">Bairro</span>
                <input value={address.district}
                  onChange={(e) => setAddress({ ...address, district: e.target.value })}
                  className="w-full rounded border px-3 py-2" />
              </label>
            </div>
          </>
        )}

        <label className="block space-y-1">
          <span className="text-sm">Observações</span>
          <input value={notes} onChange={(e) => setNotes(e.target.value)}
            className="w-full rounded border px-3 py-2" />
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

        <button type="submit" disabled={sending || lines.length === 0 || abaixoMinimo}
          className="w-full rounded bg-blue-600 px-4 py-3 text-white disabled:opacity-50">
          {sending ? "Enviando…" : "Finalizar pedido"}
        </button>
      </form>
    </main>
  );
}
```

Criar `frontend/src/pages/public/PedidoPublicoPage.tsx`:

```tsx
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { publicApi } from "../../api/public";
import { type PublicOrder, STATUS_LABEL } from "../../api/types";

export default function PedidoPublicoPage() {
  const { slug = "", code = "" } = useParams();
  const { data, isLoading, isError } = useQuery<PublicOrder>({
    queryKey: ["pedido-publico", slug, code],
    queryFn: () => publicApi<PublicOrder>(`/public/${slug}/pedidos/${code}`),
    refetchInterval: 10000,
    enabled: slug.length > 0 && code.length > 0,
  });

  if (isLoading) return <main className="p-8">Carregando…</main>;
  if (isError || !data) return <main className="p-8" role="alert">Pedido não encontrado.</main>;

  return (
    <main className="mx-auto max-w-2xl space-y-4 p-4">
      <h1 className="text-xl font-semibold">Pedido {data.code}</h1>
      <p className="text-sm">
        Status: <strong>{STATUS_LABEL[data.status] ?? data.status}</strong>
        {data.eta_minutes ? ` · ~${data.eta_minutes} min` : ""}
      </p>
      <ul className="space-y-2">
        {data.items.map((it, idx) => (
          <li key={idx} className="rounded border p-3">
            <div className="flex justify-between">
              <span>{it.quantity}× {it.product_name}</span>
              <span className="tabular-nums">R$ {Number(it.total_price).toFixed(2)}</span>
            </div>
            {it.modifiers.length > 0 && (
              <p className="text-xs text-gray-500">
                {it.modifiers.map((m) => m.modifier_name).join(", ")}
              </p>
            )}
          </li>
        ))}
      </ul>
      <div className="space-y-1 border-t pt-4 text-sm">
        <div className="flex justify-between">
          <span>Subtotal</span>
          <span className="tabular-nums">R$ {Number(data.subtotal).toFixed(2)}</span>
        </div>
        <div className="flex justify-between">
          <span>Taxa de entrega</span>
          <span className="tabular-nums">R$ {Number(data.delivery_fee).toFixed(2)}</span>
        </div>
        <div className="flex justify-between font-semibold">
          <span>Total</span>
          <span className="tabular-nums">R$ {Number(data.total).toFixed(2)}</span>
        </div>
      </div>
      <Link to={`/cardapio/${slug}`} className="block text-center text-sm text-blue-600">
        Voltar ao cardápio
      </Link>
    </main>
  );
}
```

Modificar `frontend/src/App.tsx`: adicionar as duas rotas com `CartProvider`:

```tsx
          <Route
            path="/cardapio/:slug/checkout"
            element={
              <CartProvider>
                <CheckoutPage />
              </CartProvider>
            }
          />
          <Route
            path="/cardapio/:slug/pedido/:code"
            element={
              <CartProvider>
                <PedidoPublicoPage />
              </CartProvider>
            }
          />
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd frontend && npm run typecheck && npm run lint && npm test -- checkout pedido-publico`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/public/CheckoutPage.tsx frontend/src/pages/public/PedidoPublicoPage.tsx frontend/src/App.tsx frontend/src/test/checkout.test.tsx frontend/src/test/pedido-publico.test.tsx
git commit -m "feat(web): checkout com ViaCEP e acompanhamento do pedido"
```

---

### Task 11: ZonasPage interna + navegação

**Files:**
- Create: `frontend/src/pages/ZonasPage.tsx`
- Modify: `frontend/src/App.tsx`, `frontend/src/pages/DashboardPage.tsx`
- Test: `frontend/src/test/zonas.test.tsx`

**Interfaces:**
- Consumes: `api` (autenticada), tipos `Zone`, `ZoneCreate`.
- Produces: rota `/zonas` (protegida), link "Entregas" no Dashboard.

- [ ] **Step 1: Escrever o teste que falha**

Criar `frontend/src/test/zonas.test.tsx`:

```tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ZonasPage from "../pages/ZonasPage";

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

describe("ZonasPage", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("lista zonas e mostra estado vazio", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse([
      { id: "z1", store_id: "s1", name: "Centro",
        cep_ranges: [{ start: "01000000", end: "01999999" }],
        delivery_fee: "6.00", min_order_value: "10.00", eta_minutes: 35, active: true },
    ])));
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter><ZonasPage /></MemoryRouter>
      </QueryClientProvider>,
    );
    expect(await screen.findByText("Centro")).toBeInTheDocument();
    expect(screen.getByText(/6,00|6.00/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `cd frontend && npm test -- zonas`
Expected: FAIL (página ausente).

- [ ] **Step 3: Implementar a página e a navegação**

Criar `frontend/src/pages/ZonasPage.tsx`:

```tsx
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

      <form onSubmit={(e: FormEvent) => { e.preventDefault(); create.mutate(); }}
        className="grid gap-3 rounded border p-4 sm:grid-cols-3">
        <label className="space-y-1">
          <span className="text-sm">Nome da zona</span>
          <input value={name} onChange={(e) => setName(e.target.value)} required
            className="w-full rounded border px-3 py-2" />
        </label>
        <label className="space-y-1">
          <span className="text-sm">CEP inicial</span>
          <input value={cepStart} onChange={(e) => setCepStart(e.target.value)} required
            className="w-full rounded border px-3 py-2" />
        </label>
        <label className="space-y-1">
          <span className="text-sm">CEP final</span>
          <input value={cepEnd} onChange={(e) => setCepEnd(e.target.value)} required
            className="w-full rounded border px-3 py-2" />
        </label>
        <label className="space-y-1">
          <span className="text-sm">Taxa (R$)</span>
          <input value={fee} onChange={(e) => setFee(e.target.value)}
            className="w-full rounded border px-3 py-2" />
        </label>
        <label className="space-y-1">
          <span className="text-sm">Mínimo (R$)</span>
          <input value={minOrder} onChange={(e) => setMinOrder(e.target.value)}
            className="w-full rounded border px-3 py-2" />
        </label>
        <label className="space-y-1">
          <span className="text-sm">ETA (min)</span>
          <input value={eta} onChange={(e) => setEta(e.target.value)}
            className="w-full rounded border px-3 py-2" />
        </label>
        <button type="submit" className="rounded bg-blue-600 px-4 py-2 text-white sm:col-span-3">
          Criar zona
        </button>
      </form>

      {isLoading && <p className="text-gray-600">Carregando…</p>}
      {!isLoading && zonas.length === 0 && (
        <p role="status" className="text-gray-600">Nenhuma zona de entrega cadastrada.</p>
      )}
      <ul className="space-y-2">
        {zonas.map((z) => (
          <li key={z.id} className="flex items-center justify-between rounded border p-3">
            <div>
              <p className="font-medium">{z.name}</p>
              <p className="text-sm text-gray-600 tabular-nums">
                {z.cep_ranges[0]?.start}–{z.cep_ranges[0]?.end} · R$ {Number(z.delivery_fee).toFixed(2)}
                {" · "}~{z.eta_minutes} min
              </p>
            </div>
            <button type="button" onClick={() => toggle.mutate({ id: z.id, active: !z.active })}
              className="rounded border px-3 py-2 text-sm">
              {z.active ? "Desativar" : "Ativar"}
            </button>
          </li>
        ))}
      </ul>
    </main>
  );
}
```

Modificar `frontend/src/App.tsx`: importar `ZonasPage` e adicionar rota protegida:

```tsx
          <Route
            path="/zonas"
            element={
              <Protected>
                <ZonasPage />
              </Protected>
            }
          />
```

Modificar `frontend/src/pages/DashboardPage.tsx`: adicionar link:

```tsx
        <Link to="/zonas" className="rounded border px-4 py-2">
          Entregas
        </Link>
```

- [ ] **Step 4: Rodar e ver passar**

Run: `cd frontend && npm run typecheck && npm run lint && npm test -- zonas`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/ZonasPage.tsx frontend/src/App.tsx frontend/src/pages/DashboardPage.tsx frontend/src/test/zonas.test.tsx
git commit -m "feat(web): tela de zonas de entrega"
```

---

### Task 12: Verificação final da fatia

**Files:**
- Nenhum (apenas verificação).

- [ ] **Step 1: Suíte backend completa + lint + tipos**

Run: `cd backend && ../.venv/bin/ruff check . && ../.venv/bin/mypy . && ../.venv/bin/pytest -q`
Expected: tudo verde, sem regressões.

- [ ] **Step 2: Suíte frontend completa + tipos + lint + build**

Run: `cd frontend && npm run typecheck && npm run lint && npm test && npm run build`
Expected: tudo verde.

- [ ] **Step 3: Smoke manual end-to-end (opcional mas recomendado)**

Subir backend (`cd backend && ../.venv/bin/uvicorn app.main:app --reload`) e frontend (`cd frontend && npm run dev`), registrar um tenant, criar produto + adicional + zona, abrir `/cardapio/{slug}`, adicionar item, finalizar checkout com um CEP coberto e conferir que o pedido aparece em `/pedidos` e `/cozinha`.

- [ ] **Step 4: Revisão do branch**

Usar a skill `requesting-code-review` sobre `main..feat/cardapio-checkout`, aplicar correções apontadas e re-rodar as suítes.

- [ ] **Step 5: Finalizar a branch**

Usar a skill `finishing-a-development-branch` para merge `--no-ff` em `main`, push e limpeza da branch.

---

## Self-Review (preenchido pelo autor do plano)

- **Cobertura da spec:** cardápio público (T4), busca/filtro (T4), adicionais e regras min/max (T2, T6), ViaCEP (T5), taxa por zona + fallback sem zonas (T3, T5), pedido público com pagamento em dinheiro e idempotência (T6), PWA público e acompanhamento (T9, T10), admin de zonas (T11). Todas as fases E04/US cobertas.
- **Sem migration/new deps:** confirmado — só mapeamento ORM e `urllib.request` da stdlib.
- **Consistência de tipos:** `resolve_zone`, `get_public_db`, `create_public_order`, `public_order_out` são reusados exatamente como definidos; tipos frontend espelham os schemas Pydantic.
- **Nota de performance:** `_modifiers` por produto e `_to_out` por item são N+1 aceitáveis para o volume de cardápio; revisão pode pedir agregação — anotado em T4.

