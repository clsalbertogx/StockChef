from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint
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


class Driver(Base):
    __tablename__ = "drivers"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str] = mapped_column(String, nullable=False)
    document: Mapped[str | None] = mapped_column(String, default=None)
    vehicle_type: Mapped[str] = mapped_column(
        String, nullable=False, default="motorcycle"
    )
    plate: Mapped[str | None] = mapped_column(String, default=None)
    payment_model: Mapped[str] = mapped_column(
        String, nullable=False, default="per_delivery"
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    rating_average: Mapped[Decimal] = mapped_column(
        Numeric(4, 2), nullable=False, default=Decimal("5.00")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        UniqueConstraint("tenant_id", "phone", name="drivers_tenant_id_phone_key"),
    )


class Delivery(Base):
    __tablename__ = "deliveries"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    order_id: Mapped[UUID] = mapped_column(
        ForeignKey("orders.id"), nullable=False, unique=True
    )
    driver_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("drivers.id"), default=None, nullable=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    picked_up_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    eta_minutes: Mapped[int | None] = mapped_column(default=None)
    route_hint: Mapped[dict] = mapped_column(JSONB, default=dict)
    occurrence: Mapped[str | None] = mapped_column(String, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ProofOfDelivery(Base):
    __tablename__ = "proof_of_deliveries"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[UUID] = mapped_column(nullable=False)
    delivery_id: Mapped[UUID] = mapped_column(
        ForeignKey("deliveries.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String, nullable=False)
    file_url: Mapped[str | None] = mapped_column(String, default=None)
    received_by: Mapped[str | None] = mapped_column(String, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)