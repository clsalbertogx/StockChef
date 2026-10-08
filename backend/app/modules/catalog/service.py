from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
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
        db.flush()
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
        select(StockLevel.quantity).where(StockLevel.ingredient_id == ingredient_id)
    )
    return total or Decimal("0")
