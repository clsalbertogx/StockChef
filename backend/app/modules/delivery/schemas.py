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
