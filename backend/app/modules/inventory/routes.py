from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_tenant_db, require_roles
from app.core.errors import DomainError
from app.core.tenant import Actor
from app.modules.catalog.models import Ingredient, StockMovement, Unit
from app.modules.catalog.routes import _require_store, _tenant_id
from app.modules.catalog.service import default_store, stock_totals
from app.modules.inventory.models import InventoryCount, InventoryCountItem, Loss, _now
from app.modules.inventory.schemas import (
    CountItemsIn,
    InventoryCountItemOut,
    InventoryCountOut,
    LossCreate,
    LossOut,
    MovementOut,
)
from app.modules.inventory.service import apply_movement, ensure_stock_level

router = APIRouter(tags=["estoque"])


@router.post("/perdas", status_code=status.HTTP_201_CREATED)
def create_loss(
    payload: LossCreate,
    actor: Actor = Depends(require_roles("owner", "manager", "buyer")),  # noqa: B008
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> LossOut:
    tid = _tenant_id(db)
    ing = db.get(Ingredient, payload.ingredient_id)
    if ing is None or str(ing.tenant_id) != str(tid):
        raise DomainError("not_found", "Insumo não encontrado.", status.HTTP_404_NOT_FOUND)
    store_id = (
        _require_store(db, tid, payload.store_id)
        if payload.store_id
        else default_store(db, tid).id
    )
    # custo real lido ANTES do movimento (apply_movement só altera custo em purchase).
    # garante o stock level para que a perda sobre insumo nunca estocado falhe com
    # erro de domínio (saldo insuficiente), não 404 no_stock_level.
    sl = ensure_stock_level(
        db, tenant_id=tid, store_id=store_id, ingredient_id=payload.ingredient_id
    )
    unit_cost = sl.average_cost
    apply_movement(
        db,
        tenant_id=tid,
        store_id=store_id,
        ingredient_id=payload.ingredient_id,
        type_="loss",
        quantity=-payload.quantity,
        unit_cost=unit_cost,
        reference_type="loss",
        reason=payload.reason,
        user_id=actor.id,
    )
    loss = Loss(
        tenant_id=tid,
        store_id=store_id,
        ingredient_id=payload.ingredient_id,
        quantity=payload.quantity.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP),
        cost=unit_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        reason=payload.reason,
        registered_by=actor.id,
    )
    if payload.occurred_at is not None:
        loss.occurred_at = payload.occurred_at
    db.add(loss)
    db.commit()
    return LossOut.model_validate(loss)


@router.get("/estoque/critico")
def estoque_critico(db: Session = Depends(get_tenant_db)) -> list[dict]:  # noqa: B008
    tid = _tenant_id(db)
    ings = db.scalars(
        select(Ingredient).where(
            Ingredient.tenant_id == tid, Ingredient.status == "active"
        )
    ).all()
    totals = stock_totals(db, [i.id for i in ings])
    units = {u.id: u.symbol for u in db.scalars(select(Unit).where(Unit.tenant_id == tid)).all()}
    out = []
    for ing in ings:
        current = totals.get(ing.id, Decimal("0"))
        if current < ing.minimum_stock:
            out.append({
                "ingredient_id": str(ing.id),
                "name": ing.name,
                "unit_symbol": units.get(ing.base_unit_id, ""),
                "stock_total": str(current),
                "minimum_stock": str(ing.minimum_stock),
            })
    return sorted(out, key=lambda c: Decimal(c["stock_total"]) - Decimal(c["minimum_stock"]))


@router.get("/estoque/movimentos")
def list_movimentos(
    db: Session = Depends(get_tenant_db),  # noqa: B008
    ingredient_id: UUID | None = None,
    tipo: str | None = None,
    limit: int = Query(50, ge=1, le=200),
) -> list[MovementOut]:
    tid = _tenant_id(db)
    q = select(StockMovement).where(StockMovement.tenant_id == tid)
    if ingredient_id is not None:
        q = q.where(StockMovement.ingredient_id == ingredient_id)
    if tipo is not None:
        q = q.where(StockMovement.type == tipo)
    q = q.order_by(StockMovement.created_at.desc()).limit(limit)
    rows = db.scalars(q).all()
    return [MovementOut.model_validate(m) for m in rows]


@router.post("/inventarios", status_code=status.HTTP_201_CREATED)
def open_inventory(
    actor: Actor = Depends(require_roles("owner", "manager")),  # noqa: B008
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> InventoryCountOut:
    tid = _tenant_id(db)
    store_id = default_store(db, tid).id
    ings = db.scalars(
        select(Ingredient).where(Ingredient.tenant_id == tid, Ingredient.status == "active")
    ).all()
    totals = stock_totals(db, [i.id for i in ings])
    count = InventoryCount(tenant_id=tid, store_id=store_id, status="open", started_by=actor.id)
    db.add(count)
    db.flush()
    for ing in ings:
        db.add(InventoryCountItem(
            tenant_id=tid,
            inventory_count_id=count.id,
            ingredient_id=ing.id,
            system_quantity=totals.get(ing.id, Decimal("0")),
        ))
    db.commit()
    return _count_out(db, count)


@router.post("/inventarios/{count_id}/itens")
def set_count_items(
    count_id: UUID,
    payload: CountItemsIn,
    actor: Actor = Depends(require_roles("owner", "manager")),  # noqa: B008
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> InventoryCountOut:
    tid = _tenant_id(db)
    count = db.get(InventoryCount, count_id)
    if count is None or str(count.tenant_id) != str(tid):
        raise DomainError("not_found", "Contagem não encontrada.", status.HTTP_404_NOT_FOUND)
    if count.status != "open":
        raise DomainError("invalid_state", "Contagem já finalizada.", status.HTTP_409_CONFLICT)
    items = {i.ingredient_id: i for i in db.scalars(
        select(InventoryCountItem).where(InventoryCountItem.inventory_count_id == count_id)
    ).all()}
    for it in payload.items:
        row = items.get(it.ingredient_id)
        if row is None:
            row = InventoryCountItem(
                tenant_id=tid,
                inventory_count_id=count_id,
                ingredient_id=it.ingredient_id,
                system_quantity=Decimal("0"),
            )
            db.add(row)
        row.counted_quantity = it.counted_quantity
    db.commit()
    return _count_out(db, count)


@router.post("/inventarios/{count_id}/fechar")
def close_inventory(
    count_id: UUID,
    actor: Actor = Depends(require_roles("owner", "manager")),  # noqa: B008
    db: Session = Depends(get_tenant_db),  # noqa: B008
) -> InventoryCountOut:
    tid = _tenant_id(db)
    count = db.get(InventoryCount, count_id)
    if count is None or str(count.tenant_id) != str(tid):
        raise DomainError("not_found", "Contagem não encontrada.", status.HTTP_404_NOT_FOUND)
    if count.status != "open":
        raise DomainError("invalid_state", "Contagem já finalizada.", status.HTTP_409_CONFLICT)
    items = db.scalars(select(InventoryCountItem).where(
        InventoryCountItem.inventory_count_id == count_id
    )).all()
    for row in items:
        if row.counted_quantity is None:
            row.counted_quantity = row.system_quantity
        row.difference = row.counted_quantity - row.system_quantity
        if row.difference != 0:
            sl = ensure_stock_level(
                db,
                tenant_id=tid,
                store_id=count.store_id,
                ingredient_id=row.ingredient_id,
            )
            apply_movement(
                db,
                tenant_id=tid,
                store_id=count.store_id,
                ingredient_id=row.ingredient_id,
                type_="adjustment",
                quantity=row.difference,
                unit_cost=sl.average_cost,
                reference_type="inventory_count",
                reference_id=count.id,
                reason="Ajuste de inventario",
                user_id=actor.id,
            )
            row.adjusted = True
    count.status = "closed"
    count.closed_at = _now()
    db.commit()
    return _count_out(db, count)


@router.get("/inventarios")
def list_inventories(db: Session = Depends(get_tenant_db)) -> list[InventoryCountOut]:  # noqa: B008
    tid = _tenant_id(db)
    rows = db.scalars(select(InventoryCount).where(
        InventoryCount.tenant_id == tid
    ).order_by(InventoryCount.started_at.desc())).all()
    return [_count_out(db, c) for c in rows]


@router.get("/inventarios/{count_id}")
def get_inventory(
    count_id: UUID, db: Session = Depends(get_tenant_db)  # noqa: B008
) -> InventoryCountOut:
    tid = _tenant_id(db)
    count = db.get(InventoryCount, count_id)
    if count is None or str(count.tenant_id) != str(tid):
        raise DomainError("not_found", "Contagem não encontrada.", status.HTTP_404_NOT_FOUND)
    return _count_out(db, count)


def _count_out(db: Session, count: InventoryCount) -> InventoryCountOut:
    items = db.scalars(select(InventoryCountItem).where(
        InventoryCountItem.inventory_count_id == count.id
    )).all()
    return InventoryCountOut(
        id=count.id,
        store_id=count.store_id,
        status=count.status,
        started_at=count.started_at,
        closed_at=count.closed_at,
        items=[InventoryCountItemOut.model_validate(it) for it in items],
    )
