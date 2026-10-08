from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.modules.catalog.models import StockLevel, Store, Unit

SYMBOL_TYPE = {"kg": "mass", "g": "mass", "ml": "volume", "l": "volume", "un": "count"}


def get_or_create_unit(db: Session, tenant_id: UUID, symbol: str) -> Unit:
    unit = db.scalar(select(Unit).where(Unit.tenant_id == tenant_id, Unit.symbol == symbol))
    if unit is None:
        unit = Unit(
            tenant_id=tenant_id, name=symbol, symbol=symbol,
            type=SYMBOL_TYPE.get(symbol, "other"),
        )
        db.add(unit)
        try:
            db.flush()
        except IntegrityError:
            # corrida: outra request criou a unit entre o check e o flush — reusa.
            db.rollback()
            existing = db.scalar(
                select(Unit).where(Unit.tenant_id == tenant_id, Unit.symbol == symbol)
            )
            if existing is None:
                raise
            unit = existing
    return unit


def default_store(db: Session, tenant_id: UUID) -> Store:
    store = db.scalar(
        select(Store)
        .where(Store.tenant_id == tenant_id, Store.status == "active")
        .order_by(Store.created_at)
        .limit(1)
    )
    if store is None:
        raise DomainError("no_store", "Nenhuma loja ativa para o tenant.")
    return store


def stock_total(db: Session, ingredient_id: UUID) -> Decimal:
    total = db.scalar(
        select(func.sum(StockLevel.quantity)).where(StockLevel.ingredient_id == ingredient_id)
    )
    return total or Decimal("0")


def stock_totals(db: Session, ingredient_ids: list[UUID]) -> dict[UUID, Decimal]:
    if not ingredient_ids:
        return {}
    rows = db.execute(
        select(StockLevel.ingredient_id, func.sum(StockLevel.quantity))
        .where(StockLevel.ingredient_id.in_(ingredient_ids))
        .group_by(StockLevel.ingredient_id)
    ).all()
    return {i: Decimal(q or 0) for i, q in rows}
