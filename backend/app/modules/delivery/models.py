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
