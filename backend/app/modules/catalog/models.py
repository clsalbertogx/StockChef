from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


def _now() -> Any:
    return datetime.now(UTC)


class Store(Base):
    __tablename__ = "stores"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Unit(Base):
    __tablename__ = "units"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String)
    symbol: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String, default="count")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
