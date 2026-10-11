from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.modules.catalog.models import StockLevel, StockMovement


def ensure_stock_level(
    db: Session,
    *,
    tenant_id: UUID | str,
    store_id: UUID,
    ingredient_id: UUID,
    average_cost: Decimal = Decimal("0"),
) -> StockLevel:
    sl = db.scalar(
        select(StockLevel)
        .where(StockLevel.store_id == store_id, StockLevel.ingredient_id == ingredient_id)
        .with_for_update()
    )
    if sl is None:
        # corrida: SELECT FOR UPDATE não trava linha inexistente; o savepoint
        # absorve o unique violation e a releitura pega o nível criado por outra tx.
        try:
            with db.begin_nested():
                db.add(
                    StockLevel(
                        tenant_id=tenant_id,
                        store_id=store_id,
                        ingredient_id=ingredient_id,
                        quantity=Decimal("0"),
                        average_cost=average_cost,
                    )
                )
        except IntegrityError:
            pass
        sl = db.scalar(
            select(StockLevel)
            .where(StockLevel.store_id == store_id, StockLevel.ingredient_id == ingredient_id)
            .with_for_update()
        )
        assert sl is not None
    return sl


def weighted_average_cost(
    current_qty: Decimal, current_avg: Decimal, received_qty: Decimal, received_cost: Decimal
) -> Decimal:
    if received_qty <= 0:
        raise ValueError("received_qty deve ser > 0")
    if current_qty <= 0:
        return received_cost.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    new_avg = (
        (current_qty * current_avg + received_qty * received_cost)
        / (current_qty + received_qty)
    )
    return new_avg.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def apply_movement(
    db: Session,
    *,
    tenant_id: UUID | str,
    store_id: UUID,
    ingredient_id: UUID,
    type_: str,
    quantity: Decimal,
    unit_cost: Decimal,
    reference_type: str | None = None,
    reference_id: UUID | None = None,
    reason: str | None = None,
    idempotency_key: str | None = None,
    user_id: UUID | None = None,
) -> StockMovement:
    if idempotency_key:
        existing = db.scalar(
            select(StockMovement).where(StockMovement.idempotency_key == idempotency_key)
        )
        if existing is not None:
            return existing

    sl = db.scalar(
        select(StockLevel)
        .where(StockLevel.store_id == store_id, StockLevel.ingredient_id == ingredient_id)
        .with_for_update()
    )
    if sl is None:
        raise DomainError(
            "no_stock_level", "Insumo sem nível de estoque nesta loja.", 404
        )

    new_qty = sl.quantity + quantity
    if new_qty < 0:
        raise DomainError(
            "invalid_stock_operation",
            "Operação resultaria em estoque negativo.",
            409,
        )

    if type_ == "purchase":
        sl.average_cost = weighted_average_cost(
            sl.quantity, sl.average_cost, quantity, unit_cost
        )
    sl.quantity = new_qty

    mov = StockMovement(
        tenant_id=str(tenant_id),
        store_id=store_id,
        ingredient_id=ingredient_id,
        type=type_,
        quantity=quantity,
        unit_cost=unit_cost,
        reference_type=reference_type,
        reference_id=reference_id,
        reason=reason,
        idempotency_key=idempotency_key,
        user_id=user_id,
    )
    db.add(mov)
    db.flush()
    return mov
