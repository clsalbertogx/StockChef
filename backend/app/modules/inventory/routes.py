from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_tenant_db, require_roles
from app.core.errors import DomainError
from app.core.tenant import Actor
from app.modules.catalog.models import Ingredient, StockLevel
from app.modules.catalog.routes import _require_store, _tenant_id
from app.modules.catalog.service import default_store
from app.modules.inventory.models import Loss
from app.modules.inventory.schemas import LossCreate, LossOut
from app.modules.inventory.service import apply_movement

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
    # custo real lido ANTES do movimento (apply_movement só altera custo em purchase)
    sl = db.scalar(
        select(StockLevel).where(
            StockLevel.store_id == store_id,
            StockLevel.ingredient_id == payload.ingredient_id,
        )
    )
    unit_cost = sl.average_cost if sl else Decimal("0")
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
