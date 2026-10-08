from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _now() -> Any:
    return datetime.now(UTC)


class Loss(Base):
    __tablename__ = "losses"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    store_id: Mapped[UUID] = mapped_column(ForeignKey("stores.id"), nullable=False)
    ingredient_id: Mapped[UUID] = mapped_column(ForeignKey("ingredients.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    cost: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0"))
    reason: Mapped[str] = mapped_column(String, nullable=False, default="other")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    registered_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class InventoryCount(Base):
    __tablename__ = "inventory_counts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    store_id: Mapped[UUID] = mapped_column(ForeignKey("stores.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, default="open")
    started_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"), default=None)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    notes: Mapped[str | None] = mapped_column(String, default=None)


class InventoryCountItem(Base):
    __tablename__ = "inventory_count_items"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    inventory_count_id: Mapped[UUID] = mapped_column(
        ForeignKey("inventory_counts.id"), nullable=False
    )
    ingredient_id: Mapped[UUID] = mapped_column(ForeignKey("ingredients.id"), nullable=False)
    system_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=Decimal("0"))
    counted_quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), default=None)
    difference: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), default=None)
    adjusted: Mapped[bool] = mapped_column(default=False)
    note: Mapped[str | None] = mapped_column(String, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
